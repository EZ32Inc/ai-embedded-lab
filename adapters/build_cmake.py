import os
from datetime import datetime


def run(board_cfg):
    name = board_cfg.get("name", "unknown")
    print(f"Build: target {name}")

    root = os.path.dirname(os.path.dirname(__file__))
    out_dir = os.path.join(root, "artifacts", "runs")
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    firmware_path = os.path.join(out_dir, f"firmware_{ts}.elf")
    try:
        with open(firmware_path, "w", encoding="utf-8") as f:
            f.write("dummy firmware artifact\n")
        print(f"Build: OK -> {firmware_path}")
        return firmware_path
    except Exception as exc:
        print(f"Build: FAIL ({exc})")
        return None
