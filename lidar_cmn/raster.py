"""Mosaic of the LiDAR tiles in a GDAL virtual raster (VRT).

A VRT is an XML file that GDAL, and the software based on it such as QGIS,
reads as a single raster: it refers to the tiles, without copying their data.
The module writes the XML itself, without GDAL: GDAL is needed only to read
the VRT.

The tiles of Città Metropolitana di Napoli aren't on a single grid: most of
them have the corners on whole meters, the others are shifted by a fraction
of a meter, and a few tiles have a cell size different from 1 m. The VRT is on
the most common grid: the other tiles are read with the nearest neighbour,
shifted by less than half a cell, or resampled to its cell size. The tiles
don't declare their coordinate reference system: the VRT declares EPSG:32633.
"""
import math
import os
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from geopandas import GeoDataFrame
from pyproj import CRS

from lidar_cmn.config import lidar_crs, logger, raster_cellsize, raster_nodata
from lidar_cmn.generic import check_path
from lidar_cmn.vector import read_boundaries, read_lidar_index, target_area


@dataclass(frozen=True)
class AsciiGridHeader:
    """Header of an ESRI ASCII grid.

    Attributes:
        path (pathlib.Path): Path of the file.
        ncols (int): Number of columns.
        nrows (int): Number of rows.
        xllcorner (float): X of the lower left corner of the grid.
        yllcorner (float): Y of the lower left corner of the grid.
        cellsize (float): Size of the cells.
        nodata (Optional[float]): NoData value, None if the header doesn't
            declare it.
    """
    path: Path
    ncols: int
    nrows: int
    xllcorner: float
    yllcorner: float
    cellsize: float
    nodata: Optional[float] = None

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Bounding box of the grid (minx, miny, maxx, maxy)."""
        return (
            self.xllcorner,
            self.yllcorner,
            self.xllcorner + self.ncols * self.cellsize,
            self.yllcorner + self.nrows * self.cellsize,
        )


@dataclass
class VrtSummary:
    """Result of `build_vrt`.

    Attributes:
        path (pathlib.Path): Path of the VRT.
        tiles (List[str]): Codes (refname) of the tiles in the VRT, in drawing
            order: where two tiles overlap, the later one is visible.
        shifted (List[str]): Tiles on a grid shifted from the grid of the VRT,
            read with the nearest neighbour.
        resampled (List[str]): Tiles with a cell size different from that of
            the VRT, resampled with the nearest neighbour.
        excluded (Dict[str, str]): Tiles left out of the VRT, with the reason.
    """
    path: Path
    tiles: List[str] = field(default_factory=list)
    shifted: List[str] = field(default_factory=list)
    resampled: List[str] = field(default_factory=list)
    excluded: Dict[str, str] = field(default_factory=dict)


def read_header(path: Union[str, Path]) -> AsciiGridHeader:
    """Read the header of an ESRI ASCII grid.

    Reads only the lines of the header, not the values. The position of the
    grid can be given by the corner (`xllcorner`, `yllcorner`) or by the center
    (`xllcenter`, `yllcenter`) of the lower left cell.

    Args:
        path: Path of the `.asc` file.

    Returns:
        The header of the grid.

    Raises:
        ValueError: If the header lacks `ncols`, `nrows`, `cellsize` or the
            position of the grid.

    Examples:
        >>> header = read_header(path=Path("lidar/dtm/005805.asc"))
        >>> header.ncols, header.cellsize, header.nodata
        (500, 1.0, -9999.0)
    """
    path = Path(path)
    keys = {}
    with open(path, "rb") as data:
        for line in data:
            parts = line.split()
            if not parts:
                continue
            key = parts[0].decode("ascii", errors="replace").lower()
            # The values of the grid start after the header
            if not key[0].isalpha() or len(parts) != 2:
                break
            keys[key] = float(parts[1])

    missing = [key for key in ("ncols", "nrows", "cellsize") if key not in keys]
    if missing:
        raise ValueError(f"The header of {path} lacks {missing}.")
    cellsize = keys["cellsize"]

    corners = []
    for axis in ("x", "y"):
        if f"{axis}llcorner" in keys:
            corners.append(keys[f"{axis}llcorner"])
        elif f"{axis}llcenter" in keys:
            corners.append(keys[f"{axis}llcenter"] - cellsize / 2)
        else:
            raise ValueError(f"The header of {path} lacks {axis}llcorner and {axis}llcenter.")

    return AsciiGridHeader(
        path=path,
        ncols=int(keys["ncols"]),
        nrows=int(keys["nrows"]),
        xllcorner=corners[0],
        yllcorner=corners[1],
        cellsize=cellsize,
        nodata=keys.get("nodata_value"),
    )


def grid_offset(header: AsciiGridHeader, cellsize: float = raster_cellsize) -> Tuple[float, float]:
    """Compute the offset of the grid of a tile from a grid with the origin in 0, 0.

    Args:
        header: Header of the tile.
        cellsize: Cell size of the reference grid.

    Returns:
        The offset (x, y), between 0 and cellsize, rounded to the millimeter:
            two tiles with the same offset and cell size are on the same grid.

    Examples:
        >>> header = AsciiGridHeader(Path("a.asc"), 500, 500, 431434.17, 4487895.46, 1.0)
        >>> grid_offset(header=header)
        (0.17, 0.46)
    """
    return tuple(round(round(value % cellsize, 3) % cellsize, 3) for value in (header.xllcorner, header.yllcorner))


def _format(value: float) -> str:
    """Format a number of the VRT, without the errors of the floating point."""
    return repr(round(value, 6))


def _nearest_line(coordinate: float, origin: float, cellsize: float) -> int:
    """Find the line of a grid nearest to a coordinate.

    Args:
        coordinate: X or Y coordinate.
        origin: Coordinate of a line of the grid.
        cellsize: Cell size of the grid.

    Returns:
        The number of the line, counted from origin; at half a cell, the
            following line.
    """
    return math.floor((coordinate - origin) / cellsize + 0.5)


def write_vrt(
        headers: Sequence[AsciiGridHeader],
        output_path: Union[str, Path],
        cellsize: float = raster_cellsize,
        offset: Tuple[float, float] = (0.0, 0.0),
        crs: str = lidar_crs,
        nodata: float = raster_nodata,
) -> Path:
    """Write a VRT that mosaics ESRI ASCII grids.

    The grid of the VRT has the given cell size and offset, see `grid_offset`,
    and covers all the grids. Each grid is placed by its header, with its
    edges on the nearest lines of the grid of the VRT:

    - a grid with the cell size of the VRT on a shifted grid is moved by less
      than half a cell, so that each of its cells is in the nearest cell of
      the VRT (nearest neighbour), without changing the values;
    - a grid with another cell size is resampled with the nearest neighbour
      to the cells of the VRT that it covers.

    The NoData cells of a grid are transparent; where two grids overlap, the
    later one in headers is visible. The paths of the grids are relative to
    the VRT when possible, so that the VRT can be moved with them.

    Args:
        headers: Headers of the grids, in drawing order.
        output_path: Path of the VRT.
        cellsize: Cell size of the VRT.
        offset: Offset of the grid of the VRT from a grid with the origin in 0, 0.
        crs: Coordinate reference system of the grids, in a format accepted
            by `pyproj.CRS.from_user_input`.
        nodata: NoData value of the VRT.

    Returns:
        Path of the VRT.

    Raises:
        ValueError: If headers is empty.
    """
    if not headers:
        raise ValueError("No grids to write in the VRT.")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Edges of each grid on the nearest lines of the grid of the VRT: left,
    # bottom, right, top, counted from the origin of the grid of the VRT.
    # Fractional edges would make GDAL repeat the last row or column of a
    # shifted grid in the next cell.
    edges = []
    for header in headers:
        left, bottom, right, top = header.bounds
        edges.append((
            _nearest_line(left, offset[0], cellsize), _nearest_line(bottom, offset[1], cellsize),
            _nearest_line(right, offset[0], cellsize), _nearest_line(top, offset[1], cellsize),
        ))
    first_column = min(edge[0] for edge in edges)
    top_row = max(edge[3] for edge in edges)
    columns = max(edge[2] for edge in edges) - first_column
    rows = top_row - min(edge[1] for edge in edges)

    dataset = ET.Element("VRTDataset", rasterXSize=str(columns), rasterYSize=str(rows))
    ET.SubElement(dataset, "SRS", dataAxisToSRSAxisMapping="1,2").text = CRS.from_user_input(crs).to_wkt("WKT1_GDAL")
    ET.SubElement(dataset, "GeoTransform").text = ", ".join(_format(value) for value in (
        first_column * cellsize + offset[0], cellsize, 0, top_row * cellsize + offset[1], 0, -cellsize
    ))
    band = ET.SubElement(dataset, "VRTRasterBand", dataType="Float32", band="1")
    ET.SubElement(band, "NoDataValue").text = _format(nodata)

    for header, (left, bottom, right, top) in zip(headers, edges):
        try:
            source_path, relative = Path(os.path.relpath(header.path, output_path.parent)), "1"
        except ValueError:
            # On Windows, on another drive than the VRT
            source_path, relative = header.path.resolve(), "0"
        source = ET.SubElement(band, "ComplexSource", resampling="nearest")
        ET.SubElement(source, "SourceFilename", relativeToVRT=relative).text = source_path.as_posix()
        ET.SubElement(source, "SourceBand").text = "1"
        # The properties let GDAL open the grids only when it reads them
        ET.SubElement(source, "SourceProperties", RasterXSize=str(header.ncols), RasterYSize=str(header.nrows),
                      DataType="Float32", BlockXSize=str(header.ncols), BlockYSize="1")
        ET.SubElement(source, "SrcRect", xOff="0", yOff="0", xSize=str(header.ncols), ySize=str(header.nrows))
        # A grid smaller than half a cell still covers a cell
        ET.SubElement(source, "DstRect", xOff=str(left - first_column), yOff=str(top_row - top),
                      xSize=str(max(right - left, 1)), ySize=str(max(top - bottom, 1)))
        if header.nodata is not None:
            ET.SubElement(source, "NODATA").text = _format(header.nodata)

    ET.indent(dataset)
    ET.ElementTree(dataset).write(output_path, encoding="utf-8", xml_declaration=False)

    return output_path


def build_vrt(
        folder: Union[str, Path],
        lidar_type: str,
        output_path: Optional[Union[str, Path]] = None,
        index: Optional[GeoDataFrame] = None,
        boundaries: Optional[GeoDataFrame] = None,
) -> VrtSummary:
    """Mosaic the downloaded LiDAR tiles of a folder in a VRT.

    The VRT has cells of 1 m (`lidar_cmn.config.raster_cellsize`) on the most
    common grid of the tiles, the CRS EPSG:32633 and NoData -9999. The tiles:

    - on a shifted grid are read with the nearest neighbour, shifted by less
      than half a cell;
    - with a cell size different from 1 m are resampled with the nearest
      neighbour if they overlap the municipalities of Città Metropolitana di
      Napoli, as `lidar_cmn.vector.target_area`, and are left out otherwise;
    - that overlap are drawn by year of the survey: where they overlap, the
      most recent survey (2012) is visible, and the older one (2009) shows
      through its NoData cells;
    - that aren't in the tile index or whose header can't be read are left out.

    Args:
        folder: Folder of the `.asc` files, as returned by
            `lidar_cmn.download.download_data`.
        lidar_type: LiDAR model of the tiles, `"dtm"` or `"dsm"`.
        output_path: Path of the VRT. If None, it is the folder with the
            `.vrt` extension, e.g. `lidar/dtm.vrt` for `lidar/dtm`.
        index: Tile index, with the `refname` and `data` (year) columns. If
            None, reads the index of lidar_type shipped with the package.
        boundaries: Boundaries of the municipalities, with the `COMUNE`
            column. If None, reads those shipped with the package.

    Returns:
        The path of the VRT and the tiles in it, shifted, resampled and left
            out.

    Raises:
        Exception: If folder doesn't exist.
        ValueError: If no tile can be put in the VRT.

    Examples:
        >>> summary = build_vrt(folder=Path("lidar/dtm"), lidar_type="dtm")
        >>> summary.path.name, len(summary.tiles)
        ('dtm.vrt', 5434)
    """
    folder = check_path(path=folder)
    if index is None:
        index = read_lidar_index(lidar_type=lidar_type)
    if boundaries is None:
        boundaries = read_boundaries()
    output_path = Path(output_path) if output_path is not None else folder.with_suffix(".vrt")
    summary = VrtSummary(path=output_path)

    years = dict(zip(index["refname"], index["data"]))
    inside = set(target_area(boundaries=boundaries, link_source=index)["refname"])

    headers = {}
    for path in sorted(folder.glob("*.asc")):
        refname = path.stem
        if refname not in years:
            summary.excluded[refname] = "not in the tile index"
            continue
        try:
            header = read_header(path=path)
        except (ValueError, UnicodeDecodeError, OSError) as error:
            summary.excluded[refname] = f"header not readable: {error}"
            continue
        if not math.isclose(header.cellsize, raster_cellsize):
            if refname not in inside:
                summary.excluded[refname] = (
                    f"cell size {header.cellsize:g} m, outside the municipalities of Città Metropolitana di Napoli"
                )
                continue
            summary.resampled.append(refname)
        headers[refname] = header

    if not headers:
        raise ValueError(f"No tiles of the index to put in the VRT in {folder}.")

    offsets = Counter(grid_offset(header=h) for h in headers.values() if math.isclose(h.cellsize, raster_cellsize))
    offset = offsets.most_common(1)[0][0] if offsets else (0.0, 0.0)
    summary.shifted = [
        refname for refname, h in headers.items()
        if refname not in summary.resampled and grid_offset(header=h) != offset
    ]
    summary.tiles = sorted(headers, key=lambda refname: (str(years[refname]), refname))

    write_vrt(headers=[headers[refname] for refname in summary.tiles], output_path=output_path, offset=offset)
    logger.info(
        f"VRT of {len(summary.tiles)} tiles: {output_path}. {len(summary.shifted)} tiles on a shifted grid, "
        f"{len(summary.resampled)} resampled, {len(summary.excluded)} left out."
    )
    for refname, reason in summary.excluded.items():
        logger.warning(f"Tile {refname} left out of the VRT: {reason}.")

    return summary


def write_prj_files(folder: Union[str, Path], crs: str = lidar_crs, overwrite: bool = False) -> List[Path]:
    """Write the `.prj` file of each `.asc` file of a folder.

    The tiles don't declare their coordinate reference system: with the
    `.prj` file, GDAL, QGIS and ArcGIS read it also when they open a single
    tile. The CRS is written in the ESRI WKT format.

    Args:
        folder: Folder of the `.asc` files.
        crs: Coordinate reference system, in a format accepted by
            `pyproj.CRS.from_user_input`.
        overwrite: Write also the `.prj` files that already exist.

    Returns:
        Paths of the written `.prj` files.

    Raises:
        Exception: If folder doesn't exist.

    Examples:
        >>> len(write_prj_files(folder=Path("lidar/dtm")))
        5449
    """
    folder = check_path(path=folder)
    wkt = CRS.from_user_input(crs).to_wkt("WKT1_ESRI")
    written = []
    for path in sorted(folder.glob("*.asc")):
        prj_path = path.with_suffix(".prj")
        if overwrite or not prj_path.exists():
            prj_path.write_text(wkt, encoding="utf-8")
            written.append(prj_path)

    return written
