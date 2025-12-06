import click
from pathlib import Path
from curvtools.cli.curvcfg.lib.curv_paths.curvpaths import CurvPaths

class Device:
    """
    A toml file under a CURV_CONFIG_DEVICES_DIR directory.
    """
    def __init__(self, path: Path):
        self._path = path.resolve()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._path.stem

    @classmethod
    def from_name(cls, name: str, curvpaths: CurvPaths) -> "Device":
        devices_dir = curvpaths["CURV_CONFIG_DEVICES_DIR"]
        if devices_dir is None or not devices_dir.is_fully_resolved():
            raise click.ClickException(
                f"Devices dir is not resolved; cannot resolve device {name!r}"
            )

        path = Path(devices_dir.to_str()) / f"{name}.toml"
        if not path.exists():
            raise click.ClickException(
                f"Device {name!r} not found under {devices_dir.to_str()!r}"
            )
        curvpaths.update_and_refresh(device=name)
        return cls(path)
