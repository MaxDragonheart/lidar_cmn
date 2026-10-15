import geopandas as gpd
import pytest
from geopandas import GeoDataFrame
from shapely import Polygon

from lidar_cmn.config import limiti_amministrativi_path
from lidar_cmn.vector import read_boundaries, read_lidar_index, read_vector, target_area, polygon_bbox

urls = {
    "dtm": "https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc_dtm/",
    "dsm": "https://sit.cittametropolitana.na.it/documenti/territorio/lidar_asc/",
}


def test_read_vector():
    print("test_read_vector")
    data = read_vector(data_path=limiti_amministrativi_path, layer_name="prov_na_2023")

    assert isinstance(data, GeoDataFrame)


def test_read_boundaries():
    print("test_read_boundaries")
    data = read_boundaries()

    assert len(data) == 92
    assert "Napoli" in data["COMUNE"].values


@pytest.mark.parametrize("lidar_type", ["dtm", "dsm"])
def test_read_lidar_index(lidar_type: str):
    print("test_read_lidar_index")
    data = read_lidar_index(lidar_type=lidar_type)

    assert len(data) == 5451
    assert data["url"].is_unique
    assert (data["url"] == urls[lidar_type] + data["refname"] + ".asc").all()


def test_read_lidar_index_errors():
    print("test_read_lidar_index_errors")
    with pytest.raises(ValueError, match="lidar_type"):
        read_lidar_index(lidar_type="las")
    with pytest.raises(ValueError, match="source"):
        read_lidar_index(lidar_type="dtm", source="ftp")


@pytest.mark.network
@pytest.mark.parametrize("lidar_type", ["dtm", "dsm"])
def test_read_lidar_index_wfs(lidar_type: str):
    print("test_read_lidar_index_wfs")
    official = read_lidar_index(lidar_type=lidar_type, source="wfs").set_index("refname")
    local = read_lidar_index(lidar_type=lidar_type).set_index("refname")

    # The index shipped with the package is up to date with the official one
    assert sorted(official.index) == sorted(local.index)
    assert (official.loc[local.index, "url"] == local["url"]).all()


def test_polygon_bbox():
    print("test_polygon_bbox")
    coords = read_boundaries().geometry.bounds.iloc[0].tolist()

    data = polygon_bbox(coordinates_list=coords)

    assert isinstance(data, Polygon)


def test_target_area():
    print("test_target_area")
    boundaries = read_boundaries()
    index = read_lidar_index(lidar_type="dsm")
    napoli = boundaries[boundaries["COMUNE"] == "Napoli"].geometry.union_all()

    data = target_area(boundaries=boundaries, link_source=index, target="Napoli")
    data_bbox = target_area(boundaries=boundaries, link_source=index, target="Napoli", use_bbox=True)

    assert isinstance(data, GeoDataFrame)
    assert data.intersection(napoli).area.gt(0).all()
    assert set(data["refname"]) < set(data_bbox["refname"])


def test_target_area_bbox_as_previous_versions():
    print("test_target_area_bbox_as_previous_versions")
    boundaries = read_boundaries()
    index = read_lidar_index(lidar_type="dtm")
    procida = boundaries[boundaries["COMUNE"] == "Procida"]
    bbox = GeoDataFrame(geometry=[polygon_bbox(coordinates_list=procida.geometry.bounds.iloc[0].tolist())],
                        crs=boundaries.crs)

    previous = gpd.overlay(df1=bbox, df2=index, how="intersection")
    data = target_area(boundaries=boundaries, link_source=index, target="Procida", use_bbox=True)

    assert sorted(data["refname"]) == sorted(previous["refname"])


def test_target_area_all():
    print("test_target_area_all")
    boundaries = read_boundaries()
    index = read_lidar_index(lidar_type="dtm")
    province = boundaries.geometry.union_all()

    data = target_area(boundaries=boundaries, link_source=index)

    assert 0 < len(data) < len(index)
    assert data.intersection(province).area.gt(0).all()


def test_target_area_unknown():
    print("test_target_area_unknown")
    with pytest.raises(ValueError, match="not found"):
        target_area(boundaries=read_boundaries(), link_source=read_lidar_index(lidar_type="dtm"), target="Roma")
