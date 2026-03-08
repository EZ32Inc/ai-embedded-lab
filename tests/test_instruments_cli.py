import json

import pytest

from ael import __main__ as ael_main


def test_meter_reachability_cli_success(monkeypatch, capsys):
    monkeypatch.setattr(
        "ael.instruments.provision.ensure_meter_reachable",
        lambda manifest, host=None, timeout_s=1.0: {
            "ok": True,
            "instrument_id": manifest.get("id"),
            "host": host or "192.168.4.1",
            "ping": {"ok": True},
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        ["ael", "instruments", "meter-reachability", "--id", "esp32s3_dev_c_meter"],
    )

    with pytest.raises(SystemExit) as exc:
        ael_main.main()

    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["instrument_id"] == "esp32s3_dev_c_meter"


def test_meter_reachability_cli_failure(monkeypatch, capsys):
    def _fail(manifest, host=None, timeout_s=1.0):
        raise RuntimeError(
            "meter esp32s3_dev_c_meter at 192.168.4.1 is unreachable and needs manual checking. "
            "Suggestion: add a meter reset feature."
        )

    monkeypatch.setattr("ael.instruments.provision.ensure_meter_reachable", _fail)
    monkeypatch.setattr(
        "sys.argv",
        ["ael", "instruments", "meter-reachability", "--id", "esp32s3_dev_c_meter"],
    )

    with pytest.raises(SystemExit) as exc:
        ael_main.main()

    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "manual checking" in payload["error"]
