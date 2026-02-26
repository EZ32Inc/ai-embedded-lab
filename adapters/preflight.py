import socket
import subprocess
import shutil


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


def _monitor_targets(ip, port, gdb_cmd):
    if not gdb_cmd:
        print("Preflight: gdb_cmd not set, skipping monitor targets")
        return False
    try:
        res = subprocess.run(
            [
                gdb_cmd,
                "-q",
                "--nx",
                "--batch",
                "-ex",
                f"target extended-remote {ip}:{port}",
                "-ex",
                "monitor targets",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        ok = res.returncode == 0
        print("Preflight: monitor targets -> " + ("OK" if ok else "FAIL"))
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr and not ok:
            print(res.stderr.strip())
        return ok
    except Exception as exc:
        print(f"Preflight: monitor targets error: {exc}")
        return False


def run(probe_cfg):
    ip = probe_cfg.get("ip")
    port = probe_cfg.get("gdb_port")
    gdb_cmd = probe_cfg.get("gdb_cmd")

    ok_ping = _ping(ip)
    ok_tcp = _check_tcp(ip, port)
    ok_mon = _monitor_targets(ip, port, gdb_cmd)

    if ok_ping and ok_tcp and ok_mon:
        print("Preflight: OK")
        return True
    print("Preflight: FAIL")
    return False
