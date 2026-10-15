from pathlib import Path

import pytest
from geopandas import GeoDataFrame

from lidar_cmn.download import DownloadError, download_data, is_valid_file
from lidar_cmn.vector import read_boundaries, read_lidar_index, target_area
from tests.conftest import ascii_grid


def selection_of(urls) -> GeoDataFrame:
    return GeoDataFrame({"url": urls})


def test_download_data(server, tmp_path: Path):
    print("test_download_data")
    folder = download_data(
        selection=selection_of([f"{server.url}/000001.asc", f"{server.url}/000002.asc"]),
        output_folder=tmp_path,
        output_folder_name="dsm"
    )

    assert folder == tmp_path.joinpath("dsm")
    assert sorted(path.name for path in folder.iterdir()) == ["000001.asc", "000002.asc"]


def test_download_data_resume(server, tmp_path: Path):
    print("test_download_data_resume")
    folder = tmp_path.joinpath("dtm")
    folder.mkdir()
    already_downloaded = b"ncols 1\nnrows 1\nxllcorner 0\nyllcorner 0\ncellsize 1\nNODATA_value -9999\n5\n"
    folder.joinpath("000001.asc").write_bytes(already_downloaded)
    selection = selection_of([f"{server.url}/000001.asc", f"{server.url}/000002.asc"])

    download_data(selection=selection, output_folder=tmp_path, output_folder_name="dtm")

    assert server.requests == ["/000002.asc"]
    assert folder.joinpath("000001.asc").read_bytes() == already_downloaded

    download_data(selection=selection, output_folder=tmp_path, output_folder_name="dtm", overwrite=True)

    assert folder.joinpath("000001.asc").read_bytes() == ascii_grid


def test_download_data_failures(server, no_sleep, tmp_path: Path):
    print("test_download_data_failures")
    failing = [f"{server.url}/missing.asc", f"{server.url}/not_a_grid.asc", f"{server.url}/error/000003.asc"]
    selection = selection_of([f"{server.url}/000001.asc", *failing, f"{server.url}/000002.asc"])

    with pytest.raises(DownloadError) as error:
        download_data(selection=selection, output_folder=tmp_path, output_folder_name="dsm", retries=2)

    assert error.value.urls == failing
    assert sorted(path.name for path in tmp_path.joinpath("dsm").iterdir()) == ["000001.asc", "000002.asc"]
    # 404 Not Found isn't retried
    assert server.requests.count("/missing.asc") == 1
    assert server.requests.count("/not_a_grid.asc") == 2
    assert server.requests.count("/error/000003.asc") == 2


def test_download_data_stops(server, no_sleep, tmp_path: Path):
    print("test_download_data_stops")
    selection = selection_of([f"{server.url}/error/00000{number}.asc" for number in range(1, 5)])

    with pytest.raises(DownloadError, match="consecutive failures") as error:
        download_data(
            selection=selection, output_folder=tmp_path, output_folder_name="dsm", max_consecutive_failures=2
        )

    assert len(error.value.urls) == 2


@pytest.mark.network
@pytest.mark.parametrize("lidar_type", ["dtm", "dsm"])
def test_download_lidar_data(lidar_type: str, tmp_path: Path):
    print("test_download_lidar_data")
    data = target_area(
        boundaries=read_boundaries(),
        link_source=read_lidar_index(lidar_type=lidar_type),
        target="Procida"
    )

    folder = download_data(selection=data.head(2), output_folder=tmp_path, output_folder_name=lidar_type)

    files = list(folder.iterdir())
    assert len(files) == 2
    assert all(is_valid_file(path=path) for path in files)
