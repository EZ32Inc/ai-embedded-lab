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


def test_ensure_local_stlink_gdb_server_starts_when_port_missing():
    emitted = []

    class Proc:
        pid = 4321

        @staticmethod
        def poll():
            return None

        @staticmethod
        def terminate():
            return None

    with patch.object(flash_bmda_gdbmi, "_STLINK_GDB_SERVER_SCRIPT", Path("/tmp/fake_gdb_server.sh")), patch(
        "ael.adapters.flash_bmda_gdbmi.Path.exists", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi._port_is_listening", return_value=False), patch(
        "ael.adapters.flash_bmda_gdbmi._wait_for_port", return_value=True
    ), patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen", return_value=Proc()) as popen:
        flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "127.0.0.1", "gdb_port": 4242},
            emitted.append,
        )

    popen.assert_called_once()
    assert any("starting it" in line for line in emitted)
    assert any("ready at 127.0.0.1:4242" in line for line in emitted)


def test_ensure_local_stlink_gdb_server_skips_remote_probe():
    emitted = []
    with patch("ael.adapters.flash_bmda_gdbmi.subprocess.Popen") as popen:
        flash_bmda_gdbmi._ensure_local_stlink_gdb_server(
            {"ip": "192.168.2.98", "gdb_port": 4242},
            emitted.append,
        )

    popen.assert_not_called()
    assert emitted == []


def test_run_bootstraps_local_stlink_server_before_flash(tmp_path):
    firmware = tmp_path / "fw.elf"
    firmware.write_text("stub", encoding="utf-8")

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    with patch("ael.adapters.flash_bmda_gdbmi._ensure_local_stlink_gdb_server") as ensure_server, patch(
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
    assert ensure_server.call_count >= 1
