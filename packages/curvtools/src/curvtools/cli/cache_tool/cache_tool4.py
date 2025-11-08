#! /usr/bin/env python3

#
# Simplified version of cache_tool.py.
#
# Reads in a hex file with 32-bit words addressed 0 to 0x3FF.
# The addresses are in bytes for $readmemh() and optionally prefixed with @-addresses.
#
# We build the ram initialization files for the cache line memory and the tag memory.
#
# The cache is a 2-way set associative cache with 16-word cache lines and as many sets
# as are specified in the configuration (min 4, max 128, must be a power of 2).
#

import os
import sys
from .addresses import create_configurable_address_classes
from .cache import ConfigurableCacheRam, create_memory_class
from .cache_config import CacheConfig
from .cache_type import CacheType
from .cli import parse_args
from curvpyutils.colors.ansi import AnsiColorsTool
from curvpyutils.shellutils import print_delta
from curvpyutils.file_utils import read_hex_file_as_ints

def get_cache_hex_file_names(config: CacheConfig, icache_subdir: str = None, dcache_subdir: str = None, cachelines_subdir: str = None, tagram_subdir: str = None, omit_set_number_in_file_name: bool = False) -> dict[CacheType, dict[str, list[str]]]:
    """
    Generate cache hex file names based on configuration.
    """

    def get_relpaths() -> dict[str, str]:
        ret = {}

        icache_subdir_with_slash = icache_subdir if icache_subdir is not None else ""
        icache_subdir_with_slash += "/" if icache_subdir_with_slash != "" and not icache_subdir_with_slash.endswith("/") else ""

        dcache_subdir_with_slash = dcache_subdir if dcache_subdir is not None else ""
        dcache_subdir_with_slash += "/" if dcache_subdir_with_slash != "" and not dcache_subdir_with_slash.endswith("/") else ""

        cachelines_subdir_with_slash = cachelines_subdir if cachelines_subdir is not None else ""
        cachelines_subdir_with_slash += "/" if cachelines_subdir_with_slash != "" and not cachelines_subdir_with_slash.endswith("/") else ""

        tagram_subdir_with_slash = tagram_subdir if tagram_subdir is not None else ""
        tagram_subdir_with_slash += "/" if tagram_subdir_with_slash != "" and not tagram_subdir_with_slash.endswith("/") else ""

        icache_cachelines_relpath = icache_subdir_with_slash + cachelines_subdir_with_slash
        dcache_cachelines_relpath = dcache_subdir_with_slash + cachelines_subdir_with_slash
        icache_tagram_relpath = icache_subdir_with_slash + tagram_subdir_with_slash
        dcache_tagram_relpath = dcache_subdir_with_slash + tagram_subdir_with_slash

        ret["icache_cachelines_relpath"] = icache_cachelines_relpath
        ret["dcache_cachelines_relpath"] = dcache_cachelines_relpath
        ret["icache_tagram_relpath"] = icache_tagram_relpath
        ret["dcache_tagram_relpath"] = dcache_tagram_relpath
        return ret

    if not omit_set_number_in_file_name:
        suffix = config.get_file_suffix()
    else:
        suffix = ""

    relpaths = get_relpaths()

    get_file_name = lambda icache_or_dcache_str, suffix, way_number: f"{icache_or_dcache_str}{suffix}_way{way_number}.hex" if suffix != "" else f"way{way_number}.hex"

    get_file_path_by_key = lambda key_name, icache_or_dcache_str, suffix, way_number: (relpaths[key_name] if relpaths[key_name] != "" else "") + get_file_name(icache_or_dcache_str, suffix, way_number)

    return {
        CacheType.DCACHE: {
            "cache_line_ram": [ get_file_path_by_key("dcache_cachelines_relpath", "dcache", suffix, 0),
                                get_file_path_by_key("dcache_cachelines_relpath", "dcache", suffix, 1)],
            "tag_ram": [ get_file_path_by_key("dcache_tagram_relpath", "dcache", suffix, 0),
                         get_file_path_by_key("dcache_tagram_relpath", "dcache", suffix, 1)],
        },
        CacheType.ICACHE: {
            "cache_line_ram": [ get_file_path_by_key("icache_cachelines_relpath", "icache", suffix, 0),
                                get_file_path_by_key("icache_cachelines_relpath", "icache", suffix, 1)],
            "tag_ram": [ get_file_path_by_key("icache_tagram_relpath", "icache", suffix, 0),
                         get_file_path_by_key("icache_tagram_relpath", "icache", suffix, 1)],
        },
    }

