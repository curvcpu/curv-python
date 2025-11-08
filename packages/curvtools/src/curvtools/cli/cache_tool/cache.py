from math import log2
import math
import re
from sys import stderr
import sys
from typing import Any, TextIO
from .addresses import Int32b, make_bits_class
from .cache_type import CacheType
from .cache_config import CacheConfig
import os
from collections.abc import Mapping

COLOR_WHITE = "\033[1;97m"
COLOR_BRIGHT_BLUE = "\033[1;94m"
COLOR_GREEN = "\033[1;92m"
COLOR_GRAY = "\033[1;90m"
COLOR_BLUE = "\033[1;34m"
COLOR_RED = "\033[1;91m"
COLOR_RESET = "\033[0m"
COLOR_MAGENTA = "\033[1;95m"
COLOR_YELLOW = "\033[1;93m"
COLOR_CYAN = "\033[1;96m"
COLOR_BKG_WHITE = "\033[47m"
COLOR_BKG_GRAY = "\033[48;5;240m"
COLOR_BKG_BLACK = "\033[48;5;232m"
COLOR_BOLD = "\033[1m"
COLOR_PURPLE = "\033[1;95m"

COLORS = {
    "white": COLOR_WHITE,
    "bright_blue": COLOR_BRIGHT_BLUE,
    "green": COLOR_GREEN,
    "blue": COLOR_BLUE,
    "gray": COLOR_GRAY,
    "red": COLOR_RED,
    "magenta": COLOR_MAGENTA,
    "yellow": COLOR_YELLOW,
    "cyan": COLOR_CYAN,
    "bkg_white": COLOR_BKG_WHITE,
    "bkg_gray": COLOR_BKG_GRAY,
    "bkg_black": COLOR_BKG_BLACK,
    "reset": COLOR_RESET,
    "bold": COLOR_BOLD,
    "purple": COLOR_PURPLE
}

def create_memory_class(SystemAddressCls):
    """
    Factory that creates a dict-backed memory class for a specific SystemAddressCls.

    The resulting Memory2 behaves like dict[SystemAddressCls, Int32b] and provides
    small conveniences for int keys/values and range/subset helpers.
    """

    class Memory(dict):  # type: ignore[type-arg]
        def __init__(self):
            self.SystemAddress = SystemAddressCls
            super().__init__()

        def _coerce_address(self, address):
            if isinstance(address, self.SystemAddress):
                return address
            if isinstance(address, int):
                return self.SystemAddress(address)
            raise TypeError(f"address must be {self.SystemAddress.__name__} or int, got {type(address)}")

        def _coerce_value(self, value):
            if isinstance(value, Int32b):
                return value
            if isinstance(value, int):
                return Int32b(value)
            raise TypeError(f"value must be Int32b or int, got {type(value)}")

        def __setitem__(self, key, value):
            super().__setitem__(self._coerce_address(key), self._coerce_value(value))

        def __getitem__(self, key):
            return super().__getitem__(self._coerce_address(key))

        def __contains__(self, key):
            try:
                coerced = self._coerce_address(key)
            except TypeError:
                return False
            return super().__contains__(coerced)

        def add_word(self, address, data_int: int):
            self[address] = data_int

        def get_words_in_range(self, start_address, num_words: int = 16, step: int = 4) -> list[Int32b]:
            start = self._coerce_address(start_address)
            return [self[start + i * step] for i in range(num_words)]

        def get_sub_memory(self, start_address, num_words: int):
            start = self._coerce_address(start_address)
            sub = type(self)()
            for i in range(num_words):
                addr = start + i * 4
                # will raise KeyError if missing, mirroring Memory behavior
                sub[addr] = self[addr]
            return sub

    def __str__(self):
        ret = "\n"
        for addr, word in self.items():
            ret += f"{addr.hex(width=8, omit_prefix=True)}: {word.data.hex(width=8, omit_prefix=True)}\n"
        return ret

    return Memory

