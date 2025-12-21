from typing import Dict, Any, Optional
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths

class DefaultMapArgs:
    verbosity: Optional[int] = None
    curv_root_dir: Optional[str] = None
    build_dir: Optional[str] = None
    profile: Optional[str] = None
    board: Optional[str] = None
    device: Optional[str] = None

    # internal
    _curvpaths: Optional[CurvPaths] = None

    # these can be computed once the main args above are set and curvpaths is available
    _merged_config_toml: Optional[str] = None
    _config_mk_dep: Optional[str] = None
    _merged_board_toml: Optional[str] = None
    _board_mk_dep: Optional[str] = None

    @property
    def curvpaths(self) -> CurvPaths:
        return self._curvpaths
    @curvpaths.setter
    def curvpaths(self, value: CurvPaths):
        self._curvpaths = value
        self._merged_config_toml = self._curvpaths["DEFAULT_MERGED_CFGVARS_TOML_PATH"].to_str()
        self._merged_board_toml = self._curvpaths["DEFAULT_MERGED_BOARD_TOML_PATH"].to_str()
        self._config_mk_dep = self._curvpaths["CONFIG_MK_DEP"].to_str()
        self._board_mk_dep = self._curvpaths["BOARD_MK_DEP"].to_str()

    def to_default_map(self) -> Dict[str, Any]:
        """
        Construct a Click default_map matching the curvcfg CLI hierarchy. Leaf nodes initialized to args, which
        by default makes them all None. Callers can freely overwrite any subset with real defaults 
        (from early-parsed args, env, etc.).
        """
        ret_val: Dict[str, Any] = {
            # Top-level options on `curvcfg`
            "verbosity": self.verbosity,
            "curv_root_dir": self.curv_root_dir,
            "build_dir": self.build_dir,

            # `curvcfg board ...`
            "board": {
                # curvcfg board merge --board=... --device=... --schema=... --merged_board_toml_out=... --dep-file-out=...
                "merge": {
                    "board": self.board,
                    "device": self.device,
                    "schema": None,              # repeated option -> list at runtime
                    "merged_board_toml": self._merged_board_toml,
                    "board_mk_dep": self._board_mk_dep,
                },
                # curvcfg board generate --merged_board_toml_in=...
                "generate": {
                    "merged_board_toml": self._merged_board_toml,
                },
            },

            # `curvcfg cfgvars ...`
            "cfgvars": {
                # curvcfg cfgvars merge --profile=... --overlay=... --schema=... --merged-config-toml-out=... --dep-file-out=...
                "merge": {
                    "tb": False,
                    "profile": self.profile,
                    "overlays": None,            # repeated -> list at runtime
                    "schemas": None,             # repeated -> list at runtime
                    "merged_config_toml": self._merged_config_toml,
                    "config_mk_dep": self._config_mk_dep,
                },
                # curvcfg cfgvars generate --merged-config-toml-in=...
                "generate": {
                    "merged_config_toml": self._merged_config_toml,
                },
            },

            # `curvcfg show ...`
            "show": {
                # curvcfg show profiles
                "profiles": {
                    # no options
                },
                # curvcfg show curvpaths [--board=...] [--device=...]
                "curvpaths": {
                    "profile": self.profile,
                    "board": self.board,
                    "device": self.device,
                },
                # curvcfg show vars --merged-toml-in=...
                "vars": {
                    "merged_toml_in": self._merged_config_toml,
                },
            },
        }

        def _prune_nones(obj: Any) -> Any:
            """
            Recursively drop any dict entries whose value is None.
            Leaves non-None values untouched; cleans nested dicts/lists in place.
            """
            if isinstance(obj, dict):
                for k in list(obj.keys()):
                    v = obj[k]
                    if v is None:
                        obj.pop(k, None)
                    else:
                        _prune_nones(v)
            elif isinstance(obj, list):
                # remove None elements and recurse into nested containers
                i = 0
                while i < len(obj):
                    if obj[i] is None:
                        obj.pop(i)
                    else:
                        _prune_nones(obj[i])
                        i += 1
            return obj

        _prune_nones(ret_val)
        return ret_val