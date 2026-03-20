from pathlib import Path
from unittest.mock import patch

from ael.adapters import flash_bmda_gdbmi


def test_run_gdb_respects_custom_launch_commands_without_forcing_resume():
    captured = {}

    def fake_run(args, capture_output, text, timeout):
        captured["args"] = args
        captured["timeout"] = timeout

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    with patch("ael.adapters.flash_bmda_gdbmi.subprocess.run", side_effect=fake_run):
        flash_bmda_gdbmi._run_gdb(
            "arm-none-eabi-gdb",
            "192.168.2.98",
            4242,
            "/tmp/fw.elf",
            1,
            [],
            [],
            30,
            True,
            ["file {firmware}", "monitor a", "attach {target_id}", "load", "attach {target_id}", "detach"],
        )

    args = captured["args"]
    assert args[:6] == [
        "arm-none-eabi-gdb",
        "-q",
        "--nx",
        "--batch",
        "-ex",
        "target extended-remote 192.168.2.98:4242",
    ]
    assert "file /tmp/fw.elf" in args
    assert "attach 1" in args
    assert "load" in args
    assert args.count("attach 1") == 2
    assert args.index("load") < args.index("attach 1", args.index("load"))
    assert "detach" in args
    assert "continue" not in args
    assert "monitor reset run" not in args
    assert captured["timeout"] == 30


def test_run_gdb_default_launch_still_adds_resume_and_detach():
    captured = {}

    def fake_run(args, capture_output, text, timeout):
        captured["args"] = args

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    with patch("ael.adapters.flash_bmda_gdbmi.subprocess.run", side_effect=fake_run):
        flash_bmda_gdbmi._run_gdb(
            "arm-none-eabi-gdb",
            "192.168.2.98",
            4242,
            "/tmp/fw.elf",
            1,
            [],
            [],
            30,
            True,
            None,
        )

    args = captured["args"]
    assert "file /tmp/fw.elf" in args
    assert "attach 1" in args
    assert "load" in args
    assert "monitor reset run" in args
    assert "continue" in args
    assert "detach" in args


def test_contains_rejected_output_matches_keywords_case_insensitively():
    keyword = flash_bmda_gdbmi._contains_rejected_output(
        "Warning: Remote failure reply: E01\nCould not read registers\n",
        ["error", "warning"],
    )
    assert keyword == "warning"


def test_contains_rejected_output_returns_empty_when_clean():
    keyword = flash_bmda_gdbmi._contains_rejected_output(
        "Loading section .text\nTransfer rate: 1 KB/sec\n[Inferior 1 (Remote target) detached]\n",
        ["error", "warning"],
    )
    assert keyword == ""


def test_classify_stlink_server_issue_busy():
    diag = flash_bmda_gdbmi._classify_stlink_server_issue("READREG send request failed: LIBUSB_ERROR_BUSY")
    assert diag["code"] == "usb_busy"
    assert "busy" in diag["summary"].lower()


def test_classify_stlink_server_issue_timeout():
    diag = flash_bmda_gdbmi._classify_stlink_server_issue("GET_VERSION read reply failed: LIBUSB_ERROR_TIMEOUT")
    assert diag["code"] == "usb_timeout"
    assert "timed out" in diag["summary"].lower()


