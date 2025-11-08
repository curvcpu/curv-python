#! /usr/bin/env python3

from .cache import COLORS

HELP_STRING = f"""
This script reads two tag RAM $readmemb() files (way 0 and way 1) and then outputs them in
a format that be used to populate a multidimensional SystemVerilog array like this:

    {COLORS['bold']}logic [18:0] tags_reg [4][NUM_WAYS];{COLORS['reset']}
    {COLORS['bold']}initial $readmemb(`INITIAL_INTERLEAVED_TAG_RAM_FILE, tags_reg);{COLORS['reset']}

with the above fragment generated on the fly if --sv-snippet/-sv is specified.

The input files are expected to be in the format of:

    {COLORS['gray']}# assume this is way 0{COLORS['reset']}
    {COLORS['blue']}0000000000000000000{COLORS['reset']}
    {COLORS['blue']}0000000000000000010{COLORS['reset']}
    {COLORS['blue']}0000000000000000100{COLORS['reset']}
    {COLORS['blue']}0000000000000001000{COLORS['reset']}

    and 

    {COLORS['gray']}# assume this is way 1{COLORS['reset']}
    {COLORS['purple']}0000000000000000011{COLORS['reset']}
    {COLORS['purple']}0000000000000000111{COLORS['reset']}
    {COLORS['purple']}0000000000000001111{COLORS['reset']}
    {COLORS['purple']}0000000000000011111{COLORS['reset']}

The output file will look like this:

    {COLORS['blue']}0000000000000000000{COLORS['reset']} {COLORS['purple']}0000000000000000011{COLORS['reset']}
    {COLORS['blue']}0000000000000000010{COLORS['reset']} {COLORS['purple']}0000000000000000111{COLORS['reset']}
    {COLORS['blue']}0000000000000000100{COLORS['reset']} {COLORS['purple']}0000000000000001111{COLORS['reset']}
    {COLORS['blue']}0000000000000001000{COLORS['reset']} {COLORS['purple']}0000000000000011111{COLORS['reset']}

If the input files contain low-order dirty and valid bits, pass {COLORS['yellow']}`--strip-dv`{COLORS['reset']} to
remove those bits.
"""

import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(
        description=HELP_STRING,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage='%(prog)s WAY0_BINARY_FILE WAY1_BINARY_FILE [--strip-dv]'
    )
    parser.add_argument("WAY0_BINARY_FILE", type=str, help="Path to the input binary file for way 0")
    parser.add_argument("WAY1_BINARY_FILE", type=str, help="Path to the input binary file for way 1") 
    parser.add_argument("--strip-dv", action="store_true", help="Strip 2 bits from the low-order of each line")
    parser.add_argument("--output-file", "-o", type=str, required=False, default=None, help="Path to the interleaved hex output file; if omitted, no output file is written")
    args = parser.parse_args()

    # Read the input files
    with open(args.WAY0_BINARY_FILE, "r") as f:
        way0_lines = f.readlines()
    with open(args.WAY1_BINARY_FILE, "r") as f:
        way1_lines = f.readlines()

    # strip blank lines
    way0_lines = [line.strip() for line in way0_lines if line.strip()]
    way1_lines = [line.strip() for line in way1_lines if line.strip()]

    if len(way0_lines) != len(way1_lines):
        print(f"Error: way0_lines and way1_lines must have the same number of lines: way0_lines has {len(way0_lines)} lines, way1_lines has {len(way1_lines)} lines", file=sys.stderr)
        sys.exit(1)

    # strip the low-order 2 bits from each line if requested
    if args.strip_dv:
        way0_lines = [line[:-2] for line in way0_lines]
        way1_lines = [line[:-2] for line in way1_lines]

    # combine the lines from both files
    combined_lines = []
    for i in range(len(way0_lines)):
        combined_lines.append(f"{way0_lines[i]} {way1_lines[i]}")

    # print the combined lines
    if args.output_file:
        output_file = os.path.abspath(args.output_file)
        with open(output_file, "w") as f:
            for line in combined_lines:
                f.write(line + "\n")
    else:
        output_file = None

if __name__ == "__main__":
    main()