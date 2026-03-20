import json
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Optional


_REPO_ROOT = Path(__file__).resolve().parents[2]
_STLINK_GDB_SERVER_SCRIPT = _REPO_ROOT / "instruments" / "STLinkInstrument" / "scripts" / "gdb_server.sh"


def _run_gdb(gdb_cmd, ip, port, firmware_path, target_id, pre_cmds, post_cmds, timeout_s, do_continue, launch_cmds):
    args = [
        gdb_cmd,
        "-q",
        "--nx",
        "--batch",
        "-ex",
        f"target extended-remote {ip}:{port}",
    ]
    for cmd in pre_cmds:
        args.extend(["-ex", cmd])
    if launch_cmds:
        for cmd in launch_cmds:
            cmd = cmd.replace("{firmware}", firmware_path).replace("{target_id}", str(target_id))
            args.extend(["-ex", cmd])
    else:
        args.extend(
            [
                "-ex",
                "monitor a",
                "-ex",
                f"file {firmware_path}",
                "-ex",
                f"attach {target_id}",
                "-ex",
                "load",
            ]
        )
    for cmd in post_cmds:
        args.extend(["-ex", cmd])
    if launch_cmds:
        # Custom launch commands are expected to handle run/detach.
        pass
    elif do_continue:
        args.extend(["-ex", "monitor reset run", "-ex", "continue", "-ex", "detach"])
    else:
        args.extend(["-ex", "detach"])
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)


def _run_continue(gdb_cmd, ip, port, target_id, timeout_s):
    args = [
        gdb_cmd,
        "-q",
        "--nx",
        "--batch",
        "-ex",
        f"target extended-remote {ip}:{port}",
        "-ex",
        "monitor a",
        "-ex",
        f"attach {target_id}",
        "-ex",
        "continue",
        "-ex",
        "detach",
    ]
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)


def _contains_rejected_output(out: str, keywords) -> str:
    if not keywords:
        return ""
    out_l = str(out or "").lower()
    for keyword in keywords:
        key = str(keyword or "").strip().lower()
        if key and key in out_l:
            return key
    return ""


def _append_flash_log(path: str, text: str) -> None:
    target = str(path or "").strip()
    if not target or not text:
        return
    try:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(text)
    except Exception:
        pass


def _is_local_host(ip: str) -> bool:
    value = str(ip or "").strip().lower()
    return value in {"127.0.0.1", "localhost", "::1"}


def _port_is_listening(ip: str, port: int, timeout_s: float = 0.25) -> bool:
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout_s):
            return True
    except OSError:
        return False


def _wait_for_port(ip: str, port: int, timeout_s: float) -> bool:
    deadline = time.time() + max(0.0, float(timeout_s))
    while time.time() < deadline:
        if _port_is_listening(ip, port):
            return True
        time.sleep(0.1)
    return _port_is_listening(ip, port)


def _stlink_server_log_path(flash_log_path: str) -> str:
    target = str(flash_log_path or "").strip()
    if not target:
        return ""
    flash_path = Path(target)
    return str(flash_path.with_name(f"{flash_path.stem}_stlink_server.log"))


def _read_recent_text(path: str, limit: int = 1200) -> str:
    target = str(path or "").strip()
    if not target:
        return ""
    try:
        text = Path(target).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def _classify_stlink_server_issue(text: str) -> dict[str, str]:
    low = str(text or "").lower()
    if not low:
        return {}
    if "libusb_error_busy" in low or "unable to claim" in low or "already in use" in low:
        return {
            "code": "usb_busy",
            "summary": "Flash: ST-Link USB is busy.",
            "hint": "Flash: diagnostic - ST-Link USB is busy; another process may still own the probe. Stop other ST-Link/GDB sessions, then unplug/replug the ST-Link and retry.",
        }
    if "libusb_error_timeout" in low or "get_version read reply failed" in low:
        return {
            "code": "usb_timeout",
            "summary": "Flash: ST-Link USB timed out.",
            "hint": "Flash: diagnostic - ST-Link USB timed out while talking to the probe. Unplug/replug the ST-Link, power-cycle the target if needed, then retry.",
        }
    if "no st-link devices found" in low:
        return {
            "code": "usb_missing",
            "summary": "Flash: no ST-Link device detected.",
            "hint": "Flash: diagnostic - no ST-Link device was detected. Check the USB cable and connection, then retry.",
        }
    if "more than 1 st-link" in low or "st-link devices found but no target specified" in low:
        return {
            "code": "usb_ambiguous",
            "summary": "Flash: multiple ST-Link devices detected.",
            "hint": "Flash: diagnostic - multiple ST-Link probes are connected. Select the intended probe explicitly before retrying.",
        }
    return {}


def _emit_stlink_server_failure(emit, reason: str, server_log_path: str) -> dict[str, str]:
    emit(reason)
    recent = _read_recent_text(server_log_path)
    diagnostic = _classify_stlink_server_issue(recent)
    if diagnostic.get("summary"):
        emit(diagnostic["summary"])
    if diagnostic.get("hint"):
        emit(diagnostic["hint"])
    if recent:
        emit("Flash: local ST-Link GDB server output follows:")
        emit(recent)
    elif server_log_path:
        emit(f"Flash: local ST-Link GDB server log path: {server_log_path}")
    return diagnostic


