"""
Unit tests for the memory map validator regarding the access field
"""
import pytest
from curvtools.cli.memmap2.validator import MemoryMapValidator, ValidationSeverity
pytestmark = [pytest.mark.unit]
from curvpyutils.toml_utils import read_toml_file
from pathlib import Path
from typing import Any

def load_memory_map(file_path: str) -> dict[str, Any]:
    """Load a memory map from a file"""
    return read_toml_file(file_path)

def test_access_must_be_set_on_ranges_with_no_children1():
    """
    Test that the validator fails if the access field is not set on a range with no children.
    """
    file_path = Path(__file__).parent / "test_vectors" / "input" / "access_must_be_set_on_ranges_with_no_children1.toml"
    memory_map = load_memory_map(file_path)

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen=32)

    access_must_be_set_on_ranges_with_no_children_errors = [e for e in errors if e.rule_id == "access_must_be_set_on_ranges_with_no_children"]
    assert len(access_must_be_set_on_ranges_with_no_children_errors) > 0, "Should detect errors when access is not set on a range with no children"

def test_access_must_be_set_on_ranges_with_no_children2():
    """
    Test that the validator fails if the access field is not set on a range with no children.
    """
    file_path = Path(__file__).parent / "test_vectors" / "input" / "access_must_be_set_on_ranges_with_no_children2.toml"
    memory_map = load_memory_map(file_path)

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen=32)

    access_must_be_set_on_ranges_with_no_children_errors = [e for e in errors if e.rule_id == "access_must_be_set_on_ranges_with_no_children"]
    assert len(access_must_be_set_on_ranges_with_no_children_errors) > 0, "Should detect errors when access is not set on a range with no children"


def test_access_may_not_be_set_on_a_range_with_children():
    """
    Test that the validator fails if the access field is set on a range with children.
    """
    file_path = Path(__file__).parent / "test_vectors" / "input" / "access_may_not_be_set_on_a_range_with_children.toml"
    memory_map = load_memory_map(file_path)

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen=32)

    access_cannot_be_set_on_ranges_with_children_errors = [e for e in errors if e.rule_id == "access_cannot_be_set_on_ranges_with_children"]
    assert len(access_cannot_be_set_on_ranges_with_children_errors) > 0, "Should detect errors when access is set on a range with children"