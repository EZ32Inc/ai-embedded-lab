import socket
import subprocess
import shutil
import time

import requests
from requests.auth import HTTPBasicAuth


def _maybe_disable_ssl_warnings(verify_ssl: bool, suppress: bool) -> None:
    if verify_ssl or not suppress:
        return
    try:
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning

        urllib3.disable_warnings(InsecureRequestWarning)
    except Exception:
        pass

def _ping(ip):
    if not ip:
        print("Preflight: missing probe IP")
        return False
    ping = shutil.which("ping")
    if not ping:
        print("Preflight: ping not available")
        return False
    try:
        res = subprocess.run([ping, "-c", "1", "-W", "1", ip], capture_output=True, text=True)
        ok = res.returncode == 0
        print(f"Preflight: ping {ip} -> {'OK' if ok else 'FAIL'}")
        return ok
    except Exception as exc:
        print(f"Preflight: ping error: {exc}")
        return False


def _check_tcp(ip, port):
    if not ip or not port:
        print("Preflight: missing IP/port for TCP check")
        return False
    try:
        with socket.create_connection((ip, int(port)), timeout=1.0):
            print(f"Preflight: TCP {ip}:{port} -> OK")
            return True
    except Exception as exc:
        print(f"Preflight: TCP {ip}:{port} -> FAIL ({exc})")
        return False


