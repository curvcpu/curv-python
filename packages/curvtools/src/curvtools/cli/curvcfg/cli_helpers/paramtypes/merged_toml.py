import click
from pathlib import Path
from curvtools.cli.curvcfg.lib.curv_paths.curvpaths import CurvPaths

class MergedToml:
    def __init__(self, path: Path,):
        self._path = path.resolve()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._path.stem

    @classmethod
    def from_name(cls, name: str, curvpaths: CurvPaths) -> "MergedToml":
        merged_toml_dir = curvpaths["BUILD_GENERATED_CONFIG_DIR"] 
        if merged_toml_dir is None or not merged_toml_dir.is_fully_resolved():
            raise click.ClickException(
                f"Merged toml dir is not resolved; cannot resolve merged toml {name!r}"
            )

        path = Path(merged_toml_dir.to_str()) / f"{name}.toml"
        if not path.exists():
            raise click.ClickException(
                f"Merged toml {name!r} not found under {merged_toml_dir!r}"
            )
        return cls(path)
