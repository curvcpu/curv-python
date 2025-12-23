from __future__ import annotations

from dataclasses import dataclass, field
import os
import click
from typing import Optional, TYPE_CHECKING, Any
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths, get_curv_paths
from pathlib import Path

if TYPE_CHECKING:
    from curvtools.cli.curvcfg.cli_helpers.paramtypes.profile import Profile
    from curvtools.cli.curvcfg.cli_helpers.paramtypes.board import Board
    from curvtools.cli.curvcfg.cli_helpers.paramtypes.device import Device

@dataclass
class CurvContext:
    curv_root_dir: Optional[Path]          = None
    build_dir:     Optional[Path]          = None
    profile:       Optional[Profile]       = None
    board:         Optional[Board]         = None
    device:        Optional[Device]        = None

    curvpaths:     Optional[CurvPaths]     = None

    _ctx:          Optional[click.Context] = None
    _args:         dict[str, Any]          = field(default_factory=dict)

    @property
    def args(self) -> dict[str, Any]:
        """
        The arguments passed to the command
        """
        return self._args

    @property
    def ctx(self) -> click.Context:
        """
        The click context object
        """
        return self._ctx
    
    @ctx.setter
    def ctx(self, ctx: click.Context):
        """
        Set the click context object; on every set we use
        it to refresh the internal curvpaths object.
        """
        assert isinstance(ctx, click.Context), "ctx argumentmust be a click.Context object"
        self._ctx = ctx
        self._update_and_retrieve_curvpaths()
        return

    def _update_and_retrieve_curvpaths(self) -> CurvPaths:
        if self.curvpaths is None:
            assert self._ctx is not None, "self._ctx must be set to update curvpaths"
            self.curvpaths = get_curv_paths(self._ctx)
        else:
            kwargs = {}
            for k, v in [
                ("curv_root_dir", self._ctx.params.get("curv_root_dir", self.curv_root_dir)),
                ("build_dir", self._ctx.params.get("build_dir", self.build_dir)),
                ("board", self._ctx.params.get("board", self.board)),
                ("device", self._ctx.params.get("device", self.device)),
                ("profile", self._ctx.params.get("profile", self.profile)),
            ]:
                if v is not None:
                    # if getattr(self, k, None) is None:
                        # setattr(self, k, v)
                    kwargs[k] = v
            if len(kwargs) > 0:
                self.curvpaths.update_and_refresh(**kwargs)
        retval = self.curvpaths
        return retval

    def make_paths(self) -> CurvPaths:
        if not self.curv_root_dir or not self.build_dir:
            raise click.UsageError(
                "--curv-root-dir and --build-dir are required"
            )
        return self._update_and_retrieve_curvpaths()
