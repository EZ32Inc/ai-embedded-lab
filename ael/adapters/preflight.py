import socket
import subprocess
import shutil
import time
from dataclasses import dataclass
from typing import List

import requests
from requests.auth import HTTPBasicAuth


@dataclass
class PreflightIssue:
    kind: str        # e.g. "connection_setup_incomplete", "instrument_role_unreachable", "wiring_not_verified"
    severity: str    # "blocking" or "advisory"
    message: str


def _tcp_ping(endpoint: str) -> bool:
    """Return True if host:port is reachable via TCP within 1 second."""
    if not endpoint or ":" not in endpoint:
        return False
    try:
        host, port_str = endpoint.rsplit(":", 1)
        port = int(port_str)
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except Exception:
        return False


def check_connection_readiness(bench_setup: dict) -> List[PreflightIssue]:
    """Check connection/setup readiness before run.

    Returns a list of PreflightIssue items (blocking or advisory).
    Blocking issues prevent execution; advisory issues are warnings only.
    """
    from ael.connection_model import build_setup_readiness

    issues: List[PreflightIssue] = []
    if not isinstance(bench_setup, dict):
        return issues

    readiness = build_setup_readiness(bench_setup)

    for issue_text in readiness.blocking_issues:
        issues.append(PreflightIssue(
            kind="connection_setup_incomplete",
            severity="blocking",
            message=issue_text,
        ))

    for role in bench_setup.get("instrument_roles", []) or []:
        if not isinstance(role, dict):
            continue
        endpoint = str(role.get("endpoint") or "").strip()
        required = bool(role.get("required", True))
        if endpoint and required:
            if not _tcp_ping(endpoint):
                issues.append(PreflightIssue(
                    kind="instrument_role_unreachable",
                    severity="blocking",
                    message=f"instrument_role '{role.get('role')}' endpoint {endpoint} not reachable",
                ))

    if bench_setup.get("dut_to_instrument") and not bench_setup.get("discovery_status"):
        issues.append(PreflightIssue(
            kind="wiring_not_verified",
            severity="advisory",
            message="dut_to_instrument mappings declared but wiring not verified by auto-discovery",
        ))

    return issues


def _maybe_disable_ssl_warnings(verify_ssl: bool, suppress: bool) -> None:
    if verify_ssl or not suppress:
        return
    try:
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning

        urllib3.disable_warnings(InsecureRequestWarning)
    except Exception:
        pass

def _ping(ip, attempts=3, delay_s=0.8):
    if not ip:
        print("Preflight: missing probe IP")
        return False
    ping = shutil.which("ping")
    if not ping:
        print("Preflight: ping not available")
        return False
    last_exc = None
    for attempt in range(1, int(attempts) + 1):
        try:
            res = subprocess.run([ping, "-c", "1", "-W", "1", ip], capture_output=True, text=True)
            if res.returncode == 0:
                suffix = "" if attempt == 1 else f" (attempt {attempt}/{attempts})"
                print(f"Preflight: ping {ip} -> OK{suffix}")
                return True
        except Exception as exc:
            last_exc = exc
        if attempt < attempts:
            time.sleep(max(0.0, float(delay_s)))
    print(f"Preflight: ping {ip} -> FAIL")
    if last_exc is not None:
        print(f"Preflight: ping error: {last_exc}")
    return False


def _check_tcp(ip, port, attempts=3, delay_s=0.8):
    if not ip or not port:
        print("Preflight: missing IP/port for TCP check")
        return False
    last_exc = None
    for attempt in range(1, int(attempts) + 1):
        try:
            with socket.create_connection((ip, int(port)), timeout=1.0):
                suffix = "" if attempt == 1 else f" (attempt {attempt}/{attempts})"
                print(f"Preflight: TCP {ip}:{port} -> OK{suffix}")
                return True
        except Exception as exc:
            last_exc = exc
        if attempt < attempts:
            time.sleep(max(0.0, float(delay_s)))
    print(f"Preflight: TCP {ip}:{port} -> FAIL ({last_exc})")
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


def _classify_monitor_failure(error_text: str, ip_reachable: bool) -> str:
    text = (error_text or "").lower()
    if any(marker in text for marker in ("connection refused", "connection reset by peer", "no route to host")):
        return "probe_transport_unhealthy"
    if any(marker in text for marker in ("timeout", "timed out", "connection timed out", "monitor command not supported")):
        return "probe_busy_or_stuck" if ip_reachable else "probe_transport_unhealthy"
    if "another session" in text or "already" in text:
        return "probe_busy_or_stuck"
    return "probe_monitor_failed"


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
        timeout_s = (3 + (attempt * 2)) * 2
        try:
            res = _monitor_cmd(ip, port, gdb_cmd, "monitor a", timeout_s=timeout_s)
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

    ip_ok = _ping_once(ip, timeout_s=1.0)
    failure_kind = _classify_monitor_failure(last_error, ip_ok)
    print("Preflight: monitor targets -> FAIL")
    if last_error:
        print(last_error)
    print(f"Preflight: monitor failure kind -> {failure_kind}")
    print("Hint: Check connection or release GDB connection in another session if one is active.")
    print(f"Preflight: post-fail ping {ip} -> {'OK' if ip_ok else 'FAIL'}")
    if ip_ok:
        if failure_kind == "probe_busy_or_stuck":
            print("Hint: Probe IP is reachable; the debug monitor is likely busy or stuck in another session.")
            print("Hint: Release the other debugger or reset ESP32JTAG, then retry.")
        else:
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
    preflight_cfg = probe_cfg.get("preflight", {}) if isinstance(probe_cfg.get("preflight"), dict) else {}
    capture_check = str(preflight_cfg.get("capture_check") or "la").strip().lower()

    ok_ping = _ping(ip)
    ok_tcp = _check_tcp(ip, port)
    ok_mon, targets = _monitor_targets(ip, port, gdb_cmd)
    if capture_check == "targetin":
        ok_la = True
        print("Preflight: capture self-test skipped (TARGETIN-backed path)")
    else:
        ok_la = _la_self_test(probe_cfg)
    port_cfg = _fetch_port_config(probe_cfg)

    info = {
        "ping_ok": ok_ping,
        "tcp_ok": ok_tcp,
        "monitor_ok": ok_mon,
        "targets": targets,
        "la_ok": ok_la,
        "capture_check": capture_check,
        "port_config": port_cfg,
    }

    # ICMP/TCP checks can transiently fail while the probe is still stabilizing.
    # If monitor + capture checks pass, treat ping/tcp as advisory.
    if ok_mon and ok_la:
        if not ok_ping:
            print("Preflight: ping check failed, but service checks passed; continuing.")
        if not ok_tcp:
            print("Preflight: TCP check failed, but monitor/capture checks passed; continuing.")
        print("Preflight: OK")
        return True, info
    print("Preflight: FAIL")
    return False, info