def test_probe_stlink_health_reports_missing_programmer():
    class Result:
        returncode = 0
        stdout = "Found 0 stlink programmers\n"
        stderr = ""

    with patch.object(flash_bmda_gdbmi, "_STINFO_BIN", Path("/tmp/st-info")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi.subprocess.run", return_value=Result()):
        diag = flash_bmda_gdbmi._probe_stlink_health()

    assert diag["ok"] is False
    assert diag["code"] == "usb_missing"
    assert "no ST-Link device" in diag["summary"]


def test_probe_stlink_with_retries_recovers_on_second_attempt():
    emitted = []
    calls = [
        {"ok": False, "code": "usb_missing", "summary": "missing", "hint": "retry", "output": "", "command": ""},
        {"ok": True, "code": "", "summary": "", "hint": "", "output": "", "command": ""},
    ]

    with patch("ael.adapters.flash_bmda_gdbmi._probe_stlink_health", side_effect=calls), patch(
        "ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None
    ) as sleep_mock:
        diag = flash_bmda_gdbmi._probe_stlink_with_retries(emitted.append, attempts=3, delay_s=1.0)

    assert diag["ok"] is True
    assert any("direct probe retry 1/2" in line for line in emitted)
    assert any("direct probe recovered on attempt 2/3" in line for line in emitted)
    sleep_mock.assert_called_once_with(1.0)


def test_probe_stlink_with_retries_returns_last_failure_after_budget():
    emitted = []
    failure = {"ok": False, "code": "swd_attach_failed", "summary": "bad", "hint": "retry", "output": "", "command": ""}

    with patch("ael.adapters.flash_bmda_gdbmi._probe_stlink_health", side_effect=[failure, failure, failure]), patch(
        "ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None
    ) as sleep_mock:
        diag = flash_bmda_gdbmi._probe_stlink_with_retries(emitted.append, attempts=3, delay_s=0.5)

    assert diag["ok"] is False
    assert diag["code"] == "swd_attach_failed"
    assert any("direct probe retry 1/2" in line for line in emitted)
    assert any("direct probe retry 2/2" in line for line in emitted)
    assert sleep_mock.call_count == 2


def test_probe_stlink_health_reports_swd_attach_failure():
    class Result:
        returncode = 0
        stdout = "Found 1 stlink programmers\n  chipid:     0x000\n  dev-type:   unknown\n"
        stderr = "Failed to enter SWD mode\n"

    with patch.object(flash_bmda_gdbmi, "_STINFO_BIN", Path("/tmp/st-info")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi.subprocess.run", return_value=Result()):
        diag = flash_bmda_gdbmi._probe_stlink_health()

    assert diag["ok"] is False
    assert diag["code"] == "swd_attach_failed"
    assert "SWD" in diag["summary"]


def test_cleanup_managed_local_stlink_server_terminates_pid():
    emitted = []
    with patch("ael.adapters.flash_bmda_gdbmi._pid_exists", side_effect=[True, False]), patch(
        "ael.adapters.flash_bmda_gdbmi.os.kill"
    ) as kill_mock, patch("ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None):
        flash_bmda_gdbmi._cleanup_managed_local_stlink_server({"managed": True, "pid": 123}, emitted.append)

    kill_mock.assert_called_once()
    assert any("stopping managed local ST-Link GDB server pid 123" in line for line in emitted)


def test_cleanup_managed_local_stlink_server_escalates_to_sigkill():
    emitted = []
    with patch("ael.adapters.flash_bmda_gdbmi._pid_exists", side_effect=[True, True]), patch(
        "ael.adapters.flash_bmda_gdbmi.os.kill"
    ) as kill_mock, patch("ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None):
        flash_bmda_gdbmi._cleanup_managed_local_stlink_server({"managed": True, "pid": 123}, emitted.append)

    assert kill_mock.call_count == 2
    assert any("ignored SIGTERM" in line for line in emitted)


def test_local_stlink_server_available_uses_managed_flag():
    assert flash_bmda_gdbmi._local_stlink_server_available(
        "127.0.0.1", 4242, {"managed": True}
    ) is True


def test_local_stlink_server_available_checks_port_for_unmanaged_server():
    with patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", return_value=True) as port_check:
        ok = flash_bmda_gdbmi._local_stlink_server_available(
            "127.0.0.1", 4242, {"managed": False}
        )

    assert ok is True
    port_check.assert_called_once()


def test_find_stale_stlink_pids_parses_ps_output():
    class Result:
        returncode = 0
        stdout = "aes 123 1 0 00:00 ? 00:00:00 /path/st-util --listen_port 4242\naes 456 1 0 00:00 ? 00:00:00 /path/st-util --listen_port 4343\n"

    with patch("ael.adapters.flash_bmda_gdbmi.subprocess.run", return_value=Result()):
        pids = flash_bmda_gdbmi._find_stale_stlink_pids(4242)

    assert pids == [123]


def test_terminate_stale_stlink_processes_emits_and_kills():
    emitted = []
    with patch("ael.adapters.flash_bmda_gdbmi._find_stale_stlink_pids", return_value=[123, 456]), patch(
        "ael.adapters.flash_bmda_gdbmi._pid_exists", side_effect=[False, False]
    ), patch("ael.adapters.flash_bmda_gdbmi.os.kill") as kill_mock, patch(
        "ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None
    ):
        flash_bmda_gdbmi._terminate_stale_stlink_processes(4242, emitted.append)

    assert any("found stale local ST-Link server process(es)" in line for line in emitted)
    assert kill_mock.call_count == 2



def test_terminate_stale_stlink_processes_escalates_to_sigkill():
    emitted = []
    with patch("ael.adapters.flash_bmda_gdbmi._find_stale_stlink_pids", return_value=[123]), patch(
        "ael.adapters.flash_bmda_gdbmi._pid_exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi.os.kill") as kill_mock, patch(
        "ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None
    ):
        flash_bmda_gdbmi._terminate_stale_stlink_processes(4242, emitted.append)

    assert any("ignored SIGTERM" in line for line in emitted)
    assert kill_mock.call_count == 2


def test_run_writes_flash_log_when_path_configured(tmp_path):
    firmware = tmp_path / "fw.elf"
    firmware.write_text("stub", encoding="utf-8")
    flash_log = tmp_path / "flash.log"

    class Result:
        returncode = 0
        stdout = "Transfer rate: 1 KB/sec\n[Inferior 1 (Remote target) detached]\n"
        stderr = ""

    with patch("ael.adapters.flash_bmda_gdbmi._ensure_local_stlink_gdb_server") as ensure_server, patch(
        "ael.adapters.flash_bmda_gdbmi.subprocess.run", return_value=Result()
    ):
        ok = flash_bmda_gdbmi.run(
            {"ip": "192.168.2.98", "gdb_port": 4242, "gdb_cmd": "arm-none-eabi-gdb"},
            str(firmware),
            flash_cfg={
                "gdb_launch_cmds": [
                    "file {firmware}",
                    "monitor a",
                    "attach {target_id}",
                    "load",
                    "attach {target_id}",
                    "detach",
                ],
                "flash_log_path": str(flash_log),
            },
        )

    assert ok is True
    ensure_server.assert_not_called()
    text = flash_log.read_text(encoding="utf-8")
    assert "Flash: BMDA via GDB (resilience ladder)" in text
    assert "Transfer rate: 1 KB/sec" in text
    assert "Flash: OK" in text


def test_ensure_local_stlink_gdb_server_starts_when_port_missing(tmp_path):
    emitted = []

    class Proc:
        pid = 4321

        @staticmethod
        def poll():
            return None

        @staticmethod
        def terminate():
            return None

    flash_log = tmp_path / "flash.log"
    with patch.object(flash_bmda_gdbmi, "_STLINK_GDB_SERVER_SCRIPT", Path("/tmp/fake_gdb_server.sh")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi._find_stale_stlink_pids", return_value=[]), patch(
        "ael.adapters.flash_bmda_gdbmi._probe_stlink_health", return_value={"ok": True, "code": "", "summary": "", "hint": "", "output": "", "command": ""}
    ), patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", side_effect=[False, False, True, True]
    ), patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen", return_value=Proc()) as popen, patch(
        "ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None
    ):
        result = flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "127.0.0.1", "gdb_port": 4242},
            emitted.append,
            flash_log_path=str(flash_log),
        )

    popen.assert_called_once()
    assert result["ok"] is True
    assert result["managed"] is True
    assert result["skip_port_probe"] is True
    assert any("starting it" in line for line in emitted)
    assert any("ready at 127.0.0.1:4242" in line for line in emitted)


