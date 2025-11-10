import unittest
import os
import sys
import pytest
from curvpyutils.shellutils import print_delta
from curvtools.cli.subst.replace import patterns

pytestmark = [pytest.mark.unit]

class TestPatterns(unittest.TestCase):
    """
    Test the pattern regex's used in replace.py to find the subst and endsubst markers.
    """

    sample_file = """

    preceding_stuff...
    
    // @subst[`extract_structs.py rvpkg.sv -t if_id_pipereg_t --display-sv-table`]
    $display("[%t] +------------------------+", $realtime);
    $display("[%t] | if_id_pipereg          |", $realtime);
    $display("[%t] +------------------------+", $realtime);
    $display("[%t] |  pc       |  %08h  |", $realtime, if_id_pipereg.pc);
    $display("[%t] |  pc_next  |  %08h  |", $realtime, if_id_pipereg.pc_next);
    $display("[%t] |  instr    |  %08h  |", $realtime, if_id_pipereg.instr);
    $display("[%t] +------------------------+", $realtime);
    // @endsubst

    other stuff...

    // @subst[`extract_structs.py rvpkg.sv -t if_id_pipereg_t --display-sv-table`]
    $display("[%t] +------------------------+", $realtime);
    $display("[%t] | if_id_pipereg          |", $realtime);
    $display("[%t] +------------------------+", $realtime);
    $display("[%t] |  pc       |  %08h  |", $realtime, if_id_pipereg.pc);
    $display("[%t] |  pc_next  |  %08h  |", $realtime, if_id_pipereg.pc_next);
    $display("[%t] |  instr    |  %08h  |", $realtime, if_id_pipereg.instr);
    $display("[%t] +------------------------+", $realtime);
    // @endsubst

    more stuff...

"""
    def test_start_subst(self):
        # Use re.search to find the pattern anywhere in the string.
        match = patterns["start_subst"].search(self.sample_file)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "extract_structs.py rvpkg.sv -t if_id_pipereg_t --display-sv-table")
        self.assertEqual(match.group(0), "@subst[`extract_structs.py rvpkg.sv -t if_id_pipereg_t --display-sv-table`]")

    def test_end_subst(self):
        # Use re.search to find the pattern anywhere in the string.
        match = patterns["end_subst"].search(self.sample_file)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), "@endsubst")

    def test_html_comment_style(self):
        file_content1 = """
  <!-- @subst[`printf '%s' 'xxxx'`] -->
  <!-- @endsubst -->
"""
        file_content2 = """
  <!-- @subst[`printf "%s\\n" '<a href="https://github.com/curvcpu/curv-python/releases/tag/curv-%s"><img src="https://img.shields.io/badge/%s-blue?label=curv" alt="curv version %s"></a>\\n' 'v0.1.9' 'v0.1.9' 'v0.1.9'`] -->
  <!-- @endsubst -->
"""
        file_content1_lines = file_content1.split("\n")
        file_content2_lines = file_content2.split("\n")
        
        match = patterns["start_subst"].search(file_content1_lines[1])
        self.assertIsNotNone(match)
        expected_group_1 = "printf '%s' 'xxxx'"
        self.assertEqual(match.group(1), expected_group_1)

        match = patterns["end_subst"].search(file_content1_lines[2])
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), "@endsubst")
    
        match = patterns["start_subst"].search(file_content2_lines[1])
        self.assertIsNotNone(match)
        expected_group_1 = "printf \"%s\\n\" '<a href=\"https://github.com/curvcpu/curv-python/releases/tag/curv-%s\"><img src=\"https://img.shields.io/badge/%s-blue?label=curv\" alt=\"curv version %s\"></a>\\n' 'v0.1.9' 'v0.1.9' 'v0.1.9'"
        self.assertEqual(match.group(1), expected_group_1)

        match = patterns["end_subst"].search(file_content2_lines[2])
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), "@endsubst")