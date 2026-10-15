import time
from pathlib import Path
from typing import List, Union
from urllib.error import HTTPError

from geopandas import GeoDataFrame
from tqdm import tqdm

from lidar_cmn.config import logger
from lidar_cmn.generic import download_from_url


class DownloadError(Exception):
    """Some files were not downloaded.

    Attributes:
        urls: List[str], urls of the files not downloaded
    """

    def __init__(self, message: str, urls: List[str]):
        super().__init__(message)
        self.urls = urls


def is_valid_file(path: Path) -> bool:
    """Check that a downloaded file exists, isn't empty and, if it is an `.asc`
    file, starts with the header of an ESRI ASCII grid.

    Args:
        path: Path

    Returns:
        bool
    """
    if not path.is_file() or path.stat().st_size == 0:
        return False

    if path.suffix.lower() == ".asc":
        with open(path, "rb") as data:
            return data.read(64).lstrip().lower().startswith(b"ncols")

    return True


def _is_permanent(error: Exception) -> bool:
    """Client errors, e.g. 404 Not Found, don't change by retrying."""
    return isinstance(error, HTTPError) and error.code < 500 and error.code not in (408, 429)


def download_data(
        selection: GeoDataFrame,
        output_folder: Union[str, Path],
        output_folder_name: str,
        overwrite: bool = False,
        retries: int = 3,
        timeout: float = 30,
        max_consecutive_failures: int = 5
) -> Path:
    """Download of Lidar Data.

    The files already in the destination folder are skipped, unless overwrite is
    True: if the download stops, run the function again to resume it.
    Each file is downloaded up to retries times; a file that still fails doesn't
    stop the download of the others and is reported at the end. The download
    stops after max_consecutive_failures failed files in a row, e.g. when the
    server is unreachable.

    Args:
        selection: GeoDataFrame, with the url column
        output_folder: Union[str, Path]
        output_folder_name: str
        overwrite: bool = False, download again the files already downloaded
        retries: int = 3, attempts for each file
        timeout: float = 30, seconds to wait for the server
        max_consecutive_failures: int = 5

    Returns:
        Path

    Exception:
        - DownloadError: some files were not downloaded, their urls are in DownloadError.urls
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
