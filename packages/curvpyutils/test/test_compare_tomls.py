from pathlib import Path
from curvpyutils.test_helpers import compare_toml_files

def test_compare_same_tomls():
    """
    Compares two TOML files that should be the same once canonicalized.
    """
    test_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "same" / "test1a.toml"
    expected_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "same" / "test1b.toml"
    assert compare_toml_files(test_file, expected_file)

def test_compare_differing_tomls():
    """
    Compares two TOML files that should be different once canonicalized.
    """
    test_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "diff" / "test1a.toml"
    expected_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "diff" / "test1b.toml"
    assert not compare_toml_files(test_file, expected_file, show_delta=True, delete_temp_files=False)

def test_compare_almost_same_tomls():
    """
    Compares two TOML files that should be almost the same once canonicalized.
    """
    test_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "almost_same" / "test1a.toml"
    expected_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "almost_same" / "test1b.toml"
    assert not compare_toml_files(test_file, expected_file, show_delta=True, delete_temp_files=False)

def test_compare_diff_only_in_comment():
    """
    Compares two TOML files that should be different only in a comment.
    """
    test_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "diff_only_in_comment" / "test1a.toml"
    expected_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / "diff_only_in_comment" / "test1b.toml"
    assert not compare_toml_files(test_file, expected_file, show_delta=True, delete_temp_files=False)
