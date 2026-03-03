#!/usr/bin/env python3
"""Lightweight regression checks for CLI policy resolver defaults."""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ael.config_resolver import resolve_probe_config


def _args(**kwargs):
    return argparse.Namespace(**kwargs)


def main() -> int:
    repo_root = str(REPO_ROOT)

    # 1) No --probe, no pack meta => previous run default path.
    probe = resolve_probe_config(repo_root, _args(probe=None, dut=None), board_id=None, pack_meta=None)
    assert probe == os.path.join("configs", "esp32jtag.yaml"), probe

    # 2) User-provided --probe overrides all policy defaults.
    custom = "configs/custom_probe.yaml"
    probe = resolve_probe_config(repo_root, _args(probe=custom, dut=None), board_id=None, pack_meta=None)
    assert probe == custom, probe

    # 3) Pack mode board policy matches previous behavior (notify when applicable).
    policy = {"mode": "pack", "board": "esp32s3_devkit", "absolute_paths": True}
    probe = resolve_probe_config(repo_root, _args(probe=None, dut=None), board_id="esp32s3_devkit", pack_meta=policy)
    default_abs = os.path.join(repo_root, "configs", "esp32jtag.yaml")
    notify_abs = os.path.join(repo_root, "configs", "esp32jtag_notify.yaml")
    expected = notify_abs if os.path.exists(notify_abs) else default_abs
    assert probe == expected, (probe, expected)

    print("check_resolver_defaults: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
