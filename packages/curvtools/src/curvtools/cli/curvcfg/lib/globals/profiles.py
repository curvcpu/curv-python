from __future__ import annotations
from typing import Any
from curvpyutils.toml_utils import MergedTomlDict  # type: ignore
import os
from pathlib import Path

################################################################################
#
# Public class
#
################################################################################

class Profile(dict[str, Any]):
    def __init__(self, cfg_dir: str, profile_name: str, profile_dict: dict[str, Any]):
        self.profile_file = Path(cfg_dir) / "profiles" / f"{profile_name}.toml"
        super().__init__(profile_dict)
    def toml_file(self) -> str:
        return self.profile_file

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
    
    def _get_profile_dict_by_name(self, profile_name: str) -> dict[str, Any]:
        if not profile_name.endswith(".toml"):
            profile_file_filename = profile_name + ".toml"
        else:
            profile_file_filename = profile_name
        merged_toml_dict = MergedTomlDict.from_toml_files(Path(self.profiles_dir) / profile_file_filename)
        return merged_toml_dict

    def get_all_profiles(self, sort_with_default_first: bool = True) -> dict[str, Profile]:
        ret_profiles_dict: dict[str, Profile] = {}
        for profile_name in self._get_all_profile_names():
            profile_dict = self._get_profile_dict_by_name(profile_name)
            ret_profiles_dict[profile_name] = Profile(self.cfg_dir, 
                profile_name, 
                profile_dict)
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
