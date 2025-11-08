from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .cache_config import CacheConfig

def extract_bits_verilog(value: int, msb: int, lsb: int) -> int:
    """
    Extract a range of bits from an integer, similar to Verilog bit selection.
    
    Args:
        value: 32-bit integer
        msb: Most significant bit position (inclusive)
        lsb: Least significant bit position (inclusive)
    
    Returns:
        Integer containing the extracted bits
    
    Example:
        extract_bits(0xABCD, 7, 0)  # Returns same value as Verilog's 32'habcd[7:0]
    """
    mask = (1 << (msb - lsb + 1)) - 1
    return (value >> lsb) & mask


def make_bits_class(width:int):
    """
    Factory for Bit classes of varying widths.
    """
    class Bits:
        # Class-level width so it can be accessed like Tag.width
        _width: int = width  # matches Int2b bit-width

        @staticmethod
        def get_width_static() -> int:
            """Return the tag width (convenience static helper)."""
            return Bits._width

        def __init__(self, value:int):
            self.width = width
            self.mask = (1 << width) - 1
            # Handle both int and Bits inputs
            if isinstance(value, int):
                self.value = value & self.mask
            else:
                self.value = value.value & self.mask
        def __str__(self):
            return f"{self.value:0{self.width}b}"
        def hex(self, width:int=None, sep:int=None, sepchar:str="_", omit_prefix:bool=False):
            if width is not None and width*4 < self.width:
                raise ValueError(f"width {width} is less than the width of the bits {self.width}: truncation will occur")
            prefix = "" if omit_prefix else "0x"
            if width is None:
                return f"{prefix}{self.value:x}"
            else:
                if sep is None or sepchar=='':
                    return f"{prefix}{self.value:0{width}x}"
                else:
                    s = f"{self.value:0{width}x}"
                    # Calculate how many full groups and remaining bits
                    remainder = len(s) % sep
                    if remainder == 0:
                        chunks = [s[i:i+sep] for i in range(0, len(s), sep)]
                    else:
                        # Start with remainder bits, then do full groups
                        chunks = [s[:remainder]] + [s[i:i+sep] for i in range(remainder, len(s), sep)]
                    return prefix + sepchar.join(chunks)
        def bin(self, width:int=None, sep:int=None, sepchar:str="_", omit_suffix:bool=False):
            if width is not None and width < self.width:
                raise ValueError(f"width {width} is less than the width of the bits {self.width}: truncation will occur")
            suffix = "" if omit_suffix else "b"
            if width is None:
                return f"{self.value:b}{suffix}"
            else:
                if sep is None:
                    return f"{self.value:0{width}b}{suffix}"
                else:
                    s = f"{self.value:0{width}b}"
                    # Calculate how many full groups and remaining bits
                    remainder = len(s) % sep
                    if remainder == 0:
                        chunks = [s[i:i+sep] for i in range(0, len(s), sep)]
                    else:
                        # Start with remainder bits, then do full groups
                        chunks = [s[:remainder]] + [s[i:i+sep] for i in range(remainder, len(s), sep)]
                    return "_".join(chunks) + suffix
        def get_as_hex_file_address(self, width:int=4, sep:int=4)->str:
            return f"@{self.value:0{width}x}"
        def __repr__(self):
            return f"Bits({self.width}'{self.value:0{self.width}b} = 0x{self.value:x} = {self.value:d})"
        def __concat__(self, other):
            if other is None:
                return self
            else:
                combined_width = self.width + other.width
                Int_Combined = make_bits_class(combined_width)
                return Int_Combined((self.value << other.width) | other.value)
        # use + as concatenation operator
        def append(self, other):
            return self.__concat__(other)
        def extract_bits_verilog(self, msb:int, lsb:int)->'Bits':
            res = extract_bits_verilog(self.value, msb, lsb)
            Int_Res = make_bits_class(msb - lsb + 1)
            return Int_Res(res)
        # def __add__(self, other):
        #     if isinstance(other, int):
        #         ret = self.value + other
        #         Int_Ret = make_bits_class(self.width)
        #         return Int_Ret(ret)
        #     else:
        #         return self.value + other.value

        def __add__(self, other):
           value = (int(self) + int(other)) & self.mask
           return type(self)(value)        # preserves subclass!
        
        # make int(self) work, handy in many places
        def __int__(self):
            return self.value

        # value-based equality
        def __eq__(self, other):
            if isinstance(other, Bits):
                return self.value == other.value
            if isinstance(other, int):
                return self.value == other          # allow plain ints
            return NotImplemented

        # hash must be consistent with __eq__
        def __hash__(self):
            return hash(self.value)


    return Bits

