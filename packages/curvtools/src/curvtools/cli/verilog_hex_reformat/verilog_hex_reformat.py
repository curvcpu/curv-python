#!/usr/bin/env python3

import argparse
import sys
from argparse import HelpFormatter
from typing import Any, List, Optional, Sequence, Tuple

#
# Cleans up objcopy-generated hex files into a format that plays nicely with $readmemh implementations
# For usage: run --help
#

COLOR_YELLOW = "\033[93m"
COLOR_GREEN = "\033[92m"
COLOR_RESET = "\033[0m"

class CustomHelpFormatter(HelpFormatter):
    """
    Custom formatter that allows for a custom usage description and better formatting
    """
    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: Optional[int] = None,
    ) -> None:
        super().__init__(prog, indent_increment, max_help_position, width)
        
    def _format_usage(self, usage: str, actions: Sequence[argparse.Action], groups: List[argparse._ArgumentGroup], prefix: Optional[str]) -> str:
        if usage is None:
            return self._custom_usage()
        return super()._format_usage(usage, actions, groups, prefix)
        
    def _custom_usage(self) -> str:
        """
        Returns a custom usage string. Modify this to change the usage description.
        """
        return f"""Usage: curv-verilog-hex-reformat [options] [INFILE]

This tool reformats Verilog formatted hex files produced by `objcopy`. It transforms:

    {COLOR_YELLOW}@00000000
    00112233 aabbccdd eeff0011 aaaaaabb
    ccccccdd ddddddee eeeeeeff ffffff00
    @00000010
    01010101 02020202 03030303 04040404
    05050505 06060606 07070707 08080808{COLOR_RESET}

into this:

    {COLOR_YELLOW}@0000
    00112233
    aabbccdd
    eeff0011
    aaaaaabb
    ccccccdd
    ddddddee
    eeeeeeff
    ffffff00
    @0010
    01010101
    02020202
    03030303
    04040404
    [...etc...]{COLOR_RESET}

You can specify how frequently you want @-addresses (or omit them entirely), 
and how many hex words to print per line.

{COLOR_GREEN}Examples:{COLOR_RESET}

  # Read from stdin, write to stdout, 1 word per line
  cat input.hex | curv-verilog-hex-reformat

  # Read from file, write to file, 4 words per line
  curv-verilog-hex-reformat -i input.hex -o output.hex -w 4

  # Add @-addresses every 32 hex words
  curv-verilog-hex-reformat -i input.hex -a 32

  # Suppress all @-addresses
  curv-verilog-hex-reformat -i input.hex -a 0

"""

def parse_args():
    parser = argparse.ArgumentParser(
        description="Reformat a Verilog formatted hex file into a hex file that plays nicely with various $readmemh implementations",
        formatter_class=CustomHelpFormatter,
        add_help=True,
    )
    parser.add_argument("INFILE", nargs="?", type=str, help="input hex file (stdin if omitted)")
    parser.add_argument("-o", "--outfile", type=str, help="output hex file (stdout if omitted)")
    parser.add_argument("-w", "--words-per-line", type=int, default=1, help="words per line (default: 1)")
    parser.add_argument("-a", "--addr-step", type=int, default=16, help="address step; 0 to suppress all @-addresses (default: 16)")
    parser.add_argument("-i", "--in-place", action="store_true", help="overwrite INFILE with output")
    parser.add_argument("-t", "--truncate-to-words", type=int, help="truncate to this many words")
    parser.add_argument("-s", "--skip-words", type=int, help="skip this many words then output the rest")
    args = parser.parse_args()
    if args.in_place and args.INFILE is None:
        print("ERROR: --in-place requires INFILE")
        sys.exit(1)
    if args.in_place and args.outfile is not None:
        print("ERROR: --in-place and --outfile cannot be specified together")
        sys.exit(1)
    if args.words_per_line < 1:
        args.words_per_line = 1
    if args.addr_step < 0:
        args.addr_step = 0
    return args

def shorten_for_hex_file(addr):
    """
    Shorten an address like 000000A0 to 00A0
    """
    hex_str = f"{addr:04x}"
    return hex_str

def main():
    args = parse_args()
    if args.INFILE is None:
        infile_str = sys.stdin.read()
    else:
        with open(args.INFILE, "r") as f:
            infile_str = f.read()

    infile_lines = infile_str.split("\n")
    infile_words = [word.strip() for line in infile_lines for word in line.split(" ") if word.strip() and not word.strip().startswith("@")]

    # output splitting
    truncate_to_words = args.truncate_to_words
    skip_words = args.skip_words
    if truncate_to_words is not None:
        infile_words = infile_words[:truncate_to_words]
    if skip_words is not None:
        infile_words = infile_words[skip_words:]

    out_lines = []
    line_words_cnt = 0         # number of words printed on current line
    words_since_last_addr = 0  # number of words printed since last @-address
    words_count = 0            # number of total words printed
    for word in infile_words:
        if (args.addr_step != 0) and (words_since_last_addr >= args.addr_step-1 or words_count == 0):
            addr = shorten_for_hex_file(words_count*4)
            # add newline if not first line
            out_lines.append(("\n" if words_count > 0 else "") + f"@{addr}")
            words_since_last_addr = 0
        else:
            words_since_last_addr += 1

        out_lines.append(word)
        line_words_cnt += 1
        if line_words_cnt == args.words_per_line:
            if args.words_per_line > 1:
                out_lines.append("")
            line_words_cnt = 0

        words_count += 1

    outfile_str = "\n".join(out_lines)

    if args.in_place and args.INFILE is not None:
        with open(args.INFILE, "w") as f:
            f.write(outfile_str)
    elif args.outfile is None:
        print(f"{outfile_str}")
    else:
        with open(args.outfile, "w") as f:
            f.write(outfile_str)

if __name__ == "__main__":
    main()