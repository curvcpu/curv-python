import click
from pathlib import Path
from curvtools.cli.curvcfg.lib.curv_paths.curvpaths import CurvPaths

class Board:
    """
    A board.toml file under a CURV_CONFIG_BOARD_DIR directory.  A CURV_CONFIG_BOARD_DIR directory is a 
    directory under CURV_CONFIG_BOARDS_DIR.
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
    def from_name(cls, board_name: str, curvpaths: CurvPaths) -> "Board":
        boards_dir = curvpaths["CURV_CONFIG_BOARDS_DIR"]
        if boards_dir is None or not boards_dir.is_fully_resolved():
            raise click.ClickException(
                f"Boards dir is not resolved; cannot resolve board.toml for board {board_name!r}"
            )

        path = Path(boards_dir.to_str()) / f"{board_name}" / f"board.toml"
        if not path.exists():
            raise click.ClickException(
                f"for board {board_name!r}, file not found {Path(boards_dir.to_str()) / f'{board_name}' / f'board.toml'!r}"
            )
        curvpaths.update_and_refresh(board=board_name)
        return cls(path)
