#!/usr/bin/env python3
"""
ASCII comment generation for memory maps
"""
from curvpyutils.str_utils import insert_underscores
from typing import List, Dict, Any, Optional


class MemoryRangeAdapter:
    """Adapter class to make range dictionaries work with the old ASCII generation code"""
    def __init__(self, range_dict: Dict[str, Any]):
        self.start_addr = range_dict['start']
        self.end_addr = range_dict['end']
        self.name = range_dict['name']
        # Determine access display: use explicit access if present; otherwise derive from children;
        # if mixed or unknown, show ' - '
        explicit_access = range_dict.get('access')
        if explicit_access is not None:
            self.rw = self._normalize_access(explicit_access)
        else:
            child_accesses = []
            for reg in range_dict.get('registers', []) or []:
                if 'access' in reg:
                    child_accesses.append(reg['access'])
            for buf in range_dict.get('buffers', []) or []:
                if 'access' in buf:
                    child_accesses.append(buf['access'])
            unique = set(child_accesses)
            if len(unique) == 1 and len(child_accesses) > 0:
                self.rw = self._normalize_access(next(iter(unique)))
            else:
                self.rw = ' - '
        self.cacheable = range_dict.get('cacheable', False)
        self.sub_ranges = self._create_sub_ranges(range_dict)
        self._calculate_size_str()
        self._calculate_max_name_length()

    def _normalize_access(self, access: str) -> str:
        """Normalize access string"""
        if access == 'rw':
            return 'R/W'
        elif access == 'ro':
            return 'R/O'
        elif access == 'wo':
            return 'W/O'
        elif access == ' - ':
            return ' - '
        else:
            return access.upper()

    def _create_sub_ranges(self, range_dict: Dict[str, Any]) -> List['MemoryRangeAdapter']:
        """Create sub-ranges from registers and buffers"""
        sub_ranges = []

        # Add registers as sub-ranges
        for reg in range_dict.get('registers', []):
            # Registers are single-word addresses; tolerate either legacy 'start' or new 'addr'
            start_addr = reg.get('start', reg.get('addr'))
            if start_addr is None:
                continue
            # Default to 4 bytes if size is not derivable here (display-only)
            end_addr = reg.get('end', start_addr + 4 - 1)
            sub_ranges.append(MemoryRangeAdapter({
                'start': start_addr,
                'end': end_addr,
                'name': reg['name'],
                'access': reg['access'],
                'cacheable': range_dict.get('cacheable', False),
                'registers': [],
                'buffers': []
            }))

        # Add buffers as sub-ranges
        for buf in range_dict.get('buffers', []):
            sub_ranges.append(MemoryRangeAdapter({
                'start': buf['start'],
                'end': buf['end'],
                'name': buf['name'],
                'access': buf['access'],
                'cacheable': range_dict.get('cacheable', False),
                'registers': [],
                'buffers': []
            }))

        # Sort sub-ranges by start address, reverse order for display
        sub_ranges.sort(key=lambda x: x.start_addr, reverse=True)
        return sub_ranges

    def _calculate_size_str(self):
        """Calculate human-readable size string"""
        size_bytes = self.end_addr - self.start_addr + 1
        if size_bytes >= 1024 * 1024:
            self.size_str = f"{size_bytes // (1024 * 1024)}mb"
        elif size_bytes >= 1024:
            self.size_str = f"{size_bytes // 1024}kb"
        else:
            self.size_str = f"{size_bytes}b"

    def _calculate_max_name_length(self):
        """Calculate maximum name length for formatting"""
        self.max_name_length = len(self.name)
        for sub_range in self.sub_ranges:
            self.max_name_length = max(self.max_name_length, sub_range.max_name_length)

    @property
    def cacheable_str(self) -> str:
        """Return cacheable string representation"""
        return "*" if self.cacheable else ""

    def format_start_addr(self) -> str:
        """Format start address with underscores"""
        return insert_underscores(f"{self.start_addr:08x}")

    def format_end_addr(self) -> str:
        """Format end address with underscores"""
        return insert_underscores(f"{self.end_addr:08x}")


def ljust_str_with_truncation(s: str, max_length: int, fill_char: str = " ") -> str:
    """Left justify string with truncation if too long"""
    ellipsis = "..."
    if len(s) > max_length - len(ellipsis):
        return s[:max_length - len(ellipsis)] + ellipsis
    else:
        return s.ljust(max_length, fill_char)


