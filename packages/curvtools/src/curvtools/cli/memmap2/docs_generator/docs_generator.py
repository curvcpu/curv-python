#!/usr/bin/env python3
"""
Documentation generator for memory maps using rich tables
"""
from curvpyutils.toml_utils import read_toml_file
from typing import Dict, List, Tuple, Any, Callable
from rich.table import Table
from rich.console import Console
from rich.text import Text
from pathlib import Path
import re
import sys
import os

def from_make_tower_import_make_tower() -> Callable[[List[Dict[str, Any]]], str]:
    """Import make_tower() from the correct path and return it as a callable"""
    if (Path(os.getcwd()) != Path(os.path.dirname(__file__))):
        from .make_tower import make_tower
    else:
        sys.path.insert(0, Path(os.path.dirname(__file__)).parent)
        from make_tower import make_tower
    return make_tower

def from_collect_all_ranges_import_collect_all_ranges() -> Callable[[Dict, int, bool], List[Dict[str, Any]]]:
    """Import collect_all_ranges() from the correct path and return it as a callable"""
    if (Path(os.getcwd()) != Path(os.path.dirname(__file__))):
        from ..collect_all_ranges import collect_all_ranges
    else:
        new_import_path = Path(os.path.dirname(__file__)).parent
        sys.path.insert(0, str(new_import_path))
        from collect_all_ranges import collect_all_ranges
    return collect_all_ranges

def format_address(addr: int) -> str:
    """Format address as 8-digit hex"""
    return f"{addr:08x}"

def format_size(size_bytes: int) -> str:
    """Format size in appropriate units"""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes // (1024 * 1024)}mb"
    elif size_bytes >= 1024:
        return f"{size_bytes // 1024}kb"
    else:
        return f"{size_bytes}"

def format_access(access: str) -> str:
    """Format access type for display"""
    access_map = {
        'rw': 'R/W',
        'ro': 'R/O',
        'wo': 'W/O',
        ' - ': ' - '
    }
    return access_map.get(access, access.upper())

def collect_register_ranges(memory_map: Dict, xlen: int) -> Dict[str, List[Dict]]:
    """Collect registers and buffers organized by slave using nested structure"""
    collect_all_ranges = from_collect_all_ranges_import_collect_all_ranges()
    registers = {}
    buffers = {}

    # Get all slaves with their ranges
    slaves = collect_all_ranges(memory_map.get('slaves', {}), xlen, debug_print_ranges=not False)

    for slave_info in slaves:
        slave_name = slave_info['name']
        slave_ranges = slave_info['ranges']

        slave_regs = []
        slave_bufs = []

        # Extract registers and buffers from the nested structure
        for range_info in slave_ranges:
            # Add registers from this range
            if 'registers' in range_info:
                print("registers: ", range_info['registers'])
                for reg_info in range_info['registers']:
                    slave_regs.append({
                        'name': reg_info['full_name'],  # Use dotted name for docs
                        'start': reg_info['addr'],
                        'end': reg_info['addr'] + xlen // 8 - 1,
                        'access': reg_info['access'],
                        'size': xlen // 8,
                        'range': range_info['name']  # Add parent range info
                    })

            # Add buffers from this range
            if 'buffers' in range_info:
                for buf_info in range_info['buffers']:
                    slave_bufs.append({
                        'name': buf_info['full_name'],  # Use dotted name for docs
                        'start': buf_info['start'],
                        'end': buf_info['end'],
                        'access': buf_info['access'],
                        'size': buf_info['end'] - buf_info['start'] + 1,
                        'range': range_info['name']  # Add parent range info
                    })

        if slave_regs:
            registers[slave_name] = slave_regs
        if slave_bufs:
            buffers[slave_name] = slave_bufs

    return {'registers': registers, 'buffers': buffers}

def create_markdown_slave_tables(detailed_ranges: Dict[str, List[Dict]]) -> str:
    """Create detailed markdown tables for each slave's registers and buffers"""
    sections = []

    for slave_name in detailed_ranges['registers']:
        regs = detailed_ranges['registers'][slave_name]

        if regs:
            sections.append(f"## {slave_name} Registers\n")
            sections.append("| Address | Register | Access | Size |")
            sections.append("|---------|----------|--------|------|")

            for reg in sorted(regs, key=lambda x: x['start']):
                sections.append(f"| {format_address(reg['start'])} | {reg['name']} | {format_access(reg['access'])} | {format_size(reg['size'])} |")

            sections.append("")  # Empty line

    for slave_name in detailed_ranges['buffers']:
        bufs = detailed_ranges['buffers'][slave_name]

        if bufs:
            sections.append(f"## {slave_name} Buffers\n")
            sections.append("| Address | Buffer | Access | Size |")
            sections.append("|---------|--------|--------|------|")

            for buf in sorted(bufs, key=lambda x: x['start']):
                sections.append(f"| {format_address(buf['start'])} - {format_address(buf['end'])} | {buf['name']} | {format_access(buf['access'])} | {format_size(buf['size'])} |")

            sections.append("")  # Empty line

    return "\n".join(sections)

def generate_memory_map_markdown(toml_file: str, output_file: str, xlen: int):
    """Generate MEMORY_MAP.md from TOML file"""
    # Load memory map
    memory_map = read_toml_file(toml_file)

    # Collect data
    # ranges = collect_memory_ranges(memory_map, xlen)
    detailed_ranges = collect_register_ranges(memory_map, xlen)

    # Get processed structure for tower visualization
    collect_all_ranges = from_collect_all_ranges_import_collect_all_ranges()
    processed_slaves = collect_all_ranges(memory_map.get('slaves', {}), xlen, debug_print_ranges=False)

    # Generate markdown content
    content = []
    content.append("# Memory Map\n")
    content.append("")
    content.append("Auto-generated from memory_map.toml")
    content.append("")

    # Add tower visualization
    # tower = create_address_tower_table(ranges)
    make_tower = from_make_tower_import_make_tower()
    tower = make_tower(processed_slaves)
    content.append("```text")
    content.append(tower)
    content.append("```")
    content.append("")

    # Add detailed tables
    detail_tables = create_markdown_slave_tables(detailed_ranges)
    content.append(detail_tables)

    # Write to file
    with open(output_file, 'w') as f:
        f.write("\n".join(content))

    print(f"Generated {output_file}")

def test_docs_generation():
    """Test function for development"""
    toml_file = "../../../../../test/curvtools/memmap2/test_vectors/input/example/memory_map.toml"
    if Path(toml_file).exists():
        generate_memory_map_markdown(toml_file, "test_memory_map.md", 32)

if __name__ == '__main__':
    test_docs_generation()
