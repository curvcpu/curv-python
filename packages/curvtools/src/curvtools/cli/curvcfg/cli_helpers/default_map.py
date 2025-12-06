from typing import Dict, Any, Optional
from dataclasses import dataclass

class DefaultMapArgs:
    verbosity: Optional[int] = None
    curv_root_dir: Optional[str] = None
    build_dir: Optional[str] = None
    profile: Optional[str] = None
    board: Optional[str] = None
    device: Optional[str] = None
    merged_toml: Optional[str] = None
    dep_file_out: Optional[str] = None
    merged_board_toml: Optional[str] = None
    board_dep_file_out: Optional[str] = None

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
                    "merged_board_toml": self.merged_board_toml,
                    "dep_file_out": self.board_dep_file_out,
                },
                # curvcfg board generate --merged_board_toml_in=...
                "generate": {
                    "merged_board_toml": self.merged_board_toml,
                },
            },

            # `curvcfg tb ...`
            "tb": {
                # curvcfg tb merge --profile=... --overlay=... --schema=... --merged-toml-out=... --dep-file-out=...
                "merge": {
                    "profile": self.profile,
                    "overlay": None,             # repeated -> list at runtime
                    "schema": None,              # repeated -> list at runtime
                    "merged_toml_out": self.merged_toml,
                    "dep_file_out": self.dep_file_out,
                },
                # curvcfg tb generate --merged-toml-in=...
                "generate": {
                    "merged_toml_in": self.merged_toml,
                },
            },

            # `curvcfg soc ...`
            "soc": {
                # curvcfg soc merge --profile=... --overlay=... --schema=... --merged-toml-out=... --dep-file-out=...
                "merge": {
                    "profile": self.profile,
                    "overlay": None,
                    "schema": None,
                    "merged_toml_out": self.merged_toml,
                    "dep_file_out": self.dep_file_out,
                },
                # curvcfg soc generate --merged-toml-in=...
                "generate": {
                    "merged_toml_in": self.merged_toml,
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
                    "board": self.board,
                    "device": self.device,
                },
                # curvcfg show vars --merged-toml-in=...
                "vars": {
                    "merged_toml_in": self.merged_toml,
                },
            },
        }
        return ret_val