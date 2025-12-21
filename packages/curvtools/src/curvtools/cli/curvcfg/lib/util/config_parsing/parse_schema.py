from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple
import re
import sys
import tempfile
import os
from rich import print as rprint
from pathlib import Path
import curvpyutils.tomlrw as tomlrw
from curvtools.cli.curvcfg.lib.util.config_parsing.util import ( 
    Artifact, 
    ValueSource, 
    ParseType, 
    _Domain, 
    DomainChoices, 
    DomainRange, 
    _get_domain_and_src_generic, 
    _parse_artifacts, 
    _lookup_dotted
)

__all__ = [
    "parse_dict_to_schema_vars",
    "SchemaOracle",
    "SCHEMA_ROOT_KEY",
    "Artifact",
    "ValueSource",
    "ParseType",
]

SCHEMA_ROOT_KEY = "_schema"
VARS_KEY = "vars"
ARRAYS_KEY = "arrays"

# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class SchemaBaseVar:
    """
    Base class for all schema variables.
    """

    __slots__ = (
        "var_name",
        "schema_filepath",
    )

    def __init__(self, var_name: str, schema_filepath: Path) -> None:
        self.var_name = var_name               # the actual variable name, e.g. "CFG_WHATEVER" or "BOARD_LEDS"
        self.schema_filepath = schema_filepath # schema file in this object array was defined

# ---------------------------------------------------------------------------
# SchemaObjectArrayElementVar (minimal)
# ---------------------------------------------------------------------------

class SchemaObjectArrayElementVar:
    """
    Represents one field (classvar or instancevar) of an object-array element.
    """

    __slots__ = (
        "name",
        "domain",
        "toml_path",
        "constant_value",
        "val_source",
        "parse_type",
    )

    def __init__(self, name: str, *, domain: _Domain,
                 toml_path: Optional[str],
                 constant_value: Optional[Any],
                 val_source: ValueSource,
                 parse_type: ParseType):
        self.name = name
        self.domain = domain
        self.toml_path = toml_path
        self.constant_value = constant_value
        self.val_source = val_source
        self.parse_type = parse_type

    # ---------------------------------------------------------------------------
    # Utility: convert parse types
    # ---------------------------------------------------------------------------

    @staticmethod
    def apply_parse(parse_type: ParseType, v: Any) -> Any:
        if parse_type == ParseType.STRING:
            return str(v)
        if parse_type == ParseType.INT:
            return int(v)
        if parse_type == ParseType.UINT:
            x = int(v)
            if x < 0:
                raise ValueError("uint cannot be negative")
            return x
        return v


    def extract_value(self, input_obj: dict[str,Any]) -> Any:
        """
        Return the value of this field for a single list element.
        """
        if self.val_source == ValueSource.CONSTANT:
            return SchemaObjectArrayElementVar.apply_parse(self.parse_type, self.constant_value)

        raw = input_obj.get(self.toml_path)
        if raw is None:
            # domain default OK
            if self.domain.default is not None:
                raw = self.domain.default
            else:
                raise ValueError(f"Missing value for '{self.name}' and no default")

        return SchemaObjectArrayElementVar.apply_parse(self.parse_type, raw)

# ---------------------------------------------------------------------------
# SchemaObjectArrayVar
# ---------------------------------------------------------------------------

class ArrayRenderView:
    """
    Jinja-friendly wrapper for array elements plus array-level metadata.

    - Iterable (for element loops)
    - len() works (for |length)
    - .meta (and .arrayvars) exposes array-level fields (e.g., lpf_name)
    """

    __slots__ = ("_elements", "meta", "arrayvars")

    def __init__(self, elements: List[dict[str, Any]], meta: Mapping[str, Any]) -> None:
        self._elements = list(elements)
        # Jinja attribute -> dict key fallback lets dot-lookup work: meta.lpf_name
        self.meta = dict(meta)
        self.arrayvars = self.meta

    def __iter__(self):
        return iter(self._elements)

    def __len__(self):
        return len(self._elements)

    def __getitem__(self, idx):
        return self._elements[idx]

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"ArrayRenderView(len={len(self)}, meta_keys={list(self.meta.keys())})"


