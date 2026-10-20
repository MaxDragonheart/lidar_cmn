"""Download of a selection of LiDAR tiles.

The selection is a GeoDataFrame with the `url` column, such as the tile index
returned by `lidar_cmn.vector.read_lidar_index` or a part of it selected with
`lidar_cmn.vector.target_area`.
"""
import ssl
import time
from pathlib import Path
from typing import List, Union
from urllib.error import HTTPError, URLError

from geopandas import GeoDataFrame
from tqdm import tqdm

from lidar_cmn.config import logger
from lidar_cmn.generic import download_from_url


class DownloadError(Exception):
    """Some files of a selection were not downloaded.

    Raised by `download_data` after downloading the other files of the
    selection, or when it stops after too many failures in a row.

    Args:
        message: Description of the error.
        urls: Urls of the files not downloaded.

    Attributes:
        urls (List[str]): Urls of the files not downloaded.

    Examples:
        >>> try:
        ...     download_data(selection=selection, output_folder=Path("lidar"), output_folder_name="dtm")
        ... except DownloadError as error:
        ...     print(error.urls)
    """

    def __init__(self, message: str, urls: List[str]):
        super().__init__(message)
        self.urls = urls


def is_valid_file(path: Path) -> bool:
    """Check that a downloaded file is valid.

    A file is valid if it exists and isn't empty; an `.asc` file must also
    start with the header of an ESRI ASCII grid (`ncols`).

    Args:
        path: Path of the file.

    Returns:
        True if the file is valid, False otherwise.
    """
    if not path.is_file() or path.stat().st_size == 0:
        return False

    if path.suffix.lower() == ".asc":
        with open(path, "rb") as data:
            return data.read(64).lstrip().lower().startswith(b"ncols")

    return True


def _is_permanent(error: Exception) -> bool:
    """Check whether a download error doesn't change by retrying.

    Args:
        error: Error raised by the download.

    Returns:
        True for the HTTP client errors, e.g. 404 Not Found, except 408 Request
        Timeout and 429 Too Many Requests, and for the certificates of the
        server that can't be verified; False otherwise.
    """
    if isinstance(error, HTTPError):
        return error.code < 500 and error.code not in (408, 429)

    return isinstance(error, URLError) and isinstance(error.reason, ssl.SSLCertVerificationError)


def download_data(
        selection: GeoDataFrame,
        output_folder: Union[str, Path],
        output_folder_name: str,
        overwrite: bool = False,
        retries: int = 3,
        timeout: float = 30,
        max_consecutive_failures: int = 5
) -> Path:
    """Download the LiDAR tiles of a selection.

    The files are saved in the folder `output_folder/output_folder_name`; a
    progress bar shows the advancement of the download.

    The valid files already in the folder are skipped, unless overwrite is
    True: if the download stops, run the function again to resume it. Each
    file is downloaded up to retries times, waiting 2, 4, 8... seconds between
    the attempts; the HTTP client errors, e.g. 404 Not Found, and the
    certificates of the server that can't be verified aren't retried.
    A file that still fails doesn't stop the download of the others and is
    reported at the end.

    Args:
        selection: Tiles to download, with the url of each file in the `url`
            column.
        output_folder: Folder where the folder of the data is created.
        output_folder_name: Name of the folder of the data, e.g. `"dtm"`.
        overwrite: Download again the files already in the folder.
        retries: Attempts for each file.
        timeout: Seconds to wait for the server, see
            `lidar_cmn.generic.download_from_url`.
        max_consecutive_failures: Failed files in a row after which the
            download stops, e.g. because the server is unreachable.

    Returns:
        Folder of the downloaded data.

    Raises:
        DownloadError: If some files were not downloaded, at the end of the
            download or after max_consecutive_failures failed files in a row.
            Their urls are in `DownloadError.urls`.

    Examples:
        Download all the tiles of the DTM, resuming a previous download:

        >>> from pathlib import Path
        >>> from lidar_cmn.vector import read_lidar_index
        >>> folder = download_data(
        ...     selection=read_lidar_index(lidar_type="dtm"),
        ...     output_folder=Path("lidar"),
        ...     output_folder_name="dtm"
        ... )
    """
    # Make destination folder
    output_data_folder = Path(output_folder).joinpath(output_folder_name)
    output_data_folder.mkdir(parents=True, exist_ok=True)

    urls = selection["url"].str.strip().tolist()
    logger.info(f"Download of {len(urls)} objects.")

    skipped = 0
    failed = []
    consecutive_failures = 0
    for url in tqdm(urls):
        download_path = output_data_folder.joinpath(url.split('/')[-1])
        if not overwrite and is_valid_file(path=download_path):
            skipped += 1
            continue

        downloaded = False
        for attempt in range(1, retries + 1):
            try:
                download_from_url(url=url, destination=output_data_folder, timeout=timeout)
                if not is_valid_file(path=download_path):
                    download_path.unlink(missing_ok=True)
                    raise Exception(f"{url} is not a valid file.")
                downloaded = True
                break
            except Exception as error:
                logger.warning(f"Attempt {attempt} of {retries} failed for {url}: {error}")
                if _is_permanent(error):
                    break
                if attempt < retries:
                    time.sleep(2 ** attempt)

        if downloaded:
            consecutive_failures = 0
        else:
            failed.append(url)
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                raise DownloadError(
                    f"Download stopped after {consecutive_failures} consecutive failures: check the connection "
                    f"and the urls, then run download_data again to resume it.",
                    urls=failed
                )

    if skipped > 0:
        logger.info(f"{skipped} files already downloaded, skipped.")

    if failed:
        raise DownloadError(
            f"{len(failed)} of {len(urls)} files not downloaded: run download_data again to retry them.",
            urls=failed
        )

    logger.info(f"Ends download. Data are in {output_data_folder}.")

    return output_data_folder
