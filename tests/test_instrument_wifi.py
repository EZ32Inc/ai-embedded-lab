import unittest
from unittest.mock import patch

from ael.adapters import esp32s3_dev_c_meter_tcp
from ael.instruments import provision
from ael.instruments import wifi


MANIFEST = {
    "id": "esp32s3_dev_c_meter",
    "wifi": {
        "ap_ssid_prefix": "ESP32_GPIO_METER_",
        "ap_password": "esp32gpiom",
        "ap_ip": "192.168.4.1",
        "tcp_port": 9000,
    },
}


class _Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestInstrumentWifi(unittest.TestCase):
    def test_scan_filters_by_prefix_and_sorts_by_signal(self):
        with patch(
            "ael.instruments.wifi.subprocess.run",
            return_value=_Completed(
                stdout="\n".join(
                    [
                        ":ESP32_GPIO_METER_1234:70",
                        ":OtherNetwork:99",
                        "*:ESP32_GPIO_METER_ABCD:90",
                    ]
                )
            ),
        ):
            out = wifi.scan("wlan0", MANIFEST)
        self.assertTrue(out["ok"])
        self.assertEqual(["ESP32_GPIO_METER_ABCD", "ESP32_GPIO_METER_1234"], [m["ssid"] for m in out["matches"]])
        self.assertTrue(out["matches"][0]["in_use"])
        self.assertEqual("ABCD", out["matches"][0]["ssid_suffix"])

    def test_meter_list_report_normalizes_agent_facing_shape(self):
        with patch(
            "ael.instruments.wifi.subprocess.run",
            return_value=_Completed(
                stdout="\n".join(
                    [
                        ":ESP32_GPIO_METER_67A9:100",
                        ":ESP32_GPIO_METER_BEEF:80",
                    ]
                )
            ),
        ):
            out = wifi.meter_list_report("wlan0", MANIFEST)
        self.assertTrue(out["ok"])
        self.assertEqual(2, out["meter_count"])
        self.assertTrue(out["selection_required"])
        self.assertEqual("choose_meter_by_ssid_or_suffix", out["recommended_action"])
        self.assertEqual(
            [
                {"ssid": "ESP32_GPIO_METER_67A9", "suffix": "67A9", "signal": 100, "in_use": False},
                {"ssid": "ESP32_GPIO_METER_BEEF", "suffix": "BEEF", "signal": 80, "in_use": False},
            ],
            out["available_meters"],
        )

    def test_connect_by_suffix(self):
        calls = []

        def _fake_run(cmd, check, capture_output, text):
            calls.append(cmd)
            if cmd[1:7] == ["-t", "-f", "IN-USE,SSID,SIGNAL", "dev", "wifi", "list"]:
                return _Completed(stdout=":ESP32_GPIO_METER_67A9:100\n:ESP32_GPIO_METER_BEEF:80\n")
            if cmd[1:4] == ["dev", "wifi", "connect"]:
                return _Completed(stdout="ok\n")
            raise AssertionError(f"unexpected command: {cmd}")

        with patch("ael.instruments.wifi.subprocess.run", side_effect=_fake_run):
            out = wifi.connect("wlan1", MANIFEST, ssid_suffix="67A9")
        self.assertTrue(out["ok"])
        self.assertEqual("ESP32_GPIO_METER_67A9", out["connected_ssid"])
        self.assertEqual(
            ["nmcli", "dev", "wifi", "connect", "ESP32_GPIO_METER_67A9", "password", "esp32gpiom", "ifname", "wlan1"],
            calls[-1],
        )

    def test_connect_requires_disambiguation_when_multiple_matches(self):
        with patch(
            "ael.instruments.wifi.subprocess.run",
            return_value=_Completed(stdout=":ESP32_GPIO_METER_1111:70\n:ESP32_GPIO_METER_2222:65\n"),
        ):
            with self.assertRaisesRegex(ValueError, "multiple matching meter ssids found"):
                wifi.connect("wlan0", MANIFEST)

    def test_connect_single_match_without_explicit_ssid(self):
        calls = []

        def _fake_run(cmd, check, capture_output, text):
            calls.append(cmd)
            if cmd[1:7] == ["-t", "-f", "IN-USE,SSID,SIGNAL", "dev", "wifi", "list"]:
                return _Completed(stdout=":ESP32_GPIO_METER_67A9:100\n")
            if cmd[1:4] == ["dev", "wifi", "connect"]:
                return _Completed(stdout="ok\n")
            raise AssertionError(f"unexpected command: {cmd}")

        with patch("ael.instruments.wifi.subprocess.run", side_effect=_fake_run):
            out = wifi.connect("wlan1", MANIFEST)
        self.assertEqual("ESP32_GPIO_METER_67A9", out["connected_ssid"])

    def test_flash_wait_connect_orchestrates_steps(self):
        with patch("ael.instruments.provision.flash_meter", return_value={"ok": True, "flash": "completed"}) as flash_mock, patch(
            "ael.instruments.provision.wait_for_meter",
            return_value={"ok": True, "matches": [{"ssid": "ESP32_GPIO_METER_67A9", "ssid_suffix": "67A9", "signal": 100}]},
        ) as wait_mock, patch(
            "ael.instruments.provision.wifi.connect",
            return_value={"ok": True, "connected_ssid": "ESP32_GPIO_METER_67A9", "ap_ip": "192.168.4.1", "tcp_port": 9000},
        ) as connect_mock:
            out = provision.flash_wait_connect(
                port="/dev/ttyACM0",
                ifname="wlan1",
                manifest=MANIFEST,
                ssid_suffix="67A9",
                timeout_s=20.0,
                interval_s=1.0,
            )
        self.assertTrue(out["ok"])
        self.assertEqual("ESP32_GPIO_METER_67A9", out["connected_ssid"])
        flash_mock.assert_called_once()
        wait_mock.assert_called_once()
        connect_mock.assert_called_once()

    def test_meter_ping_uses_manifest_endpoint(self):
        with patch("ael.adapters.esp32s3_dev_c_meter_tcp._send_line", return_value={"ok": True, "type": "pong", "ip": "192.168.4.1"}):
            out = esp32s3_dev_c_meter_tcp.ping({"host": MANIFEST["wifi"]["ap_ip"], "port": MANIFEST["wifi"]["tcp_port"]})
        self.assertTrue(out["ok"])
        self.assertEqual("pong", out["type"])

    def test_ready_meter_scans_connects_and_pings(self):
        with patch(
            "ael.instruments.provision.wifi.scan",
            return_value={
                "ok": True,
                "matches": [
                    {"ssid": "ESP32_GPIO_METER_67A9", "ssid_suffix": "67A9", "signal": 100, "in_use": False},
                    {"ssid": "ESP32_GPIO_METER_BEEF", "ssid_suffix": "BEEF", "signal": 80, "in_use": False},
                ],
            },
        ) as scan_mock, patch(
            "ael.instruments.provision.wifi.connect",
            return_value={"ok": True, "connected_ssid": "ESP32_GPIO_METER_BEEF", "ap_ip": "192.168.4.1", "tcp_port": 9000},
        ) as connect_mock, patch(
            "ael.instruments.provision.esp32s3_dev_c_meter_tcp.ping",
            return_value={"ok": True, "type": "pong", "ssid": "ESP32_GPIO_METER_BEEF"},
        ) as ping_mock:
            out = provision.ready_meter(ifname="wlan1", manifest=MANIFEST, ssid_suffix="BEEF")
        self.assertTrue(out["ok"])
        self.assertEqual("ESP32_GPIO_METER_BEEF", out["connected_ssid"])
        self.assertEqual("pong", out["ping"]["type"])
        scan_mock.assert_called_once()
        connect_mock.assert_called_once()
        ping_mock.assert_called_once_with({"host": "192.168.4.1", "port": 9000})


if __name__ == "__main__":
    unittest.main()
