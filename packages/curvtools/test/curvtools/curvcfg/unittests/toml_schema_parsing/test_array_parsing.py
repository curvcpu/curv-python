from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from curvpyutils.test_helpers import compare_files


pytestmark = [pytest.mark.unit]



THIS_DIR = Path(__file__).resolve().parent
VECTORS_DIR = THIS_DIR / "test_vectors"
INPUT_DIR = VECTORS_DIR / "input"
EXPECTED_DIR = VECTORS_DIR / "expected"


# Make the /home/.../scripts directory importable, so we can import parse_schema_arrays
sys.path.insert(0, str('/home/mwg/scripts/tomls'))

import parse_schema_arrays as psa  # type: ignore  # noqa: E402


def _write_pretty_json(obj: object, path: Path) -> None:
    """
    Serialize obj to JSON in a stable, pretty format so that byte-for-byte
    comparisons against the expected files are reliable.
    """
    text = json.dumps(obj, indent=4, sort_keys=True)
    # Ensure a trailing newline for POSIX-style text files.
    path.write_text(text + "\n", encoding="utf-8")


def test_compile_schema_and_profile_for_buttons_arrays(tmp_path: Path) -> None:
    """
    The outward shape (compiled[_schema]['arrays']) for buttons should match
    test_vectors/expected/btns1.json exactly.
    """
    profile_toml = (INPUT_DIR / "btns.toml").read_text(encoding="utf-8")
    schema_toml = (INPUT_DIR / "btns_schema.toml").read_text(encoding="utf-8")

    compiled = psa.compile_schema_and_profile(profile_toml, schema_toml)

    generated = tmp_path / "btns1.json"
    _write_pretty_json(compiled[psa.SCHEMA_ROOT_KEY]["arrays"], generated)
    expected = EXPECTED_DIR / "btns1.json"

    cmp_result = compare_files(generated, expected, verbose=False, show_delta=True)
    assert cmp_result is True


def test_compile_schema_and_profile_for_buttons_values(tmp_path: Path) -> None:
    """
    The validated array-of-objects for buttons should match
    test_vectors/expected/btns2.json exactly.
    """
    profile_toml = (INPUT_DIR / "btns.toml").read_text(encoding="utf-8")
    schema_toml = (INPUT_DIR / "btns_schema.toml").read_text(encoding="utf-8")

    compiled = psa.compile_schema_and_profile(profile_toml, schema_toml)

    generated = tmp_path / "btns2.json"
    _write_pretty_json(compiled["values"]["board.buttons"], generated)
    expected = EXPECTED_DIR / "btns2.json"

    cmp_result = compare_files(generated, expected, verbose=False, show_delta=True)
    assert cmp_result is True

    # Preserve the original assertion on the rendered SV declaration.
    assert compiled["sv_ports"]["board.buttons"] == "input wire [2:0] btn"


def test_compile_schema_and_profile_for_leds_arrays(tmp_path: Path) -> None:
    """
    The outward shape (compiled[_schema]['arrays']) for leds should match
    test_vectors/expected/leds1.json exactly.
    """
    profile_toml = (INPUT_DIR / "leds.toml").read_text(encoding="utf-8")
    schema_toml = (INPUT_DIR / "leds_schema.toml").read_text(encoding="utf-8")

    compiled = psa.compile_schema_and_profile(profile_toml, schema_toml)

    generated = tmp_path / "leds1.json"
    _write_pretty_json(compiled[psa.SCHEMA_ROOT_KEY]["arrays"], generated)
    expected = EXPECTED_DIR / "leds1.json"

    cmp_result = compare_files(generated, expected, verbose=False, show_delta=True)
    assert cmp_result is True


def test_compile_schema_and_profile_for_leds_values(tmp_path: Path) -> None:
    """
    The validated array-of-objects for leds should match
    test_vectors/expected/leds2.json exactly.
    """
    profile_toml = (INPUT_DIR / "leds.toml").read_text(encoding="utf-8")
    schema_toml = (INPUT_DIR / "leds_schema.toml").read_text(encoding="utf-8")

    compiled = psa.compile_schema_and_profile(profile_toml, schema_toml)

    generated = tmp_path / "leds2.json"
    _write_pretty_json(compiled["values"]["board.leds"], generated)
    expected = EXPECTED_DIR / "leds2.json"

    cmp_result = compare_files(generated, expected, verbose=False, show_delta=True)
    assert cmp_result is True

    # Preserve the original assertion on the rendered SV declaration.
    assert compiled["sv_ports"]["board.leds"] == "output wire [7:0] led"


