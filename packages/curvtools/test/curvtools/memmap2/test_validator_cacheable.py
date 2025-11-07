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

def test_cacheable_may_only_be_on_ranges_1():
    """
    Test that the validator fails if the cacheable field is set on a non-range.
    """
    file_path = Path(__file__).parent / "test_vectors" / "input" / "cacheable_may_only_be_on_ranges_1.toml"
    memory_map = load_memory_map(file_path)

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen=32)

    cacheable_may_only_be_on_ranges_errors = [e for e in errors if e.rule_id == "cacheable_cannot_be_set_on_buffers_or_registers"]
    assert len(cacheable_may_only_be_on_ranges_errors) > 0, "Should detect errors when cacheable is set on a non-range"

def test_cacheable_may_only_be_on_ranges_2():
    """
    Test that the validator fails if the cacheable field is set on a non-range.
    """
    file_path = Path(__file__).parent / "test_vectors" / "input" / "cacheable_may_only_be_on_ranges_2.toml"
    memory_map = load_memory_map(file_path)

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen=32)

    cacheable_may_only_be_on_ranges_errors = [e for e in errors if e.rule_id == "cacheable_cannot_be_set_on_buffers_or_registers"]
    assert len(cacheable_may_only_be_on_ranges_errors) > 0, "Should detect errors when cacheable is set on a non-range"


def test_cacheable_must_be_set_on_ranges():
    """
    Test that the validator fails if the cacheable field is not set on a range.
    """
    file_path = Path(__file__).parent / "test_vectors" / "input" / "cacheable_must_be_set_on_ranges.toml"
    memory_map = load_memory_map(file_path)

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen=32)

    cacheable_required_on_ranges_errors = [e for e in errors if e.rule_id == "cacheable_must_be_set_on_ranges"]
    assert len(cacheable_required_on_ranges_errors) > 0, "Should detect errors when cacheable is not set on ranges"

def test_access_and_cacheable_ok():
    """
    Test that the validator passes when cacheable and access rules are obeyed.
    """
    file_path = Path(__file__).parent / "test_vectors" / "input" / "access_and_cacheable_ok.toml"
    memory_map = load_memory_map(file_path)

    validator = MemoryMapValidator()
    errors = validator.validate(memory_map, xlen=32)

    assert len(errors) == 0, f"Expected no errors on validation, got {errors}"
