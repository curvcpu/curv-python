#!/usr/bin/env python3

import argparse,sys

############################################################################################################
#
# This script generates a hex file for a BRAM.  By default, the hex file is just 16 randon 32-bit words, but
# arguments let you specify what you want.
#
# Examples:
#
#   curv-verilog-hex-generate -o bram.hex -n 16 -t random     # 16 random 32-bit words, saved to bram.hex
#   curv-verilog-hex-generate -o bram.hex -n 16 -t zero       # all zeros, 16*32 bytes long, saved to bram.hex
#   curv-verilog-hex-generate -o - -n 16 -t zero              # same thing but printed to stdout
#
############################################################################################################



########################################################
# Helper functions
########################################################

def shorten_for_hex_file(addr, multiples_of_2=False):
    """
    Shorten an address like 000000A0 to A0
    """
    hex_val = hex(addr)[2:].upper()

    # Handle the case where the address is 0, hex(0)[2:].upper() results in '0'
    if addr == 0:
        if multiples_of_2:
            return f"00"
        else:
            return f"0"

    if multiples_of_2:
        # if odd
        if len(hex_val) % 2 == 1:
            hex_val = f"0{hex_val}"

    return f"{hex_val}"

def int_to_le_bytes(n):
    """
    Convert a 32-bit integer to a list of 4 bytes in little-endian order.
    Returns list where element 0 is least significant byte (lowest memory address).
    """
    return [
        (n >> 0) & 0xFF,   # LSB - lowest address
        (n >> 8) & 0xFF,
        (n >> 16) & 0xFF,
        (n >> 24) & 0xFF   # MSB - highest address
    ]

class HexDump:
    def __init__(self, unit_size=4):
        self.addressed_data = []
        self.addr_cntr = 0
        self.unit_size = unit_size

    def add_bytes(self, byte_arr=[]):
        self.addressed_data.append({'addr':self.addr_cntr, 'byte_arr':byte_arr})
        self.addr_cntr += 1

    def each_element(self, byte_separator=" ", unit_separator="  "):
        bytes_str = ""
        for i in range(0, len(self.addressed_data)):
            entry = self.addressed_data[i]
            addr, byte_arr = entry['addr'], entry['byte_arr']
            s = byte_separator.join(f'{b:02X}' for b in byte_arr)
            bytes_str += s + unit_separator
            bytes_str = bytes_str[:-len(unit_separator)]
            yield {'addr': addr, 'bytes_str': bytes_str}
            bytes_str = ""

    def get_hex_lines(self, byte_separator=" ", unit_separator="  "):
        lines = []
        # each entry is 1 word (4 bytes)
        for el in self.each_element(byte_separator=byte_separator, unit_separator=unit_separator):
            addr, bytes_str = el['addr'], el['bytes_str']
            lines.append(f"@{shorten_for_hex_file(addr, multiples_of_2=True)}")
            lines.append(f"{bytes_str}\n")
        return lines

def make_deterministic_pseudo_random_numbers_buffer(word_count=16):
    """
    Make list of 32-bit numbers that don't follow any obvious pattern.
    """
    numbers = [(i*i<<i) for i in range(0, word_count)]
    ret = HexDump()
    for n in numbers:
        le_n = int_to_le_bytes(n)
        ret.add_bytes(le_n)
    return ret

def make_constant_buffer(byte=0, num_units=16, unit_size=4):
    """
    Make list of 32-bit numbers (if unit_size=4) that are all 32'h{byte}{byte}{byte}{byte}.
    Or 8-bit numbers (if unit_size=1) that are all 8'h{byte}.
    """
    if unit_size == 4:
        numbers = [byte + (byte<<8) + (byte<<16) + (byte<<24)] * num_units
    elif unit_size == 1:
        numbers = [byte] * num_units
    else:
        raise ValueError(f"error: invalid unit size: {unit_size} must be 1 or 4")
    ret = HexDump()
    for n in numbers:
        if unit_size == 4:
            le_n = int_to_le_bytes(n)
        elif unit_size == 1:
            le_n = [n]
        else:
            raise ValueError(f"error: invalid unit size: {unit_size} must be 1 or 4")
        ret.add_bytes(le_n)
    return ret

def write_bram_hex(outfile, ret, byte_separator=" ", unit_separator="  "):
    lines = ret.get_hex_lines(byte_separator=byte_separator, unit_separator=unit_separator)

    if outfile is None or outfile == "-":
        for line in lines:
            print(line)
    else:
        with open(outfile, 'w') as f:
            for line in lines:
                f.write(line + '\n')

def parse_args(allowed_types=['zero']):
    parser = argparse.ArgumentParser(description='Generate a Verilog hex file"')
    parser.add_argument('-o', '--outfile', required=True, help='Output file path (use "-" for stdout)')
    word_group = parser.add_mutually_exclusive_group()
    word_group.add_argument('-w', '--num-words', type=int, help='number of 32-bit words to generate in output file')
    word_group.add_argument('-b', '--num-bytes', type=int, help='number of bytes to generate in output file')
    parser.add_argument('-t', '--type', required=False, default='deterministic-random', help=f"type of output file (choices: {', '.join(allowed_types)}) (default=deterministic-random)")
    parser.add_argument('-C', '--constant-byte', required=False, default="0", help='constant byte to use with type "constant" (default=0x00)')
    args = parser.parse_args()
    if args.type not in allowed_types:
        print(f"error: type must be one of {', '.join(allowed_types)}")
        sys.exit(1)        
    if args.num_words is None and args.num_bytes is None:
        print("error: either -w or -b must be specified")
        sys.exit(1)
    if args.type == 'deterministic-random' and args.num_words is None:
        print("error: deterministic-random is only available in word mode (-w)")
        sys.exit(1)
    return args

def main():
    args = parse_args(allowed_types=['zero', 'constant', 'deterministic-random'])

    if args.type == 'deterministic-random':
        buf = make_deterministic_pseudo_random_numbers_buffer(args.num_words)
    elif args.type == 'zero':
        buf = make_constant_buffer(byte=0, num_units=args.num_words, unit_size=4)
    elif args.type == 'constant':
        # allow "ff" or "0xff" or "ffh" to all be 255 but regular decimal numbers just convert as decimal
        constant_byte_str = str(args.constant_byte)
        if 'h' in constant_byte_str:
            constant_byte = int(constant_byte_str.replace('h', ''), 16)
        elif '0x' in constant_byte_str:
            constant_byte = int(constant_byte_str.replace('0x', ''), 16)
        elif any(c in constant_byte_str.lower() for c in 'abcdef'):
            constant_byte = int(constant_byte_str, 16)
        else:
            constant_byte = int(constant_byte_str)
            print(f"Note: treated constant byte as decimal {constant_byte}; you should suffix with 'h' and write in hex instead")
        if args.num_words is not None:
            buf = make_constant_buffer(byte=constant_byte, num_units=args.num_words, unit_size=4)
        else:
            buf = make_constant_buffer(byte=constant_byte, num_units=args.num_bytes, unit_size=1)
    else:
        raise ValueError(f"Invalid type: {args.type}")

    if args.num_words is not None:
        # word mode
        byte_separator = ""
        unit_separator = " "
    else:
        # byte mode
        byte_separator = ""
        unit_separator = " "
    write_bram_hex(args.outfile, buf, byte_separator, unit_separator)

if __name__ == "__main__":
    main()
