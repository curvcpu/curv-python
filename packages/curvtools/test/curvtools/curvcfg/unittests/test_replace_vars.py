from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from curvtools.cli.curvcfg.lib.curv_paths.replace_funcs import match_vars, replace_vars

def test_match_vars():
    s = "$(X)/${Y}/$(Z)"
    m = match_vars(s)
    assert len(m) == 3, f"Expected 3 matches, got {len(m)}"
    var_name, (start, end), match = m[0]
    assert var_name == "X", f"Expected X, got {var_name}"
    assert start == 0, f"Expected 0, got {start}"
    assert end == 4, f"Expected 4, got {end}"
    assert match == "$(X)", f"Expected $(X), got {match}"
    var_name, (start, end), match = m[1]
    assert var_name == "Y", f"Expected Y, got {var_name}"
    assert start == 5, f"Expected 5, got {start}"
    assert end == 9, f"Expected 9, got {end}"
    assert match == "${Y}", f"Expected ${Y}, got {match}"
    var_name, (start, end), match = m[2]
    assert var_name == "Z", f"Expected Z, got {var_name}"
    assert start == 10, f"Expected 10, got {start}"
    assert end == 14, f"Expected 14, got {end}"
    assert match == "$(Z)", f"Expected $(Z), got {match}"

def testreplace_vars():
    vars = { 'X': 'xxx', 'Y': 'yyy', 'Z': 'zzz' }
    s = "$(X)/${Y}/$(Z)"
    s = replace_vars(s, vars)
    assert s == "xxx/yyy/zzz", f"Expected xxx/yyy/zzz, got {s}"

def testreplace_vars_edge_cases():
    # nothing to replace
    vars = { 'X': 'xxx', 'Y': 'yyy', 'Z': 'zzz' }
    s = "xxx/yyy/zzz"
    s = replace_vars(s, vars)
    assert s == "xxx/yyy/zzz", f"Expected xxx/yyy/zzz, got {s}"

def testreplace_vars_only_some():
    # some vars are not provided and should be left unchanged
    vars = { 'Z': 'zzz' }
    s = "$(X)/${Y}/$(Z)"
    s = replace_vars(s, vars)
    assert s == "$(X)/${Y}/zzz", f"Expected $(X)/${{Y}}/zzz, got {s}"

def testreplace_vars_some_vars_are_none():
    # some vars are provided asNone and should be left unchanged
    vars = { 'X': None, 'Y': 'yyy', 'Z': 'zzz' }
    s = "$(X)/${Y}/$(Z)"
    s = replace_vars(s, vars)
    assert s == "$(X)/yyy/zzz", f"Expected $(X)/yyy/zzz, got {s}"

