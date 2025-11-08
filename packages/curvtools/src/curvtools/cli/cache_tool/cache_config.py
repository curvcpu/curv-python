from dataclasses import dataclass
from typing import NamedTuple
import math

class BitRange(NamedTuple):
    msb: int
    lsb: int

@dataclass
class CacheConfig:
    """Configuration for cache tool supporting variable address widths and number of sets."""
    
    # Configurable parameters
    num_sets: int = 4                             # Number of cache sets (4 to 128)
    address_width: int = 10                       # Address width in bits (10 to 32)
    tags_have_valid_dirty_bits: bool = False      # Whether ConfigurableTagMemData has valid and dirty bit fields
    write_hex_files_with_addresses: bool = False  # Whether to write hex files with @-addresses
    
    # Fixed parameters
    num_ways: int = 2           # 2-way associative
    words_per_line: int = 16    # 16 32-bit words per cache line
    
    def __post_init__(self):
        """Validate configuration and compute derived values."""
        # Validate input parameters
        if not (4 <= self.num_sets <= 128):
            raise ValueError(f"num_sets must be between 4 and 128, got {self.num_sets}")
        if not (10 <= self.address_width <= 32):
            raise ValueError(f"address_width must be between 10 and 32, got {self.address_width}")
        if self.num_sets & (self.num_sets - 1) != 0:
            raise ValueError(f"num_sets must be a power of 2, got {self.num_sets}")
        if self.num_ways != 2:
            raise ValueError(f"num_ways must be 2, got {self.num_ways}")
        if self.words_per_line != 16:
            raise ValueError(f"words_per_line must be 16, got {self.words_per_line}")
        
        # Compute derived values
        self._index_bits = int(math.log2(self.num_sets))
        self._offset_bits = int(math.log2(self.words_per_line))  # 4 bits for 16 words
        
        # Address layout calculation
        # Bits [1:0] are always 00 for word alignment (not counted in address_width)
        # Offset: [offset_bits+1:2] (4 bits for 16 words)
        # Index: [offset_bits+index_bits+1:offset_bits+2]
        # Tag: [address_width-1:offset_bits+index_bits+2]
        
        self._offset_lsb = 2
        self._offset_msb = self._offset_lsb + self._offset_bits - 1
        
        self._index_lsb = self._offset_msb + 1
        self._index_msb = self._index_lsb + self._index_bits - 1
        
        self._tag_lsb = self._index_msb + 1
        self._tag_msb = self.address_width - 1
        
        # Validate that we have enough bits for tag
        if self._tag_msb < self._tag_lsb:
            raise ValueError(f"Address width {self.address_width} is too small for {self.num_sets} sets")
        
        self._tag_bits = self._tag_msb - self._tag_lsb + 1
    
    @property
    def index_bits(self) -> int:
        """Number of bits for cache index."""
        return self._index_bits
    
    @property
    def tag_bits(self) -> int:
        """Number of bits for cache tag."""
        return self._tag_bits
    
    @property
    def offset_bits(self) -> int:
        """Number of bits for cache line offset."""
        return self._offset_bits
    
    @property
    def index_bits_pos(self) -> BitRange:
        """Bit range for index in address."""
        return BitRange(self._index_msb, self._index_lsb)
    
    @property
    def tag_bits_pos(self) -> BitRange:
        """Bit range for tag in address."""
        return BitRange(self._tag_msb, self._tag_lsb)
    
    @property
    def offset_bits_pos(self) -> BitRange:
        """Bit range for offset in address."""
        return BitRange(self._offset_msb, self._offset_lsb)
    
    def get_file_suffix(self) -> str:
        """Get file suffix for this configuration."""
        return f"_{self.num_sets}s"
    
    def __str__(self) -> str:
        s = f"{self.num_sets} sets, {self.address_width} bits, {self.num_ways} ways"
        return s
    
    def print_layout(self) -> None:
        """Print the address bit layout."""
        print(f"Cache Configuration: {self}")
        print(f"Address Layout ({self.address_width} bits):")
        print(f"  Tag:    [{self._tag_msb}:{self._tag_lsb}] ({self.tag_bits} bits)")
        print(f"  Index:  [{self._index_msb}:{self._index_lsb}] ({self.index_bits} bits)")
        print(f"  Offset: [{self._offset_msb}:{self._offset_lsb}] ({self.offset_bits} bits)")
        print(f"  Unused: [1:0] (2 bits for word alignment)")