def test_ensure_local_stlink_gdb_server_reports_direct_probe_failure(tmp_path):
    emitted = []
    flash_log = tmp_path / "flash.log"

    with patch.object(flash_bmda_gdbmi, "_STLINK_GDB_SERVER_SCRIPT", Path("/tmp/fake_gdb_server.sh")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi._find_stale_stlink_pids", return_value=[]), patch(
        "ael.adapters.flash_bmda_gdbmi._port_is_listening", return_value=False
    ), patch("ael.adapters.flash_bmda_gdbmi._probe_stlink_health",
        return_value={
            "ok": False,
            "code": "swd_attach_failed",
            "summary": "Flash: ST-Link could not attach to the target over SWD.",
            "hint": "Flash: diagnostic - direct ST-Link probe found the adapter but could not enter SWD mode.",
            "output": "Failed to enter SWD mode",
            "command": "st-info --probe",
        },
    ), patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen") as popen:
        result = flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "127.0.0.1", "gdb_port": 4242},
            emitted.append,
            flash_log_path=str(flash_log),
        )

    assert result["ok"] is False
    assert result["error"] == "Flash: ST-Link could not attach to the target over SWD."
    assert result["diagnostic_code"] == "swd_attach_failed"
    popen.assert_not_called()
    assert any("direct probe output follows" in line for line in emitted)


