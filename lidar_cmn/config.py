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

# Official tile index published by Città Metropolitana di Napoli
wfs_url = "https://sit.cittametropolitana.na.it/geoserver/ows"
wfs_layers = {
    "dtm": "sit:quadro_unione_lidar_dtm",
    "dsm": "sit:quadro_unione_lidar_dsm",
}
