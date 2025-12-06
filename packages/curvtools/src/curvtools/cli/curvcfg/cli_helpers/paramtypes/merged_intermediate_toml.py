import click
from pathlib import Path
from curvtools.cli.curvcfg.lib.curv_paths.curvpaths import CurvPaths

class MergedIntermediateToml:
    """
    A merged_XXXXXXX.toml file under a BUILD_GENERATED_INTERMEDIATES_DIR directory.
    This applies to merged_board.toml and merged_config.toml before they are combined into
    merged.toml.
    """
    def __init__(self, path: Path,):
        self._path = path.resolve()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._path.stem

    @classmethod
    def from_name(cls, name: str, curvpaths: CurvPaths) -> "MergedIntermediateToml":
        merged_intermediate_toml_dir = curvpaths["BUILD_GENERATED_INTERMEDIATES_DIR"] 
        if merged_intermediate_toml_dir is None or not merged_intermediate_toml_dir.is_fully_resolved():
            raise click.ClickException(
                f"Merged intermediate toml dir is not resolved; cannot resolve merged intermediate toml {name!r}"
            )

        path = Path(merged_intermediate_toml_dir.to_str()) / f"{name}.toml"
        if not path.exists():
            raise click.ClickException(
                f"Merged intermediate toml {name!r} not found under {merged_intermediate_toml_dir!r}"
            )
        return cls(path)
