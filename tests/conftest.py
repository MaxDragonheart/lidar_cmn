"""Fixtures of the tests: local HTTP and HTTPS servers for the download tests."""
import ssl
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator, Optional

import pytest

# Content of the ESRI ASCII grids served by the local servers
ascii_grid = b"ncols 2\nnrows 2\nxllcorner 0\nyllcorner 0\ncellsize 1\nNODATA_value -9999\n1 2\n3 4\n"

# Certificates of the HTTPS server, made by data/tls/make_certificates.sh
tls_path = Path(__file__).parent.joinpath("data", "tls")


class _Handler(SimpleHTTPRequestHandler):
    """HTTP handler that serves the files of a folder and simulates errors.

    The paths starting with `/html/` answer with an HTML page, as a proxy does,
    and those starting with `/error/` with 503 Service Unavailable. Each
    requested path is appended to the `requests` list of the server.
    """

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append(self.path)
        if self.path.startswith("/html/"):
            body = b"<html><body>Proxy page</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/error/"):
            self.send_error(503)
        else:
            super().do_GET()


def _serve(tmp_path_factory, context: Optional[ssl.SSLContext] = None) -> Iterator[SimpleNamespace]:
    """Start a local server for the download tests.

    The server serves `000001.asc` and `000002.asc`, two ESRI ASCII grids, and
    `not_a_grid.asc`, a file that isn't a grid; see `_Handler` for the errors.

    Args:
        tmp_path_factory: pytest fixture that creates the folder of the files.
        context: SSL context of the server. If None, the server uses HTTP,
            otherwise HTTPS.

    Yields:
        SimpleNamespace: `url` is the base url of the server, `requests` the
            list of the requested paths.
    """
    root = tmp_path_factory.mktemp("server")
    for name in ["000001.asc", "000002.asc"]:
        root.joinpath(name).write_bytes(ascii_grid)
    root.joinpath("not_a_grid.asc").write_bytes(b"not an ESRI ASCII grid")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Handler, directory=str(root)))
    scheme = "http"
    if context is not None:
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
    httpd.requests = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield SimpleNamespace(url=f"{scheme}://127.0.0.1:{httpd.server_address[1]}", requests=httpd.requests)

    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def server(tmp_path_factory):
    """Start a local HTTP server for the download tests, see `_serve`.

    Args:
        tmp_path_factory: pytest fixture that creates the folder of the files.

    Yields:
        SimpleNamespace: `url` is the base url of the server, `requests` the
            list of the requested paths.
    """
    yield from _serve(tmp_path_factory)


@pytest.fixture
def https_server(tmp_path_factory):
    """Start a local HTTPS server that sends an incomplete chain of certificates.

    The certificate of the server, `data/tls/server.pem`, is signed by the
    intermediate `data/tls/intermediate_ca.pem`, signed in turn by the root
    `data/tls/root_ca.pem`. The server sends only its own certificate, without
    the intermediate, as sit.cittametropolitana.na.it does. It serves the files
    of `_serve`.

    Args:
        tmp_path_factory: pytest fixture that creates the folder of the files.

    Yields:
        SimpleNamespace: `url` is the base url of the server, `requests` the
            list of the requested paths.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=tls_path.joinpath("server.pem"), keyfile=tls_path.joinpath("server.key"))
    yield from _serve(tmp_path_factory, context=context)


@pytest.fixture
def no_sleep(monkeypatch):
    """Skip the waits between the download attempts.

    Args:
        monkeypatch: pytest fixture that replaces `time.sleep`.
    """
    monkeypatch.setattr("lidar_cmn.download.time.sleep", lambda seconds: None)
