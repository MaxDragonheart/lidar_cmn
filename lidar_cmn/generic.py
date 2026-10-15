import shutil
from pathlib import Path
from typing import Union
from urllib import request

from fsspec import get_fs_token_paths

from lidar_cmn.config import logger


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
        logger.info(f"Folder created. Path: {destination_folder}")


def download_from_url(url: str, destination: Path, timeout: float = 60) -> Path:
    """Download file from url.

    The file is written to a temporary `.part` file, renamed only when the
    download is complete: an interrupted download never leaves a truncated file.

    Args:
        url: str, leading and trailing spaces are ignored
        destination: Path
        timeout: float, seconds to wait for the server

    Returns:
        Path

    Exception:
        - urllib.error.URLError: the server is unreachable or returns an error
        - TimeoutError: the server doesn't answer within timeout
        - {url} returned an HTML page instead of the file.
        - Incomplete download of {url}.
    """
    url = url.strip()
    file_name = url.split('/')[-1]
    download_path = destination.joinpath(file_name)
    temporary_path = destination.joinpath(f"{file_name}.part")
    make_folder(destination_folder=destination)

    try:
        with request.urlopen(url, timeout=timeout) as response:
            # Proxies and error pages answer with HTML instead of the file
            if "text/html" in response.headers.get("Content-Type", ""):
                raise Exception(f"{url} returned an HTML page instead of the file.")
            expected_size = response.headers.get("Content-Length")
            with open(temporary_path, "wb") as output:
                shutil.copyfileobj(response, output)

        downloaded_size = temporary_path.stat().st_size
        if expected_size is not None and downloaded_size != int(expected_size):
            raise Exception(f"Incomplete download of {url}: {downloaded_size} of {expected_size} bytes.")

        temporary_path.replace(download_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    logger.info(f"File downloaded. Path: {download_path}")

    return download_path
