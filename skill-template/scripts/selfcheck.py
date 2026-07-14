#!/usr/bin/env python3
"""Self-check for the minimal scenario-level Skill template."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import scenario_flow


SKILL_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = SKILL_ROOT / "package_manifest.template.json"


def assert_required_files() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    required_files = manifest["required_files"]
    missing = [path for path in required_files if not (SKILL_ROOT / path).exists()]
    assert not missing, f"missing required files: {missing}"


def assert_skill_md_frontmatter() -> None:
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    assert "\nname:" in text, "SKILL.md frontmatter missing name"
    assert "\ndescription:" in text, "SKILL.md frontmatter missing description"
    assert "🔴 CHECKPOINT" in text, "SKILL.md must contain a safety checkpoint"


def assert_no_hardcoded_external_paths() -> None:
    forbidden_patterns = [
        "/" + "Users/",
        "." + "trae/skills/",
        "human_review_ops/" + "skills/",
        "human_review_ops/" + "references/",
    ]
    scan_roots = [
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "references",
        SKILL_ROOT / "assets",
        SKILL_ROOT / "scripts",
    ]
    violations: list[str] = []
    for root in scan_roots:
        paths = [root] if root.is_file() else list(root.rglob("*"))
        for path in paths:
            if path.name == "selfcheck.py" or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if pattern in text:
                    violations.append(f"{path.relative_to(SKILL_ROOT)} contains {pattern}")
    assert not violations, "hardcoded external path violations: " + "; ".join(violations)


def assert_perception_smoke() -> None:
    payload = scenario_flow.perception("帮我看 SCENARIO_NAME 近7天变化")
    assert payload["scenario_key"] == "scenario-key"
    assert payload["readiness"] == "ready"
    assert payload["next_stage"] == "analysis"

    blocked = scenario_flow.perception("SCENARIO_NAME 直接群发给所有 Owner 并拉群")
    assert blocked["readiness"] == "blocked"
    assert blocked["next_stage"] == "stop"


def assert_pipeline_smoke() -> None:
    records = scenario_flow.analysis_records("threshold_alert")
    sample = records[1]
    for key in ("readonly_execution", "analysis_result", "source_footer"):
        assert key in sample, f"analysis sample missing {key}"

    with tempfile.TemporaryDirectory(prefix="scenario-skill-template-") as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "analysis_result.jsonl"
        source_path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )
        output_dir = tmp_path / "notification"
        paths = scenario_flow.notify(source_path, output_dir)
        draft = scenario_flow.load_json(Path(paths["notification_draft"]))
        send_plan = scenario_flow.load_json(Path(paths["send_plan"]))
        tracking_path = tmp_path / "manual_tracking.json"
        tracking = scenario_flow.track(
            notification_draft=Path(paths["notification_draft"]),
            send_plan=Path(paths["send_plan"]),
            output=tracking_path,
        )
        assert draft["run_mode"] == "debug_only"
        assert send_plan["group_send_blocked"] is True
        assert send_plan["sent"] is False
        assert tracking["tracking_mode"] == "local_debug_only"
        assert tracking["safety"]["online_write_executed"] is False
        assert tracking["closure_check"]["can_close"] is False


def main() -> None:
    assert_required_files()
    assert_skill_md_frontmatter()
    assert_no_hardcoded_external_paths()
    assert_perception_smoke()
    assert_pipeline_smoke()
    print("scenario Skill template selfcheck OK")


if __name__ == "__main__":
    main()
