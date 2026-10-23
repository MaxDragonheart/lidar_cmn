"""Generic utilities: paths, folders, SSL context and download of a single file.

The other modules of the package use these functions, but they work with any
path and any url.
"""
import shutil
import ssl
from functools import cache
from pathlib import Path
from typing import Optional, Union
from urllib import request

import certifi
from fsspec import AbstractFileSystem, get_fs_token_paths

from lidar_cmn.config import intermediate_certificates_path, logger


def check_path(path: Union[str, Path]) -> Path:
    """Convert a path to `Path` and check that it exists.

    Args:
        path: Path of a file or a folder.

    Returns:
        The path as `Path`.

    Raises:
        Exception: If path is neither a `str` nor a `Path`, or if it doesn't exist.

    Examples:
        >>> from lidar_cmn.config import geodata_path
        >>> check_path(path=str(geodata_path)) == geodata_path
        True
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


def path_exists(path: Union[str, Path], fs: Optional[AbstractFileSystem] = None) -> bool:
    """Check that a path exists, on the local disk or on a filesystem supported
    by fsspec.

    Args:
        path: Local path or fsspec url, e.g. `s3://bucket/key`.
        fs: Filesystem of path. If None, it is inferred from path.

    Returns:
        True if path exists, False otherwise.
    """
    if fs is None:
        fs, fs_token, paths = get_fs_token_paths(path)
    exists = fs.exists(path)

    return exists


def make_folder(destination_folder: Path):
    """Create a folder and its parents, if they don't exist.

    Args:
        destination_folder: Folder to create.
    """
    if not path_exists(path=destination_folder):
        fs, fs_token, paths = get_fs_token_paths(destination_folder)
        fs.mkdirs(path=destination_folder, exist_ok=True)
        logger.info(f"Folder created. Path: {destination_folder}")


@cache
def ssl_context() -> ssl.SSLContext:
    """Make the SSL context of the HTTPS connections of the package.

    The server of Città Metropolitana di Napoli, sit.cittametropolitana.na.it,
    sends only its own certificate, without the intermediate certificate that
    signed it. Python can't verify an incomplete chain, unlike the browsers
    and curl on Windows, which download the missing intermediate certificate.
    The context trusts:

    - the certificates of the operating system, as `ssl.create_default_context`,
      also those set with the `SSL_CERT_FILE` and `SSL_CERT_DIR` environment
      variables;
    - the root certificates of certifi, the same on every operating system;
    - the intermediate certificates shipped with the package, in
      `lidar_cmn.config.intermediate_certificates_path`.

    The certificate of the server and its hostname are always verified. The
    context is made once and shared by all the connections: don't modify it.
    See the page Certificato SSL of the documentation.

    Returns:
        The SSL context.

    Examples:
        >>> context = ssl_context()
        >>> context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        True
    """
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    context.load_verify_locations(cafile=intermediate_certificates_path)

    return context


def download_from_url(
        url: str,
        destination: Path,
        timeout: float = 60,
        context: Optional[ssl.SSLContext] = None
) -> Path:
    """Download a file from a url into a folder.

    The file is written to a temporary `.part` file, renamed only when the
    download is complete: an interrupted download never leaves a truncated
    file. A file with the same name in the folder is replaced.

    Args:
        url: Url of the file. The leading and trailing spaces are ignored and
            the name of the file is the last part of the url.
        destination: Folder where the file is saved. It is created if it
            doesn't exist.
        timeout: Seconds to wait for the server, when connecting and between
            two blocks of data.
        context: SSL context of the HTTPS urls. If None, uses `ssl_context`,
            which verifies the certificate of sit.cittametropolitana.na.it on
            every operating system.

    Returns:
        Path of the downloaded file.

    Raises:
        urllib.error.HTTPError: If the server answers with an HTTP error, e.g.
            404 Not Found.
        urllib.error.URLError: If the server is unreachable or doesn't answer
            within timeout, or if its certificate can't be verified: then the
            `reason` of the error is an `ssl.SSLCertVerificationError`.
        TimeoutError: If the server stops sending the file for more than
            timeout seconds.
        Exception: If the server returns an HTML page instead of the file, as
            proxies do, or if the download is incomplete.

    Examples:
        >>> from pathlib import Path
        >>> download_from_url(
        ...     url="https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc_dtm/005813.asc",
        ...     destination=Path("lidar")
        ... ).name
        '005813.asc'
    """
    url = url.strip()
    file_name = url.split('/')[-1]
    download_path = destination.joinpath(file_name)
    temporary_path = destination.joinpath(f"{file_name}.part")
    make_folder(destination_folder=destination)
    if context is None:
        context = ssl_context()

    try:
        with request.urlopen(url, timeout=timeout, context=context) as response:
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