def make_dirs(cache_hex_file_names: dict[str, list[str]], output_dir: str):
    for k,v in cache_hex_file_names.items():
        for path in v:
            os.makedirs(os.path.join(output_dir, os.path.dirname(path)), exist_ok=True)

def load_memory_from_hex_file(hex_file_path:str, base_address:int=0, SystemAddressCls=None):
    """
    Reads a hex file and returns a memory object.

    The hex file is assumed to be a Verilog $readmemh() hex file with 32-bit words.
    We assume any @-prefixed addresses in the file are word offsets, not byte offsets.

    The base_address is the starting address of the memory, i.e., the address of the first word
    in the memory.  base_address should be in bytes.
    """
    if SystemAddressCls is None:
        raise ValueError("SystemAddressCls must be provided")
    Memory  = create_memory_class(SystemAddressCls)
    memory = Memory()
    # base_address_in_words = base_address // 4
    words = read_hex_file_as_ints(hex_file_path, base_address=base_address, file_addresses_in_bytes=False)
    for i, word in enumerate(words):
        address = base_address + i*4
        memory[address] = word
    return memory


def main():
    args = parse_args()

    # Create cache configuration
    try:
        config = CacheConfig(num_sets=args.num_sets, 
                            address_width=args.address_width, 
                            tags_have_valid_dirty_bits=args.tags_have_valid_dirty_bits, 
                            write_hex_files_with_addresses=not args.no_hex_file_addresses,
                            num_ways=args.num_ways,
                            words_per_line=args.cachelines_num_words)
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Show configuration if requested
    if args.show_config or args.verbosity > 0:
        config.print_layout()
        print()

    # disable colors if output is not a terminal
    enable_colors = sys.stdout.isatty()
    enable_colors_stderr = sys.stderr.isatty()

    # Enforce cache-line alignment for the base address to ensure offset==0 at line starts
    cache_line_size = config.words_per_line * 4
    if args.base_address % cache_line_size != 0:
        print(f"base-address 0x{args.base_address:08x} must be cache-line aligned ({cache_line_size} bytes)")
        sys.exit(1)

    # Read in the hex file
    hex_file_path = args.HEX_FILE
    CACHE_HEX_FILE_DIR = args.output_dir
    # Create output directories if they don't exist
    os.makedirs(CACHE_HEX_FILE_DIR, exist_ok=True)
    # Create configurable address classes for this configuration
    Tag, Index, Offset, SystemAddress = create_configurable_address_classes(config)

    memory = load_memory_from_hex_file(hex_file_path, base_address=args.base_address, SystemAddressCls=SystemAddress)
    if args.verbosity >= 2:
        print("Memory contents read from hex file:")
        for addr, word in memory.items():
            print(f"{addr.hex(width=8, omit_prefix=True)}: {word.hex(width=8, omit_prefix=True)}")

    # Use configurable implementation
    if args.verbosity >= 1:
        print(f"Using configurable cache implementation: {config}")
    cache_hex_file_names = get_cache_hex_file_names(config, icache_subdir=args.icache_subdir, dcache_subdir=args.dcache_subdir, cachelines_subdir=args.cachelines_subdir, tagram_subdir=args.tagram_subdir, omit_set_number_in_file_name=True)
    if args.mode == "combined" or args.mode == "icache":
        make_dirs(cache_hex_file_names[CacheType.ICACHE], args.output_dir)
    if args.mode == "combined" or args.mode == "dcache":
        make_dirs(cache_hex_file_names[CacheType.DCACHE], args.output_dir)

    # Prepare README output path at root of output dir
    readme_path = args.cache_readme if os.path.isabs(args.cache_readme) else os.path.join(CACHE_HEX_FILE_DIR, args.cache_readme)

    # Calculate memory sizes based on configuration
    memory_per_cache = config.num_sets * config.words_per_line * 4
    total_memory_per_cache = memory_per_cache * config.num_ways  # Total memory for both ways

    if args.mode == "combined":
        icache = ConfigurableCacheRam(config, CacheType.ICACHE, CACHE_HEX_FILE_DIR, cache_hex_file_names[CacheType.ICACHE], Tag, Index, Offset, SystemAddress)
        dcache = ConfigurableCacheRam(config, CacheType.DCACHE, CACHE_HEX_FILE_DIR, cache_hex_file_names[CacheType.DCACHE], Tag, Index, Offset, SystemAddress)

        # if we're generating both, assuming memory is split into two halves (I$ then D$)
        icache.load_cache_ram(memory.get_sub_memory(args.base_address, total_memory_per_cache//4), starting_offset_into_hex_file=args.base_address, dirty=False, valid=args.cachelines_initially_valid)
        dcache.load_cache_ram(memory.get_sub_memory(args.base_address + total_memory_per_cache, total_memory_per_cache//4), starting_offset_into_hex_file=args.base_address + total_memory_per_cache, dirty=False, valid=args.cachelines_initially_valid)

        assert isinstance(icache, ConfigurableCacheRam) and isinstance(dcache, ConfigurableCacheRam)

        # display cache RAM table to stderr if verbosity is set
        if args.verbosity > 0:
            icache.print_cache_ram_table(enable_colors=enable_colors_stderr, print_to_file=sys.stderr)
            dcache.print_cache_ram_table(enable_colors=enable_colors_stderr, print_to_file=sys.stderr)

        # write cache README header and tables to file (no ANSI colors)
        with open(readme_path, 'w') as readme:
            print("cache_hex_file_names:", file=readme)
            data = cache_hex_file_names[CacheType.ICACHE]
            for k2, v2 in data.items():
                print(f"  {CacheType.ICACHE}.{k2}: {v2}", file=readme)
            icache.print_cache_ram_table(enable_colors=False, print_to_file=readme)
            print("cache_hex_file_names:", file=readme)
            data = cache_hex_file_names[CacheType.DCACHE]
            for k2, v2 in data.items():
                print(f"  {CacheType.DCACHE}.{k2}: {v2}", file=readme)
            dcache.print_cache_ram_table(enable_colors=False, print_to_file=readme)

        # write hex files
        icache.write_hex_files(verbosity=args.verbosity)
        dcache.write_hex_files(verbosity=args.verbosity)
    elif args.mode == "icache":
        icache = ConfigurableCacheRam(config, CacheType.ICACHE, CACHE_HEX_FILE_DIR, cache_hex_file_names[CacheType.ICACHE], Tag, Index, Offset, SystemAddress)

        # if we're generating only icache, assuming memory is only I$
        icache.load_cache_ram(memory.get_sub_memory(args.base_address, total_memory_per_cache//4), starting_offset_into_hex_file=args.base_address, dirty=False, valid=args.cachelines_initially_valid)

        assert isinstance(icache, ConfigurableCacheRam)

        # display cache RAM table to stderr if verbosity is set
        if args.verbosity > 0:
            icache.print_cache_ram_table(enable_colors=enable_colors_stderr, print_to_file=sys.stderr)

        # write cache README section for icache
        with open(readme_path, 'a') as readme:
            print("cache_hex_file_names:", file=readme)
            data = cache_hex_file_names[CacheType.ICACHE]
            for k2, v2 in data.items():
                print(f"  {CacheType.ICACHE}.{k2}: {v2}", file=readme)
            icache.print_cache_ram_table(enable_colors=False, print_to_file=readme)

        # write hex files
        icache.write_hex_files(verbosity=args.verbosity)
    elif args.mode == "dcache":
        dcache = ConfigurableCacheRam(config, CacheType.DCACHE, CACHE_HEX_FILE_DIR, cache_hex_file_names[CacheType.DCACHE], Tag, Index, Offset, SystemAddress)

        # if we're generating only dcache, assuming memory is only D$
        dcache.load_cache_ram(memory.get_sub_memory(args.base_address, total_memory_per_cache//4), starting_offset_into_hex_file=args.base_address, dirty=False, valid=args.cachelines_initially_valid)

        assert isinstance(dcache, ConfigurableCacheRam)

        # display cache RAM table to stderr if verbosity is set
        if args.verbosity > 0:
            dcache.print_cache_ram_table(enable_colors=enable_colors_stderr, print_to_file=sys.stderr)

        # write cache README section for dcache
        with open(readme_path, 'a') as readme:
            print("cache_hex_file_names:", file=readme)
            data = cache_hex_file_names[CacheType.DCACHE]
            for k2, v2 in data.items():
                print(f"  {CacheType.DCACHE}.{k2}: {v2}", file=readme)
            dcache.print_cache_ram_table(enable_colors=False, print_to_file=readme)

        # write hex files
        dcache.write_hex_files(verbosity=args.verbosity)

if __name__ == "__main__":
    main()