# Commonly used bit classes
Int2b = make_bits_class(2)
Int4b = make_bits_class(4)
Int10b = make_bits_class(10)
Int32b = make_bits_class(32)

# Tag class
class Tag(Int2b):
    def __init__(self, value:int):
        super().__init__(value)
    def __str__(self):
        return super().__str__()
    def __repr__(self):
        return f"Tag({self.width}'{self.value:0{self.width}b} = 0x{self.value:x} = {self.value:d})"

# Index class
class Index(Int2b):
    def __init__(self, value:int):
        super().__init__(value)
    def __str__(self):
        return super().__str__()
    def __repr__(self):
        return f"Index({self.width}'{self.value:0{self.width}b} = 0x{self.value:x} = {self.value:d})"

# Offset class
class Offset(Int4b):
    def __init__(self, value:int):
        super().__init__(value)
    def __str__(self):
        return super().__str__()
    def __repr__(self):
        return f"Index({self.width}'{self.value:0{self.width}b} = 0x{self.value:x} = {self.value:d})"

#
# SystemAddress class
# 

class BitRange(NamedTuple):
    msb: int
    lsb: int

def system_address_params(addr_width, index_bits_pos:BitRange, tag_bits_pos:BitRange, offset_bits_pos:BitRange):
    def decorator(cls):
        cls.ADDR_WIDTH = addr_width
        cls.INDEX_WIDTH = index_bits_pos.msb - index_bits_pos.lsb + 1
        cls.INDEX_BITS_POS = index_bits_pos
        cls.TAG_WIDTH = tag_bits_pos.msb - tag_bits_pos.lsb + 1
        cls.TAG_BITS_POS = tag_bits_pos
        cls.OFFSET_WIDTH = offset_bits_pos.msb - offset_bits_pos.lsb + 1
        cls.OFFSET_BITS_POS = offset_bits_pos
        cls.type_offset = Offset
        cls.type_tag = Tag
        cls.type_index = Index
        cls.type_address = make_bits_class(addr_width)
        cls.type_int10b = Int10b
        return cls
    return decorator

@system_address_params(addr_width=32, index_bits_pos=BitRange(7, 6), tag_bits_pos=BitRange(9, 8), offset_bits_pos=BitRange(5, 2))
class SystemAddress(Int32b):
    def __init__(self, address:int|tuple[Tag, Index, Offset]):
        if isinstance(address, int):
            super().__init__(address)
        else:
            tag, index, offset = address
            lower10 = tag.append(index).append(offset)
            super().__init__(lower10.value<<2)
    def index(self)->'SystemAddress.type_index':
        return self.type_index(self.extract_bits_verilog(self.INDEX_BITS_POS.msb, self.INDEX_BITS_POS.lsb))
    def tag(self)->'SystemAddress.type_tag':
        return self.type_tag(self.extract_bits_verilog(self.TAG_BITS_POS.msb, self.TAG_BITS_POS.lsb))
    def offset(self)->'SystemAddress.type_offset':
        return self.type_offset(self.extract_bits_verilog(self.OFFSET_BITS_POS.msb, self.OFFSET_BITS_POS.lsb))
    def __add__(self, other):
        return SystemAddress(int(self) + int(other))
    
    # make int(self) work, handy in many places
    def __int__(self):
        return self.value

    # value-based equality
    def __eq__(self, other):
        if isinstance(other, SystemAddress):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other          # allow plain ints
        return NotImplemented

    # hash must be consistent with __eq__
    def __hash__(self):
        return hash(self.value)


