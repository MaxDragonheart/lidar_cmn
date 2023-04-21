from pathlib import Path

from geopandas import GeoDataFrame
from shapely import Polygon

from lidar_cmn.vector import read_vector, target_area, polygon_bbox

geodata_path = Path.cwd().parent.joinpath("geodata")
limiti_amministrativi = geodata_path.joinpath("limiti_amministrativi.gpkg")
quadro_unione = geodata_path.joinpath("quadro_unione_lidar.gpkg")


def test_read_vector():
    print("test_read_vector")
    data = read_vector(data_path=limiti_amministrativi)

    assert isinstance(data, GeoDataFrame)


def test_polygon_bbox():
    print("test_polygon_bbox")
    coords = read_vector(data_path=limiti_amministrativi).geometry.bounds.iloc[0].tolist()

    data = polygon_bbox(coordinates_list=coords)

    assert isinstance(data, Polygon)


def test_target_area():
    print("test_target_area")
    data = target_area(
        boundaries=read_vector(data_path=limiti_amministrativi),
        link_source=read_vector(data_path=quadro_unione, layer_name="dsm"),
        target="Napoli"
    )

    assert isinstance(data, GeoDataFrame)