class SchemaObjectArrayVar(SchemaBaseVar):
    """
    Represents an object-array variable. Iterable over element dicts.
    Each element is { field_name : value }.
    """

    __slots__ = ("toml_path", "arrayvars", "vars", "elements", "array_metadata", "artifacts")

    def __init__(
        self,
        *,
        var_name: str,
        schema_filepath: Path,
        toml_path: str,
        arrayvars: Dict[str, SchemaObjectArrayElementVar],
        vars: Dict[str, SchemaObjectArrayElementVar],
        artifacts: List[Artifact],
    ) -> None:
        super().__init__(var_name, schema_filepath)
        self.toml_path = toml_path
        self.arrayvars = arrayvars
        self.vars = vars
        self.artifacts = list(artifacts)
        self.elements: List[Dict[str, Any]] = []
        self.array_metadata: Dict[str, Any] = {}
    

    @classmethod
    def from_array_schema_entry(
        cls,
        array_var_name: str,
        entry: dict[str, Any],
        schema_filepath: Path
    ) -> "SchemaObjectArrayVar":

        """
        Parse an `entry` dict like this:

            {
                'src': {'toml_path': 'board.buttons', 'parse': 'array[object]'},
                'artifacts': ['JINJA2'],
                '_arrayvars': {'lpf_name': {'src': {'toml_path': 'arrays_metadata."board.buttons".lpf_name', 'parse': 'string'}}},
                '_vars': {
                    'name': {'src': {'toml_path': 'name', 'parse': 'string'}, 'domain': {}},
                    'active_state': {
                        'src': {'toml_path': 'active_state', 'parse': 'int'},
                        'domain': {'choices': [0, 1], 'default': 1}
                    }
                }
            }
        
        into a SchemaObjectArrayVar object. A SchemaObjectArrayVar is an object that can
        parse a list[dict[str, Any]] like this:

            'board.buttons': [
                {'name': 'B1', 'active_state': 0},
                {'name': 'B2', 'active_state': 0},
                {'name': 'UP', 'active_state': 1},
                {'name': 'DOWN', 'active_state': 1},
                {'name': 'LEFT', 'active_state': 1},
                {'name': 'RIGHT', 'active_state': 1}
            ]

        and then become usable as the loop variable in a JINJA2 template.
        """

        src = entry.get("src", {})
        toml_path = src.get("toml_path")
        if toml_path is None:
            raise ValueError(f"{array_var_name} in {schema_filepath}: src.toml_path is required")

        _, _, _, _, parse_type = _get_domain_and_src_generic(
            src=src,
            domain_raw=None,  # domains on array vars themselves aren’t supported right now
            var_name=array_var_name,
            schema_filepath=schema_filepath,
        )

        if parse_type != ParseType.OBJECT_ARRAY:
            raise ValueError(f"{array_var_name}: parse must be {ParseType.OBJECT_ARRAY.value} (was {parse_type.value})")

        artifacts = _parse_artifacts(entry.get("artifacts", None))
        if artifacts != [Artifact.JINJA2]:
            raise ValueError(f"{array_var_name}: artifacts must be [JINJA2] (was {artifacts})")

        # Build arrayvars (array-level variables with toml_path lookup)
        arrayvars: Dict[str, SchemaObjectArrayElementVar] = {}
        for name, subentry in entry.get("_arrayvars", {}).items():
            src_dict = subentry.get("src", {})
            domain_raw = subentry.get("domain")
            dom, tp, const, val_src, ptype = _get_domain_and_src_generic(
                src=src_dict,
                domain_raw=domain_raw,
                var_name=name,
                schema_filepath=schema_filepath,
            )
            arrayvars[name] = SchemaObjectArrayElementVar(
                name,
                domain=dom,
                toml_path=tp,
                constant_value=const,
                val_source=val_src,
                parse_type=ptype,
            )

        # Build vars (per-element variables)
        vars_dict: Dict[str, SchemaObjectArrayElementVar] = {}
        for name, subentry in entry.get("_vars", {}).items():
            src_dict = subentry.get("src", {})
            domain_raw = subentry.get("domain")
            dom, tp, const, val_src, ptype = _get_domain_and_src_generic(
                src=src_dict,
                domain_raw=domain_raw,
                var_name=name,
                schema_filepath=schema_filepath,
            )
            vars_dict[name] = SchemaObjectArrayElementVar(
                name,
                domain=dom,
                toml_path=tp,
                constant_value=const,
                val_source=val_src,
                parse_type=ptype,
            )

        return cls(
            var_name=array_var_name,
            schema_filepath=schema_filepath,
            toml_path=toml_path,
            arrayvars=arrayvars,
            vars=vars_dict,
            artifacts=artifacts,
        )

    # -------------------------------------------------------

    def parse(self, items: List[dict[str, Any]], config_root: Mapping[str, Any] = None) -> None:
        """
        items = list of dicts from TOML, one per element.
        config_root = the full config dict for looking up arrayvars.
        Build self.elements = [element_dict, ...]
        """
        out: List[Dict[str, Any]] = []
        
        # Pre-compute arrayvar values (same for all elements); keep at array-level
        arrayvar_values: Dict[str, Any] = {}
        for name, scalar in self.arrayvars.items():
            if scalar.toml_path and config_root is not None:
                raw = _lookup_dotted(config_root, scalar.toml_path)
                arrayvar_values[name] = SchemaObjectArrayElementVar.apply_parse(scalar.parse_type, raw)
            elif scalar.val_source == ValueSource.CONSTANT:
                arrayvar_values[name] = scalar.extract_value({})
            else:
                raise ValueError(f"arrayvar {name} requires either toml_path with config_root, or constant_value")

        self.array_metadata = dict(arrayvar_values)

        for obj in items:
            elem: Dict[str, Any] = {}

            # Add per-element vars
            for name, scalar in self.vars.items():
                elem[name] = scalar.extract_value(obj)

            out.append(elem)

        self.elements = out

