import argparse
import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ael.pipeline import run_cli, run_pipeline, _simple_yaml_load, _normalize_probe_cfg
from ael import assets
from ael.doctor_checks import la_capture_ok, monitor_version, validate_config
from ael import run_manager
from ael.config_resolver import (
    resolve_board_config,
    resolve_control_instrument_config,
    resolve_doctor_required_tools,
)
from ael.probe_binding import load_probe_binding
from ael.default_verification import (
    DEFAULT_CONFIG_PATH as DEFAULT_VERIFY_CONFIG_PATH,
    load_setting as load_default_verification_setting,
    preset_payload as default_verification_preset_payload,
    run_until_fail as run_default_until_fail,
    run_default_setting,
    save_setting as save_default_verification_setting,
)
from ael import workflow_archive
from ael import hw_check
from ael import la_check
from ael import inventory
from ael import instrument_doctor
from ael import instrument_view
from ael import connection_doctor
from ael import stage_explain


def main():
    parser = argparse.ArgumentParser(prog="ael")
    # Follow docs/AI_USAGE_RULES.md: CLI is a deterministic control interface for AI agents.
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--test", required=False)
    run_p.add_argument("--pack", required=False)
    run_p.add_argument("--board", required=False, help="Board id")
    run_p.add_argument("--dut", required=False, help="DUT id from assets_golden/assets_user")
    run_p.add_argument("--control-instrument", dest="control_instrument", required=False, default=None, help="Control instrument config")
    run_p.add_argument("--probe", required=False, default=None, help="Legacy compatibility flag for --control-instrument")
    run_p.add_argument("--wiring", required=False)
    run_p.add_argument("--bench", required=False, help="Bench id (placeholder, not used)")
    run_p.add_argument("--project", required=False, default=None, help="Project id to gate-check before running")
    run_p.add_argument("--projects-root", dest="run_projects_root", default="projects", help="Root directory for projects")
    run_p.add_argument(
        "--until-stage",
        required=False,
        default="report",
        help="Stop after stage: plan, pre-flight, run, run-exit, or report (default full flow).",
    )
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    doc_p = sub.add_parser("doctor")
    doc_p.add_argument("--control-instrument", dest="control_instrument", default=None, help="Control instrument config")
    doc_p.add_argument("--probe", default=None, help="Legacy compatibility flag for --control-instrument")
    doc_p.add_argument("--board", default=None)
    doc_p.add_argument("--test", default=os.path.join("tests", "blink_gpio.json"))

    pack_p = sub.add_parser("pack")
    pack_p.add_argument("--pack", required=False)
    pack_p.add_argument("--board", required=False)
    pack_p.add_argument("--dut", required=False)
    pack_p.add_argument("--bench", required=False, help="Bench id (placeholder, not used)")
    pack_p.add_argument("--stop-on-fail", action="store_true")
    pack_p.add_argument("--no-flash", action="store_true")
    pack_p.add_argument("--no-build", action="store_true")
    pack_p.add_argument("--verify-only", action="store_true")

    instr_p = sub.add_parser("instruments")
    instr_sub = instr_p.add_subparsers(dest="instr_cmd", required=True)
    instr_list = instr_sub.add_parser("list")
    instr_describe = instr_sub.add_parser("describe")
    instr_describe.add_argument("--id", required=True)
    instr_describe.add_argument("--format", choices=["json", "text", "summary"], default="json")
    instr_show = instr_sub.add_parser("show")
    instr_show.add_argument("id")
    instr_find = instr_sub.add_parser("find")
    instr_find.add_argument("--cap", required=True)
    instr_doctor = instr_sub.add_parser("doctor")
    instr_doctor.add_argument("--id", required=True)
    instr_doctor.add_argument("--format", choices=["json", "text"], default="json")
    instr_wifi_scan = instr_sub.add_parser("wifi-scan")
    instr_wifi_scan.add_argument("--id", required=True)
    instr_wifi_scan.add_argument("--ifname", required=True)
    instr_meter_list = instr_sub.add_parser("meter-list")
    instr_meter_list.add_argument("--id", required=True)
    instr_meter_list.add_argument("--ifname", required=True)
    instr_wifi_connect = instr_sub.add_parser("wifi-connect")
    instr_wifi_connect.add_argument("--id", required=True)
    instr_wifi_connect.add_argument("--ifname", required=True)
    instr_wifi_connect.add_argument("--ssid", default=None)
    instr_wifi_connect.add_argument("--ssid-suffix", default=None)
    instr_meter_setup = instr_sub.add_parser("meter-setup")
    instr_meter_setup.add_argument("--id", required=True)
    instr_meter_setup.add_argument("--port", required=True)
    instr_meter_setup.add_argument("--ifname", required=True)
    instr_meter_setup.add_argument("--ssid", default=None)
    instr_meter_setup.add_argument("--ssid-suffix", default=None)
    instr_meter_setup.add_argument("--timeout-s", type=float, default=30.0)
    instr_meter_setup.add_argument("--interval-s", type=float, default=2.0)
    instr_meter_ping = instr_sub.add_parser("meter-ping")
    instr_meter_ping.add_argument("--id", required=True)
    instr_meter_ping.add_argument("--host", default=None)
    instr_meter_ping.add_argument("--port", type=int, default=None)
    instr_meter_reachability = instr_sub.add_parser("meter-reachability")
    instr_meter_reachability.add_argument("--id", required=True)
    instr_meter_reachability.add_argument("--host", default=None)
    instr_meter_reachability.add_argument("--timeout-s", type=float, default=1.0)
    instr_meter_ready = instr_sub.add_parser("meter-ready")
    instr_meter_ready.add_argument("--id", required=True)
    instr_meter_ready.add_argument("--ifname", required=True)
    instr_meter_ready.add_argument("--ssid", default=None)
    instr_meter_ready.add_argument("--ssid-suffix", default=None)
    instr_meter_ready.add_argument("--host", default=None)
    instr_meter_ready.add_argument("--port", type=int, default=None)

    dut_p = sub.add_parser("dut")
    dut_sub = dut_p.add_subparsers(dest="dut_cmd", required=True)
    dut_create = dut_sub.add_parser("create")
    dut_create.add_argument("--from-golden", required=True)
    dut_create.add_argument("--to", required=True)
    dut_create.add_argument("--dest", choices=["user", "branch"], default="user", help="Destination namespace: user (default) or branch")
    dut_promote = dut_sub.add_parser("promote")
    dut_promote.add_argument("--id", required=True)
    dut_promote.add_argument("--as", dest="as_id", required=False)
    dut_promote.add_argument("--from", dest="from_namespace", choices=["user", "branch"], default="user", help="Source namespace: user (default) or branch")
    dut_promote.add_argument("--delete-source", action="store_true")

    verify_default_p = sub.add_parser("verify-default")
    verify_default_sub = verify_default_p.add_subparsers(dest="verify_default_cmd", required=True)

    verify_default_show = verify_default_sub.add_parser("show")
    verify_default_show.add_argument("--file", default=str(DEFAULT_VERIFY_CONFIG_PATH))

    verify_default_set = verify_default_sub.add_parser("set")
    verify_default_set_group = verify_default_set.add_mutually_exclusive_group(required=True)
    verify_default_set_group.add_argument(
        "--preset",
        choices=["none", "preflight_only", "rp2040_only", "esp32s3_then_rp2040"],
    )
    verify_default_set_group.add_argument("--from-file")
    verify_default_set.add_argument("--file", default=str(DEFAULT_VERIFY_CONFIG_PATH))

    verify_default_run = verify_default_sub.add_parser("run")
    verify_default_run.add_argument("--file", default=str(DEFAULT_VERIFY_CONFIG_PATH))
    verify_default_run.add_argument("--skip-if-docs-only", action="store_true")
    verify_default_run.add_argument("--docs-check-mode", choices=["changed", "staged"], default="changed")

    verify_default_repeat = verify_default_sub.add_parser("repeat-until-fail")
    verify_default_repeat.add_argument("--file", default=str(DEFAULT_VERIFY_CONFIG_PATH))
    verify_default_repeat.add_argument("--limit", type=int, default=10)
    verify_default_repeat.add_argument("--skip-if-docs-only", action="store_true")
    verify_default_repeat.add_argument("--docs-check-mode", choices=["changed", "staged"], default="changed")

    verify_default_repeat_preferred = verify_default_sub.add_parser("repeat")
    verify_default_repeat_preferred.add_argument("--file", default=str(DEFAULT_VERIFY_CONFIG_PATH))
    verify_default_repeat_preferred.add_argument("--limit", type=int, default=10)
    verify_default_repeat_preferred.add_argument("--skip-if-docs-only", action="store_true")
    verify_default_repeat_preferred.add_argument("--docs-check-mode", choices=["changed", "staged"], default="changed")
    verify_default_state = verify_default_sub.add_parser("state", help="show current default verification state object")
    verify_default_state.add_argument("--file", default=str(DEFAULT_VERIFY_CONFIG_PATH))
    verify_default_state.add_argument("--runs-root", default="runs")
    verify_default_state.add_argument("--format", choices=["json", "text"], default="json")

    inventory_p = sub.add_parser("inventory")
    inventory_sub = inventory_p.add_subparsers(dest="inventory_cmd", required=True)
    inventory_list = inventory_sub.add_parser("list")
    inventory_list.add_argument("--format", choices=["json", "text"], default="json")
    inventory_instances = inventory_sub.add_parser("instances")
    inventory_instances.add_argument("--format", choices=["json", "text"], default="json")
    inventory_describe = inventory_sub.add_parser("describe-test")
    inventory_describe.add_argument("--board", required=True)
    inventory_describe.add_argument("--test", required=True)
    inventory_describe.add_argument("--format", choices=["json", "text"], default="json")
    inventory_connection = inventory_sub.add_parser("describe-connection")
    inventory_connection.add_argument("--board", required=True)
    inventory_connection.add_argument("--test", required=True)
    inventory_connection.add_argument("--format", choices=["json", "text"], default="json")
    inventory_connection_diff = inventory_sub.add_parser("diff-connection")
    inventory_connection_diff.add_argument("--board", required=True)
    inventory_connection_diff.add_argument("--test", required=True)
    inventory_connection_diff.add_argument("--against-board", required=True)
    inventory_connection_diff.add_argument("--against-test", required=True)
    inventory_connection_diff.add_argument("--format", choices=["json", "text"], default="json")

    connection_p = sub.add_parser("connection")
    connection_sub = connection_p.add_subparsers(dest="connection_cmd", required=True)
    connection_doctor_p = connection_sub.add_parser("doctor")
    connection_doctor_p.add_argument("--board", required=True)
    connection_doctor_p.add_argument("--test", required=True)
    connection_doctor_p.add_argument("--format", choices=["json", "text"], default="json")

    explain_p = sub.add_parser("explain-stage")
    explain_p.add_argument("--board", required=True)
    explain_p.add_argument("--test", required=True)
    explain_p.add_argument("--stage", required=True, choices=["plan", "pre-flight", "preflight", "run", "check"])
    explain_p.add_argument("--format", choices=["json", "text"], default="json")

    archive_p = sub.add_parser("workflow-archive")
    archive_sub = archive_p.add_subparsers(dest="archive_cmd", required=True)
    archive_show = archive_sub.add_parser("show")
    archive_show.add_argument("--limit", type=int, default=20)
    archive_show.add_argument("--run-id", default=None)
    archive_show.add_argument("--source", default="global", help="global or a path to a JSONL archive file")

    hw_check_p = sub.add_parser("hw-check")
    hw_check_p.add_argument("--board", required=True)
    hw_check_p.add_argument("--port", required=True)
    hw_check_p.add_argument("--expect-pattern", default=None)
    hw_check_p.add_argument("--samples", type=int, default=5)
    hw_check_p.add_argument("--interval-s", type=float, default=1.0)
    hw_check_p.add_argument("--boot-timeout-s", type=float, default=8.0)

    la_check_p = sub.add_parser("la-check")
    la_check_p.add_argument("--pin", required=True)
    la_check_p.add_argument("--board", required=False, help="Board id used to resolve default control instrument")
    la_check_p.add_argument("--control-instrument", dest="control_instrument", required=False, default=None, help="Control instrument config")
    la_check_p.add_argument("--probe", required=False, default=None, help="Legacy compatibility flag for --control-instrument")
    la_check_p.add_argument("--duration-s", type=float, default=1.0)
    la_check_p.add_argument("--expected-hz", type=float, default=1.0)
    la_check_p.add_argument("--min-edges", type=int, default=1)

    board_p = sub.add_parser("board", help="board/capability state")
    board_sub = board_p.add_subparsers(dest="board_cmd", required=True)
    board_state_p = board_sub.add_parser("state", help="show capability state for a board")
    board_state_p.add_argument("board_id")
    board_state_p.add_argument("--runs-root", default="runs")
    board_state_p.add_argument("--format", choices=["json", "text"], default="json")

    project_p = sub.add_parser("project", help="user project management")
    project_sub = project_p.add_subparsers(dest="project_cmd", required=True)
    project_list_p = project_sub.add_parser("list", help="list all user projects")
    project_list_p.add_argument("--projects-root", default="projects")
    project_status_p = project_sub.add_parser("status", help="show status of one user project")
    project_status_p.add_argument("project_id")
    project_status_p.add_argument("--projects-root", default="projects")
    project_update_p = project_sub.add_parser("update", help="update project.yaml fields")
    project_update_p.add_argument("project_id")
    project_update_p.add_argument("--projects-root", default="projects")
    project_update_p.add_argument("--set-status", default=None)
    project_update_p.add_argument("--set-blocker", default=None)
    project_update_p.add_argument("--set-next-action", default=None)
    project_update_p.add_argument("--set-last-action", default=None)
    project_update_p.add_argument("--append-confirmed-fact", default=None)
    project_update_p.add_argument("--resolve-unresolved", default=None, metavar="ITEM",
                                  help="Remove matching entry from unresolved_items")
    project_note_p = project_sub.add_parser("append-note", help="append a note to session_notes.md")
    project_note_p.add_argument("project_id")
    project_note_p.add_argument("text")
    project_note_p.add_argument("--projects-root", default="projects")
    project_questions_p = project_sub.add_parser("questions", help="show guided next questions for a project")
    project_questions_p.add_argument("project_id")
    project_questions_p.add_argument("--projects-root", default="projects")
    project_create_p = project_sub.add_parser("create", help="create a new user project shell")
    project_create_p.add_argument("--target-mcu", required=True)
    project_create_p.add_argument("--project-id", default=None)
    project_create_p.add_argument("--project-name", default=None)
    project_create_p.add_argument("--user-goal", default=None)
    project_create_p.add_argument("--project-user", default="local_user")
    project_create_p.add_argument("--mature-path", default=None)
    project_create_p.add_argument("--projects-root", default="projects")
    project_link_run_p = project_sub.add_parser("link-run", help="link a completed run to a project and update state")
    project_link_run_p.add_argument("project_id")
    project_link_run_p.add_argument("run_id")
    project_link_run_p.add_argument("--projects-root", default="projects")
    project_link_run_p.add_argument("--runs-root", default="runs")
    project_run_gate_p = project_sub.add_parser("run-gate", help="check if a project is safe to proceed with a run")
    project_run_gate_p.add_argument("project_id")
    project_run_gate_p.add_argument("--projects-root", default="projects")

    args = parser.parse_args()
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if args.cmd == "run":
        if getattr(args, "project", None):
            project_dir = Path(getattr(args, "run_projects_root", "projects")) / args.project
            project_payload = _project_yaml_load(project_dir / "project.yaml")
            if not project_payload:
                print(f"run-gate error: project not found: {project_dir / 'project.yaml'}")
                sys.exit(2)
            gate_ok, gate_reasons, gate_clarifications, gate_readiness = _project_run_gate_check(project_payload)
            path_maturity = str(project_payload.get("path_maturity", "mature")).strip()
            status = str(project_payload.get("status", "")).strip()
            _print_run_gate_result(gate_ok, gate_reasons, gate_clarifications, gate_readiness, args.project, path_maturity, status)
            if not gate_ok:
                sys.exit(1)
        if args.verbose:
            output_mode = "verbose"
        elif args.quiet:
            output_mode = "quiet"
        else:
            output_mode = "normal"
        board_id = args.board
        test_path = args.test
        pack_path = args.pack
        if args.dut:
            dut = assets.load_dut_prefer_user(args.dut)
            if not dut:
                print(f"DUT not found: {args.dut}")
                sys.exit(2)
            dut_path = Path(dut["path"])
            manifest = dut.get("manifest") if isinstance(dut, dict) else {}
            if not board_id:
                candidate = Path("configs") / "boards" / f"{args.dut}.yaml"
                if candidate.exists():
                    board_id = args.dut
            if test_path and not os.path.isabs(test_path):
                dut_test = dut_path / "tests" / test_path
                if dut_test.exists():
                    test_path = str(dut_test)
            if pack_path and not os.path.isabs(pack_path):
                dut_pack = dut_path / "packs" / pack_path
                if dut_pack.exists():
                    pack_path = str(dut_pack)
            if not test_path and not pack_path:
                default_packs = []
                if isinstance(manifest, dict):
                    default_packs = manifest.get("default_packs", []) or []
                if default_packs:
                    pack_path = default_packs[0]
                else:
                    dut_packs_dir = dut_path / "packs"
                    if dut_packs_dir.exists():
                        packs = sorted([p for p in dut_packs_dir.glob("*.json")])
                        if packs:
                            pack_path = str(packs[0])
                    dut_tests_dir = dut_path / "tests"
                    if not pack_path and dut_tests_dir.exists():
                        tests = sorted([t for t in dut_tests_dir.glob("*.json")])
                        if tests:
                            test_path = str(tests[0])
            if not test_path and not pack_path:
                print("DUT has no tests or packs. Provide --test or --pack.")
                sys.exit(2)
            if pack_path:
                code = run_pack(
                    pack_path=pack_path,
                    board_override=board_id,
                    stop_on_fail=False,
                    no_flash=False,
                    no_build=False,
                    verify_only=False,
                )
                sys.exit(code)
        explicit_control = getattr(args, "control_instrument", None) or getattr(args, "probe", None)
        probe_path = None
        if explicit_control:
            probe_path = resolve_control_instrument_config(repo_root, args, board_id=board_id)
        if not test_path and not pack_path:
            print("Provide --test or --pack (or use --dut with defaults).")
            sys.exit(2)
        code = run_cli(
            probe_path=probe_path,
            board_id=board_id,
            test_path=test_path,
            wiring=args.wiring,
            output_mode=output_mode,
            until_stage=args.until_stage,
        )
        sys.exit(code)
    if args.cmd == "doctor":
        doc_probe = resolve_control_instrument_config(repo_root, args, pack_meta={"mode": "doctor"})
        doc_board = resolve_board_config(repo_root, args, pack_meta={"mode": "doctor"})
        code = run_doctor(doc_probe, doc_board, args.test)
        sys.exit(code)
    if args.cmd == "instruments":
        from ael.adapters import esp32s3_dev_c_meter_tcp
        from ael.instruments.registry import InstrumentRegistry
        from ael.instruments import provision as instrument_provision
        from ael.instruments import wifi as instrument_wifi

        registry = InstrumentRegistry()
        if args.instr_cmd == "list":
            print(json.dumps(registry.list(), indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "describe":
            payload = instrument_view.build_resolved_instrument_view(Path(repo_root), args.id)
            if args.format == "text":
                print(instrument_view.render_resolved_instrument_text(payload), end="")
            elif args.format == "summary":
                print(instrument_view.render_resolved_instrument_summary_text(payload), end="")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0 if payload.get("ok") else 1)
        if args.instr_cmd == "show":
            inst = registry.get(args.id)
            if not inst:
                print(f"Instrument not found: {args.id}")
                sys.exit(2)
            print(json.dumps(inst, indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "find":
            matches = registry.find_by_capability(args.cap)
            print(json.dumps(matches, indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "doctor":
            payload = instrument_doctor.doctor(repo_root, args.id)
            if args.format == "text":
                print(instrument_view.render_doctor_text(payload), end="")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0 if payload.get("ok") else 1)
        if args.instr_cmd == "wifi-scan":
            inst = registry.get(args.id)
            if not inst:
                print(json.dumps({"ok": False, "error": f"Instrument not found: {args.id}"}, indent=2, sort_keys=True))
                sys.exit(2)
            try:
                payload = instrument_wifi.scan(ifname=args.ifname, manifest=inst)
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
                sys.exit(1)
            instrument_wifi.print_json(payload)
            sys.exit(0)
        if args.instr_cmd == "meter-list":
            inst = registry.get(args.id)
            if not inst:
                print(json.dumps({"ok": False, "error": f"Instrument not found: {args.id}"}, indent=2, sort_keys=True))
                sys.exit(2)
            try:
                payload = instrument_wifi.meter_list_report(ifname=args.ifname, manifest=inst)
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
                sys.exit(1)
            instrument_wifi.print_json(payload)
            sys.exit(0)
        if args.instr_cmd == "wifi-connect":
            inst = registry.get(args.id)
            if not inst:
                print(json.dumps({"ok": False, "error": f"Instrument not found: {args.id}"}, indent=2, sort_keys=True))
                sys.exit(2)
            try:
                payload = instrument_wifi.connect(
                    ifname=args.ifname,
                    manifest=inst,
                    ssid=args.ssid,
                    ssid_suffix=args.ssid_suffix,
                )
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
                sys.exit(1)
            instrument_wifi.print_json(payload)
            sys.exit(0)
        if args.instr_cmd == "meter-setup":
            inst = registry.get(args.id)
            if not inst:
                print(json.dumps({"ok": False, "error": f"Instrument not found: {args.id}"}, indent=2, sort_keys=True))
                sys.exit(2)
            try:
                payload = instrument_provision.flash_wait_connect(
                    port=args.port,
                    ifname=args.ifname,
                    manifest=inst,
                    ssid=args.ssid,
                    ssid_suffix=args.ssid_suffix,
                    timeout_s=args.timeout_s,
                    interval_s=args.interval_s,
                )
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
                sys.exit(1)
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "meter-ping":
            inst = registry.get(args.id)
            if not inst:
                print(json.dumps({"ok": False, "error": f"Instrument not found: {args.id}"}, indent=2, sort_keys=True))
                sys.exit(2)
            wifi_cfg = inst.get("wifi") if isinstance(inst.get("wifi"), dict) else {}
            cfg = {
                "host": args.host or wifi_cfg.get("ap_ip") or "192.168.4.1",
                "port": args.port or wifi_cfg.get("tcp_port") or 9000,
            }
            try:
                payload = esp32s3_dev_c_meter_tcp.ping(cfg)
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc), "host": cfg["host"], "port": cfg["port"]}, indent=2, sort_keys=True))
                sys.exit(1)
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "meter-reachability":
            inst = registry.get(args.id)
            if not inst:
                print(json.dumps({"ok": False, "error": f"Instrument not found: {args.id}"}, indent=2, sort_keys=True))
                sys.exit(2)
            try:
                payload = instrument_provision.ensure_meter_reachable(
                    manifest=inst,
                    host=args.host,
                    timeout_s=args.timeout_s,
                )
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc), "host": args.host}, indent=2, sort_keys=True))
                sys.exit(1)
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "meter-ready":
            inst = registry.get(args.id)
            if not inst:
                print(json.dumps({"ok": False, "error": f"Instrument not found: {args.id}"}, indent=2, sort_keys=True))
                sys.exit(2)
            try:
                payload = instrument_provision.ready_meter(
                    ifname=args.ifname,
                    manifest=inst,
                    ssid=args.ssid,
                    ssid_suffix=args.ssid_suffix,
                    host=args.host,
                    port=args.port,
                )
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
                sys.exit(1)
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
    if args.cmd == "pack":
        board_override = args.board
        if args.dut:
            dut = assets.load_dut_prefer_user(args.dut)
            if not dut:
                print(f"DUT not found: {args.dut}")
                sys.exit(2)
            if not board_override:
                candidate = Path("configs") / "boards" / f"{args.dut}.yaml"
                if candidate.exists():
                    board_override = args.dut
            if args.pack and not os.path.isabs(args.pack):
                dut_pack = Path(dut["path"]) / "packs" / args.pack
                if dut_pack.exists():
                    args.pack = str(dut_pack)
            if not args.pack:
                manifest = dut.get("manifest") if isinstance(dut, dict) else {}
                default_packs = manifest.get("default_packs", []) if isinstance(manifest, dict) else []
                if default_packs:
                    args.pack = default_packs[0]
                else:
                    dut_packs_dir = Path(dut["path"]) / "packs"
                    if dut_packs_dir.exists():
                        packs = sorted([p for p in dut_packs_dir.glob("*.json")])
                        if packs:
                            args.pack = str(packs[0])
            if not args.pack:
                print("DUT has no packs. Provide --pack.")
                sys.exit(2)
        code = run_pack(
            pack_path=args.pack,
            board_override=board_override,
            stop_on_fail=args.stop_on_fail,
            no_flash=args.no_flash,
            no_build=args.no_build,
            verify_only=args.verify_only,
        )
        sys.exit(code)
    if args.cmd == "inventory":
        if args.inventory_cmd == "list":
            payload = inventory.build_inventory(Path(repo_root))
            if args.format == "text":
                print(inventory.render_text(payload), end="")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
        if args.inventory_cmd == "instances":
            payload = inventory.build_instrument_instance_inventory(Path(repo_root))
            if args.format == "text":
                print(inventory.render_instance_text(payload), end="")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
        if args.inventory_cmd == "describe-test":
            payload = inventory.describe_test(board_id=args.board, test_path=args.test, repo_root=Path(repo_root))
            if args.format == "text":
                print(inventory.render_describe_text(payload), end="")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0 if payload.get("ok") else 1)
        if args.inventory_cmd == "describe-connection":
            payload = inventory.describe_connection(board_id=args.board, test_path=args.test, repo_root=Path(repo_root))
            if args.format == "text":
                print(inventory.render_connection_text(payload), end="")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0 if payload.get("ok") else 1)
        if args.inventory_cmd == "diff-connection":
            payload = inventory.diff_connection(
                board_id=args.board,
                test_path=args.test,
                against_board=args.against_board,
                against_test=args.against_test,
                repo_root=Path(repo_root),
            )
            if args.format == "text":
                print(inventory.render_connection_diff_text(payload), end="")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0 if payload.get("ok") else 1)
    if args.cmd == "explain-stage":
        payload = stage_explain.explain_stage(board_id=args.board, test_path=args.test, stage=args.stage, repo_root=Path(repo_root))
        if args.format == "text":
            print(stage_explain.render_text(payload), end="")
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        sys.exit(0 if payload.get("ok") else 1)
    if args.cmd == "connection":
        if args.connection_cmd == "doctor":
            payload = connection_doctor.doctor(board_id=args.board, test_path=args.test, repo_root=Path(repo_root))
            if args.format == "text":
                print(inventory.render_connection_text(payload), end="")
                checks = payload.get("consistency_checks") or []
                if checks:
                    print("consistency_checks:")
                    for item in checks:
                        print(f"  - {item.get('name')}: ok={item.get('ok')} detail={item.get('detail')}")
                if payload.get("validation_errors"):
                    print("validation_errors:")
                    for item in payload.get("validation_errors") or []:
                        print(f"  - {item}")
            else:
                print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0 if payload.get("ok") else 1)
    if args.cmd == "workflow-archive":
        if args.archive_cmd == "show":
            records = workflow_archive.read_events(limit=args.limit, run_id=args.run_id, source=args.source)
            print(json.dumps(records, indent=2, sort_keys=True))
            sys.exit(0)
    if args.cmd == "hw-check":
        try:
            payload = hw_check.run(
                board=args.board,
                port=args.port,
                expect_pattern=args.expect_pattern,
                samples=args.samples,
                interval_s=args.interval_s,
                boot_timeout_s=args.boot_timeout_s,
            )
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
            sys.exit(1)
        print(json.dumps(payload, indent=2, sort_keys=True))
        sys.exit(0 if payload.get("ok") else 1)
    if args.cmd == "la-check":
        try:
            payload = la_check.run(
                pin=args.pin,
                board=args.board,
                probe=args.control_instrument or args.probe,
                duration_s=args.duration_s,
                expected_hz=args.expected_hz,
                min_edges=args.min_edges,
            )
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
            sys.exit(1)
        print(json.dumps(payload, indent=2, sort_keys=True))
        sys.exit(0 if payload.get("toggling") else 1)
    if args.cmd == "dut":
        if args.dut_cmd == "create":
            code = dut_create_cmd(args.from_golden, args.to, dest=args.dest)
            sys.exit(code)
        if args.dut_cmd == "promote":
            code = dut_promote_cmd(args.id, args.as_id, args.delete_source, from_namespace=args.from_namespace)
            sys.exit(code)
    if args.cmd == "board":
        if args.board_cmd == "state":
            state = _board_state(args.board_id, args.runs_root)
            if args.format == "text":
                print(f"board_id: {state['board_id']}")
                print(f"board_name: {state['board_name']}")
                print(f"health_status: {state['health_status']}")
                print(f"current_blocker: {state['current_blocker'] or 'none'}")
                print(f"next_recommended_action: {state['next_recommended_action']}")
                if state["last_successful_run"]:
                    r = state["last_successful_run"]
                    print(f"last_successful_run: {r.get('test','')} ({r.get('run_id','')})")
                if state["validated_tests"]:
                    print("validated_tests:")
                    for t in state["validated_tests"]:
                        print(f"  - {t}")
                if state["failing_tests"]:
                    print("failing_tests:")
                    for t in state["failing_tests"]:
                        print(f"  - {t}")
            else:
                print(json.dumps(state, indent=2, sort_keys=True))
            health = state["health_status"]
            sys.exit(0 if health in ("pass", "partial_pass") else 1)
    if args.cmd == "project":
        sys.exit(_project_cmd(args))
    if args.cmd == "verify-default":
        if args.verify_default_cmd == "show":
            payload = load_default_verification_setting(args.file)
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
        if args.verify_default_cmd == "set":
            if args.preset:
                payload = default_verification_preset_payload(args.preset)
            else:
                src_path = Path(args.from_file)
                payload = load_default_verification_setting(str(src_path))
            save_default_verification_setting(payload, args.file)
            print(f"default_verification_setting updated: {args.file}")
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(0)
        if args.verify_default_cmd == "run":
            code, payload = run_default_setting(
                path=args.file,
                output_mode="normal",
                skip_if_docs_only=bool(args.skip_if_docs_only),
                docs_check_mode=str(args.docs_check_mode),
            )
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(int(code))
        if args.verify_default_cmd in ("repeat-until-fail", "repeat"):
            code, payload = run_default_until_fail(
                limit=int(args.limit),
                path=args.file,
                output_mode="normal",
                skip_if_docs_only=bool(args.skip_if_docs_only),
                docs_check_mode=str(args.docs_check_mode),
            )
            print(json.dumps(payload, indent=2, sort_keys=True))
            sys.exit(int(code))
        if args.verify_default_cmd == "state":
            state = _verify_default_state(args.file, args.runs_root)
            if args.format == "text":
                print(f"name: {state['name']}")
                print(f"type: {state['type']}")
                print(f"health_status: {state['health_status']}")
                print(f"configured_steps: {state['configured_steps']}")
                print(f"current_blocker: {state['current_blocker'] or 'none'}")
                print(f"next_recommended_action: {state['next_recommended_action']}")
                if state["last_successful_run"]:
                    r = state["last_successful_run"]
                    print(f"last_successful_run: {r.get('step', '')} ({r.get('run_id', '')})")
                print(f"state_basis: {state['state_basis']}")
                if state["validated_tests"]:
                    print("validated_tests:")
                    for t in state["validated_tests"]:
                        run_id = t.get("run_id") or "unknown"
                        print(f"  - {t['step']} (run: {run_id})")
                if state["failing_tests"]:
                    print("failing_tests:")
                    for t in state["failing_tests"]:
                        run_id = t.get("run_id") or "no_run_found"
                        print(f"  - {t['step']} (run: {run_id})")
            else:
                print(json.dumps(state, indent=2, sort_keys=True))
            health = state["health_status"]
            sys.exit(0 if health in ("pass", "partial_pass") else 1)


