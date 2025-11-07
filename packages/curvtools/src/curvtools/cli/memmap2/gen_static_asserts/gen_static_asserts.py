#!/usr/bin/env python3
"""
Generate a SystemVerilog file containing static asserts to validate generated memmappkg.sv

This uses the TOML as the source of truth and emits assertions covering:
- get_slave_sel_o over registers and buffers (±16 bytes, 4-byte steps)
- is_legal_access_* for each slave over each top-level range (±16 bytes, 4-byte steps)
"""
from __future__ import annotations

from curvpyutils.toml_utils import read_toml_file
from typing import Dict, List, Tuple


def _hex32(value: int) -> str:
    return f"32'h{value:08x}"


def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        ls, le = merged[-1]
        if s <= le + 1:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


def _collect_top_ranges(memory_map: Dict) -> Dict[str, List[Tuple[int, int]]]:
    """Collect top-level ranges per slave (start, end)."""
    per_slave: Dict[str, List[Tuple[int, int]]] = {}
    for slave_key, slave_cfg in memory_map.get('slaves', {}).items():
        slave_name = slave_cfg.get('name', slave_key)
        per_slave.setdefault(slave_name, [])
        for rng in slave_cfg.get('ranges', []) or []:
            per_slave[slave_name].append((rng['start'], rng['end']))
        # Merge contiguous
        per_slave[slave_name] = _merge_intervals(per_slave[slave_name])
    return per_slave