# Configurable Cache Implementation
class ConfigurableCacheRam:
    """
    Configurable cache RAM implementation that supports variable address widths and number of sets.
    """

    def __init__(self, config: CacheConfig, cache_type: CacheType, hex_files_dir: str, file_names: dict[str, list[str]], Tag, Index, Offset, SystemAddress):
        self.config = config
        self.cache_type = cache_type
        self.hex_files_dir = hex_files_dir
        self.file_names = file_names
        
        # Use provided configurable address classes
        self.Tag = Tag
        self.Index = Index
        self.Offset = Offset
        self.SystemAddress = SystemAddress

        # Initialize cache ways
        self.ways: list['ConfigurableCacheRam.ConfigurableCacheWay'] = []
        for way_index in range(config.num_ways):
            cache_line_ram_file_name = file_names['cache_line_ram'][way_index]
            cache_line_ram_file_output_path = os.path.join(hex_files_dir, cache_line_ram_file_name)
            tag_ram_file_name = file_names['tag_ram'][way_index]
            tag_ram_file_output_path = os.path.join(hex_files_dir, tag_ram_file_name)
            self.ways.append(ConfigurableCacheRam.ConfigurableCacheWay(
                way_number=way_index,
                cache_line_ram_file_output_path=cache_line_ram_file_output_path,
                tag_ram_file_output_path=tag_ram_file_output_path,
                config=config,
                Tag=self.Tag,
                Index=self.Index,
                Offset=self.Offset,
                SystemAddress=self.SystemAddress
            ))

    class ConfigurableCacheLineRam:
        """Configurable cache line implementation."""

        def __init__(self, start_address, data_words: list[Int32b], config: CacheConfig, Tag, Index, Offset, SystemAddress, dirty: bool = True, valid: bool = True):
            assert len(data_words) == config.words_per_line, f"Cache line must have {config.words_per_line} words"

            # Ensure start address is of configurable type and aligned
            if isinstance(start_address, int):
                start_addr = SystemAddress(start_address)
            else:
                start_addr = start_address
            assert start_addr.offset().value == 0, "Cache line must start at aligned address boundary (offset = 0)"

            self.config = config
            self.Tag = Tag
            self.Index = Index
            self.Offset = Offset
            self.SystemAddress = SystemAddress
            self.start_address = start_addr
            self.words = data_words
            self.tag_mem_data = ConfigurableCacheRam.ConfigurableTagMemData(
                self._compute_tag(), config, Tag, dirty=dirty, valid=valid
            )

        def _compute_index(self):
            return self.start_address.index()

        def _compute_tag(self):
            return self.start_address.tag()

        def _compute_offset(self, word_index: int = 0):
            addr = self.start_address + word_index * 4
            return addr.offset()

        @property
        def index(self):
            return self._compute_index()

        @property
        def tag(self):
            return self._compute_tag()

        @property
        def dirty(self):
            return self.tag_mem_data.dirty

        @dirty.setter
        def dirty(self, value):
            self.tag_mem_data.dirty = value

        @property
        def valid(self):
            return self.tag_mem_data.valid

        @valid.setter
        def valid(self, value):
            self.tag_mem_data.valid = value

        def tag_split(self):
            return self.tag_mem_data.split()

        def __str__(self):
            return "\n".join([str(word) for word in self.words]) + f"\ntag_mem_data: {str(self.tag_mem_data)}"

    class ConfigurableTagMemData:
        """Configurable tag memory data with variable tag width."""

        def __init__(self, tag, config: CacheConfig, Tag, dirty: bool = True, valid: bool = True):
            self.config = config
            self.Tag = Tag
            self._tag = tag if isinstance(tag, Tag) else Tag(tag)
            self.dirty = dirty if self.config.tags_have_valid_dirty_bits else None
            self.valid = valid if self.config.tags_have_valid_dirty_bits else None

            # Create combined bit representation
            total_width = config.tag_bits
            if self.config.tags_have_valid_dirty_bits:
                total_width += 2
            self.CombinedBits = make_bits_class(total_width)

            # Build combined value
            combined_value = self._tag.value
            if self.config.tags_have_valid_dirty_bits:
                combined_value = (combined_value << 2) | (1 if valid else 0) | (1 if dirty else 0)

            self.combined_bits = self.CombinedBits(combined_value)

        @property
        def tag(self):
            return self._tag

        def split(self):
            if self.config.tags_have_valid_dirty_bits:
                return self._tag, self.dirty, self.valid
            else:
                return self._tag, None, None

        def bin(self, width: int = None, omit_suffix: bool = False):
            return self.combined_bits.bin(width=width, omit_suffix=omit_suffix)

        def hex(self, width: int = None, omit_prefix: bool = False):
            return self.combined_bits.hex(width=width, omit_prefix=omit_prefix)

        def __str__(self):
            return f"Tag: {self.combined_bits}, dirty: {self.dirty if self.config.tags_have_valid_dirty_bits else 'N/A'}, valid: {self.valid if self.config.tags_have_valid_dirty_bits else 'N/A'}"

        def __repr__(self):
            return f"ConfigurableTagMemData({self.combined_bits}, dirty: {self.dirty if self.config.tags_have_valid_dirty_bits else 'N/A'}, valid: {self.valid if self.config.tags_have_valid_dirty_bits else 'N/A'})"

    class ConfigurableTagRam(Mapping):
        """Configurable tag RAM."""

        def __init__(self, config: CacheConfig, Index):
            self.config = config
            self.Index = Index
            self.tag_ram: dict[Index, 'ConfigurableCacheRam.ConfigurableTagMemData'] = {}

        def add_tag(self, addr: 'Index', tag_data: 'ConfigurableCacheRam.ConfigurableTagMemData'): # type: ignore
            if addr in self.tag_ram:
                raise ValueError("Tag already exists at this address")
            self.tag_ram[addr] = tag_data

        def __str__(self):
            return "\n".join([f"{addr}: {data}" for addr, data in self.tag_ram.items()])

        def __iter__(self):
            return iter(self.tag_ram)

        def __getitem__(self, index):
            return self.tag_ram[index]

        def __len__(self) -> int:
            return len(self.tag_ram)

    class ConfigurableCacheWay:
        """Configurable cache way."""

        def __init__(self, way_number: int, cache_line_ram_file_output_path: str, tag_ram_file_output_path: str,
                     config: CacheConfig, Tag, Index, Offset, SystemAddress):
            self.way_number = way_number
            self.cache_line_ram_file_output_path = cache_line_ram_file_output_path
            self.tag_ram_file_output_path = tag_ram_file_output_path
            self.config = config
            self.Tag = Tag
            self.Index = Index
            self.Offset = Offset
            self.SystemAddress = SystemAddress
            self.cache_lines: list['ConfigurableCacheRam.ConfigurableCacheLineRam'] = []
            self.tag_ram = ConfigurableCacheRam.ConfigurableTagRam(config, Index)

        def add_cache_line(self, cache_line: 'ConfigurableCacheRam.ConfigurableCacheLineRam'):
            self.cache_lines.append(cache_line)
            tag_addr = self.Index(cache_line.index.value)
            tag_data = ConfigurableCacheRam.ConfigurableTagMemData(
                cache_line.tag, self.config, self.Tag, dirty=cache_line.dirty, valid=cache_line.valid
            )
            self.tag_ram.add_tag(tag_addr, tag_data)

        def write_hex_files(self, verbosity: int = 0) -> None:
            # Write cache line RAM file
            outstr = ""
            for cache_line in self.cache_lines:
                for i, data_word in enumerate(cache_line.words):
                    word_addr = cache_line.start_address + i * 4
                    addr = cache_line.index.append(word_addr.offset())
                    addr_str_hex = f"{addr.hex(width=max(2, (self.config.index_bits + self.config.offset_bits + 3) // 4), omit_prefix=True)}"
                    data_word_str_hex = f"{data_word.hex(width=8, omit_prefix=True)}"
                    if self.config.write_hex_files_with_addresses:
                        outstr += f"@{addr_str_hex.upper()}\n"
                    outstr += f"{data_word_str_hex}\n"
            if verbosity > 0:
                print(f"writing {self.cache_line_ram_file_output_path}", file=stderr)
                if verbosity > 1:
                    print(outstr, file=stderr)
            with open(self.cache_line_ram_file_output_path, "w") as f:
                f.write(outstr)

            # Write tag RAM file
            outstr = ""
            for tag_addr, tag_data in self.tag_ram.tag_ram.items():
                tag_data_str_bin = f"{tag_data.bin(width=self.config.tag_bits + (2 if self.config.tags_have_valid_dirty_bits else 0), omit_suffix=True)}"
                outstr += f"{tag_data_str_bin}\n"

            if verbosity > 0:
                print(f"writing {self.tag_ram_file_output_path}", file=stderr)
                if verbosity > 1:
                    print(outstr, file=stderr)
            with open(self.tag_ram_file_output_path, "w") as f:
                f.write(outstr)

        def print_cache_ram_way_table(self, title: str, enable_colors: bool = False, print_to_file: TextIO | None = None):
            s = build_configurable_cache_way_table(self, self.way_number, title, self.config, enable_colors=enable_colors)
            if print_to_file is not None:
                print(s, file=print_to_file)
            else:
                print(s)

    def load_cache_ram(self, memory, starting_offset_into_hex_file: int = 0x0000, dirty: bool = True, valid: bool = True):
        """Load cache RAM from memory."""
        for i in range(self.config.num_ways):
            for j in range(self.config.num_sets):
                memory_per_way = (self.config.num_sets * self.config.words_per_line * 4)

                # For each way, cache lines are sequential
                # Way 0: starting_offset + j * cache_line_size
                # Way 1: (starting_offset + memory_per_way) + j * cache_line_size
                cache_line_size = self.config.words_per_line * 4
                start_address = starting_offset_into_hex_file + i * memory_per_way + j * cache_line_size

                data_words = memory.get_words_in_range(start_address=start_address, num_words=self.config.words_per_line)
                cache_line = ConfigurableCacheRam.ConfigurableCacheLineRam(
                    start_address,
                    data_words,
                    self.config, self.Tag, self.Index, self.Offset, self.SystemAddress,
                    dirty=dirty, valid=valid
                )
                self.ways[i].add_cache_line(cache_line)

    def print_cache_ram_table(self, enable_colors: bool = False, print_to_file: TextIO = None):
        for way in self.ways:
            way.print_cache_ram_way_table(
                title="I$" if self.cache_type == CacheType.ICACHE else "D$",
                enable_colors=enable_colors,
                print_to_file=print_to_file
            )

    def write_hex_files(self, verbosity: int = 0):
        for way in self.ways:
            way.write_hex_files(verbosity=verbosity)

