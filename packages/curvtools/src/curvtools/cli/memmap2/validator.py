#!/usr/bin/env python3
"""
Memory map TOML validator - checks for common errors and constraints
"""
from curvpyutils.toml_utils import read_toml_file
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class ValidationSeverity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"

@dataclass
class ValidationRule:
    """A validation rule with description and check function"""
    id: str
    severity: ValidationSeverity
    description: str
    check_func: callable

@dataclass
class ValidationError:
    """A validation error with location and message"""
    rule_id: str
    severity: ValidationSeverity
    message: str
    toml_path: str
    value: Any = None

class MemoryMapValidator:
    def __init__(self):
        self.rules = []
        self._define_rules()

    def _define_rules(self):
        """Define all validation rules"""

        # Rule 1: No overlapping address ranges
        self.rules.append(ValidationRule(
            id="no_overlaps",
            severity=ValidationSeverity.ERROR,
            description="Address ranges must not overlap with any other ranges",
            check_func=self._check_no_overlaps
        ))

        # Rule 2: Cacheable addresses must be contiguous starting from address 0
        self.rules.append(ValidationRule(
            id="cacheable_contiguous",
            severity=ValidationSeverity.ERROR,
            description="All cacheable addresses must form a contiguous block starting from address 0x00000000. Non-cacheable addresses must start after all cacheable addresses.",
            check_func=self._check_cacheable_contiguous
        ))

        # Rule 3: All addresses must start on word boundaries (4-byte aligned)
        self.rules.append(ValidationRule(
            id="word_aligned",
            severity=ValidationSeverity.ERROR,
            description="All address ranges (start and end+1) must be 4-byte aligned",
            check_func=self._check_word_aligned
        ))

        # Rule 4: Cacheable ranges must start on cacheline boundaries and be multiples of cacheline size
        self.rules.append(ValidationRule(
            id="cacheable_cacheline_aligned",
            severity=ValidationSeverity.ERROR,
            description="Cacheable ranges must start on 64-byte cacheline boundaries and have sizes that are multiples of 64 bytes",
            check_func=self._check_cacheable_cacheline_aligned
        ))

        # Rule 5: End addresses must be >= start addresses
        self.rules.append(ValidationRule(
            id="valid_range",
            severity=ValidationSeverity.ERROR,
            description="End address must be greater than or equal to start address",
            check_func=self._check_valid_range
        ))

        # Rule 6: Known access values
        self.rules.append(ValidationRule(
            id="valid_access_values",
            severity=ValidationSeverity.ERROR,
            description="Access field must be one of: 'ro', 'wo', 'rw'",
            check_func=self._check_valid_access_values
        ))

        # Rule 7: No overlaps within register sets
        self.rules.append(ValidationRule(
            id="no_register_overlaps",
            severity=ValidationSeverity.ERROR,
            description="Registers within the same register set must not overlap",
            check_func=self._check_no_register_overlaps
        ))

        # Rule 8: No unnamed ranges
        self.rules.append(ValidationRule(
            id="no_unnamed_ranges",
            severity=ValidationSeverity.ERROR,
            description="All ranges must have non-empty names",
            check_func=self._check_no_unnamed_ranges
        ))

        # Rule 9: Register/buffer sections must have corresponding range
        self.rules.append(ValidationRule(
            id="register_sections_have_range",
            severity=ValidationSeverity.ERROR,
            description="Register and buffer sections must have a corresponding named range in the parent slave",
            check_func=self._check_register_sections_have_range
        ))

        # Rule 10: Registers/buffers must be contained within their range
        self.rules.append(ValidationRule(
            id="regs_buffers_in_range",
            severity=ValidationSeverity.ERROR,
            description="All registers and buffers must be fully contained within their corresponding named range",
            check_func=self._check_regs_buffers_in_range
        ))

        # Rule 11: Cacheable must be set on all ranges
        self.rules.append(ValidationRule(
            id="cacheable_must_be_set_on_ranges",
            severity=ValidationSeverity.ERROR,
            description="Cacheable must be set on all ranges",
            check_func=self._check_cacheable_must_be_set_on_ranges
        ))

        # Rule 12: Cacheable cannot be set on buffers or registers
        self.rules.append(ValidationRule(
            id="cacheable_cannot_be_set_on_buffers_or_registers",
            severity=ValidationSeverity.ERROR,
            description="Cacheable cannot be set on buffers or registers",
            check_func=self._check_cacheable_cannot_be_set_on_buffers_or_registers
        ))

        # Rule 13:  access must be set to rw/ro/wo on ranges with no children
        self.rules.append(ValidationRule(
            id="access_must_be_set_on_ranges_with_no_children",
            severity=ValidationSeverity.ERROR,
            description="Access must be set to rw/ro/wo on ranges with no children",
            check_func=self._check_access_must_be_set_on_ranges_with_no_children
        ))

        # Rule 14:  access cannot be set on ranges with children
        self.rules.append(ValidationRule(
            id="access_cannot_be_set_on_ranges_with_children",
            severity=ValidationSeverity.ERROR,
            description="Access cannot be set on ranges with children",
            check_func=self._check_access_cannot_be_set_on_ranges_with_children
        ))

        # Rule 15:  accesss must always be set on all registers and buffers
        self.rules.append(ValidationRule(
            id="access_must_always_be_set_on_registers_and_buffers",
            severity=ValidationSeverity.ERROR,
            description="Access must always be set on all registers and buffers",
            check_func=self._check_access_must_always_be_set_on_registers_and_buffers
        ))

        # Rule 16: Registers must use 'addr' and not 'start'/'end'
        self.rules.append(ValidationRule(
            id="registers_must_have_addr",
            severity=ValidationSeverity.ERROR,
            description="Registers must use 'addr' and must not use 'start'/'end'",
            check_func=self._check_registers_must_have_addr
        ))

        # # Rule 16: Registers cannot be children of a range in TOML (new schema)
        # self.rules.append(ValidationRule(
        #     id="registers_cannot_be_children_of_a_range_in_toml",
        #     severity=ValidationSeverity.ERROR,
        #     description="registers cannot be children of a range in TOML",
        #     check_func=self._check_registers_cannot_be_children_of_a_range_in_toml
        # ))
        #
        # # Rule 17: Buffers cannot be children of a range in TOML (new schema)
        # self.rules.append(ValidationRule(
        #     id="buffers_cannot_be_children_of_a_range_in_toml",
        #     severity=ValidationSeverity.ERROR,
        #     description="buffers cannot be children of a range in TOML",
        #     check_func=self._check_buffers_cannot_be_children_of_a_range_in_toml
        # ))

        # Rule 17: Registers and buffers must be direct children of a slave in TOML
        self.rules.append(ValidationRule(
            id="registers_and_buffers_must_be_direct_children_of_a_slave_in_toml",
            severity=ValidationSeverity.ERROR,
            description="registers and buffers must be direct children of a slave in TOML",
            check_func=self._check_registers_and_buffers_must_be_direct_children_of_a_slave_in_toml
        ))

    def collect_all_ranges(self, memory_map: Dict, xlen: int = 32, include_contained_items: bool = True) -> List[Tuple[str, Dict]]:
        """Collect all address ranges with their TOML paths
        Args:
            memory_map: The memory map dictionary
            xlen: XLEN value for register size calculation
            include_contained_items: If True, include registers/buffers found under slave-level namespaces.
                                     If False, only include top-level ranges (for global overlap checking).
        """
        bytes_per_register = xlen // 8
        results: List[Tuple[str, Dict]] = []

        slaves = memory_map.get('slaves', {}) or {}
        for slave_key, slave_cfg in slaves.items():
            # Top-level ranges (always included)
            for i, range_cfg in enumerate(slave_cfg.get('ranges', []) or []):
                results.append((f"slaves.{slave_key}.ranges[{i}]", range_cfg))

            if not include_contained_items:
                continue

            # New schema: registers and buffers live at the slave level; traverse them to collect leaf items
            def collect_items(root: Dict[str, Any], base_path: str, is_registers: bool) -> None:
                if not isinstance(root, dict):
                    return
                for item_key, item_val in root.items():
                    if not isinstance(item_val, dict):
                        continue
                    next_path = f"{base_path}.{item_key}" if base_path else item_key
                    # Leaf item detection differs for registers vs buffers
                    if is_registers and 'addr' in item_val and 'access' in item_val:
                        start = item_val['addr']
                        end = start + bytes_per_register - 1
                        results.append((f"slaves.{slave_key}.registers.{next_path}", {
                            'start': start,
                            'end': end,
                            'access': item_val['access']
                        }))
                    elif (not is_registers) and 'start' in item_val and 'end' in item_val and 'access' in item_val:
                        # buffers must have explicit end
                        results.append((f"slaves.{slave_key}.buffers.{next_path}", {
                            'start': item_val['start'],
                            'end': item_val['end'],
                            'access': item_val['access']
                        }))
                    else:
                        collect_items(item_val, next_path, is_registers)

            collect_items(slave_cfg.get('registers', {}), "", True)
            collect_items(slave_cfg.get('buffers', {}), "", False)

        return results

    def _check_no_overlaps(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check for overlapping address ranges (only top-level ranges, not contained items)"""
        errors = []
        ranges = self.collect_all_ranges(memory_map, xlen, include_contained_items=False)

        for i, (path1, range1) in enumerate(ranges):
            start1, end1 = range1['start'], range1['end']

            for j, (path2, range2) in enumerate(ranges):
                if i >= j:  # Don't check against self or previously checked pairs
                    continue

                start2, end2 = range2['start'], range2['end']

                # Check for overlap
                if not (end1 < start2 or end2 < start1):
                    errors.append(ValidationError(
                        rule_id="no_overlaps",
                        severity=ValidationSeverity.ERROR,
                        message=f"Address range {start1:08x}-{end1:08x} overlaps with {start2:08x}-{end2:08x}",
                        toml_path=f"{path1} and {path2}",
                        value=(range1, range2)
                    ))

        return errors

    def _check_no_register_overlaps(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check for overlapping registers within the same register set"""
        errors = []

        # Use the parsed structure from collect_all_ranges
        from .collect_all_ranges import collect_all_ranges as get_nested_ranges
        slaves = get_nested_ranges(memory_map.get('slaves', {}), xlen, debug_print_ranges=False)

        for slave_info in slaves:
            slave_name = slave_info['name']

            for range_info in slave_info['ranges']:
                registers = range_info.get('registers', [])

                if len(registers) > 1:  # Only check for overlaps if there are multiple registers
                    register_ranges = []
                    for reg_info in registers:
                        # Registers now carry 'addr'. Fallback to 'start' for robustness.
                        start = reg_info.get('start', reg_info.get('addr'))
                        end = reg_info.get('end', start + (xlen // 8) - 1)
                        register_ranges.append((f"slaves.{slave_name}.{reg_info['full_name']}", start, end))

                    # Check for overlaps within this register set
                    errors.extend(self._check_overlaps_in_group(register_ranges, f"slaves.{slave_name}.{range_info['name'] or 'unnamed'}.registers"))

        return errors

    def _check_overlaps_in_group(self, register_ranges: List[Tuple[str, int, int]], group_path: str) -> List[ValidationError]:
        """Check for overlaps within a single group of register ranges"""
        errors = []

        for i, (path1, start1, end1) in enumerate(register_ranges):
            for j, (path2, start2, end2) in enumerate(register_ranges):
                if i >= j:  # Don't check against self or previously checked pairs
                    continue

                # Check for overlap
                if not (end1 < start2 or end2 < start1):
                    errors.append(ValidationError(
                        rule_id="no_register_overlaps",
                        severity=ValidationSeverity.ERROR,
                        message=f"Register {start1:08x}-{end1:08x} overlaps with {start2:08x}-{end2:08x}",
                        toml_path=f"{path1} and {path2}",
                        value=((path1, start1, end1), (path2, start2, end2))
                    ))

        return errors

    def _normalize_range_name(self, name: str) -> str:
        """Convert range name to TOML path segment (lowercase, spaces/special chars to underscore)"""
        import re
        # Lowercase and replace spaces and special chars with underscore
        return re.sub(r'[^a-z0-9]+', '_', name.lower())

    def _get_slave_ranges_by_name(self, slave_config: Dict) -> Dict[str, List[Dict]]:
        """Group slave ranges by their normalized names"""
        ranges_by_name = {}
        if 'ranges' in slave_config:
            for range_config in slave_config['ranges']:
                name = range_config['name']
                normalized = self._normalize_range_name(name)
                if normalized not in ranges_by_name:
                    ranges_by_name[normalized] = []
                ranges_by_name[normalized].append(range_config)
        return ranges_by_name

    def _check_no_unnamed_ranges(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check that all ranges have non-empty names"""
        errors = []

        for slave_name, slave_config in memory_map.get('slaves', {}).items():
            if 'ranges' in slave_config:
                for i, range_config in enumerate(slave_config['ranges']):
                    if not range_config['name'].strip():
                        errors.append(ValidationError(
                            rule_id="no_unnamed_ranges",
                            severity=ValidationSeverity.ERROR,
                            message="Range names cannot be empty",
                            toml_path=f"slaves.{slave_name}.ranges[{i}].name",
                            value=range_config['name']
                        ))

        return errors

    def _check_register_sections_have_range(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check that slaves with registers/buffers have at least one range defined"""
        errors = []

        for slave_name, slave_config in memory_map.get('slaves', {}).items():
            has_ranges = 'ranges' in slave_config and len(slave_config['ranges']) > 0
            # New schema: registers/buffers are properties of the slave (possibly nested under those namespaces)
            has_registers_or_buffers = isinstance(slave_config.get('registers'), dict) or isinstance(slave_config.get('buffers'), dict)

            if has_registers_or_buffers and not has_ranges:
                errors.append(ValidationError(
                    rule_id="register_sections_have_range",
                    severity=ValidationSeverity.ERROR,
                    message=f"Slave '{slave_name}' has registers/buffers but no ranges defined",
                    toml_path=f"slaves.{slave_name}",
                    value=None
                ))

        return errors

    def _check_regs_buffers_in_range(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check that all slave-level registers and buffers are contained within some defined range"""
        errors: List[ValidationError] = []
        bytes_per_register = xlen // 8

        for slave_key, slave_cfg in memory_map.get('slaves', {}).items():
            # Build list of all ranges for this slave
            defined_ranges = []
            for r in slave_cfg.get('ranges', []) or []:
                defined_ranges.append((r['start'], r['end']))

            # Helper: check containment in any range
            def contained(start: int, end: int) -> bool:
                for rs, re in defined_ranges:
                    if rs <= start and end <= re:
                        return True
                return False

            # Traverse registers
            def traverse_items(root: Dict[str, Any], path_prefix: str, is_registers: bool) -> None:
                if not isinstance(root, dict):
                    return
                for k, v in root.items():
                    if not isinstance(v, dict):
                        continue
                    next_path = f"{path_prefix}.{k}" if path_prefix else k
                    if is_registers and 'addr' in v and 'access' in v:
                        start = v['addr']
                        end = start + bytes_per_register - 1
                        if not contained(start, end):
                            errors.append(ValidationError(
                                rule_id="regs_buffers_in_range",
                                severity=ValidationSeverity.ERROR,
                                message=f"Register at '{'slaves.' + slave_key + '.registers.' + next_path}' is not contained in any range",
                                toml_path=f"slaves.{slave_key}.registers.{next_path}",
                                value=v
                            ))
                    elif (not is_registers) and 'start' in v and 'end' in v and 'access' in v:
                        start = v['start']
                        end = v['end']
                        if not contained(start, end):
                            errors.append(ValidationError(
                                rule_id="regs_buffers_in_range",
                                severity=ValidationSeverity.ERROR,
                                message=f"Buffer at '{'slaves.' + slave_key + '.buffers.' + next_path}' is not contained in any range",
                                toml_path=f"slaves.{slave_key}.buffers.{next_path}",
                                value=v
                            ))
                    else:
                        traverse_items(v, next_path, is_registers)

            traverse_items(slave_cfg.get('registers', {}), "", True)
            traverse_items(slave_cfg.get('buffers', {}), "", False)

        return errors

    # def _check_registers_cannot_be_children_of_a_range_in_toml(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
    #     """Ensure that TOML does not use [slaves.<slave>.<range_name>.registers] sections"""
    #     errors: List[ValidationError] = []
    #     for slave_key, slave_cfg in memory_map.get('slaves', {}).items():
    #         # Build set of normalized range names
    #         normalized_names = set()
    #         for r in slave_cfg.get('ranges', []) or []:
    #             normalized_names.add(self._normalize_range_name(r['name']))
    #         # Look for child tables whose key matches a range name and that contain 'registers'
    #         for key, val in slave_cfg.items():
    #             if key in ('name', 'ranges', 'registers', 'buffers'):
    #                 continue
    #             if key in normalized_names and isinstance(val, dict) and isinstance(val.get('registers'), dict):
    #                 errors.append(ValidationError(
    #                     rule_id="registers_cannot_be_children_of_a_range_in_toml",
    #                     severity=ValidationSeverity.ERROR,
    #                     message="registers cannot be children of a range in TOML",
    #                     toml_path=f"slaves.{slave_key}.{key}.registers",
    #                     value=None
    #                 ))
    #     return errors

    # def _check_buffers_cannot_be_children_of_a_range_in_toml(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
    #     """Ensure that TOML does not use [slaves.<slave>.<range_name>.buffers] sections"""
    #     errors: List[ValidationError] = []
    #     for slave_key, slave_cfg in memory_map.get('slaves', {}).items():
    #         # Build set of normalized range names
    #         normalized_names = set()
    #         for r in slave_cfg.get('ranges', []) or []:
    #             normalized_names.add(self._normalize_range_name(r['name']))
    #         # Look for child tables whose key matches a range name and that contain 'buffers'
    #         for key, val in slave_cfg.items():
    #             if key in ('name', 'ranges', 'registers', 'buffers'):
    #                 continue
    #             if key in normalized_names and isinstance(val, dict) and isinstance(val.get('buffers'), dict):
    #                 errors.append(ValidationError(
    #                     rule_id="buffers_cannot_be_children_of_a_range_in_toml",
    #                     severity=ValidationSeverity.ERROR,
    #                     message="buffers cannot be children of a range in TOML",
    #                     toml_path=f"slaves.{slave_key}.{key}.buffers",
    #                     value=None
    #                 ))
    #     return errors

    def _check_registers_and_buffers_must_be_direct_children_of_a_slave_in_toml(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Ensure that TOML does not use 
            [slaves.<slave>.<range_name>.registers] or 
            [slaves.<slave>.<range_name>.buffers] or
            [slaves.<slave>.<nonsensical_key>.registers.buffers] or
            [slaves.<slave>.<nonsensical_key>.buffers.registers]
        sections"""
        errors: List[ValidationError] = []
        for slave_key, slave_cfg in memory_map.get('slaves', {}).items():
            # Look for child tables whose key is not 'name', 'ranges', 'registers', or 'buffers'
            for key, val in slave_cfg.items():
                if key in ('name', 'ranges', 'registers', 'buffers'):
                    continue
                if isinstance(val, dict):
                    errors.append(ValidationError(
                        rule_id="registers_and_buffers_must_be_direct_children_of_a_slave_in_toml",
                        severity=ValidationSeverity.ERROR,
                        message="registers and buffers must be direct children of a slave in TOML",
                        toml_path=f"slaves.{slave_key}.{key}",
                        value=None
                    ))
        return errors


    def _check_cacheable_contiguous(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check that cacheable addresses are contiguous from 0"""
        errors = []
        # Only consider top-level ranges for cacheable contiguity; registers/buffers
        # do not participate in cacheability decisions under the new schema.
        ranges = self.collect_all_ranges(memory_map, xlen, include_contained_items=False)

        # Find all cacheable ranges
        cacheable_ranges = []
        non_cacheable_ranges = []

        for path, range_config in ranges:
            if range_config.get('cacheable', False):
                cacheable_ranges.append((path, range_config))
            else:
                non_cacheable_ranges.append((path, range_config))

        if not cacheable_ranges:
            return errors  # No cacheable ranges, that's fine

        # Check that cacheable ranges start from 0 and are contiguous
        cacheable_ranges.sort(key=lambda x: x[1]['start'])

        # First cacheable range should start at 0
        first_path, first_range = cacheable_ranges[0]
        if first_range['start'] != 0:
            errors.append(ValidationError(
                rule_id="cacheable_contiguous",
                severity=ValidationSeverity.ERROR,
                message=f"First cacheable range must start at address 0x00000000, but starts at 0x{first_range['start']:08x}",
                toml_path=first_path,
                value=first_range
            ))

        # Check contiguous coverage of cacheable ranges
        expected_end = 0
        for path, range_config in cacheable_ranges:
            if range_config['start'] != expected_end:
                errors.append(ValidationError(
                    rule_id="cacheable_contiguous",
                    severity=ValidationSeverity.ERROR,
                    message=f"Cacheable ranges must be contiguous. Expected start 0x{expected_end:08x}, got 0x{range_config['start']:08x}",
                    toml_path=path,
                    value=range_config
                ))
                break
            expected_end = range_config['end'] + 1

        # Check that non-cacheable ranges start after cacheable ranges
        highest_cacheable = max(r['end'] for _, r in cacheable_ranges) if cacheable_ranges else -1

        for path, range_config in non_cacheable_ranges:
            if range_config['start'] <= highest_cacheable:
                errors.append(ValidationError(
                    rule_id="cacheable_contiguous",
                    severity=ValidationSeverity.ERROR,
                    message=f"Non-cacheable range starts at 0x{range_config['start']:08x} but must start after highest cacheable address 0x{highest_cacheable:08x}",
                    toml_path=path,
                    value=range_config
                ))

        return errors

    def _check_cacheable_must_be_set_on_ranges(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Ensure that every top-level range has an explicit cacheable flag set"""
        errors: List[ValidationError] = []

        for slave_name, slave_config in memory_map.get('slaves', {}).items():
            if 'ranges' not in slave_config:
                continue
            for i, range_config in enumerate(slave_config['ranges']):
                if 'cacheable' not in range_config:
                    errors.append(ValidationError(
                        rule_id="cacheable_must_be_set_on_ranges",
                        severity=ValidationSeverity.ERROR,
                        message="Cacheable must be set on all ranges",
                        toml_path=f"slaves.{slave_name}.ranges[{i}].cacheable",
                        value=range_config
                    ))

        return errors

    def _check_cacheable_cannot_be_set_on_buffers_or_registers(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Ensure that no register or buffer sets a cacheable flag"""
        errors: List[ValidationError] = []

        def traverse(section: Dict[str, Any], path_segments: List[str], context: str = "") -> None:
            for key, value in section.items():
                if not isinstance(value, dict):
                    continue
                new_path = path_segments + [key]
                if key in ("registers", "buffers"):
                    # Traverse inside registers/buffers namespaces
                    traverse_registers_or_buffers(value, new_path, key)
                else:
                    traverse(value, new_path, context)

        def traverse_registers_or_buffers(section: Dict[str, Any], path_segments: List[str], kind: str) -> None:
            for item_key, item_val in section.items():
                if not isinstance(item_val, dict):
                    continue
                # Leaf items: registers have 'addr'; buffers have 'start' and 'end'
                if (kind == 'registers' and 'addr' in item_val and 'access' in item_val) or (kind == 'buffers' and 'start' in item_val and 'end' in item_val and 'access' in item_val):
                    if 'cacheable' in item_val:
                        errors.append(ValidationError(
                            rule_id="cacheable_cannot_be_set_on_buffers_or_registers",
                            severity=ValidationSeverity.ERROR,
                            message=f"'cacheable' cannot be set on {kind}",
                            toml_path=".".join(path_segments + [item_key, 'cacheable']),
                            value=item_val
                        ))
                else:
                    # Nested namespaces (e.g., registers.uart.*)
                    traverse_registers_or_buffers(item_val, path_segments + [item_key], kind)

        traverse(memory_map.get('slaves', {}), ["slaves"]) 

        return errors

    def _collect_child_items_for_normalized_range(self, slave_config: Dict[str, Any], normalized_name: str, xlen: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Collect ALL registers and buffers defined anywhere under a slave (new schema).
        We traverse the entire slave config and whenever we see a 'registers' or 'buffers'
        table, we collect its leaf items. Range membership is determined later by address containment."""
        registers: List[Dict[str, Any]] = []
        buffers: List[Dict[str, Any]] = []
        bytes_per_register = xlen // 8

        def collect_items_namespace(section: Dict[str, Any], acc: List[Dict[str, Any]], is_registers: bool) -> None:
            for item_key, item_val in section.items():
                if not isinstance(item_val, dict):
                    continue
                if is_registers and 'addr' in item_val and 'access' in item_val:
                    start = item_val['addr']
                    end = start + bytes_per_register - 1
                    acc.append({'start': start, 'end': end})
                elif (not is_registers) and 'start' in item_val and 'end' in item_val and 'access' in item_val:
                    acc.append({'start': item_val['start'], 'end': item_val['end']})
                else:
                    collect_items_namespace(item_val, acc, is_registers)

        def traverse(section: Dict[str, Any]) -> None:
            if not isinstance(section, dict):
                return
            for key, val in section.items():
                if not isinstance(val, dict):
                    continue
                if key == 'registers':
                    collect_items_namespace(val, registers, True)
                elif key == 'buffers':
                    collect_items_namespace(val, buffers, False)
                else:
                    traverse(val)

        traverse(slave_config)
        return registers, buffers

    def _check_access_must_be_set_on_ranges_with_no_children(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """If a range has no child registers/buffers within its [start,end], it must set access"""
        errors: List[ValidationError] = []

        for slave_key, slave_config in memory_map.get('slaves', {}).items():
            if 'ranges' not in slave_config:
                continue
            for i, range_config in enumerate(slave_config['ranges']):
                # New schema: collect all child items for the slave; determine membership by containment
                regs, bufs = self._collect_child_items_for_normalized_range(slave_config, "", xlen)
                start = range_config['start']
                end = range_config['end']
                # Determine if any child falls within this specific range bounds
                def child_in_range(items: List[Dict[str, Any]]) -> bool:
                    for it in items:
                        if start <= it['start'] <= it['end'] <= end:
                            return True
                    return False

                has_children = child_in_range(regs) or child_in_range(bufs)

                if not has_children:
                    if 'access' not in range_config:
                        errors.append(ValidationError(
                            rule_id="access_must_be_set_on_ranges_with_no_children",
                            severity=ValidationSeverity.ERROR,
                            message="Access must be set on ranges with no children",
                            toml_path=f"slaves.{slave_key}.ranges[{i}].access",
                            value=range_config
                        ))

        return errors

    def _check_access_cannot_be_set_on_ranges_with_children(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """If a range has any child registers/buffers within its [start,end], it must not set access"""
        errors: List[ValidationError] = []

        for slave_key, slave_config in memory_map.get('slaves', {}).items():
            if 'ranges' not in slave_config:
                continue
            for i, range_config in enumerate(slave_config['ranges']):
                # New schema: collect all child items for the slave; determine membership by containment
                regs, bufs = self._collect_child_items_for_normalized_range(slave_config, "", xlen)
                start = range_config['start']
                end = range_config['end']

                def child_in_range(items: List[Dict[str, Any]]) -> bool:
                    for it in items:
                        if start <= it['start'] <= it['end'] <= end:
                            return True
                    return False

                has_children = child_in_range(regs) or child_in_range(bufs)

                if has_children and 'access' in range_config:
                    errors.append(ValidationError(
                        rule_id="access_cannot_be_set_on_ranges_with_children",
                        severity=ValidationSeverity.ERROR,
                        message="Access cannot be set on ranges with children",
                        toml_path=f"slaves.{slave_key}.ranges[{i}].access",
                        value=range_config
                    ))

        return errors

    def _check_access_must_always_be_set_on_registers_and_buffers(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Ensure all registers and buffers explicitly set access"""
        errors: List[ValidationError] = []

        def traverse(section: Dict[str, Any], path_segments: List[str]) -> None:
            for key, value in section.items():
                if not isinstance(value, dict):
                    continue
                new_path = path_segments + [key]
                if key in ("registers", "buffers"):
                    traverse_items_namespace(value, new_path, key)
                else:
                    traverse(value, new_path)

        def traverse_items_namespace(section: Dict[str, Any], path_segments: List[str], kind: str) -> None:
            for item_key, item_val in section.items():
                if not isinstance(item_val, dict):
                    continue
                is_reg = (kind == 'registers' and 'addr' in item_val)
                is_buf = (kind == 'buffers' and 'start' in item_val)
                if is_reg or is_buf:
                    if 'access' not in item_val:
                        errors.append(ValidationError(
                            rule_id="access_must_always_be_set_on_registers_and_buffers",
                            severity=ValidationSeverity.ERROR,
                            message=f"Access must be set on all {kind}",
                            toml_path=".".join(path_segments + [item_key, 'access']),
                            value=item_val
                        ))
                else:
                    traverse_items_namespace(item_val, path_segments + [item_key], kind)

        traverse(memory_map.get('slaves', {}), ["slaves"]) 

        return errors

    def _check_word_aligned(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check that all addresses are word-aligned (4-byte boundaries)"""
        errors = []
        ranges = self.collect_all_ranges(memory_map, xlen, include_contained_items=False)

        for path, range_config in ranges:
            start, end = range_config['start'], range_config['end']

            if start % 4 != 0:
                errors.append(ValidationError(
                    rule_id="word_aligned",
                    severity=ValidationSeverity.ERROR,
                    message=f"Start address 0x{start:08x} is not word-aligned (must be multiple of 4)",
                    toml_path=path,
                    value=range_config
                ))

            if (end + 1) % 4 != 0:
                errors.append(ValidationError(
                    rule_id="word_aligned",
                    severity=ValidationSeverity.ERROR,
                    message=f"End address 0x{end:08x} + 1 is not word-aligned (must be multiple of 4)",
                    toml_path=path,
                    value=range_config
                ))

        return errors

    def _check_cacheable_cacheline_aligned(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check cacheable ranges are cacheline-aligned and multiples of cacheline size"""
        errors = []
        ranges = self.collect_all_ranges(memory_map, xlen)
        CACHELINE_SIZE = 64  # 16 words * 4 bytes/word

        for path, range_config in ranges:
            if not range_config.get('cacheable', False):
                continue

            start, end = range_config['start'], range_config['end']
            size = end - start + 1

            # Check alignment
            if start % CACHELINE_SIZE != 0:
                errors.append(ValidationError(
                    rule_id="cacheable_cacheline_aligned",
                    severity=ValidationSeverity.ERROR,
                    message=f"Cacheable range start 0x{start:08x} is not cacheline-aligned (must be multiple of {CACHELINE_SIZE})",
                    toml_path=path,
                    value=range_config
                ))

            # Check size is multiple of cacheline
            if size % CACHELINE_SIZE != 0:
                errors.append(ValidationError(
                    rule_id="cacheable_cacheline_aligned",
                    severity=ValidationSeverity.ERROR,
                    message=f"Cacheable range size {size} bytes is not a multiple of cacheline size ({CACHELINE_SIZE} bytes)",
                    toml_path=path,
                    value=range_config
                ))

        return errors

    def _check_valid_range(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check that end >= start"""
        errors = []
        ranges = self.collect_all_ranges(memory_map, xlen)

        for path, range_config in ranges:
            start, end = range_config['start'], range_config['end']
            if end < start:
                errors.append(ValidationError(
                    rule_id="valid_range",
                    severity=ValidationSeverity.ERROR,
                    message=f"End address 0x{end:08x} is less than start address 0x{start:08x}",
                    toml_path=path,
                    value=range_config
                ))

        return errors

    def _check_valid_access_values(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Check access values are valid"""
        errors = []
        ranges = self.collect_all_ranges(memory_map, xlen)
        valid_access = {'ro', 'wo', 'rw'}

        for path, range_config in ranges:
            # Only validate when 'access' is explicitly present. Missing 'access'
            # may be valid on ranges with children (checked by other rules).
            if 'access' not in range_config:
                continue
            access = range_config.get('access', '')
            if access not in valid_access:
                errors.append(ValidationError(
                    rule_id="valid_access_values",
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid access value '{access}'. Must be one of: {', '.join(sorted(valid_access))}",
                    toml_path=path,
                    value=range_config
                ))

        return errors

    def validate(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Run all validation rules"""
        all_errors = []

        for rule in self.rules:
            try:
                if 'memory_map' in rule.check_func.__code__.co_varnames:
                    errors = rule.check_func(memory_map, xlen)
                else:
                    errors = rule.check_func(memory_map)
                all_errors.extend(errors)
            except Exception as e:
                all_errors.append(ValidationError(
                    rule_id=rule.id,
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation rule failed with exception: {e}",
                    toml_path="",
                    value=None
                ))

        return all_errors

    def _check_registers_must_have_addr(self, memory_map: Dict, xlen: int) -> List[ValidationError]:
        """Ensure registers use 'addr' and not 'start'/'end'"""
        errors: List[ValidationError] = []

        def traverse(section: Dict[str, Any], path_segments: List[str]) -> None:
            for key, value in section.items():
                if not isinstance(value, dict):
                    continue
                new_path = path_segments + [key]
                if key == 'registers':
                    traverse_registers(value, new_path)
                else:
                    traverse(value, new_path)

        def traverse_registers(section: Dict[str, Any], path_segments: List[str]) -> None:
            for item_key, item_val in section.items():
                if not isinstance(item_val, dict):
                    continue
                # Identify leaf register definitions (have addr/start/access), otherwise recurse
                if ('addr' in item_val) or ('start' in item_val) or ('access' in item_val):
                    if 'addr' in item_val:
                        if 'start' in item_val or 'end' in item_val:
                            errors.append(ValidationError(
                                rule_id="registers_must_have_addr",
                                severity=ValidationSeverity.ERROR,
                                message="Registers must use 'addr' and not 'start'/'end'",
                                toml_path=".".join(path_segments + [item_key]),
                                value=item_val
                            ))
                    else:
                        errors.append(ValidationError(
                            rule_id="registers_must_have_addr",
                            severity=ValidationSeverity.ERROR,
                            message="Registers must use 'addr'",
                            toml_path=".".join(path_segments + [item_key, 'addr']),
                            value=item_val
                        ))
                else:
                    traverse_registers(item_val, path_segments + [item_key])

        traverse(memory_map.get('slaves', {}), ["slaves"])
        return errors

    def get_highest_cacheable_address(self, memory_map: Dict, xlen: int) -> int:
        """Calculate highest cacheable address for SV generation"""
        ranges = self.collect_all_ranges(memory_map, xlen)
        cacheable_ranges = [r for _, r in ranges if r.get('cacheable', False)]

        if not cacheable_ranges:
            return 0

        return max(r['end'] for r in cacheable_ranges)

def validate_toml_file(toml_file: str, xlen: int, quiet: bool = False) -> tuple[bool, int]:
    """Validate a TOML file and return (success, highest_cacheable_addr)"""
    try:
        memory_map = read_toml_file(toml_file)
    except Exception as e:
        print(f"ERROR: Failed to parse TOML file: {e}")
        return False, 0

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen)

    if not quiet:
        print(f"Validating {toml_file}...")

    if errors:
        for error in errors:
            rule = next(r for r in validator.rules if r.id == error.rule_id)
            print(f"{error.severity.value}: {error.message}")
            print(f"  Rule: {rule.description}")
            print(f"  Location: {error.toml_path}")
            print()
        return False, 0
    else:
        highest_cacheable = validator.get_highest_cacheable_address(memory_map, xlen)
        if not quiet:
            print(f"✓ Validation passed! Highest cacheable address: 0x{highest_cacheable:08x}")
        return True, highest_cacheable
