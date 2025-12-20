from pathlib import Path

import pytest

from curvtools.cli.curvcfg.lib.util.config_parsing import schema_oracle_from_merged_toml
from curvtools.cli.curvcfg.lib.util.artifact_emitter.emit_artifacts import emit_artifacts
from curvpyutils.test_helpers import compare_files

pytestmark = [pytest.mark.unit]


def _paths(base: Path):
    return (
        base / "curvcfgpkg.sv",
        base / "curvcfg.svh",
        base / "curv.env",
        base / "curv.mk",
    )


def test_emit_artifacts_with_and_without_templates(tmp_path: Path):
    inputs_dir = Path(__file__).parents[1] / "test_vectors" / "inputs" / "test_emit_artifacts"
    expected_dir = Path(__file__).parents[1] / "test_vectors" / "expected" / "test_emit_artifacts"

    merged_path = inputs_dir / "merged_schema_vars.toml"
    schema_oracle = schema_oracle_from_merged_toml(merged_path)

    # Template (svh) case
    template_path = inputs_dir / "sv_template.svpkg.jinja2"
    svpkg_template_out = tmp_path / "svpkg_from_template.svh"
    emit_artifacts(
        schema_oracle,
        svpkg_out_path=svpkg_template_out,
        svh_out_path=tmp_path / "tmpl_svh.svh",
        env_out_path=tmp_path / "tmpl_env.env",
        mk_out_path=tmp_path / "tmpl_curv.mk",
        svpkg_template=template_path,
    )
    tmpl_expected = expected_dir / "svpkg_from_template.svh"
    cmp_ok = compare_files(
        svpkg_template_out,
        tmpl_expected,
        show_delta=True,
        verbose=True,
    )
    if not cmp_ok:
        print(f"Template svpkg output differed: {svpkg_template_out}")
    assert cmp_ok

    # Default logic (no templates)
    svpkg_out, svh_out, env_out, mk_out = _paths(tmp_path)
    emit_artifacts(
        schema_oracle,
        svpkg_out_path=svpkg_out,
        svh_out_path=svh_out,
        env_out_path=env_out,
        mk_out_path=mk_out,
    )

    expected_svpkg, expected_svh, expected_env, expected_mk = _paths(expected_dir)
    outputs = [svpkg_out, svh_out, env_out, mk_out]
    expecteds = [expected_svpkg, expected_svh, expected_env, expected_mk]
    labels = ["svpkg", "svh", "env", "mk"]

    failed_outputs = []
    for label, outp, exp in zip(labels, outputs, expecteds):
        ok = compare_files(outp, exp, show_delta=True, verbose=True)
        if not ok:
            print(f"{label} output differed: {outp}")
            failed_outputs.append(outp)
    assert not failed_outputs

    # Cleanup only if all passed
    if svpkg_template_out.exists():
        svpkg_template_out.unlink()
    for p in outputs:
        if p.exists():
            p.unlink()