def build_configurable_cache_way_table(cache_way: 'ConfigurableCacheRam.ConfigurableCacheWay', way_num: int, title: str, config: CacheConfig, enable_colors: bool = True) -> str:
    """Build table display for configurable cache way."""
    indent = "  "
    COLOR_WHITE = "\033[1;97m"
    COLOR_GREEN = "\033[1;92m"
    COLOR_BLUE = "\033[1;34m"
    COLOR_BRIGHT_BLUE = "\033[1;94m"
    COLOR_RED = "\033[1;91m"
    COLOR_RESET = "\033[0m"
    COLOR_MAGENTA = "\033[1;95m"
    COLOR_YELLOW = "\033[1;93m"
    COLOR_CYAN = "\033[1;96m"
    COLOR_BKG_WHITE = "\033[47m"
    COLOR_BKG_GRAY = "\033[48;5;240m"
    COLOR_BKG_BLACK = "\033[48;5;232m"
    COLOR_BOLD = "\033[1m"

    index_field_width = 0
    tag_field_width = 0

    def colorize_index_str(index_str: str) -> str:
        return f"{COLOR_MAGENTA}{index_str}{COLOR_RESET}"
    def colorize_tag_str(tag_str: str) -> str:
        return f"{COLOR_GREEN}{tag_str}{COLOR_RESET}"
    def colorize_offset_str(offset_str: str) -> str:
        return f"{COLOR_CYAN}{offset_str}{COLOR_RESET}"
    def colorize_0x_str(zero_x_str: str) -> str:
        return f"{COLOR_RESET}{zero_x_str}{COLOR_RESET}"
    def colorize_dirty_str(dirty_str: str) -> str:
        if dirty_str == "1":
            return f"{COLOR_RED}{dirty_str}{COLOR_RESET}"
        else:
            return f"{COLOR_WHITE}{dirty_str}{COLOR_RESET}"
    def colorize_valid_str(valid_str: str) -> str:
        if valid_str == "1":
            return f"{COLOR_WHITE}{valid_str}{COLOR_RESET}"
        else:
            return f"{COLOR_RED}{valid_str}{COLOR_RESET}"
    def colorize_hex_hword_str(hex_hword_str: str) -> str:
        return f"{COLOR_WHITE}{hex_hword_str}{COLOR_RESET}"
    def colorize_system_hex_address_str(system_address_str: str, include_0x: bool = True) -> str:
        match = re.match(r's*(0x[\s\_]*)?([0-9a-fA-F]{4})([\s\_]*)([0-9a-fA-F]{4})(.*)$', system_address_str)
        if match is None:
            raise ValueError(f"system_address_str: '{system_address_str}' is not a valid system address string")
        parts = {"0x": match.group(1),
                "high_hword": match.group(2),
                "sep1": match.group(3),
                "low_hword": match.group(4),
                "unused": match.group(5)}
        if include_0x:
            ret = f"{colorize_0x_str(parts['0x'])}{colorize_hex_hword_str(parts['high_hword'])}{parts['sep1']}{colorize_hex_hword_str(parts['low_hword'])}{parts['unused']}"
        else:
            ret = f"   {colorize_hex_hword_str(parts['high_hword'])}{parts['sep1']}{colorize_hex_hword_str(parts['low_hword'])}{parts['unused']}"
        return ret
    def colorize_title_str(title_str: str) -> str:
        match = re.match(r'^(\s*)([\s\S]*?)(\s*)$', title_str)
        if match is None:
            return title_str
        else:
            parts = {"leading_spaces": match.group(1), "title": match.group(2), "trailing_spaces": match.group(3)}
            return f"{parts['leading_spaces']}{COLOR_GREEN}{COLOR_BKG_GRAY}{parts['title']}{COLOR_RESET}{COLOR_RESET}{parts['trailing_spaces']}"
    def colorize_cache_line_data_str(cache_line_data_str: str) -> str:
        match = re.match(r'^(\s*)([\s\S]*?)(\s*)$', cache_line_data_str)
        if match is None:
            return cache_line_data_str
        else:
            parts = {"leading_spaces": match.group(1), "cache_line_data": match.group(2), "trailing_spaces": match.group(3)}
            return f"{parts['leading_spaces']}{COLOR_YELLOW}{COLOR_BKG_BLACK}{parts['cache_line_data']}{COLOR_RESET}{COLOR_RESET}{parts['trailing_spaces']}"

    def colorize_configurable_addr_string(bit_string: str) -> str:
        """Colorize address string based on configurable bit layout."""
        # Find separators
        has_sep = bit_string.find("_") != -1 or bit_string[0:config.address_width].strip().find(" ") != -1
        if has_sep:
            # Handle separated format
            tag_end = config.tag_bits
            index_end = tag_end + 1 + config.index_bits
            offset_end = index_end + config.offset_bits
            parts = {
                "tag": bit_string[0:tag_end],
                "sep1": bit_string[tag_end:tag_end+1],
                "index": bit_string[tag_end+1:index_end],
                "offset": bit_string[index_end:offset_end],
                "unused": bit_string[offset_end:]
            }
            bit_string = colorize_tag_str(parts['tag']) + parts['sep1'] + colorize_index_str(parts['index']) + colorize_offset_str(parts['offset']) + parts['unused']
        else:
            # Handle unseparated format
            tag_end = config.tag_bits
            index_end = tag_end + config.index_bits
            offset_end = index_end + config.offset_bits
            parts = {
                "tag": bit_string[0:tag_end],
                "index": bit_string[tag_end:index_end],
                "offset": bit_string[index_end:offset_end],
                "unused": bit_string[offset_end:]
            }
            bit_string = colorize_tag_str(parts['tag']) + colorize_index_str(parts['index']) + colorize_offset_str(parts['offset']) + parts['unused']
        if bit_string.endswith("b"):
            bit_string = bit_string[:-1]
            bit_string = bit_string + f"{COLOR_RESET}b{COLOR_RESET}"
        return bit_string

    def build_header_lines(way_num: int) -> list[str]:
        idx_centered_str = "Idx"
        tag_centered_str = "Tag"
        ConfigurableCacheRam.index_field_width = max(config.index_bits, len(idx_centered_str))
        ConfigurableCacheRam.tag_field_width = max(config.tag_bits, len(tag_centered_str))
        full_title = f"{title} - Way {way_num}".center(29+config.tag_bits+ConfigurableCacheRam.index_field_width)
        cacheline_data_title_str = "Cache Line Data (words @ offset within hex file)".center(59+60)
        cfg_str = f"Bits: tag={config.tag_bits}, idx={config.index_bits}, off={config.offset_bits}".center(26+config.tag_bits+ConfigurableCacheRam.index_field_width)
        cfg_str2 = f"for {config.address_width} bit addresses"
        cfg_str2 = cfg_str2.center(26+config.tag_bits+ConfigurableCacheRam.index_field_width)
        idx_centered_str = idx_centered_str.center(ConfigurableCacheRam.index_field_width)
        tag_centered_str = tag_centered_str.center(ConfigurableCacheRam.tag_field_width)
        if enable_colors:
            full_title = colorize_title_str(full_title)
            cacheline_data_title_str = colorize_cache_line_data_str(cacheline_data_title_str)
        lines = []
        lines.append(f"{indent}+-{'-'*ConfigurableCacheRam.index_field_width}-+---+---+-{'-'*(ConfigurableCacheRam.tag_field_width+ConfigurableCacheRam.index_field_width)}--------------+-------------" + f"-" * (123-17) + f"+\n")
        lines.append(f"{indent}|{full_title}|{cacheline_data_title_str}|\n")
        lines.append(f"{indent}|  {COLOR_BOLD if enable_colors else ''}{cfg_str}{COLOR_RESET if enable_colors else ''} |" + f"--------------+" * 8 + f"\n")
        lines.append(f"{indent}|  {COLOR_BOLD if enable_colors else ''}{cfg_str2}{COLOR_RESET if enable_colors else ''} |" + "".join(f" Val {i:2d} @ off |" for i in range(8)) + f"\n")
        lines.append(f"{indent}+-{'-'*ConfigurableCacheRam.index_field_width}-+---+---+-{'-'*ConfigurableCacheRam.tag_field_width}-+---------------+" + f"--------------+" * 8 + f"\n")
        lines.append(f"{indent}| {idx_centered_str} | D | V | {tag_centered_str} |  System Addr  |" + "".join(f" Val {i:2d} @ off |" for i in range(8, 16)) + f"\n")
        lines.append(f"{indent}+-{'-'*ConfigurableCacheRam.index_field_width}-+---+---+-{'-'*ConfigurableCacheRam.tag_field_width}-+---------------+" + f"--------------+" * 8 + f"\n")
        return lines

    def build_separator_lines() -> list[str]:
        lines = []
        lines.append(f"{indent}+-{'-'*ConfigurableCacheRam.index_field_width}-+---+---+-{'-'*ConfigurableCacheRam.tag_field_width}-+---------------+--------------" + f"-" * (123-18) + f"+\n")
        return lines
    
    def build_cache_line_lines(cache_line: 'ConfigurableCacheRam.ConfigurableCacheLineRam') -> list[str]:
        lines = []
        index_str = cache_line.index.bin(width=config.index_bits, omit_suffix=True)
        tag, dirty, valid = cache_line.tag_mem_data.split()
        tag_str = tag.bin(width=config.tag_bits, omit_suffix=True)
        dirty_str = "1" if dirty else "0"
        valid_str = "1" if valid else "0"
        system_address_str_sepchar = "_"
        first_addr_hex = (cache_line.start_address).hex(
            width=8,
            sep=4 if system_address_str_sepchar is not None and system_address_str_sepchar != "" else None,
            sepchar=system_address_str_sepchar,
            omit_prefix=True)
        system_address_str = f"0x{system_address_str_sepchar if system_address_str_sepchar is not None and system_address_str_sepchar != '' else ''}{first_addr_hex}"
        if system_address_str_sepchar is None or system_address_str_sepchar == "":
            system_address_str += "  "
        
        # Create binary address string with proper bit layout
        addr_obj = cache_way.SystemAddress(int(cache_line.start_address))
        binary_system_address_str = f"{addr_obj.extract_bits_verilog(config.address_width-1, 0).bin(width=config.address_width, sep=None, omit_suffix=True)}"

        def get_cache_hex_file_offset(word_index: int) -> str:
            word_addr = cache_line.start_address + word_index * 4
            offset_in_cache_hex_file = cache_line.index.append(word_addr.offset()).hex(width=max(2, (config.index_bits + config.offset_bits + 3) // 4), omit_prefix=True)
            return "@" + offset_in_cache_hex_file
        
        tag_str = tag_str + ' '*(ConfigurableCacheRam.tag_field_width - len(tag_str))
        index_str = index_str + ' '*(ConfigurableCacheRam.index_field_width - len(index_str))

        # Calculate column widths for proper alignment
        index_col_width = max(3, config.index_bits)
        tag_col_width = max(3, ConfigurableCacheRam.tag_field_width + 2)  # +2 for padding
        
        # Calculate total width for binary address spanning
        span_width = ConfigurableCacheRam.tag_field_width + 15  # Tag|System Addr
        binary_padding = max(0, span_width - len(binary_system_address_str) + 1)

        if enable_colors:
            index_str = colorize_index_str(index_str)
            tag_str = colorize_tag_str(tag_str)
            dirty_str = colorize_dirty_str(dirty_str)
            valid_str = colorize_valid_str(valid_str)
            binary_system_address_str = colorize_configurable_addr_string(binary_system_address_str)
            system_address_str = colorize_system_hex_address_str(system_address_str, include_0x=False)

        binary_system_address_str = ' '*(binary_padding) + binary_system_address_str

        values_str = "".join(
            f"{word.hex(width=8, omit_prefix=True)} {get_cache_hex_file_offset(idx)} | "
            for idx, word in enumerate(cache_line.words[:8])
        )
        lines.append(f"{indent}| {index_str} | {dirty_str} | {valid_str} | {tag_str} |  {system_address_str} | {values_str}" + f"\n")    
        
        values_str = "".join(
            f"{word.hex(width=8, omit_prefix=True)} {get_cache_hex_file_offset(8+idx)} | "
            for idx, word in enumerate(cache_line.words[8:16])
        )
        # Center the binary address across the first 5 columns
        lines.append(f"{indent}|     |   |   | {binary_system_address_str} | {values_str}" + f"\n")    
        return lines

    lines = []
    lines.extend(build_header_lines(way_num))
    for cache_line in cache_way.cache_lines:
        lines.extend(build_cache_line_lines(cache_line=cache_line))
        lines.extend(build_separator_lines())
    return ''.join(lines)