# ---------------------------------------------------------------------------
# SchemaScalarVar
# ---------------------------------------------------------------------------

class SchemaScalarVar(SchemaBaseVar):
    """
    Single _schema.vars.* entry.

    Exposed attributes / methods:
        - var_name: str                   (CFG_...)
        - toml_path: str|None             (e.g. cache.hex_files.src.type; None for constant_value's)
        - schema_filepath: str            (schema file in which this var was defined, e.g., myfile.toml)
        - parse_type: ParseType
        - domain: _Domain
        - value: Any                      (set by parse() or by a constant_value)
        - value_source: ValueSource
        - artifacts: list[Artifact]
        - validate(raw) -> bool
        - parse(raw) -> T
        - sv_display() -> str
        - mk_display() -> str
    """

    __slots__ = (
        "toml_path",
        "_parse_type",
        "_domain",
        "_display_sv",
        "_display_mk",
        "artifacts",
        "value",
        "value_source",
    )

    def __init__(
        self,
        *,
        var_name: str,
        toml_path: str,
        schema_filepath: Path,
        parse_type: ParseType,
        domain: _Domain,
        display_sv: str,
        display_mk: str,
        artifacts: List[Artifact],
        value_source: ValueSource,
    ) -> None:
        super().__init__(var_name, schema_filepath)
        # domain cannot be None but it can be empty meaning any value is allowed
        if domain is None:
            domain = _Domain(kind="none", default=None)
        self.toml_path = toml_path
        self._parse_type = ParseType(parse_type)
        self._domain = domain
        self._display_sv = display_sv or ""
        self._display_mk = display_mk or ""
        self.artifacts = list(artifacts)
        self.value: Any = None  # set by parse()
        self.value_source = value_source
    @classmethod
    def from_constant_value(
        cls, 
        value: Any, 
        var_name: str, 
        schema_filepath: Path, 
        parse_type: ParseType, 
        display_sv: str, 
        display_mk: str, 
        artifacts: List[Artifact]
    ) -> SchemaScalarVar:
        # This works because the first attempt to access .value will trigger
        # _coerce(), which will set .value to the constant value stored in domain.default.
        return cls(
            var_name=var_name,
            toml_path=None,
            schema_filepath=schema_filepath,
            parse_type=parse_type,
            domain=_Domain(kind="none", default=value),
            display_sv=display_sv,
            display_mk=display_mk,
            artifacts=artifacts,
            value_source=ValueSource.CONSTANT,
        )

    # ---------- core coercion ----------

    def _coerce(self, raw: Any) -> Any:
        """
        Coerce raw (str|int|None) to the type specified by src.parse.
        Does NOT mutate self.value.

        If raw is None, uses domain.default and coerces it. 
        If domain.default is also None, raises ValueError.
        """
        if raw is None:
            if self._domain.default is None:
                raise ValueError(f"Asked to coerce a None value for {self.schema_filepath}:{self.var_name}, but domain.default was also None")
            val = self._domain.default
        else:
            val = raw

        if self._parse_type == ParseType.STRING:
            # allow any object, make it a string
            return "" if val is None else str(val)

        if self._parse_type in (ParseType.INT, ParseType.UINT):
            if isinstance(val, bool):
                # avoid bool being subclass of int in Python
                v = int(val)
            elif isinstance(val, int):
                v = val
            elif isinstance(val, str):
                s = val.strip()
                # allow python-style int literals, including 0x and underscores
                v = int(s, 0)
            else:
                raise TypeError(f"Cannot coerce {val!r} (type {type(val)}) to int/uint")

            if self._parse_type == ParseType.UINT and v < 0:
                raise ValueError(f"uint value must be >= 0, got {v}")

            return v

        raise ValueError(f"Unknown parse type {self._parse_type.value!r}")

    # ---------- validation and parsing ----------

    def validate(self, raw: Any) -> bool:
        """
        validate_fn(raw) -> bool

        Coerces raw using the src.parse type and checks against domain.{choices,range}.
        - If domain kind is "none", always True (except coercion failure).
        - If choices=[], then no value is valid (always False once coercion succeeds).

        In the case of a constant_value, this will always return False since any attempt
        to subsequently call parse() would raise.
        """
        if self.value_source == ValueSource.CONSTANT:
            return False

        try:
            v = self._coerce(raw)
        except Exception:
            return False

        if self._domain.kind == "none":
            return True

        if self._domain.kind == "choices":
            choices = self._domain.choices or []
            return v in choices

        if self._domain.kind == "range":
            assert self._domain.range is not None
            return self._domain.range[0] <= v <= self._domain.range[1]

        # shouldn't happen
        return False

    def parse(self, raw: Any) -> Any:
        """
        parse_fn(raw) -> T

        - T is determined by src.parse (ParseType.STRING -> str, 
          ParseType.INT -> int, ParseType.UINT -> int, 
          ParseType.OBJECT_ARRAY -> list[dict[str, Any]]).
        - If raw is None, uses domain.default (possibly None) and coerces it.
        - On failure, propagates exceptions.
        - On success, stores into self.value and returns it.
        """
        if self.value_source == ValueSource.CONSTANT:
            raise ValueError(f"Asked to parse a raw value for constant_value {self.value!r} in {self.schema_filepath}:{self.var_name}")

        if self.toml_path is None:
            raise ValueError(f"Asked to parse a raw value for a scalar variable {self.var_name} in {self.schema_filepath}:{self.toml_path!r}, but toml_path is None")

        v = self._coerce(raw)
        self.value = v
        return v

    # ---------- display helpers ----------

    def _ensure_value(self) -> Any:
        if self.value is None:
            # fall back to default; this will raise ValueError if there is no default
            self.value = self._coerce(None)
        return self.value

    def sv_literal(self, for_macro: bool = False) -> str:
        """
        Return the literal portion for SystemVerilog emission.

        - Bit-vectors use width'h<hex> with 2's complement masking.
        - Strings are quoted; for_macro wraps with backtick-quotes for `define.
        - Fallback returns str(value).
        """
        v = self._ensure_value()
        sv_type = self._display_sv.strip()
        if not sv_type:
            return str(v)

        m = re.search(r"\[(\d+)\s*:\s*(\d+)\]", sv_type)
        if m and isinstance(v, int):
            msb = int(m.group(1))
            lsb = int(m.group(2))
            width = abs(msb - lsb) + 1
            hex_digits = (width + 3) // 4

            mask = (1 << width) - 1
            vv = v & mask

            return f"{width}'h{vv:0{hex_digits}x}"

        if "string" in sv_type.lower() or isinstance(v, str):
            if for_macro:
                return f'`"{v}`"'
            return f'"{v}"'

        return str(v)

    def sv_display(self) -> str:
        """
        Return SystemVerilog localparam representation.

        Examples:
            display.sv = "logic [31:0]" ->
                "localparam logic [31:0] CFG_... = 32'hffff_fffc;"
            display.sv = "int" ->
                "localparam int CFG_... = 4;"
            display.sv containing "string" ->
                "localparam string CFG_... = \"asm\";"
        """
        sv_type = self._display_sv.strip()
        if not sv_type:
            return str(self._ensure_value())

        literal = self.sv_literal(for_macro=False)
        return f"localparam {sv_type} {self.var_name} = {literal};"

    def mk_display(self, value: Any = None) -> str:
        """
        Return Python-style formatted string per display.mk.

        Args:
            value: Optional value to format. If None, uses self.value (or default).
                   If provided, will be coerced to the appropriate type before formatting.

        Cases:
            - If display.mk contains "{...}", treat as format string and call
              display.mk.format(value=v).
            - Otherwise, some simple keywords:
                "int"    -> decimal int string
                "string" -> str(...)
            - Fallback: str(v)
        """
        if value is None:
            v = self._ensure_value()
        else:
            # Coerce the provided value to ensure it's the right type
            v = self._coerce(value)
        
        mk = self._display_mk.strip()
        if not mk:
            return str(v)

        if "{" in mk and "}" in mk:
            try:
                return mk.format(value=v)
            except Exception:
                # fall through to simple handling
                pass

        if mk == "int" or mk == "uint":
            return str(int(v))
        elif mk == "string":
            return str(v)
        else:
            return str(v)

    def __repr__(self) -> str:
        from_str = "constant_value" if self.value_source == ValueSource.CONSTANT else f"{self.schema_filepath.as_posix()}@{self.toml_path}"
        if self.value is None:
            if self._domain.default is None:
                value_str = "⚠️ (not set, and no default)"
            else:
                value_str = f"✔️ (not set, but defaults to {self._domain.default!r} (type {type(self._domain.default).__name__}) once requested)"
        else:
            value_str = f"✔️ set to {self.value!r} (type {type(self.value).__name__})"
        return f"SchemaVar({self.var_name!r}: {value_str}; source={from_str}, parse_type={self._parse_type!r}, domain={self._domain!r}, display_sv={self._display_sv!r}, display_mk={self._display_mk!r}, artifacts={self.artifacts!r})"

