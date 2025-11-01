#! /usr/bin/env python3

import os
import re
import tempfile
from typing import List


def read_hex_file(hex_file_path: str, base_address: int = 0, file_addresses_in_bytes: bool = False) -> list[str]:
    """Read a Verilog ``$readmemh`` hex file and return a list of 32-bit word strings."""

    hex_word_regex = r"^[0-9A-Fa-f]{8}$"

    current_word_addr = base_address
    words: List[str] = []
    with open(hex_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            line_words = line.split()
            for word in line_words:
                word = word.strip()
                if word.startswith("@"):
                    if file_addresses_in_bytes:
                        current_word_addr = int(word[1:], 16) // 4
                    else:
                        current_word_addr = int(word[1:], 16)
                    required_length = current_word_addr - (base_address // 4)
                    if len(words) < required_length:
                        words.extend(["00000000"] * (required_length - len(words)))
                else:
                    if re.match(hex_word_regex, word):
                        words.append(word)
                    else:
                        raise ValueError(f"Invalid hex word: {word}")
    return words


def read_hex_file_as_ints(hex_file_path: str, base_address: int = 0, file_addresses_in_bytes: bool = False) -> list[int]:
    """Read a Verilog ``$readmemh`` hex file and return a list of integer words."""

    words = read_hex_file(
        hex_file_path,
        base_address=base_address,
        file_addresses_in_bytes=file_addresses_in_bytes,
    )
    return [int(word, 16) for word in words]


def _self_test() -> None:
    test_hex_file = """
@0
00000000 00000001 00000002 00000003
@4
00000004 00000005
00000006
00000007
@8
00000008
00000009
0000000A
0000000B
0000000C
0000000D
0000000E
0000000F
"""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".hex") as temp_file:
        temp_file.write(test_hex_file.encode())
        temp_file_path = temp_file.name
    try:
        words = read_hex_file(temp_file_path)
        assert len(words) == 16
        assert words[0] == "00000000"
        assert words[15] == "0000000F"
    finally:
        os.unlink(temp_file_path)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".hex") as temp_file:
        temp_file.write(test_hex_file.encode())
        temp_file_path = temp_file.name
    try:
        words = read_hex_file_as_ints(temp_file_path)
        assert len(words) == 16
        assert words[0] == 0x00000000
        assert words[15] == 0x0000000F
    finally:
        os.unlink(temp_file_path)


if __name__ == "__main__":
    _self_test()