def _load_candidate_path_info(mature_path: str, repo_root: str) -> dict:
    """Load candidate instrument, wiring, and test info from the board config for a known mature path."""
    result: dict = {
        "instrument_id": None,
        "candidate_test": None,
        "candidate_wiring": [],
        "target_side_wiring": [],   # MCU/board-level connections (LED pin, GPIO pins)
        "instrument_side_wiring": [],  # instrument-specific bench connections (probe pins, SWD port)
        "default_wiring": {},
    }
    if not mature_path:
        return result
    board_cfg_path = Path(repo_root) / "configs" / "boards" / f"{mature_path}.yaml"
    if not board_cfg_path.exists():
        return result
    try:
        import yaml as _yaml  # type: ignore
        raw = _yaml.safe_load(board_cfg_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return result
        board = raw.get("board") or raw
        result["instrument_id"] = board.get("instrument_instance") or board.get("probe_instance")
        result["default_wiring"] = board.get("default_wiring") or {}
        bench = board.get("bench_connections") or []
        all_wiring = []
        target_side = []
        instrument_side = []
        for c in bench:
            if not (isinstance(c, dict) and "from" in c and "to" in c):
                continue
            frm = c["from"]
            to = c["to"]
            entry = f"{frm}→{to}"
            all_wiring.append(entry)
            to_lower = to.lower()
            # LED is on the DUT itself — target-side indicator
            if to_lower == "led":
                target_side.append(f"{frm}→{to} (LED indicator, target-side)")
            # Instrument probe pins: P0.x, P1.x, P2.x, P3 patterns
            elif to_lower.startswith("p") and len(to) >= 2 and to[1:].split(".")[0].isdigit():
                instrument_side.append(entry)
            # probe GND or instrument GND
            elif "probe" in to_lower or ("gnd" in to_lower and frm.upper() == "GND"):
                instrument_side.append(entry)
            else:
                target_side.append(entry)
        result["candidate_wiring"] = all_wiring
        result["target_side_wiring"] = target_side
        result["instrument_side_wiring"] = instrument_side
    except Exception:
        pass
    # Find a canonical test for this board from the plans directory
    plans_dir = Path(repo_root) / "tests" / "plans"
    for candidate in [f"{mature_path}_gpio_signature.json", f"{mature_path}_gpio_smoke.json"]:
        if (plans_dir / candidate).exists():
            result["candidate_test"] = candidate.replace(".json", "")
            break
    return result


def _extract_confirmed_instrument(facts_raw: list) -> str:
    """Extract the user's confirmed instrument name from a list of fact strings.

    Searches each fact individually to avoid cross-fact regex bleed.
    """
    import re
    patterns = [
        r"instrument used:\s*(.+)",
        r"instrument confirmed:\s*(.+)",
        r"^instrument:\s*(.+)",
    ]
    for fact in facts_raw:
        fact_str = str(fact).strip()
        for pat in patterns:
            m = re.search(pat, fact_str, re.IGNORECASE)
            if m:
                return m.group(1).strip()
    return ""


def _instruments_match(inst1: str, inst2: str) -> bool:
    """Check if two instrument identifiers likely refer to the same instrument."""
    if not inst1 or not inst2:
        return True  # can't determine mismatch without both
    def _norm(s: str) -> str:
        return s.lower().replace("-", "").replace("_", "").replace(" ", "")
    n1, n2 = _norm(inst1), _norm(inst2)
    return n1 == n2 or n1 in n2 or n2 in n1


def _mature_confirmation_check(payload: dict) -> dict:
    """Check how many of the known-board confirmation items are present in confirmed_facts.

    Applies partial-match evaluation: instrument mismatch invalidates instrument-side
    bench wiring confirmation even if target-side wiring is confirmed.

    Returns:
        {
            "readiness": "candidate_path_identified" | "partially_confirmed" | "confirmed_enough_to_prepare",
            "confirmed": list[str],   # items confirmed
            "missing": list[str],     # items still needed
            "instrument_mismatch": bool,   # True if user instrument differs from repo reference
            "user_instrument": str,        # extracted from confirmed_facts (empty if not yet stated)
            "candidate_instrument": str,   # from project.yaml (set at creation time)
        }
    """
    facts_raw = payload.get("confirmed_facts") or []
    facts = " ".join(str(f).lower() for f in facts_raw)
    run_evidence = payload.get("run_evidence") or []
    status = str(payload.get("status", "")).strip()

    # A validated project with real run evidence is fully confirmed
    if status == "validated" or any(ev.get("ok") for ev in run_evidence if isinstance(ev, dict)):
        return {
            "readiness": "confirmed_enough_to_prepare",
            "confirmed": ["board", "instrument", "target-side wiring", "instrument-side bench wiring", "intended test"],
            "missing": [],
            "instrument_mismatch": False,
            "user_instrument": "",
            "candidate_instrument": str(payload.get("candidate_instrument", "")),
        }

    confirmed: list[str] = []
    missing: list[str] = []

    # Board
    if any(kw in facts for kw in ("board confirmed:", "board variant confirmed", "exact board")):
        confirmed.append("board variant")
    else:
        missing.append("board variant — which exact board/variant do you have?")

    # Instrument — check if user stated one and if it matches repo reference
    candidate_instrument = str(payload.get("candidate_instrument", "")).strip()
    user_instrument = _extract_confirmed_instrument(facts_raw)
    instrument_stated = bool(any(kw in facts for kw in ("instrument used:", "instrument confirmed", "instrument:")))
    instrument_mismatch = False

    if instrument_stated:
        confirmed.append("instrument")
        if user_instrument and candidate_instrument and not _instruments_match(candidate_instrument, user_instrument):
            instrument_mismatch = True
    else:
        missing.append("instrument — what debug/flash instrument are you using?")

    # Wiring — split into target-side and instrument-side
    # Target-side: LED pin, GPIO pins (MCU-specific, unchanged when instrument changes)
    # Instrument-side: probe pin mapping, SWD port (instrument-specific bench connections)
    generic_wiring_stated = any(kw in facts for kw in ("wiring confirmed", "connections confirmed", "wiring:"))
    target_wiring_stated = any(kw in facts for kw in ("target wiring", "target-side wiring", "led pin confirmed", "gpio pins confirmed"))

    if generic_wiring_stated or target_wiring_stated:
        confirmed.append("target-side wiring (LED/GPIO pins)")
        if instrument_mismatch:
            # Instrument changed — instrument-side bench wiring (probe pin mapping) is NOT confirmed
            missing.append(
                f"instrument-side bench wiring — repo uses {candidate_instrument!r}, "
                f"you stated {user_instrument!r}: probe pin mapping and SWD path differ; "
                f"provide wiring for your instrument"
            )
        else:
            confirmed.append("instrument-side bench wiring")
    else:
        if instrument_mismatch:
            missing.append(
                "target-side wiring — do your LED pin and GPIO pins match the repo MCU-side connections?"
            )
            missing.append(
                f"instrument-side bench wiring — repo uses {candidate_instrument!r}, "
                f"you stated {user_instrument!r}: provide wiring details for your instrument"
            )
        else:
            missing.append(
                "wiring/connections — does your bench wiring match the repo bench_setup? "
                "(confirm both target-side LED/GPIO pins and instrument-side probe connections)"
            )

    # Intended test
    if any(kw in facts for kw in ("test validated:", "intended test", "first test", "test confirmed")):
        confirmed.append("intended test")
    else:
        missing.append("intended first test — what should the first test demonstrate?")

    if len(confirmed) == 0:
        readiness = "candidate_path_identified"
    elif len(missing) == 0:
        readiness = "confirmed_enough_to_prepare"
    else:
        readiness = "partially_confirmed"

    return {
        "readiness": readiness,
        "confirmed": confirmed,
        "missing": missing,
        "instrument_mismatch": instrument_mismatch,
        "user_instrument": user_instrument,
        "candidate_instrument": candidate_instrument,
    }


def _resolve_maturity(target_mcu: str, repo_root: str) -> dict:
    """Check if target_mcu maps to a known mature path in the inventory.

    Returns:
        {
            "mature": bool,
            "dut_id": str|None,      # matching dut_id from inventory
            "confidence": "high"|"medium"|"low"|"none",
            "path_maturity": "mature"|"inferred"|"unknown",
        }
    """
    try:
        inv = inventory.build_inventory(repo_root=Path(repo_root))
        duts = inv.get("duts", [])
    except Exception:
        duts = []

    # Exact match on dut_id or mcu field
    for dut in duts:
        if dut.get("dut_id") == target_mcu or dut.get("mcu") == target_mcu:
            return {
                "mature": True,
                "dut_id": dut["dut_id"],
                "confidence": "high",
                "path_maturity": "mature",
            }

    # Family-level partial match (e.g. stm32f407 vs stm32f4xx family)
    mcu_lower = target_mcu.lower()
    for dut in duts:
        dut_id = str(dut.get("dut_id", "")).lower()
        dut_mcu = str(dut.get("mcu", "")).lower()
        family = str(dut.get("family", "")).lower()
        # Match first 8 chars or family prefix
        if (
            (len(mcu_lower) >= 7 and dut_mcu[:7] == mcu_lower[:7])
            or (family and mcu_lower.startswith(family.rstrip("x")))
        ):
            return {
                "mature": False,
                "dut_id": dut["dut_id"],
                "confidence": "medium",
                "path_maturity": "inferred",
            }

    return {
        "mature": False,
        "dut_id": None,
        "confidence": "none",
        "path_maturity": "unknown",
    }


def _slugify(value: str) -> str:
    text = value.strip().lower().replace(" ", "_").replace("-", "_")
    out = [ch for ch in text if ch.isalnum() or ch == "_"]
    return "".join(out).strip("_") or "user_project"


def _project_create_shell(
    target_mcu: str,
    project_id: str,
    project_name: str,
    user_goal: str,
    project_user: str,
    mature_path: str,
    projects_root: str,
    path_maturity: str = "mature",
    maturity_confidence: str = "high",
    repo_root: str = "",
) -> int:
    project_dir = Path(projects_root) / project_id
    if project_dir.exists():
        print(f"error: project already exists: {project_dir}")
        return 1
    project_dir.mkdir(parents=True, exist_ok=True)

    confirmed_fact = f"User requested a project for {target_mcu}"
    is_mature = path_maturity == "mature"
    is_inferred = path_maturity == "inferred"
    is_unknown = path_maturity == "unknown"

    if is_mature:
        assumption = (
            f"The user's board matches the known mature {mature_path} path in the AEL repo"
        )
        status = "shell_created"
        next_action = "reuse existing mature path — run stm32f411_gpio_signature or equivalent to validate"
    elif is_inferred:
        assumption = (
            f"Target MCU {target_mcu} is not an exact match but may be compatible with {mature_path} "
            "— family-level similarity only, not verified"
        )
        status = "exploratory"
        next_action = "clarify board details, exact GPIO/LED pins, and available debug/flash tool before generating code"
    else:  # unknown
        assumption = (
            f"Target MCU {target_mcu} has no known mature path in the AEL repo — "
            "board details, wiring, LED pin, and instrument setup are all unconfirmed"
        )
        status = "exploratory"
        next_action = "answer clarification questions before proceeding: board details, LED pin, GPIO, debug tool"

    if is_mature:
        # Use the 4 confirmation-checklist items from known_board_clarify_first_policy_v0_1.md
        unresolved = [
            f"Board variant confirmation — which exact board/variant do you have? (repo reference: {mature_path})",
            "Instrument confirmation — what debug/flash instrument are you using?",
            "Wiring/connections confirmation — does your bench wiring match the repo bench_setup?",
            "Intended first test — what should the first test demonstrate?",
        ]
    else:
        unresolved = [
            f"Is {target_mcu} the exact MCU or approximate? Confirm full part number",
            "What board is this? (official devkit, custom PCB, eval board?)",
            "Where is the LED connected? Which pin?",
            "Which GPIO pins should be used for toggling?",
            "What debug/flash/instrument setup is available?",
        ]

    if is_mature:
        cross_domain_type = "mature_capability_anchor"
        cross_domain_reason = f"project is anchored to the known mature {mature_path} capability path"
    else:
        cross_domain_type = "inferred_family_anchor" if is_inferred else "no_anchor"
        cross_domain_reason = (
            f"closest family-level reference is {mature_path} — not a verified match"
            if mature_path and not is_unknown
            else f"no mature path found for {target_mcu} — exploratory project"
        )

    # Load candidate path info for instrument/wiring details and project.yaml storage
    cinfo: dict = {}
    if is_mature and repo_root:
        cinfo = _load_candidate_path_info(mature_path, repo_root)

    try:
        import yaml as _yaml  # type: ignore
        payload = {
            "project_id": project_id,
            "project_name": project_name,
            "project_type": "user_project",
            "domain": "user_project_domain",
            "project_user": project_user,
            "user_goal": user_goal,
            "target_mcu": target_mcu,
            "closest_mature_ael_path": mature_path,
            "path_maturity": path_maturity,
            "maturity_confidence": maturity_confidence,
            # Store candidate instrument so _mature_confirmation_check can detect mismatch later
            "candidate_instrument": cinfo.get("instrument_id") or "",
            "system_refs": (
                [
                    f"docs/specs/{mature_path}_bringup_preparation_v0_1.md",
                    f"docs/specs/{mature_path}_capability_anchor_status_v0_1.md",
                ]
                if mature_path and not is_unknown
                else []
            ),
            "cross_domain_links": [
                {
                    "type": cross_domain_type,
                    "target": mature_path or "none",
                    "reason": cross_domain_reason,
                }
            ],
            "capability_source": "main",
            "capability_ref": mature_path or "",
            "status": status,
            "confirmed_facts": [confirmed_fact],
            "assumptions": [assumption],
            "unresolved_items": unresolved,
            "current_blocker": "",
            "last_action": "created_project_shell",
            "next_recommended_action": next_action,
            "tool_branch": "",
            "system_change_status": "integrated",
            "motivated_by_user_goal": user_goal,
            "key_refs": [f"projects/{project_id}/README.md"],
        }
        (project_dir / "project.yaml").write_text(
            _yaml.dump(payload, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"error writing project.yaml: {exc}")
        return 1

    if is_mature:
        questions_section = """## Best Next Questions

- What exact setup/wiring is available for this board?
- What first example should be generated?
- What validation approach should be used first?
"""
    else:
        questions_section = """## Required Clarifications (path not yet mature)

- What is the exact MCU part number?
- What board is this? (official devkit, custom PCB, eval board?)
- Where is the LED connected? Which pin?
- Which GPIO pins should be used for toggling?
- What debug/flash/instrument setup is available? (JTAG, SWD, USB, ST-Link, etc.)
"""

    readme = f"""# {project_name}

## User Goal

{user_goal}

## Current Status

- status: `{status}`
- path_maturity: `{path_maturity}` (confidence: {maturity_confidence})
- target MCU: `{target_mcu}`
- closest mature AEL path: `{mature_path or 'none'}`
- domain: `user_project_domain`
- project user: `{project_user}`

## Confirmed Facts

- {confirmed_fact}

## Assumptions

- {assumption}

## Unresolved Items

{''.join(f'- {u}' + chr(10) for u in unresolved)}
{questions_section}"""
    (project_dir / "README.md").write_text(readme, encoding="utf-8")

    notes = f"""# {project_name} Session Notes

## Initial Creation

- project shell created
- status: {status}
- path_maturity: {path_maturity} (confidence: {maturity_confidence})
- user goal: {user_goal}
- target MCU: `{target_mcu}`
- closest mature AEL path: `{mature_path or 'none'}`
- domain: `user_project_domain`
- project user: `{project_user}`

## Recommended Next Step

- {next_action}
"""
    (project_dir / "session_notes.md").write_text(notes, encoding="utf-8")

    print(f"created: {project_dir}")
    print(f"  project_id: {project_id}")
    print(f"  target_mcu: {target_mcu}")
    print(f"  mature_path: {mature_path or 'none'}")
    print(f"  path_maturity: {path_maturity} (confidence: {maturity_confidence})")
    print(f"  status: {status}")
    print(f"  next: {next_action}")
    print("")
    if is_mature:
        # H1: A/B/C/D structured output for known-board clarify-first policy
        instrument_id = cinfo.get("instrument_id") or "unknown (check configs/instrument_instances/)"
        candidate_test = cinfo.get("candidate_test") or f"{mature_path}_gpio_signature (check tests/plans/)"
        target_wiring = cinfo.get("target_side_wiring") or []
        instrument_wiring = cinfo.get("instrument_side_wiring") or []
        dw = cinfo.get("default_wiring") or {}
        swd = dw.get("swd", "")
        if swd:
            instrument_wiring = [f"SWD→{swd} (debug/flash port)"] + instrument_wiring
        target_wiring_str = ", ".join(target_wiring) if target_wiring else "see board config"
        instrument_wiring_str = ", ".join(instrument_wiring) if instrument_wiring else "see board config"
        print("  A. Known from repo (candidate reference — not yet your confirmed real setup):")
        print(f"     Candidate path:                {mature_path}")
        print(f"     Candidate instrument:          {instrument_id}")
        print(f"     Candidate test:                {candidate_test}")
        print(f"     Target-side wiring (MCU/board): {target_wiring_str}")
        print(f"     Instrument bench wiring:        {instrument_wiring_str}")
        print(f"     NOTE: instrument bench wiring above is {instrument_id!r}-specific.")
        print(f"           If you use a different instrument, this wiring does NOT apply.")
        print("")
        print("  B. Assumed but NOT yet confirmed about your real setup:")
        print(f"     - Board: your board is the same variant as the repo sample ({mature_path})")
        print(f"     - Instrument: you are using {instrument_id} (if different, bench wiring will differ too)")
        print(f"     - Target-side wiring: your LED/GPIO pin connections match the repo MCU-side")
        print(f"     - Instrument-side bench wiring: probe/SWD connections match the repo bench_setup")
        print(f"       (only valid if you use {instrument_id})")
        print(f"     - Intended test: the repo candidate test covers what you want to demonstrate")
        print("")
        print("  C. Still needed from you before treating this as runnable:")
        print("     ? Which exact board variant do you have?")
        print("     ? What instrument are you using for debug/flash?")
        print("       (If different from the repo instrument, specify your instrument's wiring separately)")
        print("     ? Do your target-side connections match? (LED pin, GPIO pins on the MCU)")
        print("     ? What should the first test demonstrate? (GPIO toggle, LED blink, UART, etc.)")
        print("")
        print("  D. Next step:")
        print("     Confirm or correct the above — then I can prepare a runnable path")
        print("     that matches your real setup instead of only the repo reference.")
    else:
        print("  WARNING: target MCU is not a known mature path.")
        print("  Required clarifications before generating code or running tests:")
        for u in unresolved:
            print(f"    ? {u}")
    return 0


def _board_state(board_id: str, runs_root: str) -> dict:
    """Build a capability state object for a specific board."""
    runs_dir = Path(runs_root)
    board_cfg_path = Path("configs") / "boards" / f"{board_id}.yaml"
    board_name = board_id

    if board_cfg_path.exists():
        try:
            import yaml as _yaml  # type: ignore
            raw = _yaml.safe_load(board_cfg_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                board_name = str(raw.get("name", board_id)).strip() or board_id
        except Exception:
            pass

    validated: list[str] = []
    failing: list[str] = []
    last_successful: dict = {}
    last_failure: dict = {}
    current_blocker = ""

    if runs_dir.exists():
        candidates = sorted(
            [d for d in runs_dir.glob(f"*_{board_id}_*") if d.is_dir()],
            reverse=True,
        )
        seen_tests: set[str] = set()
        for run_dir in candidates:
            # Extract test name: <date>_<time>_<board>_<test>
            parts = run_dir.name.split(f"_{board_id}_", 1)
            test_name = parts[1] if len(parts) == 2 else run_dir.name
            if test_name in seen_tests:
                continue
            seen_tests.add(test_name)

            result_path = run_dir / "result.json"
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except Exception:
                result = {}

            ok = bool(result.get("ok", False))
            label = f"{board_id}/{test_name}"
            if ok:
                validated.append(label)
                if not last_successful:
                    last_successful = {"test": label, "run_id": run_dir.name}
            else:
                failing.append(label)
                if not last_failure:
                    last_failure = {"test": label, "run_id": run_dir.name}
                if not current_blocker:
                    err = str(result.get("error_summary", "")).strip()
                    current_blocker = f"{label}: {err}" if err else label
    else:
        candidates = []

    if not candidates:
        health = "unknown"
    elif not failing:
        health = "pass"
    elif not validated:
        health = "fail"
    else:
        health = "partial_pass"

    next_action = ""
    if health == "unknown":
        next_action = f"run a first test for {board_id} to establish baseline"
    elif failing:
        next_action = f"stabilize {failing[0]} for {board_id}"
    elif health == "pass":
        next_action = "all known tests passing — consider expanding test coverage"

    key_refs = [f"configs/boards/{board_id}.yaml"]
    dut_docs = Path("assets_golden") / "duts" / board_id / "docs.md"
    if dut_docs.exists():
        key_refs.append(str(dut_docs))

    return {
        "board_id": board_id,
        "board_name": board_name,
        "type": "board_capability",
        "health_status": health,
        "validated_tests": validated,
        "failing_tests": failing,
        "last_successful_run": last_successful,
        "last_failure": last_failure,
        "current_blocker": current_blocker,
        "next_recommended_action": next_action,
        "key_refs": key_refs,
    }


def _verify_default_state(setting_file: str, runs_root: str) -> dict:
    """Build a state object for default verification from config + recent run artifacts."""
    try:
        import yaml as _yaml  # type: ignore
        raw = _yaml.safe_load(Path(setting_file).read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}

    steps = raw.get("steps", []) if isinstance(raw.get("steps"), list) else []
    runs_dir = Path(runs_root)

    # For each step, find the most recent run result
    validated: list[dict] = []
    failing: list[dict] = []
    optional_failing: list[dict] = []
    last_successful: dict = {}
    last_failure: dict = {}
    current_blocker = ""

    for step in steps:
        if not isinstance(step, dict):
            continue
        board = str(step.get("board", "")).strip()
        test_path = str(step.get("test", "")).strip()
        if not board or not test_path:
            continue
        optional = bool(step.get("optional", False))
        # Derive test name from path: tests/plans/foo_bar.json -> foo_bar
        test_name = Path(test_path).stem
        step_label = f"{board}/{test_name}"

        # Find matching run dirs sorted newest first
        if runs_dir.exists():
            pattern = f"*_{board}_{test_name}"
            candidates = sorted(
                [d for d in runs_dir.glob(pattern) if d.is_dir()],
                reverse=True,
            )
        else:
            candidates = []

        if not candidates:
            entry = {"step": step_label, "run_id": None, "optional": optional}
            if optional:
                optional_failing.append(entry)
            else:
                failing.append(entry)
                if not current_blocker:
                    current_blocker = f"no run found for {step_label}"
            continue

        # Load the most recent result
        result_path = candidates[0] / "result.json"
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception:
            result = {}

        ok = bool(result.get("ok", False))
        run_id = candidates[0].name

        if ok:
            validated.append({"step": step_label, "run_id": run_id, "optional": optional})
            if not last_successful:
                last_successful = {"step": step_label, "run_id": run_id}
        else:
            entry = {"step": step_label, "run_id": run_id, "optional": optional}
            if optional:
                optional_failing.append(entry)
            else:
                failing.append(entry)
                if not last_failure:
                    last_failure = {"step": step_label, "run_id": run_id}
                if not current_blocker:
                    err = str(result.get("error_summary", "")).strip()
                    current_blocker = f"{step_label}: {err}" if err else step_label

    # Derive health status (optional failures do not affect health)
    if not steps:
        health = "unknown"
    elif not validated and not failing:
        health = "unknown"
    elif not failing:
        health = "pass"
    elif not validated:
        health = "fail"
    else:
        health = "partial_pass"

    next_action = ""
    if failing:
        next_action = f"stabilize {failing[0]['step']} and rerun default verification"
    elif optional_failing:
        next_action = f"{len(optional_failing)} optional step(s) failing — not required for pass"
    elif health == "pass":
        next_action = "all steps passing — consider adding next board/test to suite"

    return {
        "name": "Default Verification",
        "type": "system_baseline",
        "state_basis": "last_known_run_results",
        "health_status": health,
        "configured_steps": len(steps),
        "current_blocker": current_blocker,
        "last_successful_run": last_successful,
        "last_failure": last_failure,
        "validated_tests": validated,
        "failing_tests": failing,
        "optional_failing_tests": optional_failing,
        "next_recommended_action": next_action,
        "key_refs": [
            setting_file,
            "docs/default_verification_baseline.md",
        ],
    }


def _project_yaml_load(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _project_fmt_list(values: object) -> list:
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _project_run_gate_check(payload: dict) -> tuple[bool, list, list, str]:
    """Pure gate logic: given a project payload, return (ok, reasons, clarifications, readiness)."""
    path_maturity = str(payload.get("path_maturity", "mature")).strip()
    ok = True
    readiness = "confirmed_enough_to_prepare"
    reasons: list[str] = []
    clarifications: list[str] = []
    if path_maturity == "unknown":
        ok = False
        readiness = "candidate_path_identified"
        reasons.append("path_maturity is 'unknown' — no mature path found for this MCU")
        clarifications = [
            f"What is the exact MCU part number? (user said: {payload.get('target_mcu', '?')})",
            "What board is this? (official devkit, custom PCB, eval board?)",
            "Where is the LED connected? Which pin?",
            "Which GPIO pins should be used for toggling?",
            "What debug/flash/instrument setup is available?",
        ]
    elif path_maturity == "inferred":
        ok = False
        readiness = "candidate_path_identified"
        reasons.append(
            f"path_maturity is 'inferred' — {payload.get('target_mcu')} is not a verified match "
            f"for {payload.get('closest_mature_ael_path', '?')}"
        )
        clarifications = [
            f"Confirm the board is compatible with {payload.get('closest_mature_ael_path', '?')}",
            "Confirm LED pin mapping matches the reference board",
            "Confirm GPIO pins match the reference board",
            "Confirm instrument/flash setup is compatible",
        ]
    else:
        check = _mature_confirmation_check(payload)
        readiness = check["readiness"]
        instrument_mismatch = check.get("instrument_mismatch", False)
        if readiness == "candidate_path_identified":
            ok = False
            reasons.append(
                "path_maturity is 'mature' but no real-setup confirmations recorded — "
                "repo path is a candidate reference only"
            )
            clarifications = check["missing"]
        elif readiness == "partially_confirmed":
            if instrument_mismatch:
                ok = False
                reasons.append(
                    f"partial-match: instrument mismatch — "
                    f"you stated {check.get('user_instrument', '?')!r}, "
                    f"repo uses {check.get('candidate_instrument', '?')!r}. "
                    "Target-side wiring may carry over; instrument-side bench wiring must be re-specified."
                )
            else:
                ok = True
                reasons.append(
                    f"partially_confirmed: {len(check['confirmed'])} items confirmed — "
                    "proceeding with caution"
                )
            clarifications = check["missing"]
    return ok, reasons, clarifications, readiness


def _print_run_gate_result(
    ok: bool,
    reasons: list,
    clarifications: list,
    readiness: str,
    project_id: str,
    path_maturity: str,
    status: str,
) -> None:
    if ok and not clarifications:
        print(f"gate: ok")
        print(f"  project: {project_id}")
        print(f"  path_maturity: {path_maturity}")
        print(f"  readiness: {readiness}")
        print(f"  status: {status}")
        print(f"  safe to proceed with run: yes")
    elif ok and clarifications:
        print(f"gate: ok (with warnings)")
        print(f"  project: {project_id}")
        print(f"  path_maturity: {path_maturity}")
        print(f"  readiness: {readiness}")
        print(f"  status: {status}")
        print(f"  safe to proceed with run: yes — but setup not fully confirmed")
        for r in reasons:
            print(f"  note: {r}")
        print(f"  still unconfirmed:")
        for c in clarifications:
            print(f"    ? {c}")
    else:
        print(f"gate: blocked")
        print(f"  project: {project_id}")
        print(f"  path_maturity: {path_maturity}")
        print(f"  readiness: {readiness}")
        print(f"  status: {status}")
        print(f"  safe to proceed with run: no")
        print(f"  reasons:")
        for r in reasons:
            print(f"    - {r}")
        if clarifications:
            print(f"  required_clarifications:")
            for c in clarifications:
                print(f"    ? {c}")


def _project_cmd(args) -> int:
    root = Path(args.projects_root)
    if args.project_cmd == "list":
        if not root.exists():
            print("project_count: 0")
            return 0
        projects = []
        for pyaml in sorted(root.glob("*/project.yaml")):
            p = _project_yaml_load(pyaml)
            if p:
                projects.append(p)
        print(f"project_count: {len(projects)}")
        for p in projects:
            print(f"- {p.get('project_id', '')}")
            print(f"  - name: {p.get('project_name', '')}")
            print(f"  - user: {p.get('project_user', '')}")
            print(f"  - status: {p.get('status', '')}")
            print(f"  - target_mcu: {p.get('target_mcu', '')}")
            print(f"  - mature_path: {p.get('closest_mature_ael_path', '')}")
            blocker = str(p.get("current_blocker", "")).strip()
            if blocker:
                print(f"  - current_blocker: {blocker}")
            print(f"  - next_recommended_action: {p.get('next_recommended_action', '')}")
        return 0
    if args.project_cmd == "status":
        project_dir = root / args.project_id
        payload = _project_yaml_load(project_dir / "project.yaml")
        if not payload:
            print(f"error: missing or unreadable: {project_dir / 'project.yaml'}")
            return 1
        print(f"project_id: {payload.get('project_id', '')}")
        print(f"project_name: {payload.get('project_name', '')}")
        print(f"domain: {payload.get('domain', '')}")
        print(f"project_user: {payload.get('project_user', '')}")
        print(f"status: {payload.get('status', '')}")
        print(f"target_mcu: {payload.get('target_mcu', '')}")
        print(f"closest_mature_ael_path: {payload.get('closest_mature_ael_path', '')}")
        # E2: transparency fields
        path_maturity = str(payload.get("path_maturity", "mature")).strip()
        maturity_confidence = str(payload.get("maturity_confidence", "high")).strip()
        print(f"path_maturity: {path_maturity} (confidence: {maturity_confidence})")
        mature_path_reused = payload.get("mature_path_reused")
        if mature_path_reused is not None:
            print(f"mature_path_reused: {mature_path_reused}")
        blocker = str(payload.get("current_blocker", "")).strip()
        print(f"current_blocker: {blocker or 'none'}")
        print(f"last_action: {payload.get('last_action', '')}")
        print(f"next_recommended_action: {payload.get('next_recommended_action', '')}")
        for label, key in [
            ("confirmed_facts", "confirmed_facts"),
            ("assumptions", "assumptions"),
            ("unresolved_items", "unresolved_items"),
            ("system_refs", "system_refs"),
        ]:
            items = _project_fmt_list(payload.get(key))
            if items:
                print(f"{label}:")
                for item in items:
                    print(f"  - {item}")
        # E3: show run evidence if present
        run_evidence = payload.get("run_evidence")
        if run_evidence and isinstance(run_evidence, list):
            print(f"run_evidence:")
            for ev in run_evidence:
                ok_str = "PASS" if ev.get("ok") else "FAIL"
                print(f"  - {ev.get('run_id', '?')} [{ok_str}] board={ev.get('board','')} test={ev.get('test','')}")
        return 0
    if args.project_cmd == "update":
        project_dir = root / args.project_id
        yaml_path = project_dir / "project.yaml"
        payload = _project_yaml_load(yaml_path)
        if not payload:
            print(f"error: missing or unreadable: {yaml_path}")
            return 1
        changed = []
        if args.set_status is not None:
            payload["status"] = args.set_status
            changed.append(f"status: {args.set_status}")
        if args.set_blocker is not None:
            payload["current_blocker"] = args.set_blocker
            changed.append(f"current_blocker: {args.set_blocker!r}")
        if args.set_next_action is not None:
            payload["next_recommended_action"] = args.set_next_action
            changed.append(f"next_recommended_action: {args.set_next_action}")
        if args.set_last_action is not None:
            payload["last_action"] = args.set_last_action
            changed.append(f"last_action: {args.set_last_action}")
        if args.append_confirmed_fact is not None:
            facts = list(payload.get("confirmed_facts") or [])
            facts.append(args.append_confirmed_fact)
            payload["confirmed_facts"] = facts
            changed.append(f"confirmed_facts: appended {args.append_confirmed_fact!r}")
        if args.resolve_unresolved is not None:
            items = _project_fmt_list(payload.get("unresolved_items"))
            before = len(items)
            items = [i for i in items if i != args.resolve_unresolved]
            payload["unresolved_items"] = items
            changed.append(f"unresolved_items: removed {before - len(items)} matching entry")
        if not changed:
            print("no changes specified")
            return 0
        try:
            import yaml as _yaml  # type: ignore
            yaml_path.write_text(_yaml.dump(payload, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        except Exception as exc:
            print(f"error writing {yaml_path}: {exc}")
            return 1
        print(f"updated: {yaml_path}")
        for line in changed:
            print(f"  - {line}")
        return 0
    if args.project_cmd == "append-note":
        project_dir = root / args.project_id
        notes_path = project_dir / "session_notes.md"
        if not project_dir.exists():
            print(f"error: project directory not found: {project_dir}")
            return 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## {ts}\n\n{args.text}\n"
        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"note appended to: {notes_path}")
        return 0
    if args.project_cmd == "create":
        mcu = args.target_mcu.strip()
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Resolve maturity before creating the shell (F4)
        if args.mature_path:
            # Explicit override — trust the caller
            maturity = {"mature": True, "dut_id": args.mature_path, "confidence": "high", "path_maturity": "mature"}
        else:
            maturity = _resolve_maturity(mcu, repo_root)
        mature_path = args.mature_path or (maturity["dut_id"] or mcu)
        project_id = _slugify(args.project_id or f"{mcu}_project")
        project_name = args.project_name or f"{mcu} project"
        user_goal = args.user_goal or f"Create a first example project for a board using {mcu}"
        return _project_create_shell(
            target_mcu=mcu,
            project_id=project_id,
            project_name=project_name,
            user_goal=user_goal,
            project_user=args.project_user,
            mature_path=mature_path,
            projects_root=args.projects_root,
            path_maturity=maturity["path_maturity"],
            maturity_confidence=maturity["confidence"],
            repo_root=repo_root,
        )
    if args.project_cmd == "questions":
        project_dir = root / args.project_id
        payload = _project_yaml_load(project_dir / "project.yaml")
        if not payload:
            print(f"error: missing or unreadable: {project_dir / 'project.yaml'}")
            return 1
        status = str(payload.get("status", "")).strip()
        blocker = str(payload.get("current_blocker", "")).strip()
        unresolved = _project_fmt_list(payload.get("unresolved_items"))
        next_action = str(payload.get("next_recommended_action", "")).strip()
        path_maturity = str(payload.get("path_maturity", "mature")).strip()
        questions: list[str] = []
        mature_confirmed_topics: list[str] = []  # populated below for mature-path projects
        if blocker and blocker not in ("", "none"):
            questions.append(f"What is blocking progress? Current blocker: {blocker!r}")
            questions.append("What is the best next step to resolve this blocker?")
            questions.append("Is the blocker in setup/wiring, build, flash, or verification?")
        # Branch on path maturity (F3)
        if path_maturity in ("unknown", "inferred"):
            questions.append(f"What is the exact MCU part number? (user said: {payload.get('target_mcu', '?')})")
            questions.append("What board is this? (official devkit, custom PCB, eval board?)")
            questions.append("Where is the LED connected? Which pin?")
            questions.append("Which GPIO pins should be used for toggling?")
            questions.append("What debug/flash/instrument setup is available? (JTAG, SWD, ST-Link, etc.)")
            if path_maturity == "inferred":
                closest = payload.get("closest_mature_ael_path", "")
                questions.append(
                    f"Is the board pin-compatible with {closest}? "
                    "If yes, the existing test path may be reusable."
                )
        else:
            # H2: Mature path — use the confirmation-checklist items from known_board_clarify_first_policy_v0_1.md
            check = _mature_confirmation_check(payload)
            readiness = check["readiness"]
            instrument_mismatch = check.get("instrument_mismatch", False)
            mature_confirmed_topics = list(check.get("confirmed", []))
            if readiness == "confirmed_enough_to_prepare":
                questions.append("Setup is confirmed — ready to prepare a runnable path.")
                questions.append("What should the next test or experiment be?")
            else:
                closest = payload.get("closest_mature_ael_path", "the repo reference")
                candidate_instrument = check.get("candidate_instrument", "")
                user_instrument = check.get("user_instrument", "")
                missing_strs = check["missing"]
                # Only ask "what instrument" if user has NOT stated one yet
                if any(m.startswith("instrument —") for m in missing_strs):
                    questions.append("What instrument are you using for debug/flash? (check if it matches the repo instrument config)")
                if "board variant" in " ".join(missing_strs):
                    questions.append(f"Which exact board variant do you have? (repo reference: {closest})")
                if instrument_mismatch:
                    questions.append(
                        f"Instrument partial-match: you stated {user_instrument!r}, "
                        f"repo uses {candidate_instrument!r}. "
                        "Target-side wiring (LED/GPIO pins) may still apply. "
                        "Instrument-side bench wiring (probe pins, SWD port) will differ — "
                        "please provide your instrument's specific connections."
                    )
                    # Suppress generic "wiring/connections" unresolved item display —
                    # the partial-match question above covers it with more precision
                    mature_confirmed_topics.append("wiring/connections")
                elif any("wiring" in m for m in missing_strs):
                    questions.append(
                        "Wiring: confirm target-side (LED pin, GPIO pins on MCU) "
                        "and instrument-side (probe pin mapping, SWD port). "
                        "If you are using the same instrument as the repo, the bench_setup applies directly."
                    )
                if any("intended" in m for m in missing_strs):
                    questions.append("What should the first test demonstrate? (GPIO toggle, LED blink, UART, ADC, etc.)")
                if readiness == "partially_confirmed" and check["confirmed"]:
                    # Use the actual confirmed list from check, not mature_confirmed_topics
                    # (mature_confirmed_topics may include suppression entries not actually confirmed)
                    questions.append(f"Already confirmed: {', '.join(check['confirmed'])}")

        # Add unresolved items only if not already covered by the questions above.
        # For mature-path projects, also skip items whose topic is already confirmed.
        def _already_covered(candidate: str, existing: list, confirmed_topics: list) -> bool:
            cl = candidate.lower()
            # Topic-based skip: if a confirmed topic keyword appears in the unresolved item, skip it
            topic_map = {
                "board variant": ["board variant", "board confirmed", "which exact board"],
                "instrument": ["instrument confirmation", "instrument — what"],
                "target-side wiring": ["target-side wiring", "target wiring"],
                "instrument-side bench wiring": ["instrument-side bench wiring"],
                "wiring/connections": ["wiring/connections"],
                "intended test": ["intended first test", "test confirmation"],
            }
            for topic in confirmed_topics:
                topic_lower = topic.lower()
                for t_key, t_phrases in topic_map.items():
                    if topic_lower.startswith(t_key):
                        if any(phrase in cl for phrase in t_phrases):
                            return True
            # Trigram overlap fallback
            words = candidate.lower().split()
            if len(words) < 3:
                return False
            trigrams = [" ".join(words[i:i+3]) for i in range(len(words) - 2)]
            return any(any(tri in q.lower() for q in existing) for tri in trigrams)

        for u in unresolved:
            if not _already_covered(u, questions, mature_confirmed_topics):
                questions.append(f"Unresolved: {u}")
        if next_action:
            questions.append(f"Next recommended action: {next_action}")
        # No generic fallback questions — the 4 confirmation items above are more specific
        print(f"project: {payload.get('project_id', args.project_id)}")
        print(f"status: {status}")
        print(f"path_maturity: {path_maturity}")
        print("suggested_questions:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
        return 0
    if args.project_cmd == "link-run":
        # E1 + E3: link a completed run to a project and update state
        project_dir = root / args.project_id
        yaml_path = project_dir / "project.yaml"
        payload = _project_yaml_load(yaml_path)
        if not payload:
            print(f"error: missing or unreadable: {yaml_path}")
            return 1
        runs_dir = Path(args.runs_root) / args.run_id
        result_path = runs_dir / "result.json"
        if not result_path.exists():
            print(f"error: run result not found: {result_path}")
            return 1
        try:
            run_result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"error reading run result: {exc}")
            return 1
        run_ok = bool(run_result.get("ok", False))
        # Extract key fields — result.json nests info in validation_summary / current_setup
        vs = run_result.get("validation_summary") or {}
        cs = run_result.get("current_setup") or {}
        board_profile = vs.get("selected_board_profile") or cs.get("selected_board_profile") or {}
        board = board_profile.get("id", "") or board_profile.get("name", "")
        test = vs.get("test", "") or ""
        instrument = vs.get("control_instrument_instance", "") or cs.get("control_instrument_instance", "")
        # Build run evidence record (E3)
        run_evidence = {
            "run_id": args.run_id,
            "ok": run_ok,
            "board": board,
            "test": test,
            "instrument": instrument,
            "termination": run_result.get("termination", ""),
        }
        # Update project state (E1)
        facts = list(payload.get("confirmed_facts") or [])
        if board and f"Board confirmed: {board}" not in facts:
            facts.append(f"Board confirmed: {board}")
        if test and f"Test validated: {test}" not in facts:
            facts.append(f"Test validated: {test}" + (" (PASS)" if run_ok else " (FAIL)"))
        if instrument and f"Instrument used: {instrument}" not in facts:
            facts.append(f"Instrument used: {instrument}")
        payload["confirmed_facts"] = facts
        # Clear generic unresolved items that a successful run resolves
        if run_ok:
            resolved_patterns = [
                "Exact setup and wiring",
                "What first example",
            ]
            unresolved = _project_fmt_list(payload.get("unresolved_items"))
            unresolved = [
                u for u in unresolved
                if not any(p.lower() in u.lower() for p in resolved_patterns)
            ]
            payload["unresolved_items"] = unresolved
            payload["status"] = "validated"
            payload["last_action"] = f"run_validated: {args.run_id}"
            payload["next_recommended_action"] = (
                f"project validated — evidence: {args.run_id}"
            )
        else:
            payload["status"] = "run_failed"
            payload["last_action"] = f"run_failed: {args.run_id}"
            payload["current_blocker"] = (
                f"run failed: {run_result.get('error_summary', args.run_id)}"
            )
        # Store run evidence (E3)
        evidence_list = list(payload.get("run_evidence", []) or [])
        evidence_list.append(run_evidence)
        payload["run_evidence"] = evidence_list
        # Transparency: record mature_path_reused (E2)
        payload["mature_path_reused"] = payload.get("path_maturity", "mature") == "mature"
        try:
            import yaml as _yaml  # type: ignore
            yaml_path.write_text(_yaml.dump(payload, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        except Exception as exc:
            print(f"error writing {yaml_path}: {exc}")
            return 1
        print(f"linked: run {args.run_id} -> project {args.project_id}")
        print(f"  run_ok: {run_ok}")
        print(f"  project status: {payload['status']}")
        print(f"  last_action: {payload['last_action']}")
        print(f"  mature_path_reused: {payload['mature_path_reused']}")
        if run_ok:
            print(f"  confirmed_facts added: {len(facts)} total")
        return 0
    if args.project_cmd == "run-gate":
        # F5: check if a project is safe to proceed with a run
        project_dir = root / args.project_id
        payload = _project_yaml_load(project_dir / "project.yaml")
        if not payload:
            print(f"error: missing or unreadable: {project_dir / 'project.yaml'}")
            return 1
        ok, reasons, clarifications, readiness = _project_run_gate_check(payload)
        path_maturity = str(payload.get("path_maturity", "mature")).strip()
        status = str(payload.get("status", "")).strip()
        _print_run_gate_result(ok, reasons, clarifications, readiness, args.project_id, path_maturity, status)
        return 0 if ok else 1
    return 1


def _check_tools(tools):
    missing = [t for t in tools if shutil.which(t) is None]
    return missing


def run_doctor(probe_path, board_path, test_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    run_paths = run_manager.create_run("doctor", "doctor", repo_root)

    # Prepare log and result.
    run_manager.ensure_parent(run_paths.doctor_log)
    result = {
        "ok": False,
        "failed_step": "",
        "error_summary": "",
        "logs": {"doctor": str(run_paths.doctor_log)},
    }
    run_manager.ensure_parent(run_paths.result)
    with open(run_paths.result, "w", encoding="utf-8") as f:
        json.dump(result, f)

    probe_full = probe_path if os.path.isabs(probe_path) else os.path.join(repo_root, probe_path)
    board_full = board_path if os.path.isabs(board_path) else os.path.join(repo_root, board_path)
    test_full = test_path if os.path.isabs(test_path) else os.path.join(repo_root, test_path)

    binding = load_probe_binding(repo_root, probe_path=probe_path)
    probe_raw = binding.raw
    board_raw = _simple_yaml_load(board_full)
    test_raw = {}
    try:
        with open(test_full, "r", encoding="utf-8") as f:
            test_raw = json.load(f)
    except Exception:
        test_raw = {}

    probe_cfg = _normalize_probe_cfg(probe_raw)

    with open(run_paths.doctor_log, "w", encoding="utf-8") as logf:
        tee = run_manager.Tee(logf, sys.stdout, "normal")
        orig_out = sys.stdout
        sys.stdout = tee
        try:
            print("Doctor: starting checks")
            missing = _check_tools(list(resolve_doctor_required_tools()))
            if missing:
                print("Doctor: missing tools: " + ", ".join(missing))
            else:
                print("Doctor: tools OK")

            ok_bmp, bmp_info = monitor_version(probe_cfg)
            print("Doctor: BMP monitor -> " + ("OK" if ok_bmp else "FAIL"))
            if bmp_info:
                print(bmp_info)

            ok_la, la_info = la_capture_ok(probe_cfg)
            print("Doctor: LA capture -> " + ("OK" if ok_la else "FAIL"))
            if la_info:
                print(la_info)

            issues = validate_config(probe_raw, board_raw, test_raw)
            if issues:
                print("Doctor: config issues:")
                for item in issues:
                    print(" - " + item)
            else:
                print("Doctor: config OK")

            overall_ok = (not missing) and ok_bmp and ok_la and (not issues)
            result["ok"] = overall_ok
            result["failed_step"] = "" if overall_ok else "doctor"
            result["error_summary"] = "" if overall_ok else "doctor failed"
            with open(run_paths.result, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, sort_keys=True)
        finally:
            sys.stdout.flush()
            sys.stdout = orig_out

    meta = {
        "run_id": run_paths.run_id,
        "started_at": datetime.now().isoformat(),
        "probe_path": probe_path,
        "board_path": board_path,
        "test_path": test_path,
    }
    with open(run_paths.meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    return 0 if result["ok"] else 1


_LIFECYCLE_STAGES = ["draft", "runnable", "validated", "merge_candidate", "merged_to_main"]
_LIFECYCLE_PROMOTE_MIN = {"validated", "merge_candidate"}


def _update_manifest_id(manifest, new_id, verified_status=None, lifecycle_stage=None):
    if not isinstance(manifest, dict):
        manifest = {}
    manifest["id"] = new_id
    if verified_status is not None:
        verified = manifest.get("verified") if isinstance(manifest.get("verified"), dict) else {}
        verified["status"] = bool(verified_status)
        manifest["verified"] = verified
    if lifecycle_stage is not None:
        manifest["lifecycle_stage"] = lifecycle_stage
    return manifest


def dut_create_cmd(from_golden_id, to_user_id, dest="user"):
    src = Path("assets_golden") / "duts" / from_golden_id
    dest_root = "assets_branch" if dest == "branch" else "assets_user"
    dst = Path(dest_root) / "duts" / to_user_id
    if not src.exists():
        print(f"DUT create: golden id not found: {from_golden_id}")
        return 1
    if dst.exists():
        print(f"DUT create: destination already exists: {dst}")
        return 2
    assets.copy_dut_skeleton(src, dst)
    manifest_path = dst / "manifest.yaml"
    manifest = assets._load_yaml(manifest_path) if manifest_path.exists() else {}
    lifecycle = "draft" if dest == "branch" else None
    manifest = _update_manifest_id(manifest, to_user_id, verified_status=False, lifecycle_stage=lifecycle)
    assets.save_manifest(manifest_path, manifest)
    notes_path = dst / "notes.md"
    if not notes_path.exists():
        notes_path.write_text(f"Created from golden {from_golden_id}\n", encoding="utf-8")
    print(f"DUT create: {dst}" + (" [branch]" if dest == "branch" else ""))
    return 0


def dut_promote_cmd(user_id, as_id=None, delete_source=False, from_namespace="user"):
    src_root = "assets_branch" if from_namespace == "branch" else "assets_user"
    src = Path(src_root) / "duts" / user_id
    if not src.exists():
        print(f"DUT promote: {from_namespace} id not found: {user_id}")
        return 1
    manifest_path = src / "manifest.yaml"
    if not manifest_path.exists():
        print("DUT promote: manifest.yaml missing")
        return 2
    manifest = assets._load_yaml(manifest_path)
    missing = assets._validate_manifest(manifest)
    if missing:
        print("DUT promote: manifest missing fields: " + ", ".join(missing))
        return 3
    # lifecycle_stage gate
    lifecycle = str(manifest.get("lifecycle_stage") or "").strip() if isinstance(manifest, dict) else ""
    verified_ok = bool((manifest.get("verified") or {}).get("status")) if isinstance(manifest, dict) else False
    if lifecycle and lifecycle not in _LIFECYCLE_PROMOTE_MIN:
        print(f"DUT promote: blocked — lifecycle_stage is '{lifecycle}', must be 'validated' or 'merge_candidate'")
        return 5
    if not lifecycle and not verified_ok:
        print("DUT promote: blocked — verified.status is false and no lifecycle_stage set")
        return 5
    golden_id = as_id or user_id
    dst = Path("assets_golden") / "duts" / golden_id
    if dst.exists():
        print(f"DUT promote: destination already exists: {dst}")
        return 4
    assets.copy_dut_skeleton(src, dst)
    dst_manifest_path = dst / "manifest.yaml"
    verified_status = manifest.get("verified", {}).get("status", False) if isinstance(manifest, dict) else False
    manifest = _update_manifest_id(manifest, golden_id, verified_status=verified_status, lifecycle_stage="merged_to_main")
    assets.save_manifest(dst_manifest_path, manifest)
    promo_note = dst / "PROMOTION.md"
    promo_note.write_text(f"Promoted from {from_namespace} DUT {user_id}.\n", encoding="utf-8")
    if delete_source:
        shutil.rmtree(src)
    print(f"DUT promote: {dst} [merged_to_main]")
    return 0


def _git_describe():
    try:
        res = subprocess.run(
            ["git", "describe", "--always", "--dirty", "--tags"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            return (res.stdout or "").strip()
    except Exception:
        pass
    return ""


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def run_pack(pack_path, board_override=None, stop_on_fail=False, no_flash=False, no_build=False, verify_only=False):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    pack_full = pack_path if os.path.isabs(pack_path) else os.path.join(repo_root, pack_path)
    pack = _load_json(pack_full)

    pack_name = pack.get("name", "pack")
    pack_board = board_override or pack.get("board")
    tests = pack.get("tests", [])
    if not pack_board or not tests:
        print("Pack: missing board or tests")
        return 2

    # Validate tests for mixed boards
    for t in tests:
        t_full = t if os.path.isabs(t) else os.path.join(repo_root, t)
        t_json = _load_json(t_full)
        t_board = t_json.get("board") if isinstance(t_json, dict) else None
        if t_board and t_board != pack_board:
            print(f"Pack: test {t} targets board {t_board}, expected {pack_board}")
            return 3

    bench_path = os.path.join(repo_root, "configs", "bench.yaml")
    bench = _simple_yaml_load(bench_path)

    run_id = f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{pack_name}_{pack_board}"
    pack_root = os.path.join(repo_root, "pack_runs", run_id)
    os.makedirs(pack_root, exist_ok=True)

    meta = {
        "timestamp": datetime.now().isoformat(),
        "git_describe": _git_describe(),
        "bench": bench,
        "pack": pack_name,
        "board": pack_board,
    }
    plan = {"tests": tests}
    result = {"ok": True, "results": []}

    def _write(path, data):
        with open(os.path.join(pack_root, path), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    _write("pack_meta.json", meta)
    _write("pack_plan.json", plan)
    _write("pack_result.json", result)

    for t in tests:
        t_full = t if os.path.isabs(t) else os.path.join(repo_root, t)
        print(f"Using pack: {pack_name}")
        print(f"Pack test: {t}")
        probe_path = resolve_control_instrument_config(
            repo_root,
            args=None,
            board_id=pack_board,
            pack_meta={"mode": "pack", "board": pack_board, "absolute_paths": True},
        )
        code, run_paths = run_pipeline(
            probe_path=probe_path,
            board_arg=pack_board,
            test_path=t_full,
            wiring=None,
            output_mode="normal",
            skip_flash=no_flash or verify_only,
            no_build=no_build or verify_only,
            verify_only=verify_only,
            return_paths=True,
        )
        run_result = _load_json(run_paths.result)
        entry = {
            "test": t,
            "run_dir": str(run_paths.root),
            "ok": bool(run_result.get("ok")),
            "failed_step": run_result.get("failed_step", ""),
            "code": code,
        }
        result["results"].append(entry)
        result["ok"] = result["ok"] and entry["ok"]
        _write("pack_result.json", result)
        if stop_on_fail and not entry["ok"]:
            break

    # HTML report
    report = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Pack Report</title></head><body>",
        f"<h1>Pack {pack_name}</h1>",
        f"<p>Board: {pack_board}</p>",
        "<ul>",
    ]
    for r in result["results"]:
        run_dir = r["run_dir"]
        report.append(
            f"<li>{r['test']} — {'OK' if r['ok'] else 'FAIL'} — "
            f"<a href=\"file://{run_dir}\">{run_dir}</a></li>"
        )
    report.extend(["</ul>", "</body></html>"])
    with open(os.path.join(pack_root, "pack_report.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    main()
