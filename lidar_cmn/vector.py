from pathlib import Path
from typing import Union
import geopandas as gpd
from geopandas import GeoDataFrame

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
    geodata = gpd.read_file(
        filename=data_path,
        engine="pyogrio",
        fid_as_index=True,
        layer=layer_name,
        bbox=bbox,
        mask=mask,
        rows=rows
    )

    return geodata
