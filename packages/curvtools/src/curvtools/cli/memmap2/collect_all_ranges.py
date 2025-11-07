#!/usr/bin/env python3
"""
Memory map range collection utilities
"""
import re
from typing import Dict, List, Any


def _normalize_range_name(name: str) -> str:
    """Convert range name to normalized form (lowercase, spaces/special chars to underscore)"""
    return re.sub(r'[^a-z0-9]+', '_', name.lower())


def _collect_items_from_slave(slave_config: Dict[str, Any], item_type: str, xlen: int) -> List[Dict[str, Any]]:
    """
    Recursively collect ALL registers or buffers from a slave regardless of range, flattening any nested tables.
    Items will later be assigned to ranges by arithmetic containment.
    """
    assert item_type in ("registers", "buffers")
    items: List[Dict[str, Any]] = []
    bytes_per_register = xlen // 8

    root = slave_config.get(item_type, {})
    if not isinstance(root, dict):
        return items

    def collect_from_section(section: Dict[str, Any], prefix: str = "") -> None:
        for item_name, item_config in section.items():
            if isinstance(item_config, dict):
                current_prefix = f"{prefix}.{item_name}" if prefix else item_name
                if item_type == 'registers' and 'addr' in item_config and 'access' in item_config:
                    items.append({
                        'name': item_config['name'],
                        'full_name': current_prefix,
                        'addr': item_config['addr'],
                        'access': item_config['access']
                    })
                elif item_type == 'buffers' and 'start' in item_config and 'end' in item_config and 'access' in item_config:
                    # buffers must have explicit end
                    items.append({
                        'name': item_config['name'],
                        'full_name': current_prefix,
                        'start': item_config['start'],
                        'end': item_config['end'],
                        'access': item_config['access']
                    })
                else:
                    collect_from_section(item_config, current_prefix)

    collect_from_section(root)
    return items


def collect_all_ranges(slaves_config: Dict[str, Any], xlen: int, debug_print_ranges: bool = False) -> List[Dict[str, Any]]:
    """Collect all address ranges for all slaves with registers/buffers nested under their parent ranges

    Args:
        slaves_config: Configuration dict for all slaves (e.g., memory_map['slaves'])
        xlen: XLEN value for register size calculation (32 or 64)
        debug_print_ranges: Whether to print debug output

    Returns:
        List of slave dictionaries, each containing 'name' and 'ranges' keys
    """
    slaves = []

    for slave_name, slave_config in slaves_config.items():
        ranges = []

        # Group ranges by their normalized names
        ranges_by_name = {}
        if 'ranges' in slave_config:
            for range_config in slave_config['ranges']:
                name = range_config['name']
                normalized = _normalize_range_name(name)
                if normalized not in ranges_by_name:
                    ranges_by_name[normalized] = []
                ranges_by_name[normalized].append(range_config.copy())

        # Collect all registers/buffers once per slave (schema changed: they live under the slave)
        all_registers = _collect_items_from_slave(slave_config, 'registers', xlen)
        all_buffers = _collect_items_from_slave(slave_config, 'buffers', xlen)

        # Create the nested structure for this slave
        for normalized_name, range_configs in ranges_by_name.items():
            # Skip unnamed ranges (they're disallowed)
            if not normalized_name:
                continue

            # For each range config (even if they have the same normalized name),
            # create a separate range entry with nested registers/buffers
            # This allows discontiguous ranges with the same name to be represented separately
            for range_config in range_configs:
                range_entry = range_config.copy()
                range_entry['registers'] = []
                range_entry['buffers'] = []

                # Assign items to this range by arithmetic containment
                r_start = range_entry['start']
                r_end = range_entry['end']
                range_entry['registers'] = [
                    reg for reg in all_registers
                    if r_start <= reg['addr'] <= r_end
                ]
                range_entry['buffers'] = [
                    buf for buf in all_buffers
                    if r_start <= buf['start'] and buf['end'] <= r_end
                ]

                ranges.append(range_entry)

        # Handle slaves that don't have named ranges (like sdram) - keep original ranges
        if not ranges and 'ranges' in slave_config:
            for range_config in slave_config['ranges']:
                range_copy = range_config.copy()
                range_copy['registers'] = []
                range_copy['buffers'] = []
                ranges.append(range_copy)

        slaves.append({
            'name': slave_config.get('name', slave_name),
            'ranges': ranges
        })

    if debug_print_ranges:
        try:
            from rich.console import Console
            import inspect
            console = Console()
            console.print("--------------------------------")
            console.print("Collected slaves (called by %s):" % (inspect.currentframe().f_back.f_code.co_name))
            console.print("--------------------------------")
            console.print(slaves)
        except ImportError:
            print(slaves)

    return slaves
