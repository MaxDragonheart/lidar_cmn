"""Tests of `lidar_cmn.generic`."""
from pathlib import Path
from urllib.error import HTTPError

import pytest

from lidar_cmn.config import geodata_path
from lidar_cmn.generic import check_path, download_from_url
from tests.conftest import ascii_grid


def test_check_path():
    print("test_check_path")
    assert check_path(path=str(geodata_path)) == geodata_path

    with pytest.raises(Exception, match="doesn't exists"):
        check_path(path=geodata_path.joinpath("missing"))


def test_download_from_url(server, tmp_path: Path):
    print("test_download_from_url")
    download_path = download_from_url(url=f"{server.url}/000001.asc", destination=tmp_path)

    assert download_path == tmp_path.joinpath("000001.asc")
    assert download_path.read_bytes() == ascii_grid
    assert not list(tmp_path.glob("*.part"))


def test_download_from_url_strips_spaces(server, tmp_path: Path):
    print("test_download_from_url_strips_spaces")
    download_path = download_from_url(url=f"  {server.url}/000001.asc   ", destination=tmp_path)

    assert download_path.name == "000001.asc"


def test_download_from_url_html(server, tmp_path: Path):
    print("test_download_from_url_html")
    with pytest.raises(Exception, match="HTML page"):
        download_from_url(url=f"{server.url}/html/000001.asc", destination=tmp_path)

    assert not list(tmp_path.iterdir())


def test_download_from_url_not_found(server, tmp_path: Path):
    print("test_download_from_url_not_found")
    with pytest.raises(HTTPError):
        download_from_url(url=f"{server.url}/missing.asc", destination=tmp_path)

    assert not list(tmp_path.iterdir())