def test_ensure_local_stlink_gdb_server_reports_early_exit(tmp_path):
    emitted = []
    flash_log = tmp_path / "flash.log"
    server_log = tmp_path / "flash_stlink_server.log"
    server_log.write_text("GET_VERSION read reply failed: LIBUSB_ERROR_TIMEOUT\n", encoding="utf-8")

    class Proc:
        pid = 4321

        @staticmethod
        def poll():
            return 2

        @staticmethod
        def terminate():
            return None

    with patch.object(flash_bmda_gdbmi, "_STLINK_GDB_SERVER_SCRIPT", Path("/tmp/fake_gdb_server.sh")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", return_value=False), patch(
        "ael.adapters.flash_bmda_gdbmi._probe_stlink_health", return_value={"ok": True, "code": "", "summary": "", "hint": "", "output": "", "command": ""}
    ), patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen", return_value=Proc()
    ), patch("ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None):
        result = flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "127.0.0.1", "gdb_port": 4242},
            emitted.append,
            flash_log_path=str(flash_log),
        )

    assert result["ok"] is False
    assert result["error"] == "Flash: ST-Link USB timed out."
    assert result["diagnostic_code"] == "usb_timeout"
    assert any("Flash: ST-Link USB timed out." in line for line in emitted)
    assert any("timed out while talking to the probe" in line for line in emitted)
    assert any("local ST-Link GDB server output follows:" in line for line in emitted)
    assert any("LIBUSB_ERROR_TIMEOUT" in line for line in emitted)


def test_ensure_local_stlink_gdb_server_skips_remote_probe():
    emitted = []
    with patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen") as popen:
        result = flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "192.168.2.98", "gdb_port": 4242},
            emitted.append,
        )

    popen.assert_not_called()
    assert result["ok"] is True
    assert emitted == []


def test_run_records_managed_local_stlink_server_in_flash_json(tmp_path):
    firmware = tmp_path / "fw.elf"
    firmware.write_text("stub", encoding="utf-8")
    flash_json = tmp_path / "flash.json"

    class Result:
        returncode = 0
        stdout = "Transfer rate: 1 KB/sec\n"
        stderr = ""

    with patch("ael.adapters.flash_bmda_gdbmi._ensure_local_stlink_gdb_server", return_value={
        "ok": True,
        "managed": True,
        "port_checked": True,
        "server_log_path": "",
        "error": "",
        "diagnostic_code": "",
        "skip_port_probe": True,
        "pid": 1234,
    }), patch("ael.adapters.flash_bmda_gdbmi._run_gdb", return_value=Result()):
        ok = flash_bmda_gdbmi.run(
            {"ip": "127.0.0.1", "gdb_port": 4242, "gdb_cmd": "arm-none-eabi-gdb"},
            str(firmware),
            flash_json_path=str(flash_json),
        )

    assert ok is True
    payload = __import__("json").loads(flash_json.read_text(encoding="utf-8"))
    assert payload["managed_stlink_server"]["managed"] is True
    assert payload["managed_stlink_server"]["pid"] == 1234


def test_run_bootstraps_local_stlink_server_once_before_flash(tmp_path):
    firmware = tmp_path / "fw.elf"
    firmware.write_text("stub", encoding="utf-8")

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    with patch(
        "ael.adapters.flash_bmda_gdbmi._ensure_local_stlink_gdb_server",
        return_value={"ok": True, "managed": True, "port_checked": True, "server_log_path": "", "error": ""},
    ) as ensure_server, patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", return_value=True), patch(
        "ael.adapters.flash_bmda_gdbmi.subprocess.run", return_value=Result()
    ):
        ok = flash_bmda_gdbmi.run(
            {"ip": "127.0.0.1", "gdb_port": 4242, "gdb_cmd": "arm-none-eabi-gdb"},
            str(firmware),
            flash_cfg={
                "gdb_launch_cmds": [
                    "file {firmware}",
                    "monitor a",
                    "attach {target_id}",
                    "load",
                    "attach {target_id}",
                    "detach",
                ]
            },
        )

    assert ok is True
    ensure_server.assert_called_once()


