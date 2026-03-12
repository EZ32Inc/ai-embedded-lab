from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "artifacts" / "usb_uart_bridge_bundle"
BUNDLE_ROOT = OUT_DIR / "usb_uart_bridge_bundle"
ZIP_PATH = OUT_DIR / "usb_uart_bridge_bundle_v0_1.zip"


FILES = [
    ("ael/__init__.py", "ael/__init__.py"),
    ("ael/usb_uart_bridge_cli.py", "ael/usb_uart_bridge_cli.py"),
    ("ael/instruments/__init__.py", "ael/instruments/__init__.py"),
    ("ael/instruments/usb_uart_bridge_daemon.py", "ael/instruments/usb_uart_bridge_daemon.py"),
    ("configs/instruments/usb_uart_bridge.example.yaml", "configs/instruments/usb_uart_bridge.example.yaml"),
    ("docs/instruments/usb_uart_bridge_daemon_v0_1.md", "docs/instruments/usb_uart_bridge_daemon_v0_1.md"),
]


README = """# USB-UART Bridge Bundle v0.1

This bundle contains the minimum files required to run the AEL USB-UART bridge
daemon on another Linux/Ubuntu host.

Quick start:

1. Create a virtual environment (optional but recommended)
2. Install dependencies:
   pip install pyserial pyyaml
3. Copy the example config:
   cp configs/instruments/usb_uart_bridge.example.yaml configs/instruments/usb_uart_bridge.yaml
4. Select the attached device:
   python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml list --format text
   python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml select --device-id <ID>
5. Start the daemon:
   python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml serve --host 0.0.0.0 --port 8767
"""


INSTALL_REMOTE = """# Install / Setup (Remote Host)

This bundle is the minimum remote-host package for Phase 2b of the bounded
USB-to-UART verification path.

## 1. Unpack

Unzip the bundle on the remote Linux/Ubuntu host.

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

## 3. Create the local runtime config

```bash
cp configs/instruments/usb_uart_bridge.example.yaml configs/instruments/usb_uart_bridge.yaml
```

## 4. List devices

```bash
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml --format text list
```

## 5. Select the attached USB-UART device

If the device has a stable serial:

```bash
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml select --serial <SERIAL>
```

If it does not have a usable serial, select by stable device identity:

```bash
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml select --device-id <ID>
```

## 6. Verify the selected device

```bash
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml --format text show
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml --format text doctor
```

## 7. Start the bridge daemon

```bash
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml serve --host 0.0.0.0 --port 8767
```

## 8. What the remote host is

The remote host is only an instrument node/service for the USB-UART bridge.

It is not:

- a full AEL orchestrator
- a remote worker
- a cloud/session node
"""


def _copy_file(src_rel: str, dst_rel: str) -> None:
    src = REPO_ROOT / src_rel
    dst = BUNDLE_ROOT / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_bundle() -> dict[str, object]:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    BUNDLE_ROOT.mkdir(parents=True, exist_ok=True)

    for src_rel, dst_rel in FILES:
        _copy_file(src_rel, dst_rel)

    (BUNDLE_ROOT / "requirements.txt").write_text("pyserial\nPyYAML\n", encoding="utf-8")
    (BUNDLE_ROOT / "README.md").write_text(README, encoding="utf-8")
    (BUNDLE_ROOT / "INSTALL_REMOTE.md").write_text(INSTALL_REMOTE, encoding="utf-8")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(BUNDLE_ROOT.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(BUNDLE_ROOT))

    return {
        "ok": True,
        "bundle_root": str(BUNDLE_ROOT),
        "zip_path": str(ZIP_PATH),
        "files": sorted(str(p.relative_to(BUNDLE_ROOT)) for p in BUNDLE_ROOT.rglob("*") if p.is_file()),
    }


if __name__ == "__main__":
    print(json.dumps(build_bundle(), indent=2, sort_keys=True))
