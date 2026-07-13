#!/usr/bin/env python3
"""Run the formal perception -> analysis -> notification label-rate flow."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from human_review_ops.tools.compat.skill_path_resolver import (  # noqa: E402
    active_path_mode,
    resolve_script_dir,
)


SCENARIO_KEY = "efficiency-label-rate"
PERCEPTION_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "perception")
ANALYSIS_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "analysis")
NOTIFICATION_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "notification_artifacts")
POC_ROUTING_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "poc_routing")
for script_dir in reversed(
    tuple(dict.fromkeys((
        PERCEPTION_SCRIPTS,
        ANALYSIS_SCRIPTS,
        NOTIFICATION_SCRIPTS,
        POC_ROUTING_SCRIPTS,
    )))
):
    sys.path.insert(0, str(script_dir))

import label_rate_analysis  # noqa: E402
from label_rate_perception import detect_label_rate_perception  # noqa: E402
from label_rate_notification_artifacts import (  # noqa: E402
    build_label_rate_notification_artifacts,
)
from resolve_label_rate_poc_routing import (  # noqa: E402
    load_poc_mapping,
    poc_mapping_index,
    resolve_row_poc,
)


REGION = "cn"
DATASET_ID = "3888816"
QUERY_LIMIT = "50000"
TEST_GROUP_CHAT_ID = "oc_9c691aa76c22a16207c6f443eac25816"
TEST_GROUP_NAME = "人审阶段2群发验证-20260709"
DEFAULT_REQUEST = (
    "请按正规流程测试现有打标率：先查询近7天低效打标策略，"
    "按P0/P1/P2/notice分级，再把结果推送到飞书测试群。"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--levels", default="notice,P2,P1,P0")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--output-dir")
    parser.add_argument("--send-chat-id")
    parser.add_argument("--send-identity", choices=["bot", "user"], default="bot")
    parser.add_argument("--confirm-send", action="store_true")
    parser.add_argument("--sheet-url")
    parser.add_argument("--no-import-workbook", action="store_true")
    parser.add_argument("--idempotency-key")
    args = parser.parse_args()

    base = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT
        / "evals"
        / SCENARIO_KEY
        / "stage_2_runs"
        / f"{args.run_id}_formal_skill_flow"
    )
    base.mkdir(parents=True, exist_ok=True)
    stage1_path = (
        ROOT
        / "evals"
        / SCENARIO_KEY
        / "stage_1_runs"
        / f"{args.run_id}_formal_skill_flow_results.jsonl"
    )

    original_perception = run_perception(args.request)
    write_json(base / "perception_notification_request.json", original_perception)
    assert_notification_intent_or_raise(original_perception)

    analysis_request = build_analysis_request(original_perception)
    analysis_perception = run_perception(analysis_request)
    write_json(base / "perception_analysis_request.json", analysis_perception)
    assert_analysis_ready_or_raise(analysis_perception)

    stage1_record = run_analysis(args, base, stage1_path)

    sheet_url = args.sheet_url
    artifacts = build_notification(
        args=args,
        base=base,
        stage1_path=stage1_path,
        sheet_url=sheet_url,
        sent_payload=None,
    )
    sheet_url = artifacts.summary.get("sheet_url") or sheet_url

    dispatch_record: dict[str, Any] | None = None
    if args.send_chat_id:
        dispatch_record = dispatch_to_lark(
            args=args,
            base=base,
            artifacts=artifacts,
            sheet_url=sheet_url,
        )
        artifacts = build_notification(
            args=args,
            base=base,
            stage1_path=stage1_path,
            sheet_url=sheet_url,
            sent_payload=dispatch_record["send_result"],
        )
        dispatch_record["publish_summary"] = artifacts.publish_summary
        write_json(base / "host_dispatch_record.json", dispatch_record)

    summary = {
        "run_id": args.run_id,
        "request": args.request,
        "stage1_result": str(stage1_path),
        "stage2_output_dir": str(base),
        "level_counts": stage1_record["readonly_execution"]["level_counts"],
        "row_count": stage1_record["readonly_execution"]["row_count"],
        "sheet_url": sheet_url,
        "message_id": (dispatch_record or {}).get("message_id"),
        "target_chat_id": args.send_chat_id,
        "target_chat_name": TEST_GROUP_NAME
        if args.send_chat_id == TEST_GROUP_CHAT_ID
        else None,
        "skill_path_mode": active_path_mode(),
        "skill_paths": {
            "perception": str(PERCEPTION_SCRIPTS.relative_to(REPO_ROOT)),
            "analysis": str(ANALYSIS_SCRIPTS.relative_to(REPO_ROOT)),
            "notification_artifacts": str(NOTIFICATION_SCRIPTS.relative_to(REPO_ROOT)),
            "poc_routing": str(POC_ROUTING_SCRIPTS.relative_to(REPO_ROOT)),
        },
        "validators": [],
    }
    write_json(base / "formal_flow_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def run_perception(request: str) -> dict[str, Any]:
    return detect_label_rate_perception(raw_user_request=request)


def assert_notification_intent_or_raise(payload: dict[str, Any]) -> None:
    if payload.get("scenario_key") != SCENARIO_KEY:
        raise RuntimeError(f"perception did not identify {SCENARIO_KEY}: {payload}")
    workflow = payload.get("workflow_plan", {})
    if workflow.get("intent_type") not in {"analysis_then_notification", "analysis"}:
        raise RuntimeError(f"unsupported workflow_plan: {workflow}")


def build_analysis_request(perception: dict[str, Any]) -> str:
    time_window = perception.get("time_window") or "近7天"
    return (
        f"查询{time_window}低效打标策略，按P0/P1/P2/notice分级，"
        "按机审一级标签、策略ID、策略名称、送审原因拆分。"
    )


def assert_analysis_ready_or_raise(payload: dict[str, Any]) -> None:
    if payload.get("scenario_key") != SCENARIO_KEY:
        raise RuntimeError(f"analysis prerequisite scenario mismatch: {payload}")
    if payload.get("task_type") != "low_label_rate_grading":
        raise RuntimeError(f"analysis prerequisite task mismatch: {payload}")
    if payload.get("readiness", {}).get("status") != "ready":
        raise RuntimeError(f"analysis prerequisite is not ready: {payload}")


def run_analysis(
    args: argparse.Namespace,
    base: Path,
    stage1_path: Path,
) -> dict[str, Any]:
    levels = label_rate_analysis.parse_levels(args.levels)
    sql_map = label_rate_analysis.sql_by_level()
    query_plan = label_rate_analysis.build_query_plan(levels, sql_map)
    write_json(base / "analysis_query_plan.json", query_plan)
    write_json(base / "analysis_sql_by_level.json", sql_map)

    freshness_sql = (
        "SELECT max(`[p_date]`) AS max_dt, count() AS c "
        "FROM olap_content_security_community.dws_sft_tcs_review_task_detail_di "
        "WHERE `[p_date]` >= today() - 3"
    )
    freshness = run_aeolus_query(freshness_sql, limit="10")
    write_json(base / "analysis_freshness_check.json", freshness)

    mapping_index = poc_mapping_index(load_poc_mapping())
    payloads: dict[str, dict[str, Any]] = {}
    for level in levels:
        payload = run_aeolus_query(sql_map[level], limit=QUERY_LIMIT)
        payloads[level] = payload
        write_json(base / f"analysis_payload_{level}.json", payload, compact=True)

    records = label_rate_analysis.build_records(
        payloads,
        levels,
        sql_map,
        row_enricher=lambda row: build_poc_row_enrichment(row, mapping_index),
    )
    stage1_path.parent.mkdir(parents=True, exist_ok=True)
    stage1_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )
    sample = records[1]
    write_json(
        base / "analysis_summary.json",
        {
            "stage1_result": str(stage1_path),
            "freshness": freshness["data"]["rows"],
            "level_counts": sample["readonly_execution"]["level_counts"],
            "row_count": sample["readonly_execution"]["row_count"],
            "source_footer": sample["source_footer"],
        },
    )
    return sample


def run_aeolus_query(sql: str, *, limit: str) -> dict[str, Any]:
    command = [
        "bytedcli",
        "-j",
        "aeolus",
        "query",
        "-r",
        REGION,
        DATASET_ID,
        sql,
        "--limit",
        limit,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "Aeolus query failed:\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("status") != "success":
        raise RuntimeError(f"Aeolus query returned non-success: {payload}")
    return payload


def build_poc_row_enrichment(
    row: dict[str, Any],
    mapping_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    poc = resolve_row_poc(row, mapping_index)
    poc_name = poc.get("poc_name") or "未映射"
    return {
        "poc_name": poc_name,
        "POC": poc_name,
        "poc_open_id": poc.get("poc_open_id"),
        "poc_mapping_status": poc.get("mapping_status"),
    }


def build_notification(
    *,
    args: argparse.Namespace,
    base: Path,
    stage1_path: Path,
    sheet_url: str | None,
    sent_payload: dict[str, Any] | None,
) -> Any:
    return build_label_rate_notification_artifacts(
        source_path=stage1_path,
        output_dir=base,
        top_n=args.top_n,
        sheet_url=sheet_url,
        identity=args.send_identity,
        title="正规流程复跑：近7天低效打标策略全等级结果",
        self_send_requested=bool(args.send_chat_id),
        sent_payload=sent_payload,
        target_user_id=None,
        target_chat_id=args.send_chat_id,
        auto_import_sheet=not args.no_import_workbook,
    )


def import_workbook(workbook_path: Path, *, name: str, base: Path) -> str:
    payload = run_lark_cli(
        [
            "lark-cli",
            "sheets",
            "+workbook-import",
            "--json",
            "--as",
            "user",
            "--file",
            relative_to_repo(workbook_path),
            "--name",
            name,
        ]
    )
    write_json(base / "sheet_import_result.json", payload)
    url = payload.get("data", {}).get("url")
    if not url:
        raise RuntimeError(f"workbook import did not return url: {payload}")
    return str(url)


def dispatch_to_lark(
    *,
    args: argparse.Namespace,
    base: Path,
    artifacts: Any,
    sheet_url: str | None,
) -> dict[str, Any]:
    checks = run_pre_send_checks(args=args, artifacts=artifacts, sheet_url=sheet_url)
    card_content = artifacts.card.card_path.read_text(encoding="utf-8")
    idempotency_key = args.idempotency_key or safe_idempotency_key(
        f"formalflow-{args.run_id}-{args.send_chat_id}"
    )
    dry_run = run_lark_cli(
        [
            "lark-cli",
            "im",
            "+messages-send",
            "--as",
            args.send_identity,
            "--chat-id",
            str(args.send_chat_id),
            "--msg-type",
            "interactive",
            "--content",
            card_content,
            "--idempotency-key",
            idempotency_key,
            "--dry-run",
        ],
        expect_json=False,
    )
    write_text(base / "lark_send_dry_run.txt", dry_run)
    sent_payload = run_lark_cli(
        [
            "lark-cli",
            "im",
            "+messages-send",
            "--json",
            "--as",
            args.send_identity,
            "--chat-id",
            str(args.send_chat_id),
            "--msg-type",
            "interactive",
            "--content",
            card_content,
            "--idempotency-key",
            idempotency_key,
        ]
    )
    write_json(base / "lark_send_result.json", sent_payload)
    if not sent_payload.get("ok"):
        raise RuntimeError(f"lark send failed: {sent_payload}")
    data = sent_payload.get("data", {})
    record = {
        "schema_version": "formal_flow_host_dispatch.v1",
        "confirmed_by_user": args.confirm_send,
        "target_chat_id": args.send_chat_id,
        "target_chat_name": TEST_GROUP_NAME
        if args.send_chat_id == TEST_GROUP_CHAT_ID
        else None,
        "identity": args.send_identity,
        "idempotency_key": idempotency_key,
        "pre_send_checks": checks,
        "dry_run_request_captured": True,
        "send_result": sent_payload,
        "message_id": data.get("message_id"),
        "chat_id": data.get("chat_id"),
        "create_time": data.get("create_time"),
        "online_write_executed": False,
    }
    write_json(base / "host_dispatch_record.json", record)
    return record


def run_pre_send_checks(
    *,
    args: argparse.Namespace,
    artifacts: Any,
    sheet_url: str | None,
) -> list[dict[str, Any]]:
    checks = [
        check("confirm_send", args.confirm_send, "real group send requires --confirm-send"),
        check(
            "target_is_test_group",
            args.send_chat_id == TEST_GROUP_CHAT_ID,
            f"target chat must be {TEST_GROUP_NAME}",
        ),
        check("sheet_url_present", bool(sheet_url), "sent card requires sheet_url"),
        check("card_hash_ok", artifacts.card.hash_check.get("ok") is True, "card hash mismatch"),
        check(
            "poc_routing_complete",
            not artifacts.notification_draft.get("poc_routing", {}).get("unmapped_labels"),
            "POC routing has unmapped labels",
        ),
    ]
    failed = [item for item in checks if item["status"] != "pass"]
    if failed:
        raise RuntimeError(f"pre-send checks failed: {failed}")
    return checks


def check(check_id: str, passed: bool, message: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "message": message,
    }


def run_lark_cli(
    command: list[str],
    *,
    expect_json: bool = True,
) -> dict[str, Any] | str:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
            "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
        },
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "lark-cli command failed:\n"
            f"args={command}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    if not expect_json:
        return completed.stdout
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli returned non-json output: {completed.stdout}") from exc


def safe_idempotency_key(raw: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "", raw)
    return (key[-48:] or "formalflow")


def relative_to_repo(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(value, ensure_ascii=False, indent=2)
    )
    path.write_text(text + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


if __name__ == "__main__":
    main()