def test_run_stops_when_unmanaged_local_server_is_unavailable_before_attempt(tmp_path):
    firmware = tmp_path / "fw.elf"
    firmware.write_text("stub", encoding="utf-8")
    flash_log = tmp_path / "flash.log"

    with patch(
        "ael.adapters.flash_bmda_gdbmi._ensure_local_stlink_gdb_server",
        return_value={
            "ok": True,
            "managed": False,
            "port_checked": True,
            "server_log_path": "",
            "error": "",
            "skip_port_probe": False,
        },
    ), patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", return_value=False), patch(
        "ael.adapters.flash_bmda_gdbmi.subprocess.run"
    ) as run_gdb:
        ok = flash_bmda_gdbmi.run(
            {"ip": "127.0.0.1", "gdb_port": 4242, "gdb_cmd": "arm-none-eabi-gdb"},
            str(firmware),
            flash_cfg={
                "gdb_launch_cmds": [
                    "file {firmware}",
                    "monitor a",
                    "attach {target_id}",
                    "load",
                    "attach {target_id}",
                    "detach",
                ],
                "flash_log_path": str(flash_log),
            },
        )

    assert ok is False
    run_gdb.assert_not_called()
    text = flash_log.read_text(encoding="utf-8")
    assert "local ST-Link GDB server unavailable at 127.0.0.1:4242" in text


def test_ensure_local_stlink_gdb_server_clears_stale_process_before_start(tmp_path):
    emitted = []

    class Proc:
        pid = 4321

        @staticmethod
        def poll():
            return None

        @staticmethod
        def terminate():
            return None

    flash_log = tmp_path / "flash.log"
    with patch.object(flash_bmda_gdbmi, "_STLINK_GDB_SERVER_SCRIPT", Path("/tmp/fake_gdb_server.sh")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", side_effect=[False, False, True, True]), patch(
        "ael.adapters.flash_bmda_gdbmi._find_stale_stlink_pids", return_value=[999]
    ), patch("ael.adapters.flash_bmda_gdbmi._probe_stlink_health", return_value={"ok": True, "code": "", "summary": "", "hint": "", "output": "", "command": ""}), patch("ael.adapters.flash_bmda_gdbmi._pid_exists", return_value=False), patch(
        "ael.adapters.flash_bmda_gdbmi.os.kill"
    ) as kill_mock, patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen", return_value=Proc()
    ) as popen, patch("ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None):
        result = flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "127.0.0.1", "gdb_port": 4242},
            emitted.append,
            flash_log_path=str(flash_log),
        )

    assert result["ok"] is True
    kill_mock.assert_called_once()
    popen.assert_called_once()
    assert any("found stale local ST-Link server process(es)" in line for line in emitted)



def test_ensure_local_stlink_gdb_server_restarts_existing_listener_before_flash(tmp_path):
    emitted = []

    class Proc:
        pid = 4322

        @staticmethod
        def poll():
            return None

    flash_log = tmp_path / "flash.log"
    with patch.object(flash_bmda_gdbmi, "_STLINK_GDB_SERVER_SCRIPT", Path("/tmp/fake_gdb_server.sh")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", side_effect=[True, False, False]), patch(
        "ael.adapters.flash_bmda_gdbmi._find_stale_stlink_pids", return_value=[340032]
    ), patch("ael.adapters.flash_bmda_gdbmi._probe_stlink_with_retries", return_value={"ok": True, "code": "", "summary": "", "hint": "", "output": "", "command": ""}), patch("ael.adapters.flash_bmda_gdbmi._pid_exists", return_value=False), patch(
        "ael.adapters.flash_bmda_gdbmi.os.kill"
    ) as kill_mock, patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen", return_value=Proc()) as popen, patch(
        "ael.adapters.flash_bmda_gdbmi.time.sleep", return_value=None
    ):
        result = flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "127.0.0.1", "gdb_port": 4242},
            emitted.append,
            flash_log_path=str(flash_log),
        )

    assert result["ok"] is True
    assert result["managed"] is True
    kill_mock.assert_called_once_with(340032, flash_bmda_gdbmi.signal.SIGTERM)
    popen.assert_called_once()
    assert any("restarting existing local ST-Link GDB server" in line for line in emitted)
