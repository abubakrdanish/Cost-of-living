import socket

import pytest
import requests


def test_external_network_is_blocked():
    with pytest.raises(Exception, match="Network access attempted"):
        requests.get("https://data.api.abs.gov.au/rest/dataflow/ABS", timeout=5)


def test_loopback_is_allowed():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.socket()
    try:
        client.connect(server.getsockname())  # must not raise
    finally:
        client.close()
        server.close()