def _ping_once(ip, timeout_s=1.0):
    if not ip:
        return False
    ping = shutil.which("ping")
    if not ping:
        return False
    try:
        wait_s = max(1, int(timeout_s))
        res = subprocess.run([ping, "-c", "1", "-W", str(wait_s), ip], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def _monitor_cmd(ip, port, gdb_cmd, command, timeout_s):
    return subprocess.run(
        [
            gdb_cmd,
            "-q",
            "--nx",
            "--batch",
            "-ex",
            f"target extended-remote {ip}:{port}",
            "-ex",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def _monitor_output_failed(out_text: str) -> bool:
    text = (out_text or "").lower()
    failure_markers = (
        "no usable targets found",
        "error:",
        "remote failure reply",
        "timed out",
        "connection timed out",
        "connection refused",
        "connection reset by peer",
    )
    return any(marker in text for marker in failure_markers)


def _parse_targets(stdout_text: str):
    targets = []
    in_table = False
    for raw in (stdout_text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith("available targets"):
            in_table = True
            continue
        if in_table and line[0].isdigit():
            parts = line.split()
            if len(parts) >= 3:
                targets.append(" ".join(parts[2:]))
        elif "rp2040" in line.lower():
            targets.append(line)
    return targets


def _monitor_targets(ip, port, gdb_cmd):
    if not gdb_cmd:
        print("Preflight: gdb_cmd not set, skipping monitor targets")
        return False, []
    last_error = ""
    targets = []
    for attempt in range(1, 4):
        timeout_s = 3 + (attempt * 2)
        try:
            res = _monitor_cmd(ip, port, gdb_cmd, "monitor targets", timeout_s=timeout_s)
            combined = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
            targets = _parse_targets(combined)
            output_failed = _monitor_output_failed(combined)
            ok = (res.returncode == 0) and (not output_failed) and bool(targets)
            if ok:
                print("Preflight: monitor targets -> OK")
                print("Preflight: targets: " + ", ".join(targets))
                return True, targets
            last_error = combined or f"return code {res.returncode}"
            print(f"Preflight: monitor targets attempt {attempt}/3 -> FAIL")
            if combined:
                print(combined)
        except subprocess.TimeoutExpired:
            last_error = "timeout"
            print(f"Preflight: monitor targets attempt {attempt}/3 -> FAIL (timeout)")
        except Exception as exc:
            last_error = str(exc)
            print(f"Preflight: monitor targets attempt {attempt}/3 error: {exc}")
        time.sleep(0.4)

    # Fallback probe: sometimes monitor targets is flaky while debug stub responds.
    try:
        res = _monitor_cmd(ip, port, gdb_cmd, "monitor version", timeout_s=8)
        combined = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
        output_failed = _monitor_output_failed(combined)
        if res.returncode == 0 and not output_failed:
            print("Preflight: monitor version fallback -> OK (targets unavailable)")
            return True, targets
        if combined:
            last_error = combined
    except Exception as exc:
        last_error = str(exc)

    print("Preflight: monitor targets -> FAIL")
    if last_error:
        print(last_error)
    print("Hint: Check connection or release GDB connection in another session if one is active.")
    ip_ok = _ping_once(ip, timeout_s=1.0)
    print(f"Preflight: post-fail ping {ip} -> {'OK' if ip_ok else 'FAIL'}")
    if ip_ok:
        print("Hint: Probe IP is reachable but debug monitor is unhealthy.")
        print("Hint: Power-cycle/reset ESP32JTAG, then retry. This can be automated in a future recovery step.")
    return False, targets


def _parse_samples(buffer: bytes):
    data = list(buffer)
    words = []
    for n in range(0, len(data) - 4, 2):
        low = data[n + 2]
        high = data[n + 1]
        words.append((high << 8) | low)
    return words


def _edge_counts_all_bits(words, bits=16):
    counts = [0] * bits
    if not words:
        return counts
    prev = [(words[0] >> i) & 0x1 for i in range(bits)]
    for w in words[1:]:
        for i in range(bits):
            b = (w >> i) & 0x1
            if b != prev[i]:
                counts[i] += 1
                prev[i] = b
    return counts


def _la_self_test(probe_cfg):
    ip = probe_cfg.get("ip")
    scheme = probe_cfg.get("web_scheme", "https")
    port = int(probe_cfg.get("web_port", 443))
    user = probe_cfg.get("web_user", "admin")
    password = probe_cfg.get("web_pass", "admin")
    verify_ssl = bool(probe_cfg.get("web_verify_ssl", False))
    suppress_ssl_warnings = bool(probe_cfg.get("web_suppress_ssl_warnings", False))

    if not ip:
        print("Preflight: LA self-test skipped (missing IP)")
        return False

    base_url = f"{scheme}://{ip}:{port}"
    auth = HTTPBasicAuth(user, password)
    _maybe_disable_ssl_warnings(verify_ssl, suppress_ssl_warnings)

    try:
        cfg = {
            "sampleRate": 1_000_000,
            "triggerPosition": 50,
            "triggerEnabled": False,
            "triggerModeOR": True,
            "captureInternalTestSignal": True,
            "channels": ["disabled"] * 16,
        }
        r = requests.post(
            f"{base_url}/la_configure",
            json=cfg,
            headers={"Content-Type": "application/json"},
            auth=auth,
            timeout=5,
            verify=verify_ssl,
        )
        r.raise_for_status()

        r = requests.get(f"{base_url}/instant_capture", auth=auth, timeout=10, verify=verify_ssl)
        r.raise_for_status()
        words = _parse_samples(r.content)
        counts = _edge_counts_all_bits(words)
        ok = max(counts) > 0
        print("Preflight: LA self-test (internal signal) -> " + ("OK" if ok else "FAIL"))
        print("Preflight: LA edge counts: " + ", ".join([f"b{i}={c}" for i, c in enumerate(counts)]))
        return ok
    except Exception as exc:
        print(f"Preflight: LA self-test error: {exc}")
        return False
    finally:
        # Always restore normal capture mode so external DUT captures are not contaminated.
        try:
            restore = {
                "sampleRate": 1_000_000,
                "triggerPosition": 50,
                "triggerEnabled": False,
                "triggerModeOR": True,
                "captureInternalTestSignal": False,
                "channels": ["disabled"] * 16,
            }
            requests.post(
                f"{base_url}/la_configure",
                json=restore,
                headers={"Content-Type": "application/json"},
                auth=auth,
                timeout=5,
                verify=verify_ssl,
            ).raise_for_status()
            print("Preflight: LA internal test signal reset -> OFF")
        except Exception as exc:
            print(f"Preflight: LA reset warning: {exc}")


def _fetch_port_config(probe_cfg):
    ip = probe_cfg.get("ip")
    scheme = probe_cfg.get("web_scheme", "https")
    port = int(probe_cfg.get("web_port", 443))
    user = probe_cfg.get("web_user", "admin")
    password = probe_cfg.get("web_pass", "admin")
    verify_ssl = bool(probe_cfg.get("web_verify_ssl", False))
    suppress_ssl_warnings = bool(probe_cfg.get("web_suppress_ssl_warnings", False))

    if not ip:
        print("Preflight: Port config skipped (missing IP)")
        return {}

    base_url = f"{scheme}://{ip}:{port}"
    auth = HTTPBasicAuth(user, password)
    _maybe_disable_ssl_warnings(verify_ssl, suppress_ssl_warnings)

    try:
        # Fetch config JSON used by the UI
        r = requests.get(f"{base_url}/get_credentials", auth=auth, timeout=5, verify=verify_ssl)
        r.raise_for_status()
        data = r.json() if r.content else {}
        mapping = {
            "pacfg": "Port A Configuration",
            "pbcfg": "Port B Configuration",
            "pccfg": "Port C Configuration",
            "pdcfg": "Port D Configuration",
        }
        found = False
        out = {}
        for key, label in mapping.items():
            if key in data:
                print(f"Preflight: {label}: {data[key]}")
                out[key] = data[key]
                found = True
        if not found:
            print("Preflight: Port config values not found in /get_credentials.")
        return out
    except Exception as exc:
        print(f"Preflight: Port config fetch error: {exc}")
        return {}


def run(probe_cfg):
    ip = probe_cfg.get("ip")
    port = probe_cfg.get("gdb_port")
    gdb_cmd = probe_cfg.get("gdb_cmd")

    ok_ping = _ping(ip)
    ok_tcp = _check_tcp(ip, port)
    ok_mon, targets = _monitor_targets(ip, port, gdb_cmd)
    ok_la = _la_self_test(probe_cfg)
    port_cfg = _fetch_port_config(probe_cfg)

    info = {
        "ping_ok": ok_ping,
        "tcp_ok": ok_tcp,
        "monitor_ok": ok_mon,
        "targets": targets,
        "la_ok": ok_la,
        "port_config": port_cfg,
    }

    if ok_ping and ok_tcp and ok_mon and ok_la:
        print("Preflight: OK")
        return True, info
    print("Preflight: FAIL")
    return False, info
