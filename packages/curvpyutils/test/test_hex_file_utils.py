import tempfile
import os
import pytest
from curvpyutils.file_utils.hex_file_utils import read_hex_file, read_hex_file_as_ints

pytestmark = [pytest.mark.unit]

class TestHexFileUtils:
    def test_read_hex_file(self) -> None:
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

    def test_read_hex_file_as_ints(self) -> None:
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
            words = read_hex_file_as_ints(temp_file_path)
            assert len(words) == 16
            assert words[0] == 0x00000000
            assert words[15] == 0x0000000F
        finally:
            os.unlink(temp_file_path)