class SchemaOracle(Mapping[str, SchemaBaseVar]):
    """
    Container for all schema variables (scalars + arrays).

    - Keyed by var_name: "CFG_*", "BOARD_*", etc.
    - Also supports lookup by toml_path ("cache.hex_files.base_addr", "board.buttons").
    """

    def __init__(self, vars_by_name: Dict[str, SchemaBaseVar]) -> None:
        self._by_name: Dict[str, SchemaBaseVar] = dict(vars_by_name)
        self._by_toml_path: Dict[str, SchemaBaseVar] = {}

        for v in self._by_name.values():
            tp = getattr(v, "toml_path", None)
            if isinstance(tp, str):
                self._by_toml_path[tp] = v

    def __getitem__(self, key: str) -> SchemaBaseVar:
        # Lookup by varname
        return self._by_name[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._by_name)

    def __len__(self) -> int:
        return len(self._by_name)

    def by_toml_path(self, path: str) -> SchemaBaseVar:
        # Lookup by toml_path
        return self._by_toml_path[path]

    def values(self) -> Iterable[SchemaBaseVar]:  # type: ignore[override]
        # Return all variables
        return self._by_name.values()

    def items(self) -> Iterable[tuple[str, SchemaBaseVar]]:  # type: ignore[override]
        # Return all variables as name-value pairs
        return self._by_name.items()

    def extend(self, other: "SchemaOracle|dict[str, SchemaBaseVar]") -> None:
        if isinstance(other, SchemaOracle):
            for name, v in other._by_name.items():
                self._by_name[name] = v
                tp = getattr(v, "toml_path", None)
                if isinstance(tp, str):
                    self._by_toml_path[tp] = v
        elif isinstance(other, dict):
            for name, v in other.items():
                self._by_name[name] = v
                tp = getattr(v, "toml_path", None)
                if isinstance(tp, str):
                    self._by_toml_path[tp] = v
        else:
            raise TypeError("other must be a SchemaOracle or dict[str, SchemaBaseVar]")

    # ------------------- resolution / completeness -------------------

    def feed_config(self, config_root: Mapping[str, Any]) -> None:
        """
        Walk all known toml_paths and feed values from a non-_schema config dict
        into the underlying Schema*Var objects by calling .parse() or .parse(items).
        """
        for path, var in self._by_toml_path.items():
            raw = _lookup_dotted(config_root, path)
            if raw is None:
                # Will fall back to domain.default (if any) when value is requested.
                continue

            if isinstance(var, SchemaScalarVar):
                var.parse(raw)
            elif isinstance(var, SchemaObjectArrayVar):
                if not isinstance(raw, list):
                    raise TypeError(
                        f"{var.var_name} expects an array[object] at {path}, got {type(raw)}"
                    )
                var.parse(raw, config_root)
            else:
                # future subclasses?
                raise TypeError(f"Unsupported schema var type: {type(var)}")

    def iter_unresolved(self) -> Iterable[tuple[str, SchemaBaseVar]]:
        """
        Yield (var_name, var) pairs that have not been resolved by either
        a config value or a default.
        """
        for name, var in self._by_name.items():
            if isinstance(var, SchemaScalarVar):
                if var.value is None and var._domain.default is None:
                    yield name, var
            elif isinstance(var, SchemaObjectArrayVar):
                if var.elements is None:
                    yield name, var

    def all_resolved(self) -> bool:
        return not any(True for _ in self.iter_unresolved())

    # ------------------- artifact views -------------------

    def get_values_for_artifact(self, artifact: Artifact) -> Dict[str, Any]:
        """
        Return a dict of *values* for a given artifact.

        - For scalar vars: var_name -> resolved scalar value.
        - For JINJA2 arrays: var_name -> list[dict[str, Any]] (elements).
        """
        out: Dict[str, Any] = {}

        for name, var in self._by_name.items():
            var_artifacts = getattr(var, "artifacts", [])
            if artifact not in var_artifacts:
                continue

            if isinstance(var, SchemaScalarVar):
                out[name] = var._ensure_value()
            elif isinstance(var, SchemaObjectArrayVar):
                # Only meaningful for JINJA2 right now
                if artifact == Artifact.JINJA2:
                    out[name] = ArrayRenderView(var.elements or [], var.array_metadata or {})
            # else ignore other subclasses for now

        return out

    def get_vars_for_artifact(self, artifact: Artifact) -> Dict[str, SchemaBaseVar]:
        """
        Return a dict of *variable objects* for a given artifact.

        - For scalar vars: var_name -> SchemaScalarVar object.
        - For JINJA2 arrays: var_name -> SchemaObjectArrayVar object.
        """
        return {
            name: var
            for name, var in self._by_name.items() if artifact in getattr(var, "artifacts", [])
        }

