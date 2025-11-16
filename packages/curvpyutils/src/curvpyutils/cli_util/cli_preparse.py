"""
CLI argument preprocessing system

These tools perform an initial parse of the sys.argv[1:] CLI arguments in order to extract values from special arguments 
that may alter how the main CLI parsing occurs.

There are two situations:
  1.  Some arguments set a global value that must override an environment variable of the same name which would otherwise have been used during CLI parsing
        - Mote: `--env-vars`/`-e` files can also provide environment overrides variables, so we read them early looking only for special variables of interest
  2.  Some arguments provide a value that is needed to decide which CLI configuration to use

This library does not attempt to fully parse or validate the CLI arguments. It only extracts a limited number of values
that are needed early and then ensures that those are available before the main CLI parser runs.
"""

import sys
import os
from click.core import ParameterSource
from typing import Optional

class EarlyArg:
  """
  This class represents both a request for an early argument, and the value, if any, that is
  determined for it after preparsing the CLI and environment variables.
  """
  def __init__(self, param_decls: list[str], env_var_fallback: Optional[str] = None, default_value_fallback: Optional[str] = None):

    # these variables are the "request" part

    # list of all the cli flags that are used to provide this early arg
    self.param_decls: list[str] = param_decls
    # environment variable to fall back to if none of the CLI flags are provided
    self.env_var_fallback: Optional[str] = env_var_fallback
    # default value to fall back to if none of the CLI flags or environment variables are provided
    self.default_value_fallback: Optional[str] = default_value_fallback

    # these variables are the result part

    # the value determined for the early arg (initially None). If no value is found, remains None.
    self.value: Optional[str] = None
    # if a value was found, from what source?  if no value was found, remains None.
    self.source: Optional[ParameterSource] = None

  def set_value(self, value: str, source: ParameterSource):
    self.value = value
    self.source = source
  
  def __str__(self):
    return f"EarlyArg(value={str(self.value)}, source={str(self.source)}, param_decls={str(self.param_decls)}, env_var_fallback={str(self.env_var_fallback)}, default_value_fallback={str(self.default_value_fallback)})"

  def __repr__(self):
    return self.__str__()

def preparse(early_args: list[EarlyArg], argv: Optional[list[str]] = sys.argv[1:]) -> None:
  """
  Preprocesses the CLI arguments searching for value for the specified early args.
  If found, the EarlyArg objects are updated.  If not found, they are left unchanged.

  Example usage:
    early_curv_root_dir = EarlyArg(["--curv-root-dir", "-C"], env_var_fallback="CURV_ROOT_DIR")
    early_curv_config = EarlyArg(["--curv-config", "-c"], env_var_fallback="CURV_CONFIG")
    early = [early_curv_root_dir, early_curv_config]

    # Imagine sys.argv = ["prog", "--curv-root-dir", "/path/to/curv"]
    # and os.environ["CURV_CONFIG"] = "release"
    preparse(early)

    After preparsing, early_curv_root_dir.value will be "/path/to/curv" (with 
    early_curv_root_dir.source set to ParameterSource.COMMANDLINE) and early_curv_config.value 
    will be "release" (with early_curv_config.source set to ParameterSource.ENVIRONMENT).

  Args:
    early_args: list of EarlyArg objects to preparse and fill in with values if found.
    argv: optional list of CLI arguments to use instead of sys.argv[1:]. (This is for tests.)
      If not provided, sys.argv[1:] is used.
      If provided, the argv list is used as-is, so it is the caller's responsibility to ensure that the
      argv list is valid and complete.
  Return:
    None.  The EarlyArg objects are mutated in place.
  """
  import argparse

  # Build a minimal parser that only knows about the early args
  parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
  dests: list[str] = []

  for idx, early_arg in enumerate(early_args):
      dest = f"early_arg_{idx}" # unique destination name for this early arg
      dests.append(dest)
      parser.add_argument(*early_arg.param_decls, dest=dest)  # store one value

  # Parse only what we know; leave the rest unparsed
  ns, _unknown = parser.parse_known_args(argv)

  # Set values from the command line when present
  for idx, early_arg in enumerate(early_args):
      dest = dests[idx]
      val = getattr(ns, dest, None)
      if val is not None:
          early_arg.set_value(val, ParameterSource.COMMANDLINE)

  # Apply environment fallbacks only where still unset
  for early_arg in early_args:
      if early_arg.value is None and early_arg.env_var_fallback:
          env_val = os.getenv(early_arg.env_var_fallback)
          if env_val is not None:
              early_arg.set_value(env_val, ParameterSource.ENVIRONMENT)

  # Apply default value fallbacks only where still unset
  for early_arg in early_args:
      if early_arg.value is None and early_arg.default_value_fallback:
          default_val = early_arg.default_value_fallback
          if default_val is not None:
              early_arg.set_value(default_val, ParameterSource.DEFAULT)

  # No return needed; objects were mutated in place


__all__ = [
  "preparse",
  "EarlyArg",
]
