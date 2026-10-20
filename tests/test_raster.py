"""Tests of `lidar_cmn.raster`."""
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest
from geopandas import GeoDataFrame
from pyproj import CRS
from shapely import box

from lidar_cmn.raster import AsciiGridHeader, build_vrt, grid_offset, read_header, write_prj_files, write_vrt


def write_grid(path: Path, rows, xll: float, yll: float, cellsize: float = 1, nodata=-9999, center: bool = False):
    """Write an ESRI ASCII grid.

    Args:
        path: Path of the file.
        rows: Values of the grid, from the top row.
        xll: X of the lower left corner, or of the center of the lower left
            cell if center is True.
        yll: Y of the lower left corner or center.
        cellsize: Size of the cells.
        nodata: NoData value; if None, the header doesn't declare it.
        center: Write xllcenter and yllcenter instead of xllcorner and yllcorner.
    """
    position = "center" if center else "corner"
    header = [f"ncols {len(rows[0])}", f"nrows {len(rows)}", f"xll{position} {xll}", f"yll{position} {yll}",
              f"cellsize {cellsize}"]
    if nodata is not None:
        header.append(f"NODATA_value {nodata}")
    path.write_text("\n".join(header + [" ".join(str(value) for value in row) for row in rows]) + "\n")


@pytest.fixture
def tiles(tmp_path: Path) -> SimpleNamespace:
    """Make a folder of tiles with the cases of the LiDAR tiles.

    - 000001 (2009): 4 × 4 cells of 1 m in (0, 0)–(4, 4), integer values 1, a
      NoData cell in the top left corner;
    - 000002 (2012): 4 × 4 cells of 1 m in (2, 2)–(6, 6), values 2.5, a NoData
      cell in the bottom left corner, which overlaps 000001;
    - 000003 (2009): 2 × 2 cells of 1 m on a grid shifted by (0.17, 0.46), in
      (4.17, 0.46)–(6.17, 2.46), values 31–34;
    - 000004 (2009): 4 × 4 cells of 0.5 m in (0, 6)–(2, 8), inside the
      boundaries, values 4;
    - 000005 (2009): 2 × 2 cells of 0.5 m in (10, 10)–(11, 11), outside the
      boundaries;
    - 999999: a grid that isn't in the index.

    Args:
        tmp_path: pytest fixture with a temporary folder.

    Returns:
        SimpleNamespace: `folder` of the tiles, tile `index` and `boundaries`
            of a municipality in (0, 0)–(8, 8).
    """
    folder = tmp_path.joinpath("dtm")
    folder.mkdir()
    write_grid(folder.joinpath("000001.asc"), [[-9999, 1, 1, 1]] + [[1, 1, 1, 1]] * 3, 0, 0)
    write_grid(folder.joinpath("000002.asc"), [[2.5] * 4] * 3 + [[-9999, 2.5, 2.5, 2.5]], 2, 2)
    write_grid(folder.joinpath("000003.asc"), [[31.0, 32.0], [33.0, 34.0]], 4.17, 0.46)
    write_grid(folder.joinpath("000004.asc"), [[4.0] * 4] * 4, 0, 6, cellsize=0.5)
    write_grid(folder.joinpath("000005.asc"), [[5.0] * 2] * 2, 10, 10, cellsize=0.5)
    write_grid(folder.joinpath("999999.asc"), [[9.0]], 0, 0)

    index = GeoDataFrame(
        {
            "refname": ["000001", "000002", "000003", "000004", "000005"],
            "data": ["2009", "2012", "2009", "2009", "2009"],
        },
        geometry=[box(0, 0, 4, 4), box(2, 2, 6, 6), box(4, 0, 7, 3), box(0, 6, 2, 8), box(10, 10, 11, 11)],
        crs="EPSG:32633",
    )
    boundaries = GeoDataFrame({"COMUNE": ["Test"]}, geometry=[box(0, 0, 8, 8)], crs="EPSG:32633")

    return SimpleNamespace(folder=folder, index=index, boundaries=boundaries)


def test_read_header(tmp_path: Path):
    print("test_read_header")
    path = tmp_path.joinpath("grid.asc")
    write_grid(path, [[1.5, 2.5, 3.5]] * 2, 100.5, 200.5, cellsize=1, nodata=None, center=True)

    header = read_header(path=path)

    assert header == AsciiGridHeader(path=path, ncols=3, nrows=2, xllcorner=100, yllcorner=200, cellsize=1)
    assert header.bounds == (100, 200, 103, 202)


