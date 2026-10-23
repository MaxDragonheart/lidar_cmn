"""Download of the LiDAR data of Città Metropolitana di Napoli.

The DTM and the DSM of the LiDAR surveys of 2009 and 2012 are published by
Città Metropolitana di Napoli as 5451 tiles each, ESRI ASCII grids of
500 × 500 cells with a resolution of 1 m. The package selects the tiles of an
area, downloads them and mosaics them in a virtual raster (VRT).

Modules:
    vector: Read the tile index and the boundaries, select the tiles of an area.
    download: Download a selection of tiles.
    raster: Mosaic the downloaded tiles in a VRT.
    generic: Paths, folders, SSL context and download of a single file.
    config: Paths of the data and of the certificates shipped with the
        package and other settings.

Attributes:
    __version__ (str): Version of the installed package, `"unknown"` if the
        package isn't installed.

Examples:
    >>> from pathlib import Path
    >>> from lidar_cmn.download import download_data
    >>> from lidar_cmn.vector import read_boundaries, read_lidar_index, target_area
    >>> selection = target_area(
    ...     boundaries=read_boundaries(),
    ...     link_source=read_lidar_index(lidar_type="dtm"),
    ...     target="Procida"
    ... )
    >>> folder = download_data(selection=selection, output_folder=Path("lidar"), output_folder_name="dtm")
    >>> from lidar_cmn.raster import build_vrt
    >>> build_vrt(folder=folder, lidar_type="dtm").path.name
    'dtm.vrt'
"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lidar-cmn")
except PackageNotFoundError:
    # Package not installed, e.g. run from the source folder
    __version__ = "unknown"
