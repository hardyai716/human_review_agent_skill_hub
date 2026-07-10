#!/usr/bin/env python3
"""Regression validator for AgentBuddy analysis eval prompts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
CLI_PATH = (
    HUMAN_REVIEW_OPS_ROOT
    / "skills"
    / "analysis"
    / "scripts"
    / "analyzing_ops_metrics.py"
)
SCHEMA_VERSION = "analyzing_ops_metrics.v1"
EXPECTED_ARTIFACTS = {
    "query_plan": "query_plan.json",
    "source_footer": "source_footer.json",
    "analysis_result": "analysis_result.json",
    "summary": "analysis_summary.md",
}
BAD_TEXT_PATTERNS = (
    "command not found",
    "not recognized as an internal or external command",
    "<<EOF",
    "<<'EOF'",
    "<< EOF",
    "cat <<",
    "cat >",
    "heredoc",
    "placeholder",
    "smoke_",
    "_low_label_reason",
)
FORBIDDEN_SUCCESS_DIMENSIONS = {"community_audit_style"}


@dataclass(frozen=True)
class EvalCase:
    name: str
    args: list[str]
    expected_status: str
    expected_command: str
    expected_analysis_mode: str | None = None
    expected_next_skill: str | None = None
    expected_returncode: int = 0
    allow_sql: bool = True
    composite: bool = False


def main() -> None:
    if not CLI_PATH.exists():
        raise AssertionError(f"Missing analysis CLI: {CLI_PATH.relative_to(REPO_ROOT)}")

    with tempfile.TemporaryDirectory(prefix="analysis-eval-regression-") as tmp:
        temp_root = Path(tmp)
        for case in eval_cases():
            run_eval_case(case, temp_root / case.name)
        run_schema_block_case(temp_root / "schema_block_unknown_field")

    print("Analysis eval regression OK")


def eval_cases() -> list[EvalCase]:
    return [
        EvalCase(
            name="lowest_reason",
            args=[
                "lowest-reason",
                "--days",
                "7",
                "--execute",
                "never",
                "--format",
                "json",
                "--prompt",
                "近7天低打标率最低 reason 分级，输出 P0/P1/P2/notice 的 QueryPlan 和固定 artifacts",
            ],
            expected_status="dry_run",
            expected_command="lowest-reason",
            expected_analysis_mode="low_label_rate_grading",
        ),
        EvalCase(
            name="trend",
            args=[
                "trend",
                "--days",
                "14",
                "--execute",
                "never",
                "--format",
                "json",
                "--prompt",
                "看近14天打标率整体趋势，只需要只读分析产物",
            ],
            expected_status="dry_run",
            expected_command="trend",
            expected_analysis_mode="label_rate_trend",
        ),
        EvalCase(
            name="label_breakdown",
            args=[
                "label-breakdown",
                "--days",
                "7",
                "--dimensions",
                "mach_root_label_name,strategy_id,strategy_name,reason",
                "--execute",
                "never",
                "--format",
                "json",
                "--prompt",
                "按机审一级标签、策略ID、策略名称和 reason 拆解近7天打标率",
            ],
            expected_status="dry_run",
            expected_command="label-breakdown",
            expected_analysis_mode="label_rate_label_breakdown",
        ),
        EvalCase(
            name="notification_handoff",
            args=[
                "handoff",
                "--intent",
                "auto",
                "--execute",
                "never",
                "--format",
                "json",
                "--prompt",
                "请生成飞书卡片、send_plan，并通知 POC 群",
            ],
            expected_status="handoff",
            expected_command="handoff",
            expected_next_skill="notification",
            allow_sql=False,
        ),
        EvalCase(
            name="resolution_handoff",
            args=[
                "handoff",
                "--intent",
                "auto",
                "--execute",
                "never",
                "--format",
                "json",
                "--prompt",
                "把问题记录跟进，进入闭环，后续继续观察状态流转",
            ],
            expected_status="handoff",
            expected_command="handoff",
            expected_next_skill="resolution",
            allow_sql=False,
        ),
        EvalCase(
            name="ambiguous_scene_handoff",
            args=[
                "handoff",
                "--intent",
                "auto",
                "--execute",
                "never",
                "--format",
                "json",
                "--prompt",
                "达标率下降，不确定是打标率还是自动处置准确率，先判断应该看哪个指标",
            ],
            expected_status="handoff",
            expected_command="handoff",
            expected_next_skill="perception",
            allow_sql=False,
        ),
        EvalCase(
            name="composite_task_handoff",
            args=[
                "lowest-reason",
                "--days",
                "7",
                "--execute",
                "never",
                "--format",
                "json",
                "--prompt",
                "先分析近7天低打标率最低 reason，然后通知 POC 并安排闭环跟进",
            ],
            expected_status="dry_run",
            expected_command="lowest-reason",
            expected_analysis_mode="low_label_rate_grading",
            expected_next_skill="notification_or_resolution",
            composite=True,
        ),
    ]


def run_eval_case(case: EvalCase, output_dir: Path) -> None:
    completed, stdout_payload = run_cli(
        args=case.args,
        output_dir=output_dir,
        expected_returncode=case.expected_returncode,
    )
    artifacts = load_artifacts(stdout_payload, output_dir)
    assert_no_bad_text(completed.stdout + completed.stderr, f"{case.name} process output")
    assert_no_bad_artifact_text(artifacts, case.name)
    assert_common_contract(case, stdout_payload, artifacts)

    if case.expected_next_skill:
        assert_handoff(case, artifacts)
    else:
        assert_no_handoff_slip(case, artifacts)

    if case.expected_analysis_mode:
        query_plan = artifacts["query_plan"]
        if query_plan.get("analysis_mode") != case.expected_analysis_mode:
            raise AssertionError(
                f"{case.name} analysis_mode mismatch: {query_plan.get('analysis_mode')}"
            )
        assert_schema_passed(case, query_plan)


def run_schema_block_case(output_dir: Path) -> None:
    completed, stdout_payload = run_cli(
        args=[
            "label-breakdown",
            "--dimensions",
            "community_audit_style",
            "--execute",
            "never",
            "--format",
            "json",
            "--prompt",
            "按 community_audit_style 拆解近7天打标率",
        ],
        output_dir=output_dir,
        expected_returncode=2,
    )
    artifacts = load_artifacts(stdout_payload, output_dir)
    assert_no_bad_text(completed.stdout + completed.stderr, "schema block process output")
    assert_no_bad_artifact_text(artifacts, "schema_block_unknown_field")

    result = artifacts["analysis_result"]
    query_plan = artifacts["query_plan"]
    detail = str(result.get("detail", ""))
    schema_error = str(query_plan.get("schema_validation", {}).get("error", ""))
    if stdout_payload.get("status") != "blocked":
        raise AssertionError("Unknown field case must emit blocked status.")
    if result.get("stop_reason") != "schema_validation_error":
        raise AssertionError(f"Unexpected stop_reason: {result.get('stop_reason')}")
    if "schema validation error" not in f"{detail}\n{schema_error}".lower():
        raise AssertionError("Unknown field case must output schema validation error.")
    if query_plan.get("schema_validation", {}).get("status") != "failed":
        raise AssertionError("Unknown field case must mark schema_validation failed.")
    if "community_audit_style" in query_plan.get("dimensions", []):
        raise AssertionError("Unknown field must not be accepted as a dimension.")
    assert_safety(result, sql_executed=False)


def run_cli(
    *,
    args: list[str],
    output_dir: Path,
    expected_returncode: int,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(CLI_PATH),
        *args,
        "--output-dir",
        str(output_dir),
    ]
    command_text = " ".join(command)
    assert_no_bad_text(command_text, "validator subprocess command")

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != expected_returncode:
        raise AssertionError(
            "CLI returncode mismatch: "
            f"expected={expected_returncode} actual={completed.returncode} "
            f"stdout={completed.stdout} stderr={completed.stderr}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"CLI stdout is not JSON: {completed.stdout}") from exc
    if not isinstance(payload, dict):
        raise AssertionError("CLI stdout JSON must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise AssertionError(f"CLI stdout schema_version mismatch: {payload.get('schema_version')}")
    return completed, payload


def load_artifacts(stdout_payload: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    artifact_paths = stdout_payload.get("artifacts")
    if not isinstance(artifact_paths, dict):
        raise AssertionError("CLI stdout missing artifacts mapping.")
    if set(artifact_paths) != set(EXPECTED_ARTIFACTS):
        raise AssertionError(f"Unexpected artifact keys: {sorted(artifact_paths)}")

    loaded: dict[str, Any] = {}
    for key, filename in EXPECTED_ARTIFACTS.items():
        expected_path = output_dir / filename
        actual_path = Path(str(artifact_paths[key]))
        if actual_path != expected_path:
            raise AssertionError(
                f"{key} artifact path mismatch: expected={expected_path} actual={actual_path}"
            )
        if not actual_path.exists():
            raise AssertionError(f"Missing artifact: {actual_path}")
        if key == "summary":
            summary = actual_path.read_text(encoding="utf-8")
            if not summary.strip():
                raise AssertionError("analysis_summary.md must not be empty.")
            loaded[key] = summary
        else:
            try:
                payload = json.loads(actual_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{filename} is not parseable JSON.") from exc
            if not isinstance(payload, dict):
                raise AssertionError(f"{filename} must contain a JSON object.")
            loaded[key] = payload
    return loaded


def assert_common_contract(
    case: EvalCase,
    stdout_payload: dict[str, Any],
    artifacts: dict[str, Any],
) -> None:
    result = artifacts["analysis_result"]
    query_plan = artifacts["query_plan"]
    source_footer = artifacts["source_footer"]
    summary = artifacts["summary"]

    if stdout_payload.get("status") != case.expected_status:
        raise AssertionError(
            f"{case.name} stdout status mismatch: {stdout_payload.get('status')}"
        )
    if stdout_payload.get("command") != case.expected_command:
        raise AssertionError(
            f"{case.name} stdout command mismatch: {stdout_payload.get('command')}"
        )
    if result.get("schema_version") != SCHEMA_VERSION:
        raise AssertionError(f"{case.name} analysis_result schema_version mismatch.")
    if result.get("command") != case.expected_command:
        raise AssertionError(f"{case.name} analysis_result command mismatch.")
    if result.get("status") != case.expected_status:
        raise AssertionError(f"{case.name} analysis_result status mismatch: {result.get('status')}")
    if result.get("artifacts") != stdout_payload.get("artifacts"):
        raise AssertionError(f"{case.name} analysis_result artifacts mismatch.")
    if result.get("query_plan") != query_plan:
        raise AssertionError(f"{case.name} analysis_result query_plan mismatch.")
    if result.get("source_footer") != source_footer:
        raise AssertionError(f"{case.name} analysis_result source_footer mismatch.")

    for field in ("query_plan_id", "scenario_key", "task_type", "analysis_mode"):
        if field not in query_plan:
            raise AssertionError(f"{case.name} query_plan missing {field}.")
    for field in ("query_plan_id", "review_status", "confidence_tier", "run_mode"):
        if field not in source_footer:
            raise AssertionError(f"{case.name} source_footer missing {field}.")
    if "SELECT" in summary.upper():
        raise AssertionError(f"{case.name} summary must not inline SQL.")
    assert_safety(result, sql_executed=False)

    if not case.allow_sql and query_plan.get("sql") is not None:
        raise AssertionError(f"{case.name} handoff query_plan must not contain SQL.")
    if case.allow_sql and not case.composite and result.get("stop_reason") != "execute_never":
        raise AssertionError(f"{case.name} dry-run stop_reason mismatch.")


def assert_schema_passed(case: EvalCase, query_plan: dict[str, Any]) -> None:
    schema_validation = query_plan.get("schema_validation")
    if not isinstance(schema_validation, dict):
        raise AssertionError(f"{case.name} missing schema_validation.")
    if schema_validation.get("status") != "passed":
        raise AssertionError(f"{case.name} schema_validation did not pass.")
    allowed_dimensions = set(schema_validation.get("allowed_dimensions", []))
    dimensions = set(query_plan.get("dimensions", []))
    if not dimensions.issubset(allowed_dimensions):
        raise AssertionError(
            f"{case.name} query_plan contains unsupported dimensions: "
            f"{sorted(dimensions - allowed_dimensions)}"
        )
    forbidden_dimensions = dimensions & FORBIDDEN_SUCCESS_DIMENSIONS
    if forbidden_dimensions:
        raise AssertionError(
            f"{case.name} accepted forbidden dimensions: {sorted(forbidden_dimensions)}"
        )


def assert_handoff(case: EvalCase, artifacts: dict[str, Any]) -> None:
    result = artifacts["analysis_result"]
    query_plan = artifacts["query_plan"]
    handoff = result.get("handoff")
    if not isinstance(handoff, dict):
        raise AssertionError(f"{case.name} missing handoff payload.")
    if handoff.get("next_skill") != case.expected_next_skill:
        raise AssertionError(
            f"{case.name} next_skill mismatch: {handoff.get('next_skill')}"
        )
    if not handoff.get("workflow_plan"):
        raise AssertionError(f"{case.name} handoff missing workflow_plan.")
    if not handoff.get("blocked_actions"):
        raise AssertionError(f"{case.name} handoff missing blocked_actions.")

    if case.composite:
        if query_plan.get("task_type") != "query_only":
            raise AssertionError("Composite prompt must keep analysis task_type=query_only.")
        if query_plan.get("handoff") != handoff:
            raise AssertionError("Composite prompt must attach handoff to query_plan.")
    else:
        if result.get("status") != "handoff":
            raise AssertionError(f"{case.name} handoff status mismatch.")
        if query_plan.get("task_type") != "handoff":
            raise AssertionError(f"{case.name} query_plan must be task_type=handoff.")
        if "readonly_execution" in result:
            raise AssertionError(f"{case.name} must not execute analysis before handoff.")


def assert_no_handoff_slip(case: EvalCase, artifacts: dict[str, Any]) -> None:
    result = artifacts["analysis_result"]
    if result.get("handoff"):
        raise AssertionError(f"{case.name} unexpectedly emitted handoff.")


def assert_safety(result: dict[str, Any], *, sql_executed: bool) -> None:
    safety = result.get("safety")
    if not isinstance(safety, dict):
        raise AssertionError("Missing safety payload.")
    expected = {
        "sql_executed": sql_executed,
        "notification_sent": False,
        "online_write_executed": False,
    }
    for key, expected_value in expected.items():
        if safety.get(key) is not expected_value:
            raise AssertionError(f"Unexpected safety.{key}: {safety.get(key)}")


def assert_no_bad_artifact_text(artifacts: dict[str, Any], context: str) -> None:
    for key, payload in artifacts.items():
        if key == "summary":
            text = str(payload)
        else:
            text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        assert_no_bad_text(text, f"{context} {key}")


def assert_no_bad_text(text: str, context: str) -> None:
    lower_text = text.lower()
    for pattern in BAD_TEXT_PATTERNS:
        if pattern.lower() in lower_text:
            raise AssertionError(f"{context} contains forbidden text: {pattern}")


if __name__ == "__main__":
    main()
