import json
from pathlib import Path
from typing import Union, List
from urllib import request
from urllib.parse import urlencode

import geopandas as gpd
from geopandas import GeoDataFrame
from shapely import Polygon

from lidar_cmn.config import (
    lidar_crs, lidar_types, limiti_amministrativi_layer, limiti_amministrativi_path, quadro_unione_path,
    wfs_layers, wfs_url
)
from lidar_cmn.generic import check_path


def read_vector(
        data_path: Union[str, Path],
        layer_name: str = None,
        bbox: str = None,
        mask: str = None,
        rows: str = None,
) -> GeoDataFrame:
    """Read vector data and return a GeoDataFrame.

    Args:
        data_path: Union[str, Path]
        layer_name: str = None
        bbox: str = None
        mask: str = None
        rows: str = None

    Returns:
        GeoDataFrame
    """
    # Read path
    path = check_path(path=data_path)

    # Read vector
    geodata = gpd.read_file(
        filename=path,
        engine="pyogrio",
        fid_as_index=True,
        layer=layer_name,
        bbox=bbox,
        mask=mask,
        rows=rows
    )

    return geodata


def read_boundaries() -> GeoDataFrame:
    """Read the boundaries of the municipalities of Città Metropolitana di Napoli
    shipped with the package (ISTAT 2023).

    Returns:
        GeoDataFrame
    """
    return read_vector(data_path=limiti_amministrativi_path, layer_name=limiti_amministrativi_layer)


def read_lidar_index(lidar_type: str, source: str = "local", timeout: float = 120) -> GeoDataFrame:
    """Read the index of the LiDAR tiles (quadro d'unione), with the download url
    of each tile.

    Args:
        lidar_type: str, "dtm" or "dsm"
        source: str = "local", "local" reads the index shipped with the package,
            "wfs" reads the official index from the WFS service of Città Metropolitana di Napoli
        timeout: float = 120, seconds to wait for the WFS service

    Returns:
        GeoDataFrame

    Exception:
        - lidar_type must be one of {lidar_types}.
        - source must be "local" or "wfs".
    """
    if lidar_type not in lidar_types:
        raise ValueError(f"lidar_type must be one of {lidar_types}. Your lidar_type is {lidar_type}.")

    if source == "local":
        index = read_vector(data_path=quadro_unione_path, layer_name=lidar_type)
    elif source == "wfs":
        parameters = urlencode({
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": wfs_layers[lidar_type],
            "srsName": lidar_crs,
            "outputFormat": "application/json",
        })
        with request.urlopen(f"{wfs_url}?{parameters}", timeout=timeout) as response:
            features = json.load(response)["features"]
        index = GeoDataFrame.from_features(features, crs=lidar_crs)
    else:
        raise ValueError(f'source must be "local" or "wfs". Your source is {source}.')

    # The official index has urls with trailing spaces
    index["url"] = index["url"].str.strip()

    return index


def polygon_bbox(coordinates_list: List) -> Polygon:
    """Make polygon bbox from list of coordinates.

    Args:
        coordinates_list: list

    Returns:
        Polygon
    """
    if len(coordinates_list) == 4:
        return Polygon(
            [
                (coordinates_list[0], coordinates_list[3]),
                (coordinates_list[2], coordinates_list[3]),
                (coordinates_list[2], coordinates_list[1]),
                (coordinates_list[0], coordinates_list[1]),
                (coordinates_list[0], coordinates_list[3]),
            ]
        )
    else:
        raise Exception(f'The list must contain 4 objects. Your list has {len(coordinates_list)} objects.')


def target_area(
        boundaries: GeoDataFrame,
        link_source: GeoDataFrame,
        target: str = None,
        use_bbox: bool = False
) -> GeoDataFrame:
    """Select target area data.

    Selects the tiles that overlap the boundary of the target area: the
    municipality target or, if target is None, all the boundaries. With
    use_bbox=True selects the tiles that overlap the bounding box of the target
    area, as the versions before 2.0.0. Tiles that only touch the area along an
    edge are excluded.

    To download all the tiles, pass the whole index to download_data instead.

    Args:
        boundaries: GeoDataFrame, with the COMUNE column
        link_source: GeoDataFrame
        target: str = None, name of the municipality as in the COMUNE column
        use_bbox: bool = False

    Returns:
        GeoDataFrame

    Exception:
        - {target} not found in the COMUNE column of boundaries.
    """
    # Get target area
    if target is not None:
        focus_area = boundaries[boundaries["COMUNE"] == target]
        if focus_area.empty:
            raise ValueError(f"{target} not found in the COMUNE column of boundaries.")
    else:
        focus_area = boundaries

    if link_source.crs is not None and focus_area.crs != link_source.crs:
        focus_area = focus_area.to_crs(link_source.crs)
    area = focus_area.geometry.union_all()

    if use_bbox:
        area = polygon_bbox(coordinates_list=list(area.bounds))

    # Select target area data
    selection = link_source.intersects(area) & ~link_source.touches(area)

    return link_source[selection]
