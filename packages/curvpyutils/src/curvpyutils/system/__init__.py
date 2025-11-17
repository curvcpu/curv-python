"""System utilities."""

from .nprocs import get_nprocs
from .ulimits import (
    get_max_memory_kb,
    get_recursion_limit,
    get_stack_limit,
    raise_recursion_limit,
    raise_stack_limit,
)
from .user_config_file import UserConfigFile

__all__ = [
    "get_nprocs",
    "get_max_memory_kb",
    "raise_recursion_limit",
    "get_recursion_limit",
    "get_stack_limit",
    "raise_stack_limit",
    "UserConfigFile",
]

