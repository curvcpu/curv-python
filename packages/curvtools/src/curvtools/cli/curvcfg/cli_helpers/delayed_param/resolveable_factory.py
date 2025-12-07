import os
import click
import re
from pathlib import Path
from functools import partial
from typing import TypeVar, Callable
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths, CurvPath
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.cli_helpers.delayed_param.resolveable import Resolvable

T = TypeVar("T")

def make_resolvable_param_type(
    type_name: str,
    from_path: Callable[[Path], T],
    is_input_path: bool,
    from_name: Callable[[str, CurvPaths], T]
) -> click.ParamType:
    """
    Build a Click ParamType that parses a CLI string into Resolvable[T]:
      * path-like      -> eager from_path(Path, is_input_path)
      * name           -> eager from_name(name, curvpaths) if available
                       -> otherwise deferred Resolvable[T] that will call from_name(name, curvpaths) later
                       when CurvPaths is available.
    """

    class _ResolvableType(click.ParamType):
        name = type_name

        def convert(self, value, param, ctx) -> Resolvable[T]:
            if isinstance(value, CurvPath):
                return value
            
            # 1) path-like?
            if os.path.sep in value:
                p = Path(value)
                if is_input_path and not p.exists():
                    self.fail(
                        f"{type_name} path {str(p)!r} does not exist",
                        param,
                        ctx,
                    )
                try:
                    obj = from_path(p)
                except click.ClickException as e:
                    # normalize to fail()
                    self.fail(str(e), param, ctx)
                return Resolvable(_value=obj, raw=value)

            # 2) name, maybe we can resolve now (if CurvPaths already exists)
            need_deferred = False
            try:
                curvctx: CurvContext | None = ctx.find_object(CurvContext) if ctx else None
                curvpaths = getattr(curvctx, "curvpaths", None) if curvctx else None
                if curvpaths is not None:
                    try:
                        obj = from_name(value, curvpaths)
                    except click.ClickException as e:
                        need_deferred = True
                    if not need_deferred:
                        return Resolvable(_value=obj, raw=value)
            except Exception as e:
                need_deferred = True

            # 3) name, but no CurvPaths yet → make it deferred
            if curvpaths is None or need_deferred:
                resolver = partial(from_name, value)
                return Resolvable(_resolver=resolver, raw=value)
            else:
                self.fail(str(e), param, ctx)

    return _ResolvableType()