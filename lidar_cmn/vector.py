"""Read the tile index and the boundaries, select the tiles of an area.

The tile index (quadro d'unione) has a polygon for each LiDAR tile, with the
url of its file. The index and the boundaries are in EPSG:32633
(WGS 84 / UTM zone 33N).
"""
import json
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union
from urllib import request
from urllib.parse import urlencode

import geopandas as gpd
from geopandas import GeoDataFrame, GeoSeries
from shapely import Polygon
from shapely.geometry.base import BaseGeometry

from lidar_cmn.config import (
    lidar_crs, lidar_types, limiti_amministrativi_layer, limiti_amministrativi_path, quadro_unione_path,
    wfs_layers, wfs_url
)
from lidar_cmn.generic import check_path


def read_vector(
        data_path: Union[str, Path],
        layer_name: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        mask: Optional[Union[GeoDataFrame, GeoSeries, BaseGeometry]] = None,
        rows: Optional[Union[int, slice]] = None,
) -> GeoDataFrame:
    """Read vector data and return a GeoDataFrame.

    Reads the file with `geopandas.read_file` and the pyogrio engine.

    Args:
        data_path: Path of the vector file, e.g. a GeoPackage.
        layer_name: Layer to read. If None, reads the first layer of the file.
        bbox: Read only the features that intersect the bounding box
            (minx, miny, maxx, maxy), in the coordinate reference system of the
            layer.
        mask: Read only the features that intersect this geometry.
        rows: Read only these rows: a number of rows from the start or a slice.

    Returns:
        The features, with the feature id (fid) as index.

    Raises:
        Exception: If data_path doesn't exist.

    Examples:
        >>> from lidar_cmn.config import quadro_unione_path
        >>> len(read_vector(data_path=quadro_unione_path, layer_name="dtm"))
        5451
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
    """Read the boundaries of the municipalities of Città Metropolitana di Napoli.

    The boundaries are shipped with the package: ISTAT 2023, layer
    `prov_na_2023` of `limiti_amministrativi.gpkg`.

    Returns:
        A polygon for each of the 92 municipalities, with its name in the
            `COMUNE` column.

    Examples:
        >>> boundaries = read_boundaries()
        >>> len(boundaries)
        92
        >>> "Procida" in boundaries["COMUNE"].values
        True
    """
    return read_vector(data_path=limiti_amministrativi_path, layer_name=limiti_amministrativi_layer)


def read_lidar_index(lidar_type: str, source: str = "local", timeout: float = 120) -> GeoDataFrame:
    """Read the index of the LiDAR tiles (quadro d'unione).

    The index has a polygon of 500 × 500 m for each tile, with the columns:

    - `refname`: code of the tile, also the name of its file;
    - `foglio_50k`: sheet of the 1:50000 map;
    - `appartenen`: `"Prov Na"` for the tiles of Città Metropolitana di Napoli,
      `"Extra Prov Na"` for those outside;
    - `data`: year of the survey, 2009 or 2012;
    - `url`: url of the file of the tile.

    Args:
        lidar_type: LiDAR model, `"dtm"` or `"dsm"`.
        source: `"local"` reads the index shipped with the package; `"wfs"`
            reads the official index from the WFS service of Città
            Metropolitana di Napoli, useful if the urls of the files change.
        timeout: Seconds to wait for the WFS service.

    Returns:
        The 5451 tiles of the model.

    Raises:
        ValueError: If lidar_type isn't `"dtm"` or `"dsm"`, or source isn't
            `"local"` or `"wfs"`.
        urllib.error.URLError: If source is `"wfs"` and the WFS service is
            unreachable or returns an error.

    Examples:
        >>> index = read_lidar_index(lidar_type="dsm")
        >>> index.loc[index["refname"] == "005816", "url"].iloc[0]
        'https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc/005816.asc'
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


def polygon_bbox(coordinates_list: Sequence[float]) -> Polygon:
    """Make the polygon of a bounding box.

    Args:
        coordinates_list: Coordinates of the bounding box (minx, miny, maxx,
            maxy), as the `bounds` of a shapely geometry.

    Returns:
        The rectangle of the bounding box.

    Raises:
        Exception: If coordinates_list doesn't contain 4 values.

    Examples:
        >>> polygon_bbox(coordinates_list=[0, 0, 2, 1]).bounds
        (0.0, 0.0, 2.0, 1.0)
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
        target: Optional[str] = None,
        use_bbox: bool = False
) -> GeoDataFrame:
    """Select the tiles of an area.

    Selects the tiles that overlap the boundary of the area; the tiles that
    only touch it along an edge are excluded. With use_bbox=True selects the
    tiles that overlap the bounding box of the area, as the versions before
    2.0.0.

    To download all the tiles, pass the whole index to
    `lidar_cmn.download.download_data` instead.

    Args:
        boundaries: Boundaries of the municipalities, with their names in the
            `COMUNE` column, as returned by `read_boundaries`.
        link_source: Tile index, as returned by `read_lidar_index`.
        target: Name of the municipality, as in the `COMUNE` column. If None,
            the area is the union of all the boundaries.
        use_bbox: Select the tiles on the bounding box of the area instead of
            its boundary.

    Returns:
        The selected tiles of link_source, with their index and their whole
            geometries.

    Raises:
        ValueError: If target isn't in the `COMUNE` column of boundaries.

    Examples:
        >>> boundaries = read_boundaries()
        >>> index = read_lidar_index(lidar_type="dtm")
        >>> len(target_area(boundaries=boundaries, link_source=index, target="Napoli"))
        566
        >>> len(target_area(boundaries=boundaries, link_source=index, target="Napoli", use_bbox=True))
        870
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
