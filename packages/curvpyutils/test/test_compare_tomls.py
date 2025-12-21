from pathlib import Path
from curvpyutils.test_helpers import compare_toml_files

def test_compare_toml_files_falls_back_to_tomli_when_taplo_is_missing(tmp_path, monkeypatch):
    # Monkeypatch shutil.which used inside curvpyutils.shellutils.which to hide taplo
    import curvpyutils.shellutils.which as which_mod

    real_shutil_which = which_mod.shutil.which

    def fake_which(name, *args, **kwargs):
        if name == "taplo":
            return None
        return real_shutil_which(name, *args, **kwargs)

    monkeypatch.setattr(which_mod.shutil, "which", fake_which)

    from curvpyutils.test_helpers import compare_toml_files

    for name, expected_equal in [
        ("same", True),
        ("diff", False),
        ("almost_same", False),
        # ("diff_only_in_comment", False), # have to skip this one b/c python can't detect comment-only diffs
    ]:
        test_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / name / "test1a.toml"
        expected_file = Path(__file__).parent / "test_vectors" / "input" / "toml_files_for_comparison" / name / "test1b.toml"
        assert expected_equal == compare_toml_files(
            test_file,
            expected_file,
            show_delta=True,          # fine now
            delete_temp_files=False,
        )

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
