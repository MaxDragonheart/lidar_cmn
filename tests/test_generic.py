"""Tests of `lidar_cmn.generic`."""
import hashlib
import socket
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError

import certifi
import pytest

from lidar_cmn.config import geodata_path, intermediate_certificates_path
from lidar_cmn.generic import check_path, download_from_url, ssl_context
from tests.conftest import ascii_grid, tls_path

# Server of Città Metropolitana di Napoli, which sends an incomplete chain of certificates
sit_host = "sit.cittametropolitana.na.it"

# SHA-256 of Sectigo Public Server Authentication CA DV R36, the intermediate
# certificate shipped with the package
sectigo_dv_r36_sha256 = "8C54C334B66BA4E426772AF4A3F9136C19A1AEC729FDB28C535C07A5A4EF22E0"


def client_context(*cafiles: Path) -> ssl.SSLContext:
    """Make an SSL context that trusts only the certificates of some files.

    Unlike `ssl_context`, the context doesn't trust the certificates of the
    operating system: the result of the tests that use it is the same on every
    operating system.

    Args:
        cafiles: PEM files of the trusted certificates.

    Returns:
        The SSL context, which verifies the certificate and the hostname of
            the server.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    for cafile in cafiles:
        context.load_verify_locations(cafile=cafile)

    return context


def sha256_of(context: ssl.SSLContext) -> set:
    """Compute the SHA-256 of the certificate authorities trusted by an SSL context.

    Args:
        context: SSL context.

    Returns:
        The SHA-256 of the certificates, in uppercase hexadecimal.
    """
    return {hashlib.sha256(certificate).hexdigest().upper() for certificate in context.get_ca_certs(binary_form=True)}


def handshake(context: ssl.SSLContext, host: str = sit_host) -> dict:
    """Open a TLS connection to a server on port 443.

    Args:
        context: SSL context of the connection.
        host: Hostname of the server.

    Returns:
        The certificate of the server, as `ssl.SSLSocket.getpeercert`.
    """
    with socket.create_connection((host, 443), timeout=30) as connection:
        with context.wrap_socket(connection, server_hostname=host) as tls:
            return tls.getpeercert()


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


def test_download_from_url_incomplete_chain(https_server, tmp_path: Path):
    print("test_download_from_url_incomplete_chain")
    # The server sends only its certificate: the root alone can't verify it
    with pytest.raises(URLError) as error:
        download_from_url(
            url=f"{https_server.url}/000001.asc",
            destination=tmp_path,
            context=client_context(tls_path.joinpath("root_ca.pem"))
        )

    assert isinstance(error.value.reason, ssl.SSLCertVerificationError)
    assert "unable to get local issuer certificate" in str(error.value.reason)
    assert not list(tmp_path.iterdir())


def test_download_from_url_intermediate(https_server, tmp_path: Path):
    print("test_download_from_url_intermediate")
    # The trusted intermediate completes the chain, as intermediate_certificates.pem in ssl_context
    context = client_context(tls_path.joinpath("root_ca.pem"), tls_path.joinpath("intermediate_ca.pem"))

    download_path = download_from_url(url=f"{https_server.url}/000001.asc", destination=tmp_path, context=context)

    assert download_path.read_bytes() == ascii_grid
    assert https_server.requests == ["/000001.asc"]


def test_intermediate_certificates():
    print("test_intermediate_certificates")
    context = client_context(intermediate_certificates_path)

    assert sha256_of(context) == {sectigo_dv_r36_sha256}
    for certificate in context.get_ca_certs():
        assert ssl.cert_time_to_seconds(certificate["notAfter"]) > time.time()


def test_ssl_context():
    print("test_ssl_context")
    context = ssl_context()

    assert ssl_context() is context
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
    # Trusts the intermediate shipped with the package and the roots of certifi
    trusted = sha256_of(context)
    assert sectigo_dv_r36_sha256 in trusted
    assert sha256_of(client_context(Path(certifi.where()))) <= trusted


@pytest.mark.network
def test_ssl_context_sit():
    print("test_ssl_context_sit")
    certificate = handshake(context=ssl_context())

    assert ("DNS", "*.cittametropolitana.na.it") in certificate["subjectAltName"]


@pytest.mark.network
@pytest.mark.parametrize("verify_flags", [ssl.VERIFY_DEFAULT, ssl.VERIFY_X509_STRICT | ssl.VERIFY_X509_PARTIAL_CHAIN])
def test_intermediate_certificates_sit(verify_flags: ssl.VerifyFlags):
    print("test_intermediate_certificates_sit")
    # A proxy that inspects the HTTPS traffic, as in many corporate networks,
    # replaces the certificate of the server with one of its own authority,
    # trusted by the operating system but not by certifi
    issuer = dict(name for rdn in handshake(context=ssl_context())["issuer"] for name in rdn)
    if issuer.get("organizationName") != "Sectigo Limited":
        pytest.skip(f"The certificate of {sit_host} is issued by {issuer.get('commonName')}: TLS inspection by a proxy.")

    # Without the certificates of the operating system, certifi and the
    # intermediate shipped with the package are enough: the download works on
    # every operating system. The second verify_flags are those of
    # ssl.create_default_context since Python 3.13
    context = client_context(Path(certifi.where()), intermediate_certificates_path)
    context.verify_flags |= verify_flags

    certificate = handshake(context=context)

    assert ("DNS", "*.cittametropolitana.na.it") in certificate["subjectAltName"]