def demo_system_address():
    """
    Demo the SystemAddress class.
    """
    a = SystemAddress(0x0000_0344)
    print(f"a.index: {a.index()}")
    print(f"a.tag: {a.tag()}")
    print(f"a.offset: {a.offset()}")

    b = SystemAddress((Tag(0b11), Index(0b01), Offset(0b0001)))
    print(f"b.index: {b.index()}")
    print(f"b.tag: {b.tag()}")
    print(f"b.offset: {b.offset()}")
    print(f"b: {b.bin(10, 4, omit_suffix=True)}")
    print(f"b: {b.hex(4, 4, omit_prefix=False)}")
    print(f"b[1:0]: {b.extract_bits_verilog(1, 0)}")
    print(f"b[9:8]: {b.extract_bits_verilog(9,8)} = tag {b.tag()}")
    print(f"b[7:6]: {b.extract_bits_verilog(7,6)} = index {b.index()}")
    print(f"b[5:2]: {b.extract_bits_verilog(5,2)} = offset {b.offset()}")


# Configurable address classes factory functions
def create_configurable_address_classes(config: 'CacheConfig'):
    """
    Create configurable Tag, Index, Offset, and SystemAddress classes based on cache configuration.
    """
    
    # Create configurable Tag class
    TagBase = make_bits_class(config.tag_bits)
    class ConfigurableTag(TagBase):
        def __init__(self, value: int):
            super().__init__(value)
        def __str__(self):
            return super().__str__()
        def __repr__(self):
            return f"Tag({self.width}'{self.value:0{self.width}b} = 0x{self.value:x} = {self.value:d})"
    
    # Create configurable Index class
    IndexBase = make_bits_class(config.index_bits)
    class ConfigurableIndex(IndexBase):
        def __init__(self, value: int):
            super().__init__(value)
        def __str__(self):
            return super().__str__()
        def __repr__(self):
            return f"Index({self.width}'{self.value:0{self.width}b} = 0x{self.value:x} = {self.value:d})"
    
    # Create configurable Offset class (always 4 bits for 16 words)
    OffsetBase = make_bits_class(config.offset_bits)
    class ConfigurableOffset(OffsetBase):
        def __init__(self, value: int):
            super().__init__(value)
        def __str__(self):
            return super().__str__()
        def __repr__(self):
            return f"Offset({self.width}'{self.value:0{self.width}b} = 0x{self.value:x} = {self.value:d})"
    
    # Create configurable SystemAddress class with decorator
    @system_address_params(
        addr_width=config.address_width,
        index_bits_pos=config.index_bits_pos,
        tag_bits_pos=config.tag_bits_pos,
        offset_bits_pos=config.offset_bits_pos
    )
    class ConfigurableSystemAddress(make_bits_class(config.address_width)):
        def __init__(self, address: int | tuple[ConfigurableTag, ConfigurableIndex, ConfigurableOffset]):
            if isinstance(address, int):
                super().__init__(address)
            else:
                tag, index, offset = address
                # Construct address from components
                combined = tag.append(index).append(offset)
                # Shift left by 2 to account for word alignment
                super().__init__(combined.value << 2)
        
        def index(self) -> ConfigurableIndex:
            return ConfigurableIndex(self.extract_bits_verilog(self.INDEX_BITS_POS.msb, self.INDEX_BITS_POS.lsb))
        
        def tag(self) -> ConfigurableTag:
            return ConfigurableTag(self.extract_bits_verilog(self.TAG_BITS_POS.msb, self.TAG_BITS_POS.lsb))
        
        def offset(self) -> ConfigurableOffset:
            return ConfigurableOffset(self.extract_bits_verilog(self.OFFSET_BITS_POS.msb, self.OFFSET_BITS_POS.lsb))
        
        def __add__(self, other):
            return ConfigurableSystemAddress(int(self) + int(other))
        
        def __int__(self):
            return self.value
        
        def __eq__(self, other):
            if isinstance(other, ConfigurableSystemAddress):
                return self.value == other.value
            if isinstance(other, int):
                return self.value == other
            return NotImplemented
        
        def __hash__(self):
            return hash(self.value)
    
    # Update class references for the SystemAddress
    ConfigurableSystemAddress.type_offset = ConfigurableOffset
    ConfigurableSystemAddress.type_tag = ConfigurableTag
    ConfigurableSystemAddress.type_index = ConfigurableIndex
    ConfigurableSystemAddress.type_address = make_bits_class(config.address_width)
    
    return ConfigurableTag, ConfigurableIndex, ConfigurableOffset, ConfigurableSystemAddress
