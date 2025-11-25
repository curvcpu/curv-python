from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from curvpyutils.toml_utils import MergedTomlDict


TEST_DIR = Path(__file__).parent
SPLITTABLE_TOML = (
    TEST_DIR / "test_vectors" / "inputs" / "key_splitter" / "splittable.toml"
).resolve()


def _count_leaf_kv_pairs(obj: Any) -> int:
    """
    Count the number of leaf key/value pairs in a nested mapping structure.

    A leaf is any non-mapping value. For mappings, we recurse into the values.
    """
    if isinstance(obj, dict):
        total = 0
        for v in obj.values():
            total += _count_leaf_kv_pairs(v)
        return total
    return 1


def _count_subkeys_per_top_level(merged: MergedTomlDict) -> Dict[str, int]:
    """
    Helper used by tests to count how many (leaf) subkeys each top-level key has.
    """
    counts: Dict[str, int] = {}
    for top_key in merged.get_top_level_keys():
        counts[top_key] = _count_leaf_kv_pairs(merged[top_key])
    return counts


@pytest.fixture
def merged_splittable() -> MergedTomlDict:
    """Fixture that loads the splittable TOML into a MergedTomlDict."""
    return MergedTomlDict(SPLITTABLE_TOML)


def test_group_by_top_level_keys_all_keys(merged_splittable: MergedTomlDict) -> None:
    """
    group_by_top_level_keys(keys=[]) -> should split on all top-level keys.

    We verify that:
    - the returned groups correspond exactly to the four expected top-level keys
      in the TOML file, and
    - the leaf subkey counts per top-level key match those computed directly
      from the merged TOML.
    """
    expected_top_keys = {"_schema", "cpu", "cache", "tb"}

    # Sanity: make sure our helper sees the same top-level keys.
    top_keys = set(merged_splittable.get_top_level_keys())
    assert top_keys == expected_top_keys

    expected_counts = _count_subkeys_per_top_level(merged_splittable)

    grouped = merged_splittable.group_by_top_level_keys(keys=[])
    assert set(grouped.keys()) == expected_top_keys

    # For each group, we expect it to contain the full dictionary under that
    # top-level key, and the leaf counts should match.
    for key in expected_top_keys:
        group_dict = grouped[key]
        # Inner mapping should contain exactly the entries starting with that key.
        # In our current representation this is just the single top-level key.
        assert set(group_dict.keys()) == {key}
        assert group_dict[key] is merged_splittable[key]
        assert _count_leaf_kv_pairs(group_dict[key]) == expected_counts[key]


def test_group_by_top_level_keys_schema_only(merged_splittable: MergedTomlDict) -> None:
    """
    group_by_top_level_keys(keys=["_schema"]) -> only the _schema.* keys are present.
    """
    grouped = merged_splittable.group_by_top_level_keys(keys=["_schema"])

    assert set(grouped.keys()) == {"_schema"}
    schema_group = grouped["_schema"]

    # Only entries whose keys start with "_schema" should be present.
    assert set(schema_group.keys()) == {"_schema"}
    assert schema_group["_schema"] is merged_splittable["_schema"]

def test_group_by_top_level_keys_cpu_only(merged_splittable: MergedTomlDict) -> None:
    """
    group_by_top_level_keys(keys=["cpu"]) -> only the cpu.* keys are present ->
    test a cpu.* scalar value to make sure it is included.
    """
    grouped = merged_splittable.group_by_top_level_keys(keys=["cpu"])

    assert set(grouped.keys()) == {"cpu"}
    cpu_group = grouped["cpu"]

    # Only entries whose keys start with "cpu" should be present.
    assert set(cpu_group.keys()) == {"cpu"}
    assert cpu_group["cpu"] is merged_splittable["cpu"]

    # try to get the value for cpu.xlen and make sure it matches the
    # input file
    assert grouped["cpu"]["cpu"]["xlen"] == merged_splittable["cpu"]["xlen"], "cpu.xlen value should match the input file"


def test_group_by_top_level_keys_with_missing_key(
    merged_splittable: MergedTomlDict,
) -> None:
    """
    group_by_top_level_keys(keys=["cpu", "does_not_exist_key"]) should:
    - include the cpu.* entries under the "cpu" key, and
    - map "does_not_exist_key" to an empty dict.
    """
    grouped = merged_splittable.group_by_top_level_keys(
        keys=["cpu", "does_not_exist_key"]
    )

    assert set(grouped.keys()) == {"cpu", "does_not_exist_key"}

    cpu_group = grouped["cpu"]
    assert set(cpu_group.keys()) == {"cpu"}
    assert cpu_group["cpu"] is merged_splittable["cpu"]

    missing_group = grouped["does_not_exist_key"]
    assert isinstance(missing_group, dict)
    assert missing_group == {}


def test_get_top_level_keys_returns_expected_keys(
    merged_splittable: MergedTomlDict,
) -> None:
    """
    Verify that get_top_level_keys() returns exactly the four expected top-level
    keys for the splittable TOML.
    """
    top_keys = merged_splittable.get_top_level_keys()

    # We intentionally ignore scalar fields like "description" and only include
    # dictionary-valued top-level keys.
    assert set(top_keys) == {"_schema", "cpu", "cache", "tb"}

