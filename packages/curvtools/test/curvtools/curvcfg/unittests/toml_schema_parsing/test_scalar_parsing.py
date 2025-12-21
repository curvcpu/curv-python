from pathlib import Path
import sys
import json
import pytest
import tempfile
import shutil
from curvtools.cli.curvcfg.lib.util.config_parsing.combine_merge_tomls import combine_tomls, merge_tomls
import curvpyutils.tomlrw as tomlrw
from curvtools.cli.curvcfg.lib.util.config_parsing import (
    schema_oracle_from_merged_toml,
    SchemaOracle,
    Artifact,
    ValueSource,
    ParseType,
)
from curvtools.cli.curvcfg.lib.util.config_parsing.util import render_template_to_str
from curvpyutils.test_helpers import compare_toml_files, compare_files
from rich import print as rprint
from conftest import class_had_failures

pytestmark = [pytest.mark.unit]


#
# Define paths to the test input files
#

INPUT_DIR = Path(__file__).parent / "test_vectors" / "input"
EXPECTED_DIR = Path(__file__).parent / "test_vectors" / "expected"

SCHEMA_FILES = [
    INPUT_DIR / "scalars_schema1.toml",
    INPUT_DIR / "scalars_schema2.toml",
    INPUT_DIR / "btns_schema.toml",
    INPUT_DIR / "leds_schema.toml",
]

CONFIG_FILES = [
    INPUT_DIR / "scalars.toml",
    INPUT_DIR / "btns.toml",
    INPUT_DIR / "leds.toml",
    INPUT_DIR / "scalars_overlay.toml",
]



@pytest.fixture(scope="class")
def temp_combine_and_merge_tomls(request):
    """Class-scoped fixture that creates combined schema 
    files and merged config/board vars TOML files."""

    # Setup
    temp_dir = Path(tempfile.mkdtemp(prefix="curvcfg_test_"))
    combined_schema_file = temp_dir / "combined_schema.toml"
    merged_vars_toml_file = temp_dir / "merged_vars.toml"
    merged_schema_vars_toml_file = temp_dir / "merged_schema_vars.toml"
    expected_combined_schema_file = EXPECTED_DIR / "combined_schema.toml"
    expected_merged_vars_toml_file = EXPECTED_DIR / "merged_vars.toml"
    expected_merged_schema_vars_toml_file = EXPECTED_DIR / "merged_schema_vars.toml"

    # Create combined schema file
    schema_dict = combine_tomls(SCHEMA_FILES)
    schema_dict_str = tomlrw.dumps(schema_dict, should_canonicalize=True, should_sort_if_canonicalizing=True)
    with open(combined_schema_file, "w") as f:
        f.write(schema_dict_str)

    # Merge config/board vars TOML files
    merged_vars_dict = merge_tomls(CONFIG_FILES)
    merged_vars_dict_str = tomlrw.dumps(merged_vars_dict, should_canonicalize=True, should_sort_if_canonicalizing=True)
    with open(merged_vars_toml_file, "w") as f:
        f.write(merged_vars_dict_str)

    # Make available to the test class
    request.cls.combined_schema_file = combined_schema_file
    request.cls.merged_vars_toml_file = merged_vars_toml_file
    request.cls.merged_schema_vars_toml_file = merged_schema_vars_toml_file # empty file that tests write to
    request.cls.expected_combined_schema_file = expected_combined_schema_file
    request.cls.expected_merged_vars_toml_file = expected_merged_vars_toml_file
    request.cls.expected_merged_schema_vars_toml_file = expected_merged_schema_vars_toml_file
    request.cls.temp_dir = temp_dir  # Expose for manual inspection if needed
    
    yield  # Tests run here
    
    # Teardown - automatically preserve files if any test in the class failed
    if class_had_failures(request.cls):
        print(f"\n📣 Test(s) failed - preserving temp files at: {temp_dir} ", file=sys.stderr)
        print(f"  combined_schema_file:                  {combined_schema_file}", file=sys.stderr)
        print(f"  merged_vars_toml_file:                 {merged_vars_toml_file}", file=sys.stderr)
        print(f"  merged_schema_vars_toml_file:          {merged_schema_vars_toml_file}", file=sys.stderr)
        print(f"  expected_combined_schema_file:         {expected_combined_schema_file}", file=sys.stderr)
        print(f"  expected_merged_vars_toml_file:        {expected_merged_vars_toml_file}", file=sys.stderr)
        print(f"  expected_merged_schema_vars_toml_file: {expected_merged_schema_vars_toml_file}", file=sys.stderr)
    else:
        shutil.rmtree(temp_dir)