def _ensure_local_stlink_gdb_server(
    probe_cfg,
    emit,
    flash_log_path: str = "",
    startup_timeout_s: float = 5.0,
    stable_grace_s: float = 0.5,
):
    ip = str(probe_cfg.get("ip") or "").strip()
    port = int(probe_cfg.get("gdb_port") or 0)
    result = {
        "ok": True,
        "managed": False,
        "port_checked": bool(_is_local_host(ip) and port > 0),
        "server_log_path": _stlink_server_log_path(flash_log_path),
        "error": "",
        "diagnostic_code": "",
    }
    if not result["port_checked"]:
        return result
    if _port_is_listening(ip, port):
        return result
    if not _STLINK_GDB_SERVER_SCRIPT.exists():
        msg = f"Flash: local ST-Link GDB server script missing: {_STLINK_GDB_SERVER_SCRIPT}"
        diagnostic = _emit_stlink_server_failure(emit, msg, result["server_log_path"])
        result["ok"] = False
        result["error"] = diagnostic.get("summary") or msg
        result["diagnostic_code"] = diagnostic.get("code", "")
        return result

    emit(f"Flash: local ST-Link GDB server not detected at {ip}:{port}; starting it")
    cmd = [str(_STLINK_GDB_SERVER_SCRIPT), "--port", str(port)]
    log_handle: Optional[object] = None
    try:
        if result["server_log_path"]:
            log_handle = open(result["server_log_path"], "a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            cwd=str(_REPO_ROOT),
            stdout=log_handle or subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception as exc:
        if log_handle:
            log_handle.close()
        msg = f"Flash: failed to start local ST-Link GDB server ({exc})"
        diagnostic = _emit_stlink_server_failure(emit, msg, result["server_log_path"])
        result["ok"] = False
        result["error"] = diagnostic.get("summary") or msg
        result["diagnostic_code"] = diagnostic.get("code", "")
        return result
    finally:
        if log_handle:
            log_handle.close()

    result["managed"] = True
    deadline = time.time() + max(0.0, float(startup_timeout_s))
    while time.time() < deadline:
        if _port_is_listening(ip, port):
            break
        exit_code = proc.poll()
        if exit_code is not None:
            msg = f"Flash: local ST-Link GDB server exited during startup with code {exit_code}"
            diagnostic = _emit_stlink_server_failure(emit, msg, result["server_log_path"])
            result["ok"] = False
            result["error"] = diagnostic.get("summary") or msg
            result["diagnostic_code"] = diagnostic.get("code", "")
            return result
        time.sleep(0.1)

    if not _port_is_listening(ip, port):
        msg = f"Flash: local ST-Link GDB server did not become ready at {ip}:{port}"
        diagnostic = _emit_stlink_server_failure(emit, msg, result["server_log_path"])
        result["ok"] = False
        result["error"] = diagnostic.get("summary") or msg
        result["diagnostic_code"] = diagnostic.get("code", "")
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception:
            pass
        return result

    time.sleep(max(0.0, float(stable_grace_s)))
    exit_code = proc.poll()
    if exit_code is not None:
        msg = f"Flash: local ST-Link GDB server exited immediately after startup with code {exit_code}"
        diagnostic = _emit_stlink_server_failure(emit, msg, result["server_log_path"])
        result["ok"] = False
        result["error"] = diagnostic.get("summary") or msg
        result["diagnostic_code"] = diagnostic.get("code", "")
        return result

    emit(f"Flash: local ST-Link GDB server ready at {ip}:{port} (pid {proc.pid})")
    return result


def run(probe_cfg, firmware_path, flash_cfg=None, flash_json_path=None):
    if not firmware_path or not os.path.exists(firmware_path):
        print("Flash: firmware not found")
        return False

    ip = probe_cfg.get("ip")
    port = probe_cfg.get("gdb_port")
    gdb_cmd = probe_cfg.get("gdb_cmd")

    if not gdb_cmd:
        print("Flash: gdb_cmd not set")
        return False

    flash_cfg = flash_cfg or {}
    target_id = flash_cfg.get("target_id", 1)
    speed_khz = flash_cfg.get("speed_khz", None)
    reset_strategy = flash_cfg.get("reset_strategy", "")
    timeout_s = int(flash_cfg.get("timeout_s", 120))
    do_continue = True
    reset_available = bool(flash_cfg.get("reset_available", True))
    launch_cmds = flash_cfg.get("gdb_launch_cmds", None)
    retry_continue_on_remote_failure = bool(flash_cfg.get("retry_continue_on_remote_failure", False))
    continue_retry_timeout_s = int(flash_cfg.get("continue_retry_timeout_s", 8))
    notice_output_keywords = flash_cfg.get("notice_output_keywords", [])
    if not isinstance(notice_output_keywords, list):
        notice_output_keywords = []
    flash_log_path = str(flash_cfg.get("flash_log_path") or "").strip()

    def emit(line: str = "") -> None:
        print(line)
        _append_flash_log(flash_log_path, f"{line}\n")

    attempts = []
    strategies = [
        {
            "name": "normal",
            "pre": [],
            "post": [],
        },
        {
            "name": "connect_under_reset",
            "pre": ["monitor connect_srst enable", "monitor reset halt"],
            "post": ["monitor connect_srst disable"],
        },
        {
            "name": "reduced_speed",
            "pre": ([f"monitor swd_freq {int(speed_khz)}"] if speed_khz else []),
            "post": [],
        },
        {
            "name": "reconnect",
            "pre": ["monitor reconnect"],
            "post": [],
        },
    ]

    if reset_strategy and reset_strategy != "connect_under_reset":
        # If a custom reset strategy is set, only include it as attempt 2.
        strategies[1]["name"] = reset_strategy

    emit("Flash: BMDA via GDB (resilience ladder)")
    ok = False
    strategy_used = ""
    last_error = ""
    stlink_bootstrap = {"ok": True, "managed": False, "port_checked": False, "server_log_path": "", "error": "", "diagnostic_code": ""}
    if _is_local_host(ip) and port:
        stlink_bootstrap = _ensure_local_stlink_gdb_server(probe_cfg, emit, flash_log_path=flash_log_path)
        if not stlink_bootstrap.get("ok", True):
            last_error = stlink_bootstrap.get("error") or "local ST-Link GDB server startup failed"

    for idx, strat in enumerate(strategies, start=1):
        if last_error and not ok and stlink_bootstrap.get("port_checked") and not stlink_bootstrap.get("ok", True):
            break
        if stlink_bootstrap.get("port_checked") and not _port_is_listening(ip, port):
            if stlink_bootstrap.get("managed"):
                last_error = "local ST-Link GDB server stopped before flash attempt"
                _emit_stlink_server_failure(emit, f"Flash: {last_error}", stlink_bootstrap.get("server_log_path", ""))
            else:
                last_error = f"local ST-Link GDB server unavailable at {ip}:{port}"
                emit(f"Flash: {last_error}")
            break
        try:
            res = _run_gdb(
                gdb_cmd,
                ip,
                port,
                firmware_path,
                target_id,
                strat.get("pre", []),
                strat.get("post", []),
                timeout_s,
                do_continue,
                launch_cmds,
            )
            out = (res.stdout or "") + (res.stderr or "")
            out_l = out.lower()
            noticed_keyword = _contains_rejected_output(out, notice_output_keywords)
            attempt_ok = res.returncode == 0 and "failed" not in out_l
            attempts.append(
                {
                    "attempt": idx,
                    "strategy": strat.get("name"),
                    "ok": attempt_ok,
                    "returncode": res.returncode,
                    "noticed_keyword": noticed_keyword or None,
                }
            )
            emit(f"Flash: attempt {idx} ({strat.get('name')}) -> " + ("OK" if attempt_ok else "FAIL"))
            if res.stdout:
                emit(res.stdout.strip())
            if res.stderr:
                emit(res.stderr.strip())
            if noticed_keyword:
                msg = f"There is warning/error during flash: matched '{noticed_keyword}'."
                if flash_log_path:
                    msg += f" Check more details in log file {flash_log_path}"
                emit(msg)
            if attempt_ok:
                ok = True
                strategy_used = strat.get("name")
                # If the probe reports a remote failure, try a delayed continue.
                if (not launch_cmds) and ("remote failure reply" in out_l or "could not read registers" in out_l):
                    if reset_available and retry_continue_on_remote_failure:
                        emit("Flash: warning - remote failure reply, retrying continue")
                        time.sleep(0.5)
                        try:
                            res2 = _run_continue(gdb_cmd, ip, port, target_id, continue_retry_timeout_s)
                            if res2.stdout:
                                emit(res2.stdout.strip())
                            if res2.stderr:
                                emit(res2.stderr.strip())
                        except Exception as exc:
                            emit(f"Flash: continue retry error ({exc})")
                    elif reset_available:
                        emit("Flash: warning - remote failure reply after load; skipping continue retry")
                    else:
                        emit("Flash: warning - remote failure reply; reset not wired, skipping continue retry")
                break
            last_error = "flash attempt failed"
        except Exception as exc:
            attempts.append(
                {
                    "attempt": idx,
                    "strategy": strat.get("name"),
                    "ok": False,
                    "error": str(exc),
                }
            )
            last_error = str(exc)
        time.sleep(0.2)

    if not ok:
        emit("Flash: FAIL")
    else:
        emit("Flash: OK")

    if flash_json_path:
        payload = {
            "ok": ok,
            "attempts": attempts,
            "strategy_used": strategy_used,
            "speed_khz": speed_khz,
            "target_id": target_id,
            "reset_strategy": reset_strategy,
            "error_summary": last_error,
        }
        try:
            with open(flash_json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
        except Exception:
            pass

    return ok
