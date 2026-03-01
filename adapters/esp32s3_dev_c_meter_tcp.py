import json
import socket
from pathlib import Path


DEFAULT_HOST = "192.168.4.1"
DEFAULT_PORT = 9000
DEFAULT_TIMEOUT_S = 3


def _send_line(host, port, line, timeout_s=DEFAULT_TIMEOUT_S):
    with socket.create_connection((host, port), timeout=timeout_s) as sock:
        sock.settimeout(timeout_s)
        sock.sendall((line.strip() + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(1024)
            if not chunk:
                break
            data += chunk
        if b"\n" in data:
            data = data.split(b"\n", 1)[0]
        if not data:
            raise RuntimeError("no response")
        return json.loads(data.decode("utf-8"))


def _write_json(path, data):
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def ping(cfg, out_path=None):
    host = cfg.get("host", DEFAULT_HOST)
    port = int(cfg.get("port", DEFAULT_PORT))
    res = _send_line(host, port, "PING")
    _write_json(out_path, res)
    return res


def measure_digital(cfg, pins, duration_ms=500, out_path=None):
    host = cfg.get("host", DEFAULT_HOST)
    port = int(cfg.get("port", DEFAULT_PORT))
    pins_csv = ",".join(str(p) for p in pins)
    cmd = f"MEAS DIGITAL PINS={pins_csv} DUR_MS={int(duration_ms)}"
    res = _send_line(host, port, cmd)
    _write_json(out_path, res)
    return res


def measure_voltage(cfg, gpio=4, avg=16, out_path=None):
    host = cfg.get("host", DEFAULT_HOST)
    port = int(cfg.get("port", DEFAULT_PORT))
    cmd = f"MEAS VOLT GPIO={int(gpio)} AVG={int(avg)}"
    res = _send_line(host, port, cmd)
    _write_json(out_path, res)
    return res


def stim_digital(cfg, gpio, mode, duration_us=None, freq_hz=None, pattern=None, keep=0, out_path=None):
    host = cfg.get("host", DEFAULT_HOST)
    port = int(cfg.get("port", DEFAULT_PORT))
    parts = [f"STIM DIGITAL GPIO={int(gpio)}", f"MODE={mode}"]
    if duration_us is not None:
        parts.append(f"DUR_US={int(duration_us)}")
    if freq_hz is not None:
        parts.append(f"FREQ_HZ={int(freq_hz)}")
    if pattern is not None:
        parts.append(f"PATTERN={pattern}")
    if keep:
        parts.append("KEEP=1")
    cmd = " ".join(parts)
    res = _send_line(host, port, cmd)
    _write_json(out_path, res)
    return res
