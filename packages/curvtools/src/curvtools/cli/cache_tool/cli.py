import argparse
import os
from pathlib import Path
import sys
from typing import Any, Dict
from dotenv import dotenv_values
import re

CACHE_README_FILENAME = "cache_readme.txt"

_BOOL_TRUE  = {"1", "true", "yes", "on", "y", "t"}
_BOOL_FALSE = {"0", "false", "no", "off", "n", "f"}
_INT_RE = re.compile(r'^[\+\-]?(0[xX][0-9a-fA-F_]+|\d[\d_]*)$')

class DefaultValue():
    def __init__(self, default_value: Any, coerce_to_type: type):
        self.coerce_to_type = coerce_to_type
        self.default_value = self.coerce_value(default_value)
    def coerce_value(self, value: Any) -> Any:
        if value is None:
            return None
        value_str = str(value).strip()
        if self.coerce_to_type is int:
            if _INT_RE.match(value_str):
                value_str = value_str.replace("_", "")
                # Avoid int("08", 0) -> ValueError; prefer base 10 unless explicit hex
                base = 0 if value_str.lower().startswith(("+0x", "-0x", "0x")) else 10
                try:
                    return int(value_str, base)
                except ValueError:
                    return value_str  # not an int-looking string; leave it
        elif self.coerce_to_type is bool:
            low = value_str.lower()
            if low in _BOOL_TRUE:
                return True
            if low in _BOOL_FALSE:
                return False
            raise ValueError(f"Invalid boolean literal for env key: '{value_str!r}'")
        elif self.coerce_to_type is type(None):
            if value_str.lower() in {"none"} or value_str == "":
                return None
            return value_str
        elif self.coerce_to_type is str:
            return value_str
        else:
            return value

DEFAULT_ENV_CFG: Dict[str, DefaultValue] = {
    'CFG_CACHE_SETS': DefaultValue(4, int),
    'CFG_CACHE_WAYS': DefaultValue(2, int),
    'CFG_CACHE_CACHEABLE_ADDRESSES_WIDTH': DefaultValue(27, int),
    'CFG_CACHE_CACHELINES_NUM_WORDS': DefaultValue(16, int),
    'CFG_CACHE_CACHELINES_LATENCY': DefaultValue(0, int),
    'CFG_CACHE_CACHELINES_INITIALLY_VALID': DefaultValue(1, bool),
    'CFG_CACHE_TAGS_HAVE_VALID_DIRTY_BITS': DefaultValue(0, bool),
    'CFG_CACHE_HEX_FILES_BASE_ADDR': DefaultValue(0, int),
    'CFG_CACHE_HEX_FILES_SUBDIRS_ICACHE': DefaultValue(None, str),
    'CFG_CACHE_HEX_FILES_SUBDIRS_DCACHE': DefaultValue(None, str),
    'CFG_CACHE_HEX_FILES_SUBDIRS_CACHELINES': DefaultValue(None, str),
    'CFG_CACHE_HEX_FILES_SUBDIRS_TAGRAM': DefaultValue(None, str),
}

def load_env_into_cfg(path: str) -> Dict[str, Any]:
    """
    Load KEY=VALUE pairs from a .env file using python-dotenv, then coerce
    booleans/ints/None where reasonable. Raises if file missing.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f".env file not found: {path}")
    # dotenv handles whitespace, comments, quotes, escapes, interpolation, etc.
    raw = dotenv_values(dotenv_path=p, interpolate=True, encoding="utf-8")

    # raw: dict[str, Optional[str]]
    coerced: Dict[str, Any] = {}
    for k, v in raw.items():
        if k in DEFAULT_ENV_CFG:
            coerced[k] = DEFAULT_ENV_CFG[k].coerce_value(v)
        else:
            coerced[k] = v
    return coerced

def get_defaults(env_file_cfg: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Get defaults, deferring to environment variables (if provided) with lower precedence than env_file_cfg (if provided)
    """

    ret: Dict[str, Any] = {k: DEFAULT_ENV_CFG[k].default_value for k in DEFAULT_ENV_CFG.keys()}

    # environment variables take precedence over defaults
    for k, v in os.environ.items():
        if k in DEFAULT_ENV_CFG:
            ret[k] = DEFAULT_ENV_CFG[k].coerce_value(v)

    # .env file values take precedence over defaults and environment variables
    if env_file_cfg is not None:
        for k, v in env_file_cfg.items():
            if k in DEFAULT_ENV_CFG:
                ret[k] = v
    return ret