def parse_dict_to_schema_vars(data: dict[str, Any], schema_filepath: Path) -> Dict[str, SchemaBaseVar]:
    """
    Parse a dict[str, Any] and return a dict[str, SchemaBaseVar], mapping variable
    names onto SchemaBaseVar-derived objects.

    Only tables under [_schema.*] are considered. 
    
    schema_filepath is not read; it is used to construct the SchemaBaseVar objects so they can point back to their source.
    """
    
    schema = data.get(SCHEMA_ROOT_KEY, {})
    vars_section = schema.get(VARS_KEY, {})
    arrays_section = schema.get(ARRAYS_KEY, {})

    vars_by_name: Dict[str, SchemaBaseVar] = {}

    for array_var_name, entry in arrays_section.items():
        vars_by_name[array_var_name] = SchemaObjectArrayVar.from_array_schema_entry(array_var_name, entry, schema_filepath)

    for var_name, entry in vars_section.items():
        # entry is the table under _schema.vars.<var_name>
        src = entry.get("src", {})
        domain_raw = entry.get("domain", None)
        display = entry.get("display", {})
        artifacts_raw = entry.get("artifacts", None)

        domain, toml_path, constant_value, val_source, parse_type = _get_domain_and_src_generic(
            src=src,
            domain_raw=domain_raw,
            var_name=var_name,
            schema_filepath=schema_filepath,
        )

        display_sv = display.get("sv", "")
        display_mk = display.get("mk", "")
        artifacts = _parse_artifacts(artifacts_raw)

        if val_source == ValueSource.CONSTANT:
            vars_by_name[var_name] = SchemaScalarVar.from_constant_value(
                value=constant_value,
                var_name=var_name,
                schema_filepath=schema_filepath,
                parse_type=parse_type,
                display_sv=display_sv,
                display_mk=display_mk,
                artifacts=artifacts,
            )
        else:
            vars_by_name[var_name] = SchemaScalarVar(
                var_name=var_name,
                toml_path=toml_path,
                schema_filepath=schema_filepath,
                parse_type=parse_type,
                domain=domain,
                display_sv=display_sv,
                display_mk=display_mk,
                artifacts=artifacts,
                value_source=val_source,
            )

    return vars_by_name
