from __future__ import annotations
import re
from pathlib import Path
from typing import TYPE_CHECKING

def match_vars(s: str) -> list[tuple[str, tuple[int, int], str]]:
    """
    Match all $(VAR_NAME) and ${VAR_NAME} patterns in the given string and 
    return a list of tuples containing the variable name, the span of the match, 
    and the match itself.

    Args:
        s: the string to match $(VAR_NAME) and ${VAR_NAME} patterns in

    Returns:
        A list of tuples containing the variable name, the span of the match, and the match itself.
    """
    regex = re.compile(r'\$\((?P<var_name_parens>[^)]+)\)|\$\{(?P<var_name_braces>[^}]+)\}')
    vars_spans = []
    for match in regex.finditer(s):
        var_name = match.group("var_name_parens") or match.group("var_name_braces")
        vars_spans.append((var_name, match.span(), s[match.start():match.end()]))
    return vars_spans or []

def replace_vars(s: str, vars: dict[str, str]) -> str:
    """
    Replace all $(VAR_NAME) and ${VAR_NAME} patterns in the given string with the value of the variable.

    Args:
        s: the string to replace $(VAR_NAME) and ${VAR_NAME} patterns in
        vars: a dict[str, str] of variable names -> their values 
            (None values are ignored and the $(VAR_NAME) or ${VAR_NAME} is left unchanged)

    Returns:
        The string with the $(VAR_NAME) and ${VAR_NAME} patterns replaced with 
        the value of the variable if provided and not None.
    """
    vars_spans = match_vars(s)
    pos_delta = 0
    for var_name, (start, end), match in vars_spans:
        if vars is not None and var_name in vars and vars[var_name] is not None:
            s = s[:start + pos_delta] + vars[var_name] + s[end + pos_delta:]
            pos_delta += len(vars[var_name]) - len(match)
    return s

