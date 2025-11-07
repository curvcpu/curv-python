#!/usr/bin/env python3
"""
Unit tests for the memory map validator
"""
import pytest
from curvtools.cli.memmap2.validator import MemoryMapValidator, ValidationSeverity

pytestmark = [pytest.mark.unit]

def test_valid_memory_map():
    """Test validation on a valid memory map"""
    valid_memory_map = {
        "slaves": {
            "sdram": {
                "ranges": [
                    {"name": "RAM", "start": 0x00000000, "end": 0x01FFFFFF, "access": "rw", "cacheable": True}
                ]
            }
        }
    }

    validator = MemoryMapValidator()
    errors = validator.validate(valid_memory_map, xlen=32)

    assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

def test_overlapping_ranges():
    """Test detection of overlapping ranges"""
    invalid_memory_map = {
        "slaves": {
            "test": {
                "ranges": [
                    {"name": "Range1", "start": 0x00000000, "end": 0x0000000F, "access": "rw", "cacheable": False},
                    {"name": "Range2", "start": 0x00000008, "end": 0x00000017, "access": "rw", "cacheable": False}
                ]
            }
        }
    }

    validator = MemoryMapValidator()
    errors = validator.validate(invalid_memory_map, xlen=32)

    overlap_errors = [e for e in errors if e.rule_id == "no_overlaps"]
    assert len(overlap_errors) > 0, "Should detect overlapping ranges"

def test_overlapping_registers():
    """Test detection of overlapping registers with XLEN-dependent sizing"""
    # Create a slave with a range containing two adjacent 4-byte spaced registers
    memory_map = {
        "slaves": {
            "test": {
                "ranges": [
                    {"name": "Test Range", "start": 0x00000000, "end": 0x0000000F, "cacheable": False}
                ],
                "registers": {
                    "reg1": {"name": "Register 1", "addr": 0x00000000, "access": "rw"},
                    "reg2": {"name": "Register 2", "addr": 0x00000004, "access": "rw"}
                }
            }
        }
    }

    validator = MemoryMapValidator()

    # With XLEN=32, registers should NOT overlap (4-byte registers, 4-byte spacing)
    errors_32 = validator.validate(memory_map, xlen=32)
    register_overlap_errors_32 = [e for e in errors_32 if e.rule_id == "no_register_overlaps"]
    assert len(register_overlap_errors_32) == 0, f"XLEN=32 should not have register overlaps, got: {[e.message for e in register_overlap_errors_32]}"

    # With XLEN=64, registers SHOULD overlap (8-byte registers, 4-byte spacing)
    errors_64 = validator.validate(memory_map, xlen=64)
    register_overlap_errors_64 = [e for e in errors_64 if e.rule_id == "no_register_overlaps"]
    assert len(register_overlap_errors_64) > 0, "XLEN=64 should detect register overlaps"

def test_invalid_access_value():
    """Test detection of invalid access values"""
    invalid_memory_map = {
        "slaves": {
            "test": {
                "ranges": [
                    {"name": "Test", "start": 0x00000000, "end": 0x00000003, "access": "invalid", "cacheable": False}
                ]
            }
        }
    }

    validator = MemoryMapValidator()
    errors = validator.validate(invalid_memory_map, xlen=32)

    access_errors = [e for e in errors if e.rule_id == "valid_access_values"]
    assert len(access_errors) > 0, "Should detect invalid access values"

def test_word_alignment():
    """Test word alignment validation"""
    invalid_memory_map = {
        "slaves": {
            "test": {
                "ranges": [
                    {"name": "Test", "start": 0x00000001, "end": 0x00000004, "access": "rw", "cacheable": False}
                ]
            }
        }
    }

    validator = MemoryMapValidator()
    errors = validator.validate(invalid_memory_map, xlen=32)

    alignment_errors = [e for e in errors if e.rule_id == "word_aligned"]
    assert len(alignment_errors) > 0, "Should detect unaligned addresses"

def test_highest_cacheable_address():
    """Test calculation of highest cacheable address"""
    memory_map = {
        "slaves": {
            "sdram": {
                "ranges": [
                    {"name": "RAM", "start": 0x00000000, "end": 0x01FFFFFF, "cacheable": True}
                ]
            },
            "flash": {
                "ranges": [
                    {"name": "ROM", "start": 0x02000000, "end": 0x02FFFFFF, "access": "ro"}
                ]
            }
        }
    }

    validator = MemoryMapValidator()
    highest = validator.get_highest_cacheable_address(memory_map, xlen=32)

    assert highest == 0x01FFFFFF, f"Expected highest cacheable address 0x01FFFFFF, got 0x{highest:08x}"
