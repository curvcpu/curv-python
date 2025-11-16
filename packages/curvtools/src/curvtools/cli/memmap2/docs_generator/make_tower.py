from rich.table import Table
from rich.console import Console
from rich.text import Text
import sys
import os
from copy import deepcopy
from typing import List, Dict, Any, Union, Tuple
from dataclasses import dataclass
from rich import box
from rich.align import Align
from rich.markup import escape
from rich.padding import PaddingDimensions
from curvpyutils.str_utils import insert_underscores

@dataclass
class Range:
    bus_slave_name: str
    range_name: str
    start: int
    end: int
    access: str
    cacheable: bool
    def format_start(self) -> str:
        return insert_underscores(format(self.start, '08x'))
    def format_end(self) -> str:
        return insert_underscores(format(self.end, '08x'))
    def format_access(self) -> str:
        if self.access == 'rw':
            return 'R/W'
        if self.access == 'ro':
            return 'R/O'
        if self.access == 'wo':
            return 'W/O'
        if self.access == ' - ':
            return ' - '
        return (self.access or '').upper()
    def format_cacheable(self) -> str:
        return "Yes" if self.cacheable else "No"
    def format_size(self) -> str:
        size_bytes = self.end - self.start + 1
        if size_bytes > 1024*1024:
            return f"{size_bytes // (1024*1024)}mb"
        elif size_bytes > 1024:
            return f"{size_bytes // 1024}kb"
        else:
            return f"{size_bytes}b"
    def __str__(self) -> str:
        return f"{self.range_name} ({self.bus_slave_name}) {self.format_start()}-{self.format_end()}"
    def __repr__(self) -> str:
        return f"Range(bus_slave_name='{self.bus_slave_name}', range_name='{self.range_name}', start={self.format_start()}, end={self.format_end()}, access='{self.format_access()}', cacheable={self.format_cacheable()})"

def _strip_registers_and_buffers(slaves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strip registers and buffers from a range info dictionary"""
    return_slaves = []
    for slave_info in slaves:
        new_slave_info = deepcopy(slave_info)
        for range in new_slave_info['ranges']:
            range.pop('registers', None)
            range.pop('buffers', None)
        return_slaves.append(new_slave_info)
    return return_slaves

def _create_ranges(slaves: List[Dict[str, Any]]) -> List[Range]:
    """Create a sorted (by start address) list of ranges from a list of slaves"""
    ranges = []
    for slave_info in slaves:
        for rng in slave_info['ranges']:
            # Determine access: prefer explicit, else derive from children; if mixed/unknown use ' - '
            access = rng.get('access')
            if access is None:
                child_accesses = []
                for reg in rng.get('registers', []) or []:
                    if 'access' in reg:
                        child_accesses.append(reg['access'])
                for buf in rng.get('buffers', []) or []:
                    if 'access' in buf:
                        child_accesses.append(buf['access'])
                uniq = set(child_accesses)
                if len(uniq) == 1 and len(child_accesses) > 0:
                    access = next(iter(uniq))
                else:
                    access = ' - '

            ranges.append(Range(
                bus_slave_name=slave_info['name'],
                range_name=rng['name'],
                start=rng['start'],
                end=rng['end'],
                access=access,
                cacheable=rng.get('cacheable', False)
            ))
    sorted_ranges = sorted(ranges, key=lambda x: x.start)
    return sorted_ranges

def stack(data: List[Range], want_access_cacheable: bool = False, column_titles: List[str] = ["Size", "Access", "Cacheable"], padding:Union[PaddingDimensions, Tuple[int, int]] = (0, 4)) -> Table:    
    # sort data by start address
    data.sort(key=lambda x: x.start)
    data.reverse()
    
    # find the longest of each column's string
    max_range_name_length = max(len(range.range_name) for range in data)
    max_start_or_end_length = max( max(len(range.format_end()) for range in data), max(len(range.format_start()) for range in data) )
    max_size_length = max(max(len(range.format_size()) for range in data), len(column_titles[0]))
    max_access_length = max(max(len(range.format_access()) for range in data), len(column_titles[1]))
    max_cacheable_length = max(max(len(range.format_cacheable()) for range in data), len(column_titles[2]))

    inner_width = max_range_name_length
    left_width = max_start_or_end_length
    right0_width = max_size_length
    right1_width = max_access_length
    right2_width = max_cacheable_length
   
    # Right side: one table, one column, one row per box
    inner = Table(
        show_header=False,
        show_lines=True,   # <- single separator between data rows
        box=box.ASCII2,
        pad_edge=False,
        padding=(0, padding[1]),
        expand=False,
    )
    inner.add_column(no_wrap=True, width=inner_width)

    for range in data:
        inner.add_row(Align(escape(range.range_name), align="center", vertical="middle", height=5))

    # Left gutter built to the same line count as the inner table:
    #   top border blank, top label, 3 blanks, bottom label, separator blank
    left_gutter_lines = [""]
    for range in data:
        left_gutter_lines += [escape(range.format_end()), "", "", "", escape(range.format_start()), ""]
    left = "\n".join(left_gutter_lines)

    # Right gutters (one for access, one for cacheable) built to the same line count as the inner table:
    #   top border blank, top label, 3 blanks, bottom label, separator blank
    rt0_gutter_lines = [""]
    rt1_gutter_lines = [""]
    rt2_gutter_lines = [""]
    for range in data: 
        rt0_gutter_lines += ["", "", range.format_size(), "", "", ""]
        rt1_gutter_lines += ["", "", range.format_access(), "", "", ""]
        rt2_gutter_lines += ["", "", range.format_cacheable(), "", "", ""]
    rt0_gutter = "\n".join(rt0_gutter_lines)
    rt1_gutter = "\n".join(rt1_gutter_lines)
    rt2_gutter = "\n".join(rt2_gutter_lines)

    grid = Table.grid(padding=padding)
    grid.add_column(justify="right", width=left_width, no_wrap=True)
    grid.add_column(no_wrap=True)
    grid.add_column(justify="center", width=right0_width, no_wrap=True)
    if want_access_cacheable:
        grid.add_column(justify="center", width=right1_width, no_wrap=True)
        grid.add_column(justify="center", width=right2_width, no_wrap=True)
        grid.add_row("", "", column_titles[0], column_titles[1], column_titles[2])
        grid.add_row("", "", '-'*right0_width, '-'*right1_width, '-'*right2_width)
        grid.add_row(left, inner, rt0_gutter, rt1_gutter, rt2_gutter)
    else:
        grid.add_row("", "", column_titles[0])
        grid.add_row("", "", '-'*right0_width)
        grid.add_row(left, inner, rt0_gutter)
    return grid

def make_tower(slaves) -> str:
    """Make a tower visualization of the memory map"""

    console = Console()
    sorted_ranges = _create_ranges(slaves)
    # console.print(f"sorted_ranges: {sorted_ranges}")

    tower = stack(sorted_ranges, want_access_cacheable=True)
    with console.capture() as capture:
        console.print(tower)
    ascii = capture.get()
    return ascii
