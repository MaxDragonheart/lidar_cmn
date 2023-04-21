from pathlib import Path
from typing import Union, List
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely import Polygon

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
        target: str = None
) -> GeoDataFrame:
    """Select target area data.

    Args:
        boundaries: GeoDataFrame
        link_source: GeoDataFrame
        target: str

    Returns:
        GeoDataFrame
    """
    # Get target area
    if target is not None:
        focus_area = boundaries[boundaries["COMUNE"] == target]
    else:
        focus_area = boundaries.dissolve()

    # Get bbox of target area
    bbox_coordinates = focus_area.geometry.bounds.iloc[0].tolist()

    # Make bbox
    bbox_shapely = polygon_bbox(coordinates_list=bbox_coordinates)
    bbox = gpd.GeoDataFrame(geometry=gpd.GeoSeries(bbox_shapely), crs=boundaries.crs)

    # Select target area data
    select_data = gpd.overlay(
        df1=bbox,
        df2=link_source,
        how="intersection"
    )

    return select_data


