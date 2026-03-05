from datetime import datetime


def notify(event: dict, cfg: dict) -> None:
    ts = datetime.now().isoformat()
    summary = event.get("summary") or event.get("type")
    print(f"Notify[{ts}]: {summary}")
