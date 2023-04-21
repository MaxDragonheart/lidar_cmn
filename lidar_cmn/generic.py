import logging
from pathlib import Path
from typing import Union
from urllib import request

from fsspec import get_fs_token_paths

from lidar_cmn.config import logger, console_handler

logger.addHandler(console_handler)


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


def path_exists(path, fs=None):
    if fs is None:
        fs, fs_token, paths = get_fs_token_paths(path)
    exists = fs.exists(path)

    return exists


def make_folder(destination_folder: Path):
    """Make folder from path.

    Args:
        destination_folder: Path
    """
    if not path_exists(path=destination_folder):
        fs, fs_token, paths = get_fs_token_paths(destination_folder)
        fs.mkdirs(path=destination_folder, exist_ok=True)
        logging.info(f"Folder created. Path: {destination_folder}")


def download_from_url(url: str, destination: Path) -> Path:
    """Download file from url.

    Args:
        url: str
        destination: Path
    """
    file_name = url.split('/')[-1]
    download_path = destination.joinpath(file_name)
    make_folder(destination_folder=destination)
    request.urlretrieve(url, download_path)
    logging.info(f"File downloaded. Path: {download_path}")

    return download_path
