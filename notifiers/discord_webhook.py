import json
import os
import subprocess
from datetime import datetime


def _tail_lines(path, max_lines):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        if max_lines <= 0:
            return []
        return lines[-max_lines:]
    except Exception:
        return []


def _format_title(event):
    status = "❌" if event.get("severity") == "error" else "✅"
    dut = event.get("dut", "unknown")
    run_id = event.get("run_id", "")
    return f"{status} {dut} {run_id}".strip()


def _format_lines(event, log_tails):
    lines = []
    lines.append(_format_title(event))
    lines.append(f"type: {event.get('type', '')}")
    if event.get("step"):
        lines.append(f"step: {event.get('step')}")
    if event.get("summary"):
        lines.append(f"summary: {event.get('summary')}")
    if event.get("details"):
        lines.append(f"details: {event.get('details')}")
    if event.get("artifacts_path"):
        lines.append(f"artifacts: {event.get('artifacts_path')}")

    for name, tail in log_tails.items():
        if not tail:
            continue
        lines.append(f"{name} tail:")
        lines.extend(tail)

    return lines


def _format_message(event, cfg, log_tails):
    mention = cfg.get("mention", "") or ""
    lines = _format_lines(event, log_tails)
    content = "\n".join(lines)
    if mention:
        content = f"{mention}\n{content}"
    # Discord content limit is 2000 chars. Keep a safe margin.
    if len(content) > 1900:
        content = content[:1890] + "\n...[truncated]"
    return content


def _should_notify(event_type, cfg):
    notify_on = cfg.get("notify_on") or ["run_failed", "need_input"]
    include_success = bool(cfg.get("include_success", False))
    if event_type == "run_succeeded" and include_success:
        return True
    return event_type in notify_on


def notify(event: dict, cfg: dict) -> None:
    discord = (cfg or {}).get("discord", {}) if isinstance(cfg, dict) else {}
    if not discord.get("enabled"):
        return
    webhook_url = discord.get("webhook_url")
    if not webhook_url:
        return
    event_type = event.get("type", "")
    if not _should_notify(event_type, discord):
        return

    max_log_lines = int(discord.get("max_log_lines", 20))
    log_tails = {}
    log_paths = event.get("log_paths", {}) if isinstance(event.get("log_paths"), dict) else {}
    for key in ("uart", "observe", "flash", "build", "verify", "preflight"):
        path = log_paths.get(key)
        if path and os.path.exists(path):
            log_tails[key] = _tail_lines(path, max_log_lines)

    payload = {"content": _format_message(event, discord, log_tails)}

    try:
        data = json.dumps(payload)
        res = subprocess.run(
            [
                "curl",
                "-sS",
                "-w",
                "%{http_code}",
                "-H",
                "Content-Type: application/json",
                "-H",
                "User-Agent: AEL/1.0",
                "--data",
                data,
                webhook_url,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or "curl failed")
        if res.stdout and res.stdout.strip() not in ("200", "204"):
            raise RuntimeError(f"discord http {res.stdout.strip()}")
    except Exception as exc:  # pragma: no cover - network dependent
        ts = datetime.now().isoformat()
        print(f"Notify: Discord webhook failed at {ts}: {exc}")
