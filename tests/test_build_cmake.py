from pathlib import Path
from unittest.mock import patch

from ael.adapters import build_artifacts, build_cmake


def test_default_firmware_path_uses_target_specific_cmake_artifact():
    repo_root = Path("/repo")
    board_cfg = {
        "target": "rp2350",
        "build": {
            "type": "cmake",
            "project_dir": "firmware/targets/rp2350_pico2",
            "artifact_stem": "pico2_gpio_signature",
        },
    }

    path = build_artifacts.default_firmware_path(repo_root, board_cfg, "cmake")
    assert path == "/repo/artifacts/build_rp2350/pico2_gpio_signature.elf"


def test_build_cmake_uses_board_project_dir_and_artifact_stem(tmp_path):
    project_dir = tmp_path / "firmware" / "targets" / "rp2350_pico2"
    project_dir.mkdir(parents=True)
    build_dir = tmp_path / "artifacts" / "build_rp2350"
    build_dir.mkdir(parents=True)
    elf_path = build_dir / "pico2_gpio_signature.elf"
    elf_path.write_text("elf", encoding="utf-8")

    board_cfg = {
        "name": "Pico 2",
        "target": "rp2350",
        "build": {
            "project_dir": "firmware/targets/rp2350_pico2",
            "artifact_stem": "pico2_gpio_signature",
        },
    }

    calls = []

    class Result:
        def __init__(self):
            self.stdout = ""
            self.stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return Result()

    with patch("ael.adapters.build_cmake._toolchain_ok", return_value=True), patch(
        "ael.adapters.build_cmake._get_pico_sdk_path", return_value="/sdk"
    ), patch("ael.adapters.build_cmake.os.path.isdir", return_value=True), patch(
        "ael.adapters.build_cmake.subprocess.run", side_effect=fake_run
    ), patch(
        "ael.adapters.build_cmake.os.path.dirname",
        side_effect=[
            str(tmp_path / "ael" / "adapters"),
            str(tmp_path / "ael"),
            str(tmp_path),
        ],
    ):
        firmware_path = build_cmake.run(board_cfg)

    assert firmware_path == str(elf_path)
    assert calls[0][:4] == ["cmake", "-S", str(project_dir), "-B"]
    assert calls[0][4] == str(build_dir)
    assert calls[1][:4] == ["cmake", "--build", str(build_dir), "-j"]
