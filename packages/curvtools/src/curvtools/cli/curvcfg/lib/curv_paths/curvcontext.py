from dataclasses import dataclass
import os
import click
from typing import Optional
# from curvtools.cli.curvcfg.cli_helpers import Profile
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths, get_curv_paths
from pathlib import Path

@dataclass
class CurvContext:
    curv_root_dir: Optional[str]     = None
    build_dir:     Optional[str]     = None
    profile:       Optional[str] = None
    board:         Optional[str]     = None
    device:        Optional[str]     = None
    merged_toml:   Optional[Path]    = None

    ctx: click.Context | None = None
    
    _curvpaths: CurvPaths | None = None

    @property
    def curvpaths(self) -> CurvPaths:
        if self._curvpaths is None:
            self._curvpaths = get_curv_paths(self.ctx)
        if self._curvpaths is not None:
            self._curvpaths.update_and_refresh(
                curv_root_dir=self.ctx.params.get("curv_root_dir", self.curv_root_dir),
                build_dir=self.ctx.params.get("build_dir", self.build_dir),
                board=self.ctx.params.get("board", self.board),
                device=self.ctx.params.get("device", self.device),
                profile=self.ctx.params.get("profile", self.profile),
                merged_toml=self.ctx.params.get("merged_toml", self.merged_toml),
            )
        return self._curvpaths

    def make_paths_tb(self) -> CurvPaths:
        if not self.curv_root_dir or not self.build_dir:
            raise click.UsageError(
                "--curv-root-dir and --build-dir are required"
            )
        return self.curvpaths

    def make_paths_soc(self) -> CurvPaths:
        missing = [
            name for name, value in [
                ("--curv-root-dir", self.curv_root_dir),
                ("--build-dir", self.build_dir),
                ("--board", self.board),
                ("--device", self.device),
                ("--profile", self.profile),
            ] if not value
        ]
        if missing:
            raise click.UsageError(
                "Missing required options for 'soc' commands: " + ", ".join(missing)
            )
        return self.curvpaths