def _preparse_env(argv):
    # No -h here; this parser only peeks -e and later becomes a parent for help text
    pre = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    pre.add_argument(
        "-e", "--config-env-file",
        dest="config_env_file",
        metavar="FILE",
        help="Path to .env with defaults (KEY=VALUE)."
    )
    ns, _ = pre.parse_known_args(argv)
    return ns.config_env_file, pre

def auto_int(x: str) -> int:
    # decimal or 0x... hex
    return int(x, 0)

def build_main_parser(defaults: Dict[str, Any] | None, parent: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # build parser
    parser = argparse.ArgumentParser(
        description="Configurable cache tool for 2-way set associative cache",
        parents=[parent],  # makes -e show up in --help
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        allow_abbrev=False,
    )

    parser.add_argument("HEX_FILE", help="Input hex file (32-bit words per line).")
    parser.add_argument("-o", "--output-dir", required=True, help="Output directory.")
    # NOTE: -e comes from the parent; no need to redefine it here.

    cache_config_group = parser.add_argument_group("Cache Configuration")
    cache_config_group.add_argument("--num-sets", "-s", type=int, choices=[4, 8, 16, 32, 64, 128],
                   default=defaults['CFG_CACHE_SETS'],
                   help="Number of sets in the cache, must be a power of 2 between 4 and 128")
    cache_config_group.add_argument("--num-ways", "-w", type=int, choices=[2],
                   default=defaults['CFG_CACHE_WAYS'],
                   help="Number of ways in the cache, currently only 2-way associative is supported")
    cache_config_group.add_argument("--address-width", "-a", type=int,
                   default=defaults['CFG_CACHE_CACHEABLE_ADDRESSES_WIDTH'],
                   help="Width of the highest cacheable address (in bits), must be between 10 and 32")
    cache_config_group.add_argument("--tags-have-valid-dirty-bits",
                   action=argparse.BooleanOptionalAction,
                   default=bool(defaults['CFG_CACHE_TAGS_HAVE_VALID_DIRTY_BITS']),
                   help="Whether tags have two low bits appended: valid, dirty")
    cache_config_group.add_argument("--base-address", "-b", type=auto_int,
                   default=defaults['CFG_CACHE_HEX_FILES_BASE_ADDR'],
                   help="Base address, in bytes (decimal or 0x...). For combined mode, this is the base address of the I$.  For icache-only or dcache-only mode, this is the base address of the I$ or D$ respectively.")
    cache_config_group.add_argument("--cachelines-num-words", "-W", type=int, choices=[16],
                   default=defaults['CFG_CACHE_CACHELINES_NUM_WORDS'],
                   help="Number of 32-bit words per cache line")
    cache_config_group.add_argument("--cachelines-latency", "-l", type=int, choices=[0, 1, 2],
                   default=defaults['CFG_CACHE_CACHELINES_LATENCY'],
                   help="Latency of the cache line, 0: no latency, 1: 1 cycle latency, 2: 2 cycle latency; this affects the type of ram used and therefore fmax")
    cache_config_group.add_argument("--cachelines-initially-valid",
                   action=argparse.BooleanOptionalAction,
                   default=bool(defaults['CFG_CACHE_CACHELINES_INITIALLY_VALID']),
                   help="Whether the cache line is initially valid; set to true if you are prepopulating cache lines from a hex file, false if they will be filled with garbage or zeros")

    output_gen_group = parser.add_argument_group("Output Generation")
    which_mode = output_gen_group.add_mutually_exclusive_group()
    which_mode.add_argument(
        "--mode",
        choices=["icache", "dcache", "combined"],
        default="combined",
        help="which caches to generate: icache means generate I$ only and interpret HEX_FILE input file as the words of I$ only; dcache means the same for D$, and combined means generate both and interpret HEX_FILE as I$ concatenated with D$ (first half of file is I$, second half is D$)"
    )
    # alises for modes enum
    which_mode.add_argument("--icache-only", "-i", dest="mode", action="store_const", const="icache",
                            help="alias for --mode=icache; generate I$ only and interpret HEX_FILE input file as the words of I$ only")
    which_mode.add_argument("--dcache-only", "-d", dest="mode", action="store_const", const="dcache",
                            help="alias for --mode=dcache; generate D$ only and interpret HEX_FILE input file as the words of D$ only")
    which_mode.add_argument("--combined-icache-dcache", "-c", dest="mode", action="store_const", const="combined",
                            help="alias for --mode=combined; generate both I$ and D$ and interpret HEX_FILE input file as I$ concatenated with D$ (first half of file is I$, second half is D$)")
    output_gen_group.add_argument("--no-hex-file-addresses", action="store_true",
                            help="Suppress @-addresses in hex output.")

    subdirs_group = parser.add_argument_group("Output Directory Names")
    subdirs_group.add_argument("--icache-subdir", default=defaults['CFG_CACHE_HEX_FILES_SUBDIRS_ICACHE'])
    subdirs_group.add_argument("--dcache-subdir", default=defaults['CFG_CACHE_HEX_FILES_SUBDIRS_DCACHE'])
    subdirs_group.add_argument("--cachelines-subdir", default=defaults['CFG_CACHE_HEX_FILES_SUBDIRS_CACHELINES'])
    subdirs_group.add_argument("--tagram-subdir", default=defaults['CFG_CACHE_HEX_FILES_SUBDIRS_TAGRAM'])

    readme_group = parser.add_argument_group("Cache README Generation")
    readme_group.add_argument("--cache-readme", default=CACHE_README_FILENAME, help="filename or path of the README file to generate or append to")

    misc_group = parser.add_argument_group("Miscellaneous")
    misc_group.add_argument("--show-config", "-C", action="store_true", help="Show cache configuration and address layout.")
    misc_group.add_argument("-v", "--verbosity", "--verbose", action="count", default=0, help="Verbose output (repeat up to 2).")

    return parser

def parse_args(argv=None):
    argv = sys.argv[1:] if argv is None else argv

    # phase 1: peek at -e without consuming --help
    env_path, parent = _preparse_env(argv)
    if env_path:
        env_file_cfg = load_env_into_cfg(env_path)
    else:
        env_file_cfg = None

    # phase 2: build full parser with env-backed defaults and parse everything (incl --help)
    defaults = get_defaults(env_file_cfg)
    parser = build_main_parser(defaults, parent)
    args = parser.parse_args(argv)

    # validations that argparse can't express directly
    if not os.path.exists(args.output_dir):
        parser.error(f"output directory {args.output_dir} does not exist")
    if not os.path.exists(args.HEX_FILE):
        parser.error(f"input hex file {args.HEX_FILE} does not exist")
    if args.num_sets not in (4, 8, 16, 32, 64, 128):
        parser.error(f"num-sets must be a power of 2 between 4 and 128, got {args.num_sets}")
    if not (10 <= args.address_width <= 32):
        parser.error(f"address-width must be between 10 and 32, got {args.address_width}")

    if args.verbosity >= 1:
        if args.verbosity >= 2:
            if env_file_cfg is not None:
                print("ENVIRONMENT VARIABLES + .env FILE:")
                for k, v in env_file_cfg.items():
                    print(f"  {k}: {v}")
                print()
            else:
                print("ENVIRONMENT VARIABLES (no .env file supplied):")
                for k, v in defaults.items():
                    print(f"  {k}: {v}")
                print()
        print("FINAL ARGUMENTS (after env and CLI overrides):")
        for k, v in args.__dict__.items():
            print(f"  {k}: {v}")
        print()

    return args