def test_read_header_incomplete(tmp_path: Path):
    print("test_read_header_incomplete")
    path = tmp_path.joinpath("grid.asc")
    path.write_text("ncols 1\nnrows 1\nxllcorner 0\ncellsize 1\n5\n")

    with pytest.raises(ValueError, match="yllcorner"):
        read_header(path=path)


def test_grid_offset():
    print("test_grid_offset")
    header = AsciiGridHeader(Path("a.asc"), 500, 500, 431434.17, 4487895.46, 1.0)

    assert grid_offset(header=header) == (0.17, 0.46)
    assert grid_offset(header=AsciiGridHeader(Path("b.asc"), 500, 500, 431433.9999999, 4487895.0, 1.0)) == (0, 0)


def test_write_vrt_empty(tmp_path: Path):
    print("test_write_vrt_empty")
    with pytest.raises(ValueError, match="No grids"):
        write_vrt(headers=[], output_path=tmp_path.joinpath("empty.vrt"))


def test_build_vrt(tiles):
    print("test_build_vrt")
    summary = build_vrt(folder=tiles.folder, lidar_type="dtm", index=tiles.index, boundaries=tiles.boundaries)

    assert summary.path == tiles.folder.with_suffix(".vrt")
    # 2009 first, 2012 last: where they overlap, the 2012 survey is visible
    assert summary.tiles == ["000001", "000003", "000004", "000002"]
    assert summary.shifted == ["000003"]
    assert summary.resampled == ["000004"]
    assert sorted(summary.excluded) == ["000005", "999999"]

    vrt = ET.parse(summary.path).getroot()
    # 000003 ends in x 6.17: moved to the nearest cells, it doesn't widen the VRT
    assert (vrt.get("rasterXSize"), vrt.get("rasterYSize")) == ("6", "8")
    assert [float(value) for value in vrt.find("GeoTransform").text.split(",")] == [0, 1, 0, 8, 0, -1]
    assert CRS.from_wkt(vrt.find("SRS").text).to_epsg() == 32633
    sources = vrt.findall("VRTRasterBand/ComplexSource")
    assert [source.find("SourceFilename").text for source in sources] == [
        "dtm/000001.asc", "dtm/000003.asc", "dtm/000004.asc", "dtm/000002.asc"
    ]
    assert {source.find("SourceFilename").get("relativeToVRT") for source in sources} == {"1"}
    # 000003 in (4.17, 0.46)–(6.17, 2.46) moved to the cells (4, 0)–(6, 2)
    assert sources[1].find("DstRect").attrib == {"xOff": "4", "yOff": "6", "xSize": "2", "ySize": "2"}
    # 000004, 4 × 4 cells of 0.5 m, resampled to 2 × 2 cells of 1 m
    assert sources[2].find("DstRect").attrib == {"xOff": "0", "yOff": "0", "xSize": "2", "ySize": "2"}


def test_build_vrt_values(tiles):
    print("test_build_vrt_values")
    rasterio = pytest.importorskip("rasterio")
    summary = build_vrt(folder=tiles.folder, lidar_type="dtm", index=tiles.index, boundaries=tiles.boundaries)

    with rasterio.open(summary.path) as vrt:
        assert vrt.crs.to_epsg() == 32633
        assert vrt.nodata == -9999
        assert vrt.res == (1, 1)
        values = vrt.read(1)

    # Rows from the top (y 7–8) to the bottom (y 0–1), columns from x 0–1 to x 5–6
    assert values.shape == (8, 6)
    assert values[0:2, 0:2].tolist() == [[4, 4], [4, 4]]   # 000004, resampled from 0.5 m
    assert values[4, 0] == -9999                           # NoData of 000001, no other tile
    assert values[4, 1] == 1                               # 000001, integer values
    assert values[4, 3] == 2.5                             # 000001 and 000002 overlap: 2012 visible
    assert values[5, 2] == 1                               # NoData of 000002: 000001 shows through
    assert values[6:8, 4:6].tolist() == [[31, 32], [33, 34]]  # 000003, shifted by (-0.17, -0.46)
    assert values[0, 5] == -9999                           # no tile


def test_write_prj_files(tiles):
    print("test_write_prj_files")
    written = write_prj_files(folder=tiles.folder)

    assert len(written) == 6
    assert all(CRS.from_wkt(path.read_text()).to_epsg() == 32633 for path in written)
    assert write_prj_files(folder=tiles.folder) == []
    assert len(write_prj_files(folder=tiles.folder, overwrite=True)) == 6
