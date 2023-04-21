from pathlib import Path

from lidar_cmn.download import download_data
from lidar_cmn.vector import target_area, read_vector
from tests.vector import limiti_amministrativi, quadro_unione

data = target_area(
    boundaries=read_vector(data_path=limiti_amministrativi),
    link_source=read_vector(data_path=quadro_unione, layer_name="dsm"),
    target="Procida"
)


def test_download_data(tmp_path: Path) -> None:
    print("test_download_data")
    download_data(
        selection=data,
        output_folder=tmp_path,
        output_folder_name="dsm"
    )
