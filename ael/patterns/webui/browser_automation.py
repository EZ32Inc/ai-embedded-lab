"""
ael.patterns.webui.browser_automation
======================================
Reusable pattern for verifying embedded-device Web UIs using Playwright.

Background
----------
Many embedded systems expose a web interface for configuration and status:
ESP32/ESP8266 httpd, lwIP httpd, Mongoose, custom RTOS servers, etc.
Manually clicking buttons to verify firmware fixes is slow and unreliable.
This pattern provides a programmatic browser that can:

  - Handle self-signed HTTPS certificates
  - Send HTTP Basic Auth credentials
  - Navigate tabs/accordions to expose hidden elements
  - Click buttons and assert resulting DOM state changes
  - Capture WebSocket traffic and dynamic text output
  - Detect alert/confirm dialogs
  - Adapt to actual device state instead of hardcoded assumptions

CE Experience ID: 747fdb40-7ceb-4ec7-ad9c-85cf8bf0486d  (scope=pattern)

Installation
------------
  pip install playwright requests urllib3
  playwright install chromium

Usage
-----
Typical test script structure:

    from ael.patterns.webui.browser_automation import (
        make_browser_context,
        find_hidden_ancestor,
        check,
        print_results,
    )

    DEVICE_URL = "https://192.168.x.x"
    USER, PASS = "admin", "admin"

    results = []
    with make_browser_context(DEVICE_URL, USER, PASS) as (page, dialogs):
        # 1. Reveal hidden section (tab, accordion)
        page.locator("#some-tab").click()
        page.wait_for_timeout(300)

        # 2. Assert initial state
        check(results, "Button enabled at start", page.locator("#go-btn").is_enabled())

        # 3. Click and wait for async/WS op
        page.locator("#go-btn").click()
        page.wait_for_timeout(1500)

        # 4. Assert post-action state
        check(results, "Button disabled while active", page.locator("#go-btn").is_disabled())
        check(results, "Output contains expected text",
              "OK" in page.locator("#output").inner_text())

    print_results(results)

Debugging
---------
If an element is not found or not visible, use debug_visibility() to find the
hidden ancestor whose display=none is blocking interaction.
"""

from contextlib import contextmanager
from typing import Optional

# ---------------------------------------------------------------------------
# Optional import guard — Playwright may not be installed in all environments
# ---------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

@contextmanager
def make_browser_context(base_url: str, username: str, password: str,
                          viewport_width: int = 1280, viewport_height: int = 900):
    """
    Context manager that launches a headless Chromium browser configured for
    typical embedded-device web servers:
      - Ignores self-signed TLS certificates
      - Sends HTTP Basic Auth on every request
      - Captures console errors and alert dialogs

    Yields: (page, dialog_messages)
      page            — Playwright Page object
      dialog_messages — list that accumulates any alert/confirm/prompt text

    Example:
        with make_browser_context("https://192.168.1.1", "admin", "admin") as (page, dialogs):
            page.goto("/")
            page.locator("#my-button").click()
    """
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    dialog_messages: list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--ignore-certificate-errors", "--no-sandbox"]
        )
        context = browser.new_context(
            ignore_https_errors=True,
            http_credentials={"username": username, "password": password},
            viewport={"width": viewport_width, "height": viewport_height},
        )
        page = context.new_page()

        # Capture browser-side errors for debugging
        page.on("console",
                lambda m: print(f"  [browser:{m.type}] {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: print(f"  [pageerror] {e}"))

        # Auto-accept dialogs and record their messages
        def _on_dialog(dialog):
            dialog_messages.append(dialog.message)
            dialog.accept()
        page.on("dialog", _on_dialog)

        try:
            yield page, dialog_messages
        finally:
            browser.close()


def fetch_device_state(base_url: str, username: str, password: str,
                        path: str = "/api/config") -> Optional[dict]:
    """
    Fetch device configuration via REST before running UI tests.
    Returns parsed JSON dict, or None on failure.

    Use this to make tests adaptive — skip branches that don't apply to the
    current device state instead of hardcoding assumptions.

    Example:
        cfg = fetch_device_state(DEVICE_URL, USER, PASS, "/api/settings")
        uart_mode_active = cfg and cfg.get("port_b") == "uart"
    """
    try:
        import requests
        import urllib3
        urllib3.disable_warnings()
        r = requests.get(f"{base_url}{path}", auth=(username, password),
                         verify=False, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [warn] fetch_device_state({path}) failed: {e}")
        return None


def debug_visibility(page, selector: str) -> list:
    """
    Walk the DOM ancestor chain of *selector* and return computed style info
    for each node. Use this to identify which ancestor has display:none when
    an element is unexpectedly invisible.

    Returns list of dicts: [{tag, id, display, visibility, height}, ...]

    Example:
        styles = debug_visibility(page, "#my-button")
        for s in styles:
            print(s)
        # Look for the entry with display='none' — that is the container to expand first.
    """
    js = (
        'el => { let n = el, out = []; '
        'while (n && n !== document.body) { '
        'const cs = window.getComputedStyle(n); '
        'out.push({tag: n.tagName, id: n.id, cls: n.className, '
        'display: cs.display, visibility: cs.visibility, height: cs.height}); '
        'n = n.parentElement; } return out; }'
    )
    return page.eval_on_selector(selector, js)


def list_buttons(page) -> list:
    """
    Return [{id, text}] for all <button> elements on the current page.
    Use this when you don't know the correct selector for a button.

    Example:
        for b in list_buttons(page):
            print(b)
    """
    buttons = []
    for b in page.locator("button").all():
        try:
            buttons.append({
                "id": b.get_attribute("id"),
                "text": b.inner_text(timeout=500).strip(),
            })
        except Exception:
            pass
    return buttons


# ---------------------------------------------------------------------------
# Test result helpers
# ---------------------------------------------------------------------------

def check(results: list, name: str, passed: bool, info: str = "") -> bool:
    """
    Record a test result and print it immediately.
    Returns the passed value so it can be used in compound assertions.

    Example:
        check(results, "Button enabled at start", btn.is_enabled())
    """
    mark = "✓" if passed else "✗"
    suffix = f" ({info})" if info else ""
    print(f"  {mark}  {name}{suffix}")
    results.append((name, passed))
    return passed


def skip(name: str, reason: str = "") -> None:
    """Print a skipped test (no result recorded — skip does not count as fail)."""
    print(f"  –  [SKIP] {name}" + (f" — {reason}" if reason else ""))


def print_results(results: list) -> bool:
    """
    Print summary and return True if all tests passed.

    Example:
        ok = print_results(results)
        sys.exit(0 if ok else 1)
    """
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"\n{'=' * 50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"  {'PASS' if failed == 0 else 'FAIL'}")
    return failed == 0
