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
            ["file {firmware}", "monitor a", "attach {target_id}", "load", "detach"],
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
