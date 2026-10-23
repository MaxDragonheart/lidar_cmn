"""Settings of the package: logging, data and certificates shipped with the
package, WFS service.

Attributes:
    logger (logging.Logger): Logger of the package, named `lidar_cmn`. It has
        only a `logging.NullHandler`: its messages are shown if the application
        configures logging, e.g. with `logging.basicConfig(level=logging.INFO)`.
    log_format (str): Format of the log messages used by the package before
        version 2.0.0, to pass to `logging.basicConfig(format=log_format)`.
    raster_nodata (int): NoData value of the LiDAR tiles.
    geodata_path (pathlib.Path): Folder of the data shipped with the package.
    quadro_unione_path (pathlib.Path): GeoPackage of the tile index, with the
        layers `dtm` and `dsm`.
    limiti_amministrativi_path (pathlib.Path): GeoPackage of the boundaries of
        the municipalities of Città Metropolitana di Napoli.
    limiti_amministrativi_layer (str): Layer of the boundaries in
        `limiti_amministrativi_path`.
    lidar_types (tuple[str, ...]): Available LiDAR models, `"dtm"` and `"dsm"`.
    lidar_crs (str): Coordinate reference system of the tile index and of the
        boundaries, EPSG:32633 (WGS 84 / UTM zone 33N).
    certificates_path (pathlib.Path): Folder of the certificates shipped with
        the package.
    intermediate_certificates_path (pathlib.Path): PEM file of the
        intermediate certificates that `lidar_cmn.generic.ssl_context` trusts
        in addition to those of the system and of certifi, because
        sit.cittametropolitana.na.it doesn't send them; see the page
        Certificato SSL of the documentation.
    wfs_url (str): WFS service of Città Metropolitana di Napoli that publishes
        the official tile index.
    wfs_layers (dict[str, str]): WFS layer of the tile index of each LiDAR model.
"""
import logging
from pathlib import Path

# Package logger: messages are shown only if the application configures logging,
# e.g. logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("lidar_cmn")
logger.addHandler(logging.NullHandler())
log_format = '%(asctime)s | %(process)d - %(message)s'

raster_nodata = -9999

# Base geodata shipped with the package
geodata_path = Path(__file__).parent.joinpath("geodata")
quadro_unione_path = geodata_path.joinpath("quadro_unione_lidar.gpkg")
limiti_amministrativi_path = geodata_path.joinpath("limiti_amministrativi.gpkg")
limiti_amministrativi_layer = "prov_na_2023"
lidar_types = ("dtm", "dsm")
lidar_crs = "EPSG:32633"

# Intermediate certificates missing from the chain sent by sit.cittametropolitana.na.it
certificates_path = Path(__file__).parent.joinpath("certificates")
intermediate_certificates_path = certificates_path.joinpath("intermediate_certificates.pem")

# Official tile index published by Città Metropolitana di Napoli
wfs_url = "https://sit.cittametropolitana.na.it/geoserver/ows"
wfs_layers = {
    "dtm": "sit:quadro_unione_lidar_dtm",
    "dsm": "sit:quadro_unione_lidar_dsm",
}
