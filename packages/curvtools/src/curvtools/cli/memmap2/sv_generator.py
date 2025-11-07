#!/usr/bin/env python3
"""
SystemVerilog generator for memory maps
"""
import re
import os
from curvpyutils.toml_utils import read_toml_file
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from .collect_all_ranges import collect_all_ranges
from .docs_generator.comment_generator import generate_memmap_comment, generate_registers_and_sub_ranges_comment
from curvpyutils.str_utils import insert_underscores

class RegisterData:
    """Simple register data class for template rendering"""
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr

    def get_name_snake_case(self, unused):
        """Convert name to snake_case (simplified)"""
        import re
        return re.sub(r'[^a-zA-Z0-9]+', '_', self.name.lower())

    def get_addr_hex_str(self, unused1, unused2, unused3):
        """Return hex string of register address"""
        return f"32'h{self.addr:08x}"

class SlaveTemplateData:
    """Class to hold slave data for Jinja2 template rendering"""
    def __init__(self, slave_name, bitpos, enum_width, read_legal_exprs, write_legal_exprs, registers=None):
        self.slave_name = slave_name
        self.slave_name_ljust = slave_name.upper()
        self.bitpos = bitpos
        self.one_hot = 1 << bitpos
        self.read_legal_exprs = read_legal_exprs
        self.write_legal_exprs = write_legal_exprs
        self.registers = registers or []

    def format_one_hot(self, one_hot_val, width):
        return f"{width}'b{one_hot_val:0{width}b}"

def merge_contiguous_ranges(ranges):
    """Merge contiguous ranges to reduce OR conditions"""
    if not ranges:
        return []

    # Sort by start address
    sorted_ranges = sorted(ranges, key=lambda x: x['start'])

    # Merge contiguous ranges
    merged = [sorted_ranges[0]]
    for current in sorted_ranges[1:]:
        last = merged[-1]
        # Check if current range is contiguous with the last merged range
        if last['end'] + 1 == current['start']:
            # Merge: extend the last range to include the current one
            last['end'] = current['end']
        else:
            # Not contiguous, add as new range
            merged.append(current)

    return merged

def generate_range_condition_with_gte_lte(range_config: Dict[str, int], use_dollar_unsigned: bool = True, addr_varname_str: str = "addr") -> str:
    """Generate a simple range condition for SV"""
    start = range_config['start']
    end = range_config['end']
    addr_varname_str = f"$unsigned({addr_varname_str})" if use_dollar_unsigned else addr_varname_str
    if (start != 0):
        return f"({addr_varname_str} >= 32'h{start:08x} && {addr_varname_str} <= 32'h{end:08x})"
    else:
        return f"({addr_varname_str} <= 32'h{end:08x})"

def generate_range_condition_with_inside(range_configs: List[Dict[str, int]], use_dollar_unsigned: bool = True, addr_varname_str: str = "addr") -> str:
    """Generate a simple range condition for SV"""
    verilog_ranges: List[str] = []
    addr_varname_str = f"$unsigned({addr_varname_str})" if use_dollar_unsigned else addr_varname_str
    for range_config in range_configs:
        start = range_config['start']
        end = range_config['end']
        left_brace = "{"; right_brace = "}";
        verilog_ranges.append( f"[32'h{start:08x} : 32'h{end:08x}]")
    verilog_ranges_joined = '\n                ' + ",\n                ".join(verilog_ranges)
    ret_str = f"({addr_varname_str} inside {left_brace}{verilog_ranges_joined}" + f"{right_brace})"
    return ret_str

def generate_access_condition(ranges: List[Dict[str, int]], use_inside_range_condition: bool = False, addr_varname_str: str = "addr") -> List[str]:
    """Generate list of condition strings for access conditions with contiguous range merging"""
    # The ranges passed in are already filtered by access type, so we just merge them
    merged_ranges = merge_contiguous_ranges(ranges)

    # Generate conditions for merged ranges
    if not use_inside_range_condition:
        conditions = []
        for r in merged_ranges:
            condition = generate_range_condition_with_gte_lte(r, addr_varname_str=addr_varname_str)
            conditions.append(condition)

        # For multiple conditions, create a single OR expression
        if len(conditions) > 1:
            return [" ||\n        ".join(conditions)]
        elif conditions:
            return conditions
        else:
            return ["1'b0"]
    else:
        if len(merged_ranges) == 0:
            return ["1'b0"]
        else:
            return [generate_range_condition_with_inside(merged_ranges, addr_varname_str=addr_varname_str)]

