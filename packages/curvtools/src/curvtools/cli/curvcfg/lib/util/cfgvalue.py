import hashlib
from typing import Any, Dict

class CfgValue():
    """
    Class that stores a CFG_ value with its user-readable string representation along with meta information from the schema.

    Attributes:
        value (str | int | None): CFG_ native value or None
        string_value (str): user-readable string representation of the value
        meta (CfgValueMeta): meta information about the value
        python_type (type): python type of the value (int, str, or None)
        is_default (bool): whether the value is a default value
    """

    class BaseSchemaMeta:
        def __init__(self, meta: Dict[str, Any]):
            self.toml_path = meta["toml_path"]
            self.value_type = meta["type"]
            self.default_value = meta.get("default", None)
    class IntSchemaMeta(BaseSchemaMeta):
        def __init__(self, meta: Dict[str, Any]):
            super().__init__(meta)
        def get_type_str(self) -> tuple[str, str]:
            return ("int", "-")
    class IntMinMaxSchemaMeta(BaseSchemaMeta):
        def __init__(self, meta: Dict[str, Any]):
            super().__init__(meta)
            self.min = meta.get("min", None)
            self.max = meta.get("max", None)
        def get_type_str(self) -> tuple[str, str]:
            return ("int", f"{self.min}-{self.max}")
    class IntEnumSchemaMeta(BaseSchemaMeta):
        def __init__(self, meta: Dict[str, Any]):
            super().__init__(meta)
            self.enum_values = meta.get("enum_values", [])
        def get_type_str(self) -> tuple[str, str]:
            return ("int enum", f"[{','.join([str(v) for v in self.enum_values])}]")
    class StringEnumSchemaMeta(BaseSchemaMeta):
        def __init__(self, meta: Dict[str, Any]):
            super().__init__(meta)
            self.enum_values = meta.get("enum_values", [])
        def get_type_str(self) -> tuple[str, str]:
            joined_values = ','.join(['"[bold green]'+str(v)+'[/bold green]"' for v in self.enum_values])
            return ("string enum", f"[{joined_values}]")
    class StringSchemaMeta(BaseSchemaMeta):
        def __init__(self, meta: Dict[str, Any]):
            super().__init__(meta)
        def get_type_str(self) -> tuple[str, str]:
            return ("string", "-")
    class CfgValueMeta:
        def __init__(self, meta: Dict[str, Any]):
            self.makefile_type = meta["makefile_type"]
            self.locations = meta["locations"]
            self.toml_path = meta["toml_path"]
            self.sv_type = meta["sv_type"]
            self.type = meta["type"]
            self.is_default = meta["is_default"]

    def __init__(self, value: str | int | None, meta: Dict[str, Any], schema_entry: Any):
        self.value = value
        self.meta = self.CfgValueMeta(meta)
        self.python_type = self._get_type()
        self.is_default = self.meta.is_default
        self.schema_meta: Any = self._get_schema_meta(schema_entry)

    def _get_schema_meta(self, schema_entry: Any) -> Any:
        if self.meta.type == "int":
            if schema_entry.get("min", None) is not None and schema_entry.get("max", None) is not None:
                return CfgValue.IntMinMaxSchemaMeta(schema_entry)
            else:
                return CfgValue.IntSchemaMeta(schema_entry)
        elif self.meta.type == "enum":
            if type(self.value) is int:
                return CfgValue.IntEnumSchemaMeta(schema_entry)
            else:
                return CfgValue.StringEnumSchemaMeta(schema_entry)
        elif self.meta.type == "string":
            return CfgValue.StringSchemaMeta(schema_entry)

    def _string_value(self) -> str|None:
        if self.value is None:
            return "None"
        if self.meta.makefile_type in ("decimal", "enum", "hex32", "hex16", "hex8", "hex") and isinstance(self.value, int):
            # either an int or an int-valued enum => decimal or hex => string
            if (self.meta.makefile_type=="hex32"):
                s = f"0x{self.value:08X}"
            elif (self.meta.makefile_type=="hex16"):
                s = f"0x{self.value:04X}"
            elif (self.meta.makefile_type=="hex8"):
                s = f"0x{self.value:02X}"
            elif (self.meta.makefile_type=="hex"):
                s = f"0x{self.value:08X}"
            else:
                s = f"{self.value:d}"
            return s
        elif self.meta.makefile_type in ("string", "enum", "decimal") and isinstance(self.value, str):
            # either a string or a string-valued enum => string
            return self.value.strip()
        else:
            # Fallback types: default to decimal => string, or string => string
            if isinstance(self.value, int):
                return f"{self.value:d}"
            else:
                return self.value.strip()

    def _get_type(self) -> type:
        if isinstance(self.value, int):
            return int
        elif isinstance(self.value, str):
            return str
        else:
            return type(self.value)

    def get_raw_value(self) -> int|str|None:
        return self.value
    
    def __str__(self) -> str|None:
        return self._string_value()
    
    def __int__(self) -> int|None:
        try:
            ret = int(self.value)
        except ValueError:
            ret = None
        return ret
    
    def locations_str(self) -> str:
        s = ""
        if "makefiles" in self.meta.locations or "all" in self.meta.locations:
            s += "MK,"
        if "cfgpkg" in self.meta.locations or "all" in self.meta.locations:
            s += "SV,"
        if "defines" in self.meta.locations or "all" in self.meta.locations:
            s += "SVH,"
        if "json" in self.meta.locations or "all" in self.meta.locations:
            s += "JS,"
        if "env" in self.meta.locations or "all" in self.meta.locations:
            s += "E,"
        return s[:-1]
    
    # def hashable_value(self) -> int|str|None:
    #     if self.value is None:
    #         return None
    #     if isinstance(self.value, int):
    #         return int(self._string_value(), base=0)
    #     elif isinstance(self.value, str):
    #         return self._string_value()
    #     else:
    #         return None # should never happen
    
    def __repr__(self) -> str:
        return f"CfgValue(value={self.value if self.value is not None else 'None'}, makefile_type={self.meta.makefile_type}, string_value={self._string_value() if self._string_value() is not None else 'None'}, locations={','.join(self.meta.locations)}, toml_path={self.meta.toml_path}, python type={self.python_type}, is_default={self.is_default})"

