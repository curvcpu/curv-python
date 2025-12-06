import click
from pathlib import Path
from curvtools.cli.curvcfg.lib.curv_paths.curvpaths import CurvPaths

class Profile:
    def __init__(self, path: Path):
        self._path = path.resolve()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._path.stem

    @classmethod
    def from_name(cls, name: str, curvpaths: CurvPaths) -> "Profile":
        profiles_dir = curvpaths["CURV_CONFIG_PROFILES_DIR"]
        if profiles_dir is None or not profiles_dir.is_fully_resolved():
            raise click.ClickException(
                f"Profiles dir is not resolved; cannot resolve profile {name!r}"
            )

        path = Path(profiles_dir.to_str()) / f"{name}.toml"
        if not path.exists():
            raise click.ClickException(
                f"Profile {name!r} not found under {profiles_dir!r}"
            )
        curvpaths.update_and_refresh(profile=name)
        return cls(path)
