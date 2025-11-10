from __future__ import annotations
from typing import Any
from curvpyutils.toml_utils import MergedTomlDict  # type: ignore
import os
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.constants import CURRENT_PROFILE_MK_FILENAME

################################################################################
#
# Public class
#
################################################################################

class Profile(dict[str, Any]):
    def __init__(self, cfg_dir: str, profile_name: str, profile_dict: dict[str, Any], is_active: bool):
        self.profile_is_active = is_active
        self.profile_toml_file = Path(cfg_dir) / "profiles" / f"{profile_name}.toml"
        super().__init__(profile_dict)
    def is_active(self) -> bool:
        return self.profile_is_active
    def toml_file(self) -> str:
        return self.profile_toml_file

################################################################################
#
# Internal classes and functions
#
################################################################################

class _ProfileRetriever():
    def __init__(self, cfg_dir: str):
        self.cfg_dir = cfg_dir
        self.profiles_dir = Path(cfg_dir) / "profiles"

    def _get_all_profile_names(self) -> list[str]:
        return [f[:-(len(".toml"))] for f in os.listdir(self.profiles_dir) 
                if f.endswith('.toml')]
    
    def _get_active_profile_name(self) -> str|None:

        def get_curv_config_from_current_profile_mk() -> str|None:
            import re
            pat = re.compile(r"^\s*CURV_CONFIG\s*(?:\?=|:=|=)\s*(.*)$")
            current_profile_file = Path(self.cfg_dir) / CURRENT_PROFILE_MK_FILENAME
            if not current_profile_file.is_file():
                return None
            kv_str = current_profile_file.read_text()
            kv_pairs = kv_str.split("\n")
            for kv_pair in kv_pairs:
                m = pat.match(kv_pair)
                if m:
                    v = m.group(1).strip()
                    return v

        def get_curv_config_from_environment() -> str|None:
            return os.environ.get("CURV_CONFIG", None)
        
        curv_config_from_current_profile_mk = get_curv_config_from_current_profile_mk()
        curv_config_from_environment = get_curv_config_from_environment()
        if curv_config_from_environment:
            return curv_config_from_environment
        elif curv_config_from_current_profile_mk:
            return curv_config_from_current_profile_mk
        else:
            return None

    def _get_profile_dict_by_name(self, profile_name: str) -> dict[str, Any]:
        if not profile_name.endswith(".toml"):
            profile_toml_filename = profile_name + ".toml"
        else:
            profile_toml_filename = profile_name
        merged_toml_dict = MergedTomlDict.from_toml_files(Path(self.profiles_dir) / profile_toml_filename)
        return merged_toml_dict

    def get_all_profiles(self, sort_with_default_first: bool = True) -> dict[str, Profile]:
        active_profile_name = self._get_active_profile_name()
        ret_profiles_dict: dict[str, Profile] = {}
        for profile_name in self._get_all_profile_names():
            profile_dict = self._get_profile_dict_by_name(profile_name)
            is_active_profile = profile_name == active_profile_name
            ret_profiles_dict[profile_name] = Profile(self.cfg_dir, profile_name, profile_dict, is_active_profile)
        sorted_profile_names = sorted(ret_profiles_dict.keys())
        if sort_with_default_first:
            sorted_profile_names.remove("default")
            sorted_profile_names.insert(0, "default")
        ret: dict[str, Profile] = {}
        for profile_name in sorted_profile_names:
            ret[profile_name] = ret_profiles_dict[profile_name]
        return ret

################################################################################
#
# Public function
#
################################################################################

def get_all_profiles(cfg_dir: str, sort_with_default_first: bool = True) -> dict[str, Profile]:
    retriever = _ProfileRetriever(cfg_dir)
    ret = retriever.get_all_profiles(sort_with_default_first)
    return ret

def get_active_profile_name(cfg_dir: str) -> str|None:
    retriever = _ProfileRetriever(cfg_dir)
    ret = retriever._get_active_profile_name()
    return ret