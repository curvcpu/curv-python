import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from curvpyutils.test_helpers import compare_files, compare_toml_files


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Repository root not found")


REPO_ROOT = _repo_root()
SRC_PATHS = [
    REPO_ROOT / "packages" / "curvtools" / "src",
    REPO_ROOT / "packages" / "curvpyutils" / "src",
    REPO_ROOT / "packages" / "curv" / "src",
]
CURVCFG_MODULE = "curvtools.cli.curvcfg"


pytestmark = [pytest.mark.e2e]


# Pytest hook to expose test outcome to fixtures so they can decide on cleanup.
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


BOARD_MERGE_OUTPUTS = [
    ("generated/config/merged_board.toml", True),
    ("generated/make/board.mk.d", False),
]

BOARD_GENERATE_OUTPUTS = [
    ("generated/hdl/board.svh", False),
    ("generated/hdl/boardpkg.sv", False),
    ("generated/make/board.mk", False),
    ("generated/shell/board.env", False),
]

CFGVARS_MERGE_OUTPUTS = [
    ("generated/config/merged_cfgvars.toml", True),
    ("generated/make/config.mk.d", False),
]

CFGVARS_GENERATE_OUTPUTS = [
    ("generated/hdl/curvcfg.svh", False),
    ("generated/hdl/curvcfgpkg.sv", False),
    ("generated/make/curv.mk", False),
    ("generated/shell/curv.env", False),
]


@pytest.fixture
def fake_root_dir() -> Path:
    return Path(__file__).resolve().parent / "fake_curv_root"


@pytest.fixture
def expected_build_dir() -> Path:
    return Path(__file__).resolve().parent / "expected" / "builddir"


@pytest.fixture
def build_dir(tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest) -> Path:
    path = tmp_path_factory.mktemp("curvcfg-build")
    yield path
    rep_call = getattr(request.node, "rep_call", None)
    if rep_call is None or rep_call.failed:
        print(f"Keeping build dir for debugging: {path}")
    else:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def curvcfg_env(fake_root_dir: Path, build_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CURV_ROOT_DIR"] = str(fake_root_dir)
    env["CURV_BUILD_DIR"] = str(build_dir)
    python_paths = [str(p) for p in SRC_PATHS]
    existing = env.get("PYTHONPATH")
    if existing:
        python_paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    return env


def _run_curvcfg(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, "-m", CURVCFG_MODULE, *args],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"curvcfg command failed with exit code {proc.returncode}\n"
            f"cmd: {proc.args}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            pytrace=False,
        )
    return proc


def _assert_outputs(build_dir: Path, expected_dir: Path, outputs: list[tuple[str, bool]]) -> None:
    for rel_path, is_toml in outputs:
        actual = build_dir / rel_path
        expected = expected_dir / rel_path
        assert actual.exists(), f"Missing output file: {actual}"
        assert expected.exists(), f"Expected file missing: {expected}"
        if is_toml:
            cmp_ok = compare_toml_files(actual, expected, show_delta=True, verbose=True)
        else:
            cmp_ok = compare_files(actual, expected, show_delta=True, verbose=True)
        assert cmp_ok, f"Mismatch for {actual}"


class TestMergeGenerate:
    def test_board_merge_then_generate(
        self,
        fake_root_dir: Path,
        expected_build_dir: Path,
        build_dir: Path,
        curvcfg_env: dict[str, str],
    ) -> None:
        board_schema = fake_root_dir / "boards" / "schema" / "schema.toml"
        board_schema_flash = fake_root_dir / "boards" / "schema" / "schema_flash.toml"
        merged_board_toml = build_dir / "generated" / "config" / "merged_board.toml"
        template = fake_root_dir / "boards" / "templates" / "boardpkg.sv.jinja2"

        _run_curvcfg(
            [
                "-vv",
                "board",
                "merge",
                f"--board=ulx3s",
                f"--device=85f",
                f"--schema={board_schema}",
                f"--schema={board_schema_flash}",
            ],
            cwd=fake_root_dir,
            env=curvcfg_env,
        )

        _assert_outputs(build_dir, expected_build_dir, BOARD_MERGE_OUTPUTS)

        _run_curvcfg(
            [
                "-vv",
                "board",
                "generate",
                f"--merged-board-toml={merged_board_toml}",
                f"--template={template}",
            ],
            cwd=fake_root_dir,
            env=curvcfg_env,
        )

        _assert_outputs(build_dir, expected_build_dir, BOARD_GENERATE_OUTPUTS)

    def test_cfgvars_merge_then_generate(
        self,
        fake_root_dir: Path,
        expected_build_dir: Path,
        build_dir: Path,
        curvcfg_env: dict[str, str],
    ) -> None:
        cfg_schema = fake_root_dir / "config" / "schema" / "schema.toml"
        cfg_tb_schema = fake_root_dir / "config" / "schema" / "tb-extras-schema.toml"
        cfg_overlay = fake_root_dir / "config" / "profiles" / "overlays" / "tb.toml"
        merged_cfgvars = build_dir / "generated" / "config" / "merged_cfgvars.toml"

        _run_curvcfg(
            [
                "-vv",
                "cfgvars",
                "merge",
                "--profile=default",
                f"--schema={cfg_schema}",
                f"--schema={cfg_tb_schema}",
                f"--overlay={cfg_overlay}",
            ],
            cwd=fake_root_dir,
            env=curvcfg_env,
        )

        _assert_outputs(build_dir, expected_build_dir, CFGVARS_MERGE_OUTPUTS)

        _run_curvcfg(
            [
                "-vv",
                "cfgvars",
                "generate",
                f"--merged-config-toml={merged_cfgvars}",
            ],
            cwd=fake_root_dir,
            env=curvcfg_env,
        )

        _assert_outputs(build_dir, expected_build_dir, CFGVARS_GENERATE_OUTPUTS)
