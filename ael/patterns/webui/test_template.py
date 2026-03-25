#!/usr/bin/env python3
"""
Embedded Web UI Browser Automation — Reusable Test Template
============================================================
Copy this file, fill in the CONFIGURATION block, then implement
the test cases in the TESTS block.

Pattern source: CE 747fdb40 (scope=pattern, HIGH_PRIORITY)
Helper module : ael.patterns.webui.browser_automation

Usage:
    cp test_template.py test_<device_name>_webui.py
    # Fill in CONFIGURATION and TESTS sections
    python3 test_<device_name>_webui.py
"""

import sys
sys.path.insert(0, '/nvme1t/work/codex/ai-embedded-lab')

from ael.patterns.webui.browser_automation import (
    make_browser_context,
    fetch_device_state,
    debug_visibility,
    list_buttons,
    check,
    skip,
    print_results,
)

# ===========================================================================
# CONFIGURATION — fill in for each device/project
# ===========================================================================

DEVICE_URL = "https://<device-ip>"   # e.g. "https://192.168.x.x"
USERNAME   = "<username>"             # e.g. "admin"
PASSWORD   = "<password>"             # e.g. "admin"

# API path that returns device configuration as JSON (used for adaptive tests)
# Set to None if the device has no config API
CONFIG_API_PATH = "/api/<config-endpoint>"   # e.g. "/api/settings", "/get_config"

# CSS selector of the tab/section that contains the UI under test.
# Set to None if the target UI is visible without clicking a tab.
TAB_SELECTOR = "#<tab-id>"    # e.g. "#uart-tab", "#debug-tab", None

# ===========================================================================
# DEVICE STATE — populated at runtime from CONFIG_API_PATH
# ===========================================================================

device_cfg = None   # dict or None if API unavailable


# ===========================================================================
# TESTS — implement one function per logical test group
# ===========================================================================

def test_initial_state(page, results):
    """
    Verify the UI is in the correct initial state before any interaction.
    Common checks: correct buttons enabled/disabled, labels present, etc.
    """
    # REPLACE with your device's actual selectors and expected initial state:
    # check(results, "Primary action button enabled",
    #       page.locator("#<action-btn>").is_enabled())
    # check(results, "Secondary button disabled",
    #       page.locator("#<secondary-btn>").is_disabled())
    pass


def test_action_and_state_change(page, results, dialogs):
    """
    Click a button/toggle, wait for async/WS operation, assert DOM state changed.
    """
    # --- Prerequisite guard (example) ---
    # Some actions require a specific device config.
    # Use device_cfg to decide whether this test applies.
    #
    # required_mode = "<mode-key>"
    # if device_cfg and device_cfg.get("<config-key>") != required_mode:
    #     skip("Action test", f"device not in {required_mode} mode")
    #     return

    # REPLACE with your device's action and expected outcome:
    # page.locator("#<action-btn>").click()
    # page.wait_for_timeout(1500)   # wait for async/WS op
    #
    # check(results, "Action button disabled after click",
    #       page.locator("#<action-btn>").is_disabled())
    # check(results, "Related control enabled",
    #       page.locator("#<related-btn>").is_enabled())
    pass


def test_output_content(page, results):
    """
    Assert that a dynamic output area (terminal, log, status div) contains
    expected text after an action.
    """
    # REPLACE with your device's output selector and expected content:
    # text = page.locator("#<output-div>").inner_text()
    # check(results, "Output shows expected status",
    #       "<expected string>" in text,
    #       info=repr(text[:80]))
    pass


def test_alert_on_invalid_action(page, results, dialogs):
    """
    Verify that attempting an invalid action triggers a browser alert.
    Only run if device state makes the invalid action possible.
    """
    # REPLACE with your device's invalid-action scenario:
    # if device_cfg and device_cfg.get("<config-key>") == "<valid-value>":
    #     skip("Invalid action alert", "device already in valid state")
    #     return
    #
    # dialogs.clear()
    # page.locator("#<action-btn>").click()
    # page.wait_for_timeout(300)
    # check(results, "Alert fired for invalid action", len(dialogs) > 0)
    # check(results, "Button re-enabled after alert dismiss",
    #       page.locator("#<action-btn>").is_enabled())
    pass


def test_recovery(page, results):
    """
    After an active state (connection open, operation running), verify
    that stopping/disconnecting restores the initial UI state.
    """
    # REPLACE with your device's recovery scenario:
    # page.locator("#<stop-btn>").click()
    # page.wait_for_timeout(500)
    # check(results, "Action button re-enabled after stop",
    #       page.locator("#<action-btn>").is_enabled())
    # check(results, "Stop button disabled after stop",
    #       page.locator("#<stop-btn>").is_disabled())
    pass


# ===========================================================================
# RUNNER — do not modify
# ===========================================================================

def run():
    global device_cfg

    print(f"\n  Target : {DEVICE_URL}")

    # 1. Fetch device state for adaptive tests
    if CONFIG_API_PATH:
        device_cfg = fetch_device_state(DEVICE_URL, USERNAME, PASSWORD, CONFIG_API_PATH)
        print(f"  Config : {device_cfg}")
    print()

    results = []

    with make_browser_context(DEVICE_URL, USERNAME, PASSWORD) as (page, dialogs):
        page.goto(DEVICE_URL, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(500)

        # Reveal hidden tab/section if needed
        if TAB_SELECTOR:
            page.locator(TAB_SELECTOR).click()
            page.wait_for_timeout(300)

        # Run test groups
        test_initial_state(page, results)
        test_action_and_state_change(page, results, dialogs)
        test_output_content(page, results)
        test_alert_on_invalid_action(page, results, dialogs)
        test_recovery(page, results)

    return print_results(results)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
