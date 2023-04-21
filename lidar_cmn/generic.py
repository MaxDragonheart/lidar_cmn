from pathlib import Path
from typing import Union


def check_path(path: Union[str, Path]) -> Path:
    """Convert string path to Path and check path existences.

    Args:
        path: Union[str, Path]

    Returns:
        Path

    Exception:
        - Not recognized path
        - {path} doesn't exists.
    """
    if isinstance(path, str):
        target_path = Path(path)
    elif isinstance(path, Path):
        target_path = path
    else:
        raise Exception("Not recognized path")

    if target_path.exists():
        return target_path
    else:
        raise Exception(f"{path} doesn't exists.")