def collect_accessible_ranges(ranges, xlen: int):
    """Collect all accessible address ranges based on individual register/buffer permissions"""
    accessible_ranges = {'read': [], 'write': []}
    bytes_per_register = xlen // 8

    for range_info in ranges:
        # Process registers in this range
        for reg in range_info.get('registers', []):
            reg_start = reg['addr']
            # registers are single-word addresses; derive end from xlen
            reg_end = reg_start + bytes_per_register - 1
            access = reg['access']

            # Add to read ranges if readable
            if access in ['ro', 'rw']:
                accessible_ranges['read'].append({'start': reg_start, 'end': reg_end})

            # Add to write ranges if writable
            if access in ['wo', 'rw']:
                accessible_ranges['write'].append({'start': reg_start, 'end': reg_end})

        # Process buffers in this range
        for buf in range_info.get('buffers', []):
            buf_start = buf['start']
            buf_end = buf['end']
            access = buf['access']

            # Add to read ranges if readable
            if access in ['ro', 'rw']:
                accessible_ranges['read'].append({'start': buf_start, 'end': buf_end})

            # Add to write ranges if writable
            if access in ['wo', 'rw']:
                accessible_ranges['write'].append({'start': buf_start, 'end': buf_end})

        # If there are no nested registers or buffers, fall back to the parent range access
        has_registers = bool(range_info.get('registers'))
        has_buffers = bool(range_info.get('buffers'))
        if not has_registers and not has_buffers:
            parent_access = range_info.get('access', 'rw')
            start_addr = range_info['start']
            end_addr = range_info['end']
            if parent_access in ['ro', 'rw']:
                accessible_ranges['read'].append({'start': start_addr, 'end': end_addr})
            if parent_access in ['wo', 'rw']:
                accessible_ranges['write'].append({'start': start_addr, 'end': end_addr})

    return accessible_ranges

def generate_access_function(slave_name: str, ranges: List[Dict[str, int]], xlen: int, use_inside_range_condition: bool = False, addr_varname_str: str = "addr") -> Dict[str, List[str]]:
    """Generate structure for read/write legal function for a slave"""
    # Collect all accessible ranges based on individual register/buffer permissions
    accessible_ranges = collect_accessible_ranges(ranges, xlen)

    # Generate conditions for read access
    read_conditions = generate_access_condition(accessible_ranges['read'], use_inside_range_condition, addr_varname_str)

    # Generate conditions for write access
    write_conditions = generate_access_condition(accessible_ranges['write'], use_inside_range_condition, addr_varname_str)

    return {
        'slave_name': slave_name,
        'read_legal_exprs': read_conditions,
        'write_legal_exprs': write_conditions
    }