def _collect_accessible_ranges(memory_map: Dict, xlen: int) -> Dict[str, Dict[str, List[Tuple[int, int]]]]:
    """Collect read/write accessible intervals per slave, mirroring sv_generator logic."""
    from ..collect_all_ranges import collect_all_ranges

    result: Dict[str, Dict[str, List[Tuple[int, int]]]] = {}
    slaves = collect_all_ranges(memory_map.get('slaves', {}), xlen, debug_print_ranges=False)

    for slave_info in slaves:
        slave_name = slave_info['name']
        read_iv: List[Tuple[int, int]] = []
        write_iv: List[Tuple[int, int]] = []
        for rng in slave_info['ranges']:
            has_regs = bool(rng.get('registers'))
            has_bufs = bool(rng.get('buffers'))
            if has_regs:
                for reg in rng.get('registers', []):
                    acc = reg['access']
                    if acc in ('ro', 'rw'):
                        s = reg['addr']
                        e = s + (xlen // 8) - 1
                        read_iv.append((s, e))
                    if acc in ('wo', 'rw'):
                        s = reg['addr']
                        e = s + (xlen // 8) - 1
                        write_iv.append((s, e))
            if has_bufs:
                for buf in rng.get('buffers', []):
                    acc = buf['access']
                    if acc in ('ro', 'rw'):
                        read_iv.append((buf['start'], buf['end']))
                    if acc in ('wo', 'rw'):
                        write_iv.append((buf['start'], buf['end']))
            if not has_regs and not has_bufs:
                acc = rng.get('access', 'rw')
                s, e = rng['start'], rng['end']
                if acc in ('ro', 'rw'):
                    read_iv.append((s, e))
                if acc in ('wo', 'rw'):
                    write_iv.append((s, e))

        result[slave_name] = {
            'read': _merge_intervals(read_iv),
            'write': _merge_intervals(write_iv)
        }

    return result


def _addr_in_any(addr: int, intervals: List[Tuple[int, int]]) -> bool:
    for s, e in intervals:
        if s <= addr <= e:
            return True
    return False


def _derive_selection(addr: int, top_ranges: Dict[str, List[Tuple[int, int]]]) -> str:
    """Return WB_SLAVE_<NAME> or WB_SLAVE_NONE constant name for an address."""
    for slave_name, ivs in top_ranges.items():
        for s, e in ivs:
            if s <= addr <= e:
                return f"WB_SLAVE_{slave_name.upper()}"
    return "WB_SLAVE_NONE"


def _boundary_addrs(start: int, end: int) -> List[int]:
    """Return word-aligned addresses from [start-16, start+16] and [end-16, end+16]"""
    addrs: List[int] = []
    for base in (start, end):
        a0 = max(0, base - 16)
        a1 = base + 16
        a = a0
        while a <= a1:
            addrs.append(a)
            a += 4
    return addrs


def generate_static_asserts_from_toml(toml_file: str, output_file: str, xlen: int = 32) -> None:
    memory_map = read_toml_file(toml_file)

    top_ranges = _collect_top_ranges(memory_map)
    access_ranges = _collect_accessible_ranges(memory_map, xlen)

    # Order slaves deterministically by name for stable output
    slave_names = sorted(top_ranges.keys())

    # Gather registers and buffers via collect_all_ranges to get starts/ends
    from ..collect_all_ranges import collect_all_ranges
    slaves_nested = collect_all_ranges(memory_map.get('slaves', {}), xlen, debug_print_ranges=False)

    # Build lines
    lines: List[str] = []
    lines.append("module slang_top;")
    lines.append("    import memmappkg::*;")
    lines.append("")
    lines.append("    `ifdef SLANG")

    # 1. Assert selections for each register address
    for slave in slaves_nested:
        slave_name = slave['name']
        expected_const = f"WB_SLAVE_{slave_name.upper()}"
        for rng in slave['ranges']:
            for reg in rng.get('registers', []):
                addr = reg['addr']
                sel_const = _derive_selection(addr, top_ranges)
                lines.append(
                    f"    $static_assert(get_slave_sel_o({_hex32(addr)}) == {sel_const}, \"Register {reg['full_name']} selection mismatch at 0x{addr:08x}\");"
                )

    # 2. Assert selections around buffers (±16, step 4) at start/end boundaries only
    for slave in slaves_nested:
        for rng in slave['ranges']:
            for buf in rng.get('buffers', []):
                start, end = buf['start'], buf['end']
                for addr in _boundary_addrs(start, end):
                    sel_const = _derive_selection(addr, top_ranges)
                    lines.append(
                        f"    $static_assert(get_slave_sel_o({_hex32(addr)}) == {sel_const}, \"Buffer selection mismatch at 0x{addr:08x}\");"
                    )

    # 3. Assert is_legal_access_* across each top-level range boundaries (±16, step 4)
    # Build function names for all slaves observed in access_ranges
    func_names = [f"is_legal_access_{name.lower()}" for name in sorted(access_ranges.keys())]

    for slave_name in slave_names:
        for s, e in top_ranges.get(slave_name, []):
            # Check only at boundary neighborhoods
            for addr in _boundary_addrs(s, e):
                for target_slave, rw in sorted(access_ranges.items()):
                    fn = f"is_legal_access_{target_slave.lower()}"
                    can_read = 1 if _addr_in_any(addr, rw['read']) else 0
                    can_write = 1 if _addr_in_any(addr, rw['write']) else 0
                    lines.append(
                        f"    $static_assert({fn}({_hex32(addr)}, READ_LEGAL) == 1'b{can_read}, \"{fn} READ at 0x{addr:08x}\");"
                    )
                    lines.append(
                        f"    $static_assert({fn}({_hex32(addr)}, WRITE_LEGAL) == 1'b{can_write}, \"{fn} WRITE at 0x{addr:08x}\");"
                    )

    # 4. Assert register/range/buffer test functions
    import re as _re
    def _snake(s: str) -> str:
        return _re.sub(r'[^a-zA-Z0-9]+', '_', s.lower())

    # 4a. Register equality functions
    for slave in slaves_nested:
        for rng in slave['ranges']:
            for reg in rng.get('registers', []):
                base = _snake(reg['name'])
                fn = f"is_addr_{base if base.endswith('_register') else base + '_register'}"
                addr = reg['addr']
                lines.append(f"    $static_assert({fn}({_hex32(addr)}) == 1'b1, \"{fn} true at 0x{addr:08x}\");")
                # Nearby addresses should be false
                for delta in (-8, -4, 4, 8):
                    a = addr + delta
                    if a < 0:
                        continue
                    if a == addr:
                        continue
                    lines.append(f"    $static_assert({fn}({_hex32(a)}) == 1'b0, \"{fn} false at 0x{a:08x}\");")

    # 4b. Range membership functions
    for slave in slaves_nested:
        for rng in slave['ranges']:
            fn = f"is_addr_in_{_snake(rng['name'])}_range"
            s, e = rng['start'], rng['end']
            for a in _boundary_addrs(s, e):
                inside = 1 if (s <= a <= e) else 0
                lines.append(f"    $static_assert({fn}({_hex32(a)}) == 1'b{inside}, \"{fn} at 0x{a:08x}\");")

    # 4c. Buffer membership functions
    for slave in slaves_nested:
        for rng in slave['ranges']:
            for buf in rng.get('buffers', []):
                bbase = _snake(buf['name'])
                fn = f"is_addr_in_{bbase if bbase.endswith('_buffer') else bbase + '_buffer'}"
                s, e = buf['start'], buf['end']
                for a in _boundary_addrs(s, e):
                    inside = 1 if (s <= a <= e) else 0
                    lines.append(f"    $static_assert({fn}({_hex32(a)}) == 1'b{inside}, \"{fn} at 0x{a:08x}\");")

    # 4d. Overall per-slave range membership functions
    # Use top_ranges computed earlier
    for slave_name in slave_names:
        overall_fn = f"is_addr_in_{_snake(slave_name)}"
        intervals = top_ranges.get(slave_name, [])
        for s, e in intervals:
            for a in _boundary_addrs(s, e):
                inside_any = 1 if _addr_in_any(a, intervals) else 0
                lines.append(f"    $static_assert({overall_fn}({_hex32(a)}) == 1'b{inside_any}, \"{overall_fn} at 0x{a:08x}\");")

    lines.append("    `else")
    lines.append("    $static_assert(0==1, \"SLANG is not defined, but should be\");")
    lines.append("    `endif")
    lines.append("")
    lines.append("endmodule")

    with open(output_file, 'w') as f:
        f.write("\n".join(lines))



