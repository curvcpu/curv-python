import pytest
import unittest
from curvtools.cli.subst.util import StrListWithMostCommon

pytestmark = [pytest.mark.unit]

class TestListWithMostCommon(unittest.TestCase):
    def test_most_common_str(self):
        indent_strs = StrListWithMostCommon(["abc", " ", "\t", " "])
        s = str(indent_strs) # s = " "
        self.assertEqual(s, " ")
    def test_most_common_str_empty_list(self):
        indent_strs = StrListWithMostCommon(default_str="def")
        s = str(indent_strs) # s = "def"
        self.assertEqual(s, "def")
    def test_most_common_str_with_default_str(self):
        indent_strs = StrListWithMostCommon(["abc", " ", "\t", " "], default_str="def")
        s = str(indent_strs) # s = " "
        self.assertEqual(s, " ")