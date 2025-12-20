from pathlib import Path
from typing import TYPE_CHECKING, List, Mapping, Optional, Any

from jinja2 import Template

from .types import Artifact, ValueSource, _Domain, ParseType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# Exported helpers
# ---------------------------------------------------------------------------
__all__ = [
    "_parse_artifacts",
    "_get_domain_and_src_generic",
    "_lookup_dotted",
    "render_template_to_str",
]

if TYPE_CHECKING:
    from ..parse_schema import SchemaOracle


# ---------------------------------------------------------------------------
# Utility: artifacts
# ---------------------------------------------------------------------------

def _parse_artifacts(raw: Optional[List[str]]) -> List[Artifact]:
    if raw is None:
        return [Artifact.NONE]
    if not isinstance(raw, list):
        raise TypeError("artifacts must be a list of strings")

    if not raw:
        return [Artifact.NONE]

    res: List[Artifact] = []
    for s in raw:
        if not isinstance(s, str):
            raise TypeError("artifacts entries must be strings")
        try:
            res.append(Artifact[s])
        except KeyError:
            # if you want to be strict, raise here instead.
            raise ValueError(f"Unknown artifact kind {s!r}") from None
    return res


# ---------------------------------------------------------------------------
# Extract domain + source info (constant or toml_path)
# ---------------------------------------------------------------------------

def _parse_domain(raw: Mapping[str, Any]) -> _Domain:
    if raw is None:
        return _Domain(kind="none", default=None)

    choices = raw.get("choices")
    rng = raw.get("range")
    default = raw.get("default")

    if len(raw) == 0:
        return _Domain(kind="none", default=None)

    if choices is not None and rng is not None:
        raise ValueError("domain cannot have both 'choices' and 'range'")

    if choices is not None:
        # choices may be empty; that's legal and simply means no value validates
        return _Domain(kind="choices", choices=list(choices), default=default)

    if rng is not None:
        rng_list = list(rng)
        if len(rng_list) != 2:
            raise ValueError("domain.range must have exactly two elements [lo, hi]")
        lo, hi = rng_list
        if not isinstance(lo, int) or not isinstance(hi, int):
            raise TypeError("domain.range elements must be ints")
        if lo > hi:
            raise ValueError("domain.range[0] must be <= domain.range[1]")
        return _Domain(kind="range", range=(lo, hi), default=default)

    # neither choices nor range -> unconstrained
    return _Domain(kind="none", default=default)


def _get_domain_and_src_generic(
    *,
    src: Mapping[str, Any],
    domain_raw: Optional[Mapping[str, Any]],
    var_name: str,
    schema_filepath: Path,
) -> tuple[_Domain, Optional[str], Optional[Any], ValueSource, ParseType]:
    """
    Shared between scalars and array fields.

    src.toml_path or src.constant_value is required, but they are mutually exclusive.
    Returns:
        domain, toml_path, constant_value, value_source, parse_type
    """
    parse_type_raw: Optional[str] = src.get("parse")
    if parse_type_raw is None:
        raise ValueError(f"{var_name} in {schema_filepath}: src.parse is required")
    parse_type = ParseType.from_str(parse_type_raw)

    toml_path = src.get("toml_path")
    const = src.get("constant_value")

    if const is not None and toml_path is not None:
        raise ValueError(
            f"{var_name} in {schema_filepath}: src.constant_value and src.toml_path are mutually exclusive"
        )

    if const is None and toml_path is None:
        raise ValueError(
            f"{var_name} in {schema_filepath}: src.constant_value and src.toml_path are both missing"
        )

    if const is not None:
        # constant_value does not allow a domain
        if domain_raw is not None and len(domain_raw) > 0:
            raise ValueError(
                f"{var_name} in {schema_filepath}: src.constant_value does not allow a domain"
            )
        domain = _Domain(kind="none", default=const)
        val_source = ValueSource.CONSTANT
    else:
        # TOML-driven
        domain = _parse_domain(domain_raw or {})
        val_source = ValueSource.TOML

    return domain, toml_path, const, val_source, parse_type


# ---------------------------------------------------------------------------
# Utility: lookup dotted path
# ---------------------------------------------------------------------------

def _split_toml_path(path: str) -> list[str]:
    """
    Split a TOML dotted path, respecting quoted keys.
    
    E.g., 'arrays_metadata."board.buttons".lpf_name' becomes
    ['arrays_metadata', 'board.buttons', 'lpf_name']
    """
    parts: list[str] = []
    current = ""
    in_quotes = False
    
    i = 0
    while i < len(path):
        c = path[i]
        if c == '"':
            in_quotes = not in_quotes
            i += 1
        elif c == '.' and not in_quotes:
            if current:
                parts.append(current)
                current = ""
            i += 1
        else:
            current += c
            i += 1
    
    if current:
        parts.append(current)
    
    return parts


def _lookup_dotted(root: Mapping[str, Any], path: str) -> Any:
    """
    Resolve a dotted TOML path like "board.sdram.native_row_width"
    or 'arrays_metadata."board.buttons".lpf_name' inside a nested dict.
    Returns None if any component is missing.
    """
    cur: Any = root
    for part in _split_toml_path(path):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


# ---------------------------------------------------------------------------
# Utility: Jinja2 rendering helpers
# ---------------------------------------------------------------------------

def render_template_to_str(
    template_path: str | Path,
    schema_oracle: "SchemaOracle",
) -> str:
    """
    Render a Jinja2 template with all variables that declare the JINJA2 artifact.

    The SchemaOracle provides the variable names (keys) and values, so templates
    can simply reference whatever the schema defines without hardcoding names
    here.
    """
    path = Path(template_path)
    jinja2_values = schema_oracle.get_values_for_artifact(Artifact.JINJA2)

    template = Template(path.read_text(), keep_trailing_newline=True)
    return template.render(**jinja2_values)