def generate_sv_package_file(memory_map, highest_cacheable, xlen, template_file: Optional[str] = None, use_inside_range_condition: bool = False):
    """Generate complete SystemVerilog package using Jinja2 template"""
    from jinja2 import Environment, FileSystemLoader, Template

    slaves = collect_all_ranges(memory_map['slaves'], xlen, debug_print_ranges=False)

    # Calculate enum width (number of slaves)
    enum_width = len(slaves)

    # Generate access function structures for each slave
    slave_access_functions = []
    for i, slave_info in enumerate(slaves):
        slave_name = slave_info['name']
        access_func_data = generate_access_function(slave_name, slave_info['ranges'], xlen, use_inside_range_condition)

        # Collect all registers from all ranges for this slave
        registers = []
        for range_info in slave_info['ranges']:
            for reg in range_info.get('registers', []):
                registers.append(RegisterData(reg['name'], reg['addr']))

        # Create template data object
        slave_template_data = SlaveTemplateData(
            slave_name=slave_name,
            bitpos=i,
            enum_width=enum_width,
            read_legal_exprs=access_func_data['read_legal_exprs'],
            write_legal_exprs=access_func_data['write_legal_exprs'],
            registers=registers
        )

        slave_access_functions.append(slave_template_data)

    # Generate comment strings
    memmap_comment_str = generate_memmap_comment(slaves, with_header=True)
    registers_and_sub_ranges_comment_str = generate_registers_and_sub_ranges_comment(slaves, xlen)

    # Generate highest cacheable address string
    highest_addr_cacheable_str = f"32'h{insert_underscores(format(highest_cacheable, '08X'))}"

    # Generate region invalid one hot string
    wb_slave_none_value_str = f"{enum_width}'b{format(0, f'0{enum_width}b')}"

    # Build merged top-level address ranges per slave for selection function
    slave_addr_ranges = []
    # Maintain order consistent with 'slaves' list collected above
    for slave_info in slaves:
        slave_name = slave_info['name']
        # find original slave_config by matching name or key
        original_slave_key = None
        for key, cfg in memory_map.get('slaves', {}).items():
            if key == slave_name or cfg.get('name') == slave_name:
                original_slave_key = key
                break
        merged = []
        if original_slave_key is not None:
            cfg = memory_map['slaves'][original_slave_key]
            top_ranges = []
            for r in cfg.get('ranges', []) or []:
                # Skip unnamed (shouldn't exist due to validation)
                top_ranges.append({'start': r['start'], 'end': r['end']})
            merged = merge_contiguous_ranges(top_ranges)
        slave_addr_ranges.append({'slave_name': slave_name, 'ranges': merged})

    # Prepare range/buffer data with snake_case helpers for template
    import re as _re
    def _snake(s: str) -> str:
        return _re.sub(r'[^a-zA-Z0-9]+', '_', s.lower())

    slaves_collected = []
    for s in slaves:
        ranges_prepared = []
        for r in s.get('ranges', []):
            buffers_prepared = []
            for b in r.get('buffers', []) or []:
                buffers_prepared.append({
                    'name': b['name'],
                    'name_snake': _snake(b['name']),
                    'start': b['start'],
                    'end': b['end'],
                })
            ranges_prepared.append({
                'name': r['name'],
                'name_snake': _snake(r['name']),
                'start': r['start'],
                'end': r['end'],
                'buffers': buffers_prepared,
            })
        slaves_collected.append({
            'name': s['name'],
            'ranges': ranges_prepared,
        })

    # Prepare template data (initial, before composing sub-templates)
    template_data = {
        'slaves': slave_access_functions,  # This should be formatted for the template
        'enum_width': enum_width,
        'num_slaves': len(slaves),
        'memmap_comment_str': memmap_comment_str,
        'registers_and_sub_ranges_comment_str': registers_and_sub_ranges_comment_str,
        'highest_addr_cacheable_str': highest_addr_cacheable_str,
        'wb_slave_none_value_str': wb_slave_none_value_str,
        'script_name': os.path.basename(__file__),
        'slave_addr_ranges': slave_addr_ranges,
        'use_inside_range_condition': use_inside_range_condition,
        'slaves_collected': slaves_collected,
    }

    # Use Jinja2 template (either from file or string)
    if template_file is not None and os.path.isfile(template_file):
        # template_file is a file path
        template_dir = os.path.dirname(os.path.abspath(template_file))
        env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        template = env.get_template(os.path.basename(template_file))
    elif template_file is not None and isinstance(template_file, str):
        # template_file is a template string
        template = Template(template_file)
    else:
        # use default template
        from jinja2 import Environment, DictLoader
        from .default_template import (
            DEFAULT_JINJA2_TEMPLATE,
            DEFAULT_GET_SLAVE_SEL_FUNC_OR_CHAIN,
            DEFAULT_GET_SLAVE_SEL_FUNC_INSIDE,
            DEFAULT_RANGE_TEST_FUNCTIONS_GTE_LTE,
            DEFAULT_RANGE_TEST_FUNCTIONS_INSIDE,
        )
        env = Environment(
            loader=DictLoader({
                'main.sv.j2': DEFAULT_JINJA2_TEMPLATE,
                'get_slave_sel_or_chain.sv.j2': DEFAULT_GET_SLAVE_SEL_FUNC_OR_CHAIN,
                'get_slave_sel_inside.sv.j2': DEFAULT_GET_SLAVE_SEL_FUNC_INSIDE,
                'range_buffer_tests_gte_lte.sv.j2': DEFAULT_RANGE_TEST_FUNCTIONS_GTE_LTE,
                'range_buffer_tests_inside.sv.j2': DEFAULT_RANGE_TEST_FUNCTIONS_INSIDE,
            }),
            trim_blocks=True,
            lstrip_blocks=True
        )
        template = env.get_template('main.sv.j2')
    return template.render(**template_data)

def generate_sv_from_toml(toml_file: str, output_file: str, skip_validation: bool = False, xlen: int = 32, template_file: Optional[str] = None, use_inside_range_condition: bool = False):
    """Generate SV file from TOML config"""
    from .validator import validate_toml_file

    if not skip_validation:
        success, highest_cacheable = validate_toml_file(toml_file, quiet=True, xlen=xlen)
        if not success:
            print("Validation failed, aborting SV generation")
            return False
    else:
        # Load and calculate highest cacheable without full validation
        try:
            memory_map = read_toml_file(toml_file)
            from .validator import MemoryMapValidator
            validator = MemoryMapValidator()
            highest_cacheable = validator.get_highest_cacheable_address(memory_map, xlen)
        except Exception as e:
            print(f"ERROR: Failed to parse TOML file: {e}")
            return False

    memory_map = read_toml_file(toml_file)
    sv_code = generate_sv_package_file(memory_map, highest_cacheable, xlen, template_file, use_inside_range_condition)

    if output_file == '-':
        print(sv_code)
    else:
        with open(output_file, 'w') as f:
            f.write(sv_code)
        print(f"Wrote to {output_file}")

    return True
