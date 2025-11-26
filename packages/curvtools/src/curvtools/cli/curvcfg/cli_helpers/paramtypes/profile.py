import os
import click
from pathlib import Path
from typing import Optional, Callable
from functools import partial
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.lib.curv_paths.curvpaths import CurvPaths, get_curv_paths

DelayedInitFunc = Callable[[CurvPaths], "Profile"]

class Profile:
    def __init__(self, path: str|DelayedInitFunc):
        if isinstance(path, str):
            self._path = Path(path).resolve() if path is not None else None
        elif isinstance(path, DelayedInitFunc):
            self._delayed_init_func = path
            self._path = None
        else:
            raise ValueError(f"Invalid path type: {type(path)}")

    @classmethod
    def from_name(cls, name: str, curvpaths: CurvPaths) -> Profile:
        profiles_dir = curvpaths['CURV_CONFIG_PROFILES_DIR']
        if profiles_dir is not None and profiles_dir.is_fully_resolved():
            path = os.path.join(str(profiles_dir), f"{name}.toml")
            if not os.path.exists(path):
                raise click.ClickException(f"Profile {name!r} not found under {profiles_dir!r}")
            else:
                return cls(path=path)
        raise click.ClickException(f"Profile {name!r} not found under {profiles_dir!r}")

    def finish_init(self, curvpaths: CurvPaths) -> "Profile":
        if self._delayed_init_func is not None:
            new = self._delayed_init_func(curvpaths)
            self._path = new._path
            self._delayed_init_func = None
        return self

    @property
    def name(self) -> str | None:
        return self.path.stem if self.path is not None else None
    @property
    def path(self) -> Path | None:
        return self._path if self._path is not None and self._path.exists() else None

class ProfileType(click.ParamType):
    name = "profile"

    def __init__(self):
        pass

    def convert(self, value, param, ctx) -> Profile:
        # if looks like a path, resolve directly
        if os.path.isabs(value) or os.path.sep in value:
            path = os.path.abspath(value)
            if not os.path.exists(path):
                self.fail(f"Profile path {path!r} does not exist", param, ctx)
            name = os.path.splitext(os.path.basename(path))[0]
            return Profile(name=name, path=path)

        # treat as logical name
        curvctx = ctx.find_object(CurvContext)
        if curvctx is not None and curvctx.curvpaths is not None:
            profiles_dir = curvpaths['CURV_CONFIG_PROFILES_DIR']
            if profiles_dir is not None and profiles_dir.is_fully_resolved():
                path = os.path.join(profiles_dir, f"{value}.toml")
                if not os.path.exists(path):                    
                    self.fail(
                        f"Profile {value!r} not found under {self.profiles_base_dir!r}",
                        param,
                        ctx,
                    )
                else:
                    return Profile(path=path)
        
        fn: Callable[[CurvPaths], Profile] = partial(Profile.from_name, name=value)
        return Profile(path=fn)