def _generate_simple_memmap_comment(all_ranges: List[MemoryRangeAdapter], with_header: bool) -> str:
    """Generate simplified ASCII memory map visualization"""

    NAME_FIELD_WIDTH = 17
    RW_FIELD_WIDTH = 7
    SIZE_FIELD_WIDTH = 8
    CACHE_FIELD_WIDTH = 12

    def format_cell(content: str, width: int) -> str:
        content = content or ""
        total_padding = width - len(content)
        if total_padding <= 0:
            return content[:width]
        left_padding = total_padding // 2
        right_padding = total_padding - left_padding
        return (" " * left_padding) + content + (" " * right_padding)

    blank_rw = format_cell("", RW_FIELD_WIDTH)
    blank_size = format_cell("", SIZE_FIELD_WIDTH)
    blank_cache = format_cell("", CACHE_FIELD_WIDTH)

    lines = []
    if with_header:
        lines.append("//   >>>> Memory Map <<<<")
        lines.append("//")
        lines.append("//   Memory Range                                                         |  R/W  | Size   | Cacheable?")
        lines.append(f"// -----------------------------------------------------------------------|{'-' * RW_FIELD_WIDTH}|{'-' * SIZE_FIELD_WIDTH}|{'-' * CACHE_FIELD_WIDTH}+")
        lines.append(f"//              +-----------------+                                       |{blank_rw}|{blank_size}|{blank_cache}|")

    for rng in all_ranges:
        lines.append(f"//   {rng.format_end_addr()}  |                 |                                       |{blank_rw}|{blank_size}|{blank_cache}|")
        lines.append(f"//              |                 |                                       |{blank_rw}|{blank_size}|{blank_cache}|")

        centered_name = format_cell(rng.name, NAME_FIELD_WIDTH)
        access_cell = format_cell(rng.rw, RW_FIELD_WIDTH)
        size_cell = format_cell(rng.size_str, SIZE_FIELD_WIDTH)
        cache_cell = format_cell(rng.cacheable_str if rng.cacheable_str else "", CACHE_FIELD_WIDTH)
        lines.append(f"//              |{centered_name}|                                       |{access_cell}|{size_cell}|{cache_cell}|")

        lines.append(f"//              |                 |                                       |{blank_rw}|{blank_size}|{blank_cache}|")
        lines.append(f"//   {rng.format_start_addr()}  |                 |                                       |{blank_rw}|{blank_size}|{blank_cache}|")

        lines.append(f"//              +-----------------+                                       +{'-' * RW_FIELD_WIDTH}+{'-' * SIZE_FIELD_WIDTH}+{'-' * CACHE_FIELD_WIDTH}+")

    lines.append("//                                                                                          * = cacheable")
    lines.append("//")

    return "\n".join(lines)


def generate_memmap_comment(slaves_data, with_header: bool = True) -> str:
    """
    Generate simplified ASCII memory map visualization
    """
    if not slaves_data:
        return "// No slaves defined"

    # Convert slaves_data to MemoryRangeAdapter objects
    all_ranges = []
    for slave in slaves_data:
        for range_dict in slave['ranges']:
            all_ranges.append(MemoryRangeAdapter(range_dict))

    # Sort ranges by start address, reverse order for display
    all_ranges.sort(key=lambda x: x.start_addr, reverse=True)

    # Create the simplified ASCII visualization
    return _generate_simple_memmap_comment(all_ranges, with_header)


def generate_registers_and_sub_ranges_comment(slaves_data, xlen: int = 32) -> str:
    """Generate ASCII table of registers and sub-ranges"""
    if not slaves_data:
        return "// No slaves defined"

    lines = []
    first_slave = True

    for slave in slaves_data:
        slave_name = slave['name']

        # Check if this slave has any registers or buffers
        has_items = False
        for range_info in slave['ranges']:
            if range_info.get('registers') or range_info.get('buffers'):
                has_items = True
                break

        if not has_items:
            continue

        if not first_slave:
            lines.append("//")
        first_slave = False

        lines.append(f"//   +-------------------------------------------------------------------------------------------------+")
        lines.append(f"//   | {slave_name.center(95)} |")
        lines.append(f"//   +-------------------------+------------------------------+----------+-----------------------------+")
        lines.append(f"//   | Address                 | Name                         | R/W?     | Size                        |")
        lines.append(f"//   +-------------------------+------------------------------+----------+-----------------------------+")

        for range_info in slave['ranges']:
            range_name = range_info['name']

            # Add registers
            bytes_per_register = xlen // 8
            for reg in range_info.get('registers', []):
                start_addr = reg.get('start', reg.get('addr'))
                # Derive end for registers
                end_addr = reg.get('end', start_addr + bytes_per_register - 1)
                name = reg['name']
                access = reg['access']

                # For registers, display a single address (no start-end range)
                addr_str = f"{start_addr:08X}"

                if access == 'rw':
                    rw_str = 'R/W'
                elif access == 'ro':
                    rw_str = 'R'
                elif access == 'wo':
                    rw_str = 'W'
                else:
                    rw_str = '?'

                size_bytes = end_addr - start_addr + 1
                if size_bytes == 4:
                    size_str = "4 bytes"
                elif size_bytes == 8:
                    size_str = "8 bytes"
                else:
                    size_str = f"{size_bytes} bytes"

                lines.append(f"//   | {addr_str.ljust(23)} | {name.ljust(28)} | {rw_str.center(8)} | {size_str.ljust(27)} |")

            # Add buffers
            for buf in range_info.get('buffers', []):
                start_addr = buf['start']
                end_addr = buf['end']
                name = buf['name']
                access = buf['access']

                addr_str = f"{start_addr:08X} - {end_addr:08X}"

                if access == 'rw':
                    rw_str = 'R/W'
                elif access == 'ro':
                    rw_str = 'R'
                elif access == 'wo':
                    rw_str = 'W'
                else:
                    rw_str = '?'

                size_bytes = end_addr - start_addr + 1
                if size_bytes >= 1024 * 1024:
                    size_str = f"{size_bytes // (1024 * 1024)} MB"
                elif size_bytes >= 1024:
                    size_str = f"{size_bytes // 1024} KB"
                else:
                    size_str = f"{size_bytes} bytes"

                lines.append(f"//   | {addr_str.ljust(23)} | {name.ljust(28)} | {rw_str.center(8)} | {size_str.ljust(27)} |")

        lines.append(f"//   +-------------------------+------------------------------+----------+-----------------------------+")

    return "\n".join(lines)