class CfgValues(Dict[str, CfgValue]):
    """
    Encapsulates a collection of CfgValue objects as a dictionary of str->CfgValue.
    """

    def __init__(self, vals: Dict[str, CfgValue] | None = None):
        super().__init__(vals or {})

    def __repr__(self) -> str:
        return f"CfgValues({', '.join([f'{k}: {v}' for k, v in self.items()])})"
    
    def __str__(self) -> str:
        return f"CfgValues({', '.join([f'{k}: {v}' for k, v in self.items()])})"
    
    def __getitem__(self, key: str) -> CfgValue:
        return super().__getitem__(key)
    
    def __setitem__(self, key: str, value: CfgValue|str|int|None):
        if isinstance(value, CfgValue):
            super().__setitem__(key, value)
        elif isinstance(value, (str, int, type(None))):
            # For simple values, we need existing meta - only works for updating existing keys
            if key in self:
                # Preserve existing meta when updating with a simple value
                super().__setitem__(key, CfgValue(value, self[key].meta.__dict__))
            else:
                raise KeyError(f"Cannot add new key '{key}' with simple value. Provide a CfgValue object for new keys.")
        else:
            raise ValueError(f"Expected CfgValue, str, int, or None, got {type(value)}")
    
    def hash(self) -> str:
        d: dict[str, int|str|None] = {}
        sorted_keys = sorted(self.keys())
        for k in sorted_keys:
            raw_value = self[k].get_raw_value()
            if raw_value is not None:
                d[k] = raw_value        
        s = str(d)

        # hash and truncate to 6 chars
        h6_str = hashlib.sha256(s.encode()).hexdigest()[:6]
        return h6_str

class MissingVars(list[str]):
    """
    Encapsulates a list of missing variables.
    """

    def __init__(self, missing_vars: list[str] | None = None):
        super().__init__(missing_vars or [])

    def __repr__(self) -> str:
        return f"MissingVars({', '.join(self)})"

    def __str__(self) -> str:
        return f"MissingVars({', '.join(self)})"