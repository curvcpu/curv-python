import os
from typing import Optional
from click.core import ParameterSource
from pathlib import Path

__all__ = [
    "EpilogEnvVarValue",
    "update_epilog_env_vars",
    "get_epilog_str",
]

def _get_source_str(source: ParameterSource) -> str:
    match source:
        case ParameterSource.ENVIRONMENT:
            return "(env)"
        case ParameterSource.COMMANDLINE:
            return "(cli)"
        case ParameterSource.DEFAULT_MAP:
            return "(repo or default)"
        case ParameterSource.DEFAULT:
            return "(repo or default)"
        case _:
            return "(not set)"

class EpilogEnvVarValue:
    env_var_value: Optional[str]
    env_var_source: Optional[ParameterSource]
    def __init__(self, env_var_value: Optional[str|Path], env_var_source: Optional[ParameterSource]):
        self.env_var_value = str(env_var_value) if env_var_value is not None else None
        self.env_var_source = env_var_source.value if env_var_source is not None else None
    def __str__(self):
        env_var_value_str = f"{self.env_var_value} {_get_source_str(self.env_var_source)}" if self.is_set() else "(unknown)"
        return env_var_value_str
    def __repr__(self):
        return self.__str__()
    def is_set(self) -> bool:
        return (self.env_var_value is not None)

# global singleton dict of epilog env vars as we learn them
_epilog_env_vars: dict[str, EpilogEnvVarValue] = {
    "CURV_ROOT_DIR":  EpilogEnvVarValue(None, None),
    "CURV_BUILD_DIR": EpilogEnvVarValue(None, None),
    "CURV_PROFILE":   EpilogEnvVarValue(None, None),
    "CURV_BOARD":     EpilogEnvVarValue(None, None),
    "CURV_DEVICE":    EpilogEnvVarValue(None, None),
}

def update_epilog_env_vars(key: str, value: str|Path, source: ParameterSource) -> None:
    """
    Update the epilog env vars with the given key, value, and source.

    If the key is already set, updates the value and source.

    Args:
        key: the key to update
        value: the new value
        source: source of that value

    Returns:
        None

    Raises:
        KeyError: if the key is not an env var we care about (ie, in _epilog_env_vars dict)
    """
    global _epilog_env_vars
    if key not in _epilog_env_vars.keys():
        raise KeyError(f"Key {key} not part of epilog; we only display these env vars: {', '.join(_epilog_env_vars.keys())}")
    if value is not None:
        value_str = str(Path(value).resolve().as_posix())
        _epilog_env_vars[key] = EpilogEnvVarValue(value_str, source)

def split_str_at_last_slash_before(s: str, max_len: int) -> list[str]:
    """
    Split a long path string into a list of lines, each no longer than max_len.

    Splits only at os.pathsep characters. If no pathsep is found within the next
    max_len characters, the line may exceed max_len (splitting at the next available
    pathsep, or taking the remainder if no more pathseps exist).

    Args:
        s: the path string to split (e.g., a PATH-like env var with os.pathsep separators)
        max_len: the maximum desired length for each line

    Returns:
        a list of strings, each ideally <= max_len (unless no pathsep is found within range)
    """
    if len(s) <= max_len:
        return [s]

    result = []
    remaining = s

    while remaining:
        if len(remaining) <= max_len:
            result.append(remaining)
            break

        # Look for the last pathsep within max_len characters
        search_region = remaining[:max_len]
        last_sep_idx = search_region.rfind('/')

        if last_sep_idx != -1:
            # Found a pathsep within max_len, split after it (include the pathsep)
            result.append(remaining[:last_sep_idx + 1])
            remaining = remaining[last_sep_idx + 1:]
        else:
            # No pathsep found within max_len, look for the next pathsep beyond max_len
            next_sep_idx = remaining.find('/')
            if next_sep_idx != -1:
                # Found a pathsep after max_len, split after it
                result.append(remaining[:next_sep_idx + 1])
                remaining = remaining[next_sep_idx + 1:]
            else:
                # No pathsep found at all, take the entire remainder
                result.append(remaining)
                break

    return result

def get_epilog_str() -> str:
    """
    Get the epilog string for the currently known epilog env vars.

    Returns:
        the epilog string to display in the help output
    """
    prefix = "\b• "
    suffix = " = "
    max_key_len = max(len(k) for k in _epilog_env_vars.keys())
    key_str_len = max_key_len + len(prefix) + len(suffix)
    EPILOG = ""
    for k, v in _epilog_env_vars.items():
        kstr = f"{prefix}{k:<{max_key_len}}{suffix}"
        EPILOG += f"{kstr}{v}\n\n"
        # vstr = split_str_at_last_slash_before(
        #     str(v), 
        #     60-key_str_len
        # )
        # EPILOG += f"{kstr}{vstr[0]} \n"
        # for v_line in vstr[1:]:
        #     EPILOG += f"{' ' * len(kstr)}{v_line} \n"
        # EPILOG += "\n"
    return EPILOG
