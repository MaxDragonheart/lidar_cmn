import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

ascii_grid = b"ncols 2\nnrows 2\nxllcorner 0\nyllcorner 0\ncellsize 1\nNODATA_value -9999\n1 2\n3 4\n"


class _Handler(SimpleHTTPRequestHandler):
    """Serves the files of a folder; /html/* answers with an HTML page, as a proxy
    does, and /error/* with 503 Service Unavailable."""

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


@pytest.fixture
def server(tmp_path_factory):
    """Local HTTP server: server.url is its base url, server.requests the requested paths."""
    root = tmp_path_factory.mktemp("server")
    for name in ["000001.asc", "000002.asc"]:
        root.joinpath(name).write_bytes(ascii_grid)
    root.joinpath("not_a_grid.asc").write_bytes(b"not an ESRI ASCII grid")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Handler, directory=str(root)))
    httpd.requests = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield SimpleNamespace(url=f"http://127.0.0.1:{httpd.server_address[1]}", requests=httpd.requests)

    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def no_sleep(monkeypatch):
    """Skip the waits between the download attempts."""
    monkeypatch.setattr("lidar_cmn.download.time.sleep", lambda seconds: None)
