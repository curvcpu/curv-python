from pathlib import Path
import sys
import json
import pytest

# Make the /home/.../scripts directory importable, so we can import parse_schema_scalars
sys.path.insert(0, str('/home/mwg/scripts/tomls'))
import parse_schema_scalars as pss  # type: ignore  # noqa: E402

pytestmark = [pytest.mark.unit]

INPUT_DIR = Path(__file__).parent / "test_vectors" / "input"
EXPECTED_DIR = Path(__file__).parent / "test_vectors" / "expected"

def _write_pretty_json(obj: object, path: Path) -> None:
    """
    Serialize obj to JSON in a stable, pretty format so that byte-for-byte
    comparisons against the expected files are reliable.
    """
    text = json.dumps(obj, indent=4, sort_keys=True)
    # Ensure a trailing newline for POSIX-style text files.
    path.write_text(text + "\n", encoding="utf-8")

def test_schema_scalars() -> None:
    file_path1 = INPUT_DIR / "scalar_tests" / "myfile1.toml"
    file_path2 = INPUT_DIR / "scalar_tests" / "myfile2.toml"
    file_path3 = INPUT_DIR / "scalar_tests" / "myfile3.toml"
    schema1 = pss.load_schema_file(file_path1.as_posix())
    schema2 = pss.load_schema_file(file_path2.as_posix())
    schema3 = pss.load_schema_file(file_path3.as_posix())

    # lookup by CFG_* name
    base_addr_var = schema1["CFG_CACHE_HEX_FILES_BASE_ADDR"]
    tags_in_lutram_var = schema1["CFG_CACHE_TAGS_IN_LUTRAM"]
    icache_var = schema2["CFG_CACHE_HEX_FILES_SUBDIRS_ICACHE"]

    # or by toml path
    same_var = schema1["cache.tags_in_lutram"]

    assert tags_in_lutram_var is same_var
    assert base_addr_var.filename == file_path1.as_posix(), f"base_addr_var.filename (was {base_addr_var.filename}) should be {file_path1.as_posix()}"   # "myfile.toml"
    assert icache_var.filename == file_path2.as_posix(), f"icache_var.filename (was {icache_var.filename}) should be {file_path2.as_posix()}"     # "myfile2.toml"

    raw_val = "0x0000_000f"  # from some other TOML
    assert base_addr_var.validate(raw_val), "base_addr_var.validate(raw_val) should be True"  # True/False
    raw_val = 1
    assert tags_in_lutram_var.validate(raw_val), "tags_in_lutram_var.validate(raw_val) should be True"

    parsed = tags_in_lutram_var.parse(raw_val)   # int/uint coercion
    assert parsed == 1, f"parsed (was {parsed}) should be 1"
    assert type(parsed) == type(1), f"type(parsed) (was {type(parsed)}) should be {type(1)}"                 # e.g. 15 <class 'int'>

    # rprint("tags_in_lutram_var.sv_display():", tags_in_lutram_var.sv_display())
    # rprint("tags_in_lutram_var.mk_display():", tags_in_lutram_var.mk_display())
    assert tags_in_lutram_var.sv_display() == "localparam int CFG_CACHE_TAGS_IN_LUTRAM = 1;", f"tags_in_lutram_var.sv_display() (was {tags_in_lutram_var.sv_display()}) should be 'localparam int CFG_CACHE_TAGS_IN_LUTRAM = 1;'"
    assert tags_in_lutram_var.mk_display() == "1", f"tags_in_lutram_var.mk_display() (was {tags_in_lutram_var.mk_display()}) should be '1'"

    # rprint("icache_var.sv_display():", icache_var.sv_display())
    # rprint("icache_var.mk_display():", icache_var.mk_display())
    assert icache_var.sv_display() == "localparam string CFG_CACHE_HEX_FILES_SUBDIRS_ICACHE = \"icache\";", f"icache_var.sv_display() (was {icache_var.sv_display()}) should be 'localparam string CFG_CACHE_HEX_FILES_SUBDIRS_ICACHE = \"icache\";'"
    assert icache_var.mk_display() == "icache", f"icache_var.mk_display() (was {icache_var.mk_display()}) should be 'icache'"


    # rprint("tags_in_lutram_var.artifacts:", tags_in_lutram_var.artifacts)          # [Artifact.MK, Artifact.SVPKG, Artifact.ENV, Artifact.SVH]

    assert tags_in_lutram_var.artifacts == [pss.Artifact.MK, pss.Artifact.SVPKG, pss.Artifact.ENV, pss.Artifact.SVH], f"tags_in_lutram_var.artifacts (was {tags_in_lutram_var.artifacts}) should be [Artifact.MK, Artifact.SV, Artifact.SVPKG, Artifact.ENV, Artifact.SVH]"
