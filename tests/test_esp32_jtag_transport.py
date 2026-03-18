from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from ael.instruments.backends.esp32_jtag.errors import InvalidRequest, RequestTimeout, TransportUnavailable
from ael.instruments.backends.esp32_jtag.transport import Esp32JtagTransport, TransportConfig


def _transport() -> Esp32JtagTransport:
    return Esp32JtagTransport(TransportConfig(host="127.0.0.1", port=5555, timeout_s=1.0))


def test_transport_rejects_empty_command():
    transport = _transport()
    with pytest.raises(InvalidRequest):
        transport.request("", {})


def test_transport_maps_timeout():
    transport = _transport()
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.socket.create_connection",
        side_effect=socket.timeout(),
    ):
        with pytest.raises(RequestTimeout):
            transport.request("reset", {})


def test_transport_maps_oserror_to_transport_unavailable():
    transport = _transport()
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.socket.create_connection",
        side_effect=OSError("refused"),
    ):
        with pytest.raises(TransportUnavailable):
            transport.request("reset", {})


def test_transport_rejects_invalid_json_response():
    transport = _transport()
    with patch.object(Esp32JtagTransport, "_send_json", return_value="not-a-dict"):
        with pytest.raises(TransportUnavailable):
            transport.request("reset", {})