@pytest.mark.usefixtures("temp_combine_and_merge_tomls")
class TestWithFixture:
    """Test class using fixture for setup/teardown."""

    def test_combined_schema_file_exists(self):
        assert self.combined_schema_file.exists()

    def test_merged_vars_toml_file_exists(self):
        assert self.merged_vars_toml_file.exists()

    def _make_merged_schema_vars_toml(self) -> Path:
        """
        Makes a merged.toml file with everything combined and returns its
        path (which is just self.merged_schema_vars_toml_file). Idempotent.
        """
        if self.merged_schema_vars_toml_file.exists():
            return self.merged_schema_vars_toml_file
        merged_schema_vars_dict = combine_tomls([self.combined_schema_file, self.merged_vars_toml_file])
        merged_schema_vars_dict_str = tomlrw.dumps(merged_schema_vars_dict, should_canonicalize=True, should_sort_if_canonicalizing=True)
        self.merged_schema_vars_toml_file.write_text(merged_schema_vars_dict_str)
        return self.merged_schema_vars_toml_file

    def test_merged_schema_vars_toml_file_exists(self):
        assert self._make_merged_schema_vars_toml().exists()

    @pytest.fixture(scope="class")
    def build_schema_oracle(self, temp_combine_and_merge_tomls):
        """
        Builds a SchemaOracle from the merged schema vars TOML file.
        """
        merged_path = self._make_merged_schema_vars_toml()
        schema_oracle = schema_oracle_from_merged_toml(merged_path)

        # Ensure all required vars got resolved (either via config or default)
        unresolved = list(schema_oracle.iter_unresolved())
        assert not unresolved, f"Unresolved schema entries: {unresolved}"

        yield schema_oracle

    @pytest.mark.usefixtures("build_schema_oracle")
    def test_schema_oracle_smoke_test(self, build_schema_oracle: SchemaOracle):
        assert build_schema_oracle is not None

        # Smoke-check artifact views
        env_values   = build_schema_oracle.get_values_for_artifact(Artifact.ENV)
        svh_values   = build_schema_oracle.get_values_for_artifact(Artifact.SVH)
        jinja_values = build_schema_oracle.get_values_for_artifact(Artifact.JINJA2)
        assert len(env_values) != 0
        assert len(svh_values) != 0
        assert len(jinja_values) != 0
        # rprint("ENV values:", env_values)
        # rprint("SVH values:", svh_values)
        # rprint("JINJA2 arrays:", {k: len(v) for k, v in jinja_values.items()})
        # rprint("✅")
    
    @pytest.mark.usefixtures("build_schema_oracle")
    def test_config_var_values(self, build_schema_oracle):
        assert build_schema_oracle is not None
        schema_oracle = build_schema_oracle

        # Smoke-check config var values and display
        config_var_values = schema_oracle.get_values_for_artifact(Artifact.MK)
        assert config_var_values["CFG_CACHE_HEX_FILES_BASE_ADDR"] == 0x0000_FFFC
        assert config_var_values["CFG_CACHE_HEX_FILES_SRC_TYPE"] == "asm"
        assert config_var_values["CFG_CACHE_TAGS_IN_LUTRAM"] == 0
        assert config_var_values["CFG_CACHE_SETS"] == 64

    @pytest.mark.usefixtures("build_schema_oracle")
    def test_config_var_value_formatting(self, build_schema_oracle):
        assert build_schema_oracle is not None
        schema_oracle = build_schema_oracle

        s = schema_oracle.by_toml_path("cache.hex_files.base_addr").sv_display()
        assert s == "localparam logic [31:0] CFG_CACHE_HEX_FILES_BASE_ADDR = 32'h0000fffc;"
        s = schema_oracle.by_toml_path("cache.hex_files.base_addr").mk_display()
        assert s == "0x0000fffc"

        s = schema_oracle.by_toml_path("cache.hex_files.src.type").mk_display()
        assert s == "asm"

        s = schema_oracle.by_toml_path("cache.tags_in_lutram").mk_display()
        assert s == "0"

        s = schema_oracle.by_toml_path("cache.sets").mk_display()
        assert s == "64"
        s = schema_oracle.by_toml_path("cache.sets").sv_display()
        assert s == "localparam int CFG_CACHE_SETS = 64;"

    @pytest.mark.usefixtures("build_schema_oracle")
    def test_config_array_values(self, build_schema_oracle):
        assert build_schema_oracle is not None
        schema_oracle = build_schema_oracle

        # Smoke-check config array values and display
        config_array_values = schema_oracle.get_values_for_artifact(Artifact.JINJA2)
        assert set(config_array_values.keys()) == {"BOARD_BTNS", "BOARD_LEDS"}

        btns = config_array_values["BOARD_BTNS"]
        leds = config_array_values["BOARD_LEDS"]

        assert len(btns) == 6
        assert len(leds) == 8

        # Array-level metadata should live on the array, not per element
        assert btns.meta["lpf_name"] == "btn"
        assert leds.meta["lpf_name"] == "leds"

        # Elements should not carry array-level metadata
        assert all("lpf_name" not in elem for elem in btns)
        assert all("lpf_name" not in elem for elem in leds)

        assert [b["name"] for b in btns] == ["B1", "B2", "UP", "DOWN", "LEFT", "RIGHT"]
        assert [b["active_state"] for b in btns] == [0, 0, 1, 1, 1, 1]

        assert [l["name"] for l in leds] == [
            "RT_RED_LED",
            "RT_ORNG_LED",
            "RT_GRN_LED",
            "RT_BLU_LED",
            "LFT_RED_LED",
            "LFT_ORNG_LED",
            "LFT_GRN_LED",
            "LFT_BLU_LED",
        ]

    def test_merged_schema_vars_toml_file_contents(self):
        merged_path = self._make_merged_schema_vars_toml()
        cmp = compare_toml_files(merged_path, self.expected_merged_schema_vars_toml_file, show_delta=True, debug_output_silent=True)
        assert cmp is True

    def test_combined_schema_file_contents(self):
        cmp = compare_toml_files(self.combined_schema_file, self.expected_combined_schema_file, show_delta=True, debug_output_silent=True)
        assert cmp is True

    def test_merged_vars_toml_file_contents(self):
        cmp = compare_toml_files(self.merged_vars_toml_file, self.expected_merged_vars_toml_file, show_delta=True, debug_output_silent=True)
        assert cmp is True

    @pytest.mark.usefixtures("build_schema_oracle")
    def test_boardpkg_sv_file_contents(self, build_schema_oracle: SchemaOracle):
        assert build_schema_oracle is not None
        schema_oracle = build_schema_oracle

        template_path = INPUT_DIR / "boardpkg.sv.jinja2"
        rendered_template = render_template_to_str(template_path, schema_oracle)

        generated_path = self.temp_dir / "boardpkg.sv"
        generated_path.write_text(rendered_template)

        expected_path = EXPECTED_DIR / "boardpkg.sv"

        cmp_ok = compare_files(
            generated_path,
            expected_path,
            show_delta=True,
            verbose=True,
        )
        if not cmp_ok:
            assert cmp_ok, "Jinja2 template test failed"