import click

def make_all_legal_expansion_patterns(s: str) -> list[str]:
    """
    Given a string like "CURV_ROOT_DIR", returns a list of all possible patterns we accept as 
    variable expansions for that string:
        - '<CURV_ROOT_DIR>'   # single-quoted with angle brackets
        - "<CURV_ROOT_DIR>"   # double-quoted with angle brackets
        - '<curv-root-dir>'   # single-quoted, lowercase, angled brackets
        - "<curv-root-dir>"   # double-quoted, lowercase, angled brackets
        - <curv-root-dir>     # no quotes, lowercase, angled brackets
        - <CURV_ROOT_DIR>     # no quotes, uppercase, angled brackets
    """
    underscored = s.replace("-", "_")
    hyphenated = s.replace("_", "-")
    base_tokens_in_order:list[str] = [
        s,
        s.lower(),
        s.upper(),
        underscored,
        underscored.lower(),
        underscored.upper(),
        hyphenated,
        hyphenated.lower(),
        hyphenated.upper(),
    ]
    # order-preserving de-dup
    base_tokens_unique:list[str] = list(dict.fromkeys(base_tokens_in_order))
    l:list[str] = [f"<{t}>" for t in base_tokens_unique]
    list_with_single_quotes:list[str] = [f"'{t}'" for t in l]
    list_with_double_quotes:list[str] = [f"\"{t[1:-1]}\"" for t in list_with_single_quotes]
    # order-preserving de-dup over the combined set
    final:list[str] = list(dict.fromkeys(l + list_with_single_quotes + list_with_double_quotes))
    return final

def expand_build_dir_vars(s: str, ctx: click.Context) -> str:
    BUILD_DIR_VAR_PATTERNS = make_all_legal_expansion_patterns("build-dir")
    # Only resolve build_dir if we actually need to expand a pattern
    for var in BUILD_DIR_VAR_PATTERNS:
        if var in s:
            # Access build_dir from CurvContext
            curvctx = ctx.obj
            build_dir = getattr(curvctx, "build_dir", None) or "build"
            s = s.replace(var, str(build_dir))
    return s

def expand_curv_root_dir_vars(s: str, ctx: click.Context) -> str:
    CURV_ROOT_DIR_VAR_PATTERNS = make_all_legal_expansion_patterns("CURV_ROOT_DIR")
    # Only resolve curv_root_dir if we actually need to expand a pattern
    for var in CURV_ROOT_DIR_VAR_PATTERNS:
        if var in s:
            # Access curv_root_dir from CurvContext
            curvctx = ctx.obj
            curv_root_dir = getattr(curvctx, "curv_root_dir", None) or ""
            s = s.replace(var, str(curv_root_dir))
    return s
