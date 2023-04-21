import logging
from pathlib import Path

from fsspec import get_fs_token_paths
from geopandas import GeoDataFrame
from tqdm import tqdm

from lidar_cmn.config import logger, console_handler
from lidar_cmn.generic import download_from_url

logger.addHandler(console_handler)


def download_data(
        selection: GeoDataFrame,
        output_folder: Path,
        output_folder_name: str
) -> Path:
    """Download of Lidar Data.

    Args:
        selection: GeoDataFrame
        output_folder: Path
        output_folder_name: str

    Returns:
        Path
    """
    # Make destinantion folder
    output_data_folder = output_folder.joinpath(output_folder_name)
    fs, fs_token, paths = get_fs_token_paths(output_data_folder)
    Path(output_data_folder).mkdir(parents=True, exist_ok=True)

    logging.info(f"Download of {selection.shape[0]} objects.")
    for _index, _row in tqdm(selection.iterrows()):
        download_from_url(
            url=_row["url"],
            destination=output_data_folder
        )

    logging.info(f"Ends download. Data are in {output_data_folder}.")

    return output_data_folder
