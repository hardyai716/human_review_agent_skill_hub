#!/usr/bin/env python3
"""Validate core Skills as standalone release packages."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
SKILLS_ROOT = HUMAN_REVIEW_OPS_ROOT / "skills"
MANIFEST_PATH = SKILLS_ROOT / "skill_release_manifest.json"
SKILLS = ("perception", "analysis", "notification", "resolution")
SCRIPT_LEVEL_VALIDATORS = {
    "perception": HUMAN_REVIEW_OPS_ROOT
    / "tools"
    / "validators"
    / "validate_label_rate_perception_scripts.py",
    "analysis": HUMAN_REVIEW_OPS_ROOT
    / "tools"
    / "validators"
    / "validate_label_rate_analysis_scripts.py",
    "notification": HUMAN_REVIEW_OPS_ROOT
    / "tools"
    / "validators"
    / "validate_label_rate_notification_scripts.py",
}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt"}
LOCAL_PATH_PATTERNS = {
    "mac_user_home": re.compile(r"/Users/[A-Za-z0-9._-]+"),
    "linux_user_home": re.compile(r"/home/[A-Za-z0-9._-]+"),
    "windows_user_home": re.compile(r"[A-Za-z]:\\Users\\"),
    "workspace_desktop_path": re.compile(r"Desktop/人审运营"),
}
FORBIDDEN_RUNTIME_REFERENCE_PATTERNS = {
    "external_relative_scenario_package": re.compile(
        r"\.\./\.\./\.\./references/scenarios"
    ),
    "external_human_review_ops_scenario_package": re.compile(
        r"human_review_ops/references/scenarios"
    ),
    "split_runtime_scenario_markdown": re.compile(
        r"(?:references/scenarios/|scenarios/|/)"
        r"(?:efficiency-label-rate|efficiency-auto-disposal-accuracy)"
        r"\.(?:manifest|metric_contract|dataset_reference|analysis|examples|"
        r"notification_templates|owner_routing|sla|state_machine)\.md\b"
    ),
}
# SKILL.md must stay self-contained: it may not point at dev-time tooling that
# is not shipped with the Skill package.
SKILL_MD_FORBIDDEN_PATTERNS = {
    "external_tools_reference_in_skill_md": re.compile(r"human_review_ops/tools/"),
}
SECRET_PATTERNS = {
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}"),
    "assigned_secret": re.compile(
        r"(?i)\b(token|secret|password|api[_-]?key)\b\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9._\-]{24,}"
    ),
}
PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "dummy",
    "sample",
    "smoke",
    "xxxx",
    "<",
    "{{",
    "your_",
)


class ValidationError(Exception):
    """Raised when a standalone package validation step fails."""


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{rel(path)} JSON parse failed: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{rel(path)} must be a JSON object.")
    return data


def manifest_path(raw_path: str, issues: list[str]) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        issues.append("Manifest path must be a non-empty string.")
        return None
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        issues.append(f"Manifest path must be relative to skills root: {raw_path}")
        return None
    return SKILLS_ROOT / path


def validate_manifest(
    selected_skills: tuple[str, ...],
    issues: list[str],
) -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        issues.append(f"Missing release manifest: {rel(MANIFEST_PATH)}")
        return {}

    try:
        manifest = load_json_object(MANIFEST_PATH)
    except ValidationError as exc:
        issues.append(str(exc))
        return {}

    if manifest.get("schema_version") != "human_review_ops_skill_release_manifest.v1":
        issues.append(f"{rel(MANIFEST_PATH)} schema_version mismatch.")
    if manifest.get("package_root") != "human_review_ops/skills":
        issues.append(f"{rel(MANIFEST_PATH)} package_root must be human_review_ops/skills.")

    skills = manifest.get("skills")
    if not isinstance(skills, dict):
        issues.append(f"{rel(MANIFEST_PATH)} skills must be an object.")
        return manifest

    for skill in selected_skills:
        entry = skills.get(skill)
        if not isinstance(entry, dict):
            issues.append(f"{rel(MANIFEST_PATH)} missing skill entry: {skill}")
            continue
        validate_manifest_skill_entry(skill, entry, issues)
    scan_text_file(MANIFEST_PATH, issues)
    return manifest


def validate_manifest_skill_entry(
    skill: str,
    entry: dict[str, Any],
    issues: list[str],
) -> None:
    declared_paths: set[str] = set()
    for field in ("skill_md", "test_prompts"):
        raw_path = entry.get(field)
        path = manifest_path(raw_path, issues)
        if path is None:
            continue
        declared_paths.add(raw_path)
        if not raw_path.startswith(f"{skill}/"):
            issues.append(f"{rel(MANIFEST_PATH)} {skill}.{field} points outside its Skill.")
        if not path.exists():
            issues.append(f"{rel(MANIFEST_PATH)} {skill}.{field} missing path: {raw_path}")

    for field in ("references", "assets"):
        values = entry.get(field)
        if not isinstance(values, list) or not values:
            issues.append(f"{rel(MANIFEST_PATH)} {skill}.{field} must be a non-empty array.")
            continue
        for raw_path in values:
            path = manifest_path(raw_path, issues)
            if path is None:
                continue
            declared_paths.add(raw_path)
            expected_part = f"{skill}/{field}/"
            if not raw_path.startswith(expected_part):
                issues.append(
                    f"{rel(MANIFEST_PATH)} {skill}.{field} path outside {expected_part}: "
                    f"{raw_path}"
                )
            if not path.exists():
                issues.append(f"{rel(MANIFEST_PATH)} missing {skill}.{field} path: {raw_path}")

    scripts = entry.get("scripts")
    if not isinstance(scripts, list) or not scripts:
        issues.append(f"{rel(MANIFEST_PATH)} {skill}.scripts must be a non-empty array.")
    else:
        for index, script in enumerate(scripts):
            validate_manifest_script_entry(skill, script, index, declared_paths, issues)

    release_assets = entry.get("release_assets")
    if not isinstance(release_assets, list) or not release_assets:
        issues.append(f"{rel(MANIFEST_PATH)} {skill}.release_assets must be non-empty.")
    else:
        release_asset_set = set(release_assets)
        missing = sorted(declared_paths - release_asset_set)
        if missing:
            issues.append(
                f"{rel(MANIFEST_PATH)} {skill}.release_assets missing declared paths: "
                f"{', '.join(missing)}"
            )
        for raw_path in release_assets:
            path = manifest_path(raw_path, issues)
            if path is not None and not path.exists():
                issues.append(
                    f"{rel(MANIFEST_PATH)} {skill}.release_assets missing path: {raw_path}"
                )

    dependencies = entry.get("external_dependencies")
    if not isinstance(dependencies, list) or not all(
        isinstance(item, str) for item in dependencies
    ):
        issues.append(f"{rel(MANIFEST_PATH)} {skill}.external_dependencies must be strings.")


def validate_manifest_script_entry(
    skill: str,
    script: Any,
    index: int,
    declared_paths: set[str],
    issues: list[str],
) -> None:
    if not isinstance(script, dict):
        issues.append(f"{rel(MANIFEST_PATH)} {skill}.scripts[{index}] must be an object.")
        return

    raw_path = script.get("path")
    path = manifest_path(raw_path, issues)
    if path is not None:
        declared_paths.add(raw_path)
        expected_part = f"{skill}/scripts/"
        if not raw_path.startswith(expected_part):
            issues.append(
                f"{rel(MANIFEST_PATH)} {skill}.scripts[{index}] outside scripts dir: "
                f"{raw_path}"
            )
        if not path.exists():
            issues.append(
                f"{rel(MANIFEST_PATH)} {skill}.scripts[{index}] missing path: {raw_path}"
            )

    for field in ("entrypoint", "smoke_command"):
        if not isinstance(script.get(field), str) or not script[field]:
            issues.append(f"{rel(MANIFEST_PATH)} {skill}.scripts[{index}].{field} missing.")

    side_effects = script.get("side_effects")
    if not isinstance(side_effects, list) or "none" not in side_effects:
        issues.append(
            f"{rel(MANIFEST_PATH)} {skill}.scripts[{index}].side_effects must include none."
        )


def validate_skill_layout(skill: str, issues: list[str]) -> None:
    skill_dir = SKILLS_ROOT / skill
    if not skill_dir.exists():
        issues.append(f"Missing Skill directory: {rel(skill_dir)}")
        return

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        issues.append(f"Missing SKILL.md: {rel(skill_md)}")

    test_prompt_candidates = [
        skill_dir / "test-prompts.json",
        skill_dir / "assets" / "test-prompts.json",
    ]
    if not any(path.exists() for path in test_prompt_candidates):
        issues.append(
            "Missing test-prompts.json: "
            + " or ".join(rel(path) for path in test_prompt_candidates)
        )

    for required_dir in ("references", "assets", "scripts"):
        path = skill_dir / required_dir
        if not path.is_dir():
            issues.append(f"Missing {required_dir}/ directory: {rel(path)}")
            continue
        if required_dir in {"references", "assets"} and not any(path.rglob("*")):
            issues.append(f"{rel(path)} must contain at least one release asset.")

    scripts = list((skill_dir / "scripts").rglob("*.py"))
    if not scripts:
        issues.append(f"{rel(skill_dir / 'scripts')} must contain Python entry scripts.")


def validate_skill_md_self_containment(skill: str, issues: list[str]) -> None:
    skill_md = SKILLS_ROOT / skill / "SKILL.md"
    if not skill_md.exists():
        return
    text = skill_md.read_text(encoding="utf-8", errors="ignore")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in SKILL_MD_FORBIDDEN_PATTERNS.items():
            if pattern.search(line):
                issues.append(
                    f"{rel(skill_md)}:{line_number} contains forbidden external "
                    f"reference: {pattern_name}"
                )


def validate_python_compilation(skill: str, issues: list[str]) -> int:
    count = 0
    with tempfile.TemporaryDirectory(prefix="skill-compile-") as tmp:
        tmp_path = Path(tmp)
        for script in sorted((SKILLS_ROOT / skill / "scripts").rglob("*.py")):
            count += 1
            cfile = tmp_path / f"{skill}-{script.stem}-{count}.pyc"
            try:
                py_compile.compile(str(script), cfile=str(cfile), doraise=True)
            except py_compile.PyCompileError as exc:
                issues.append(f"{rel(script)} failed to compile: {exc.msg}")
    return count


def declared_dependency_names(entry: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for dependency in entry.get("external_dependencies", []):
        name = re.split(r"[<>=!~\s]", dependency, maxsplit=1)[0]
        name = name.replace("-", "_").strip().lower()
        if name and name != "python":
            names.add(name)
    return names


def validate_external_dependencies(
    skill: str,
    manifest: dict[str, Any],
    issues: list[str],
) -> None:
    entry = manifest.get("skills", {}).get(skill, {})
    if not isinstance(entry, dict):
        return
    declared = declared_dependency_names(entry)
    script_dir = SKILLS_ROOT / skill / "scripts"
    local_modules = {path.stem for path in script_dir.rglob("*.py")}
    missing: set[str] = set()

    for script in sorted(script_dir.rglob("*.py")):
        try:
            tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except SyntaxError as exc:
            issues.append(f"{rel(script)} failed AST parse: {exc}")
            continue
        for module_name in imported_top_level_modules(tree):
            if is_stdlib_module(module_name) or module_name in local_modules:
                continue
            if module_name not in declared:
                missing.add(module_name)

    if missing:
        issues.append(
            f"{skill} scripts use undeclared external dependencies: "
            f"{', '.join(sorted(missing))}"
        )


def imported_top_level_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".", 1)[0])
    modules.discard("__future__")
    return modules


def is_stdlib_module(module_name: str) -> bool:
    if module_name in sys.builtin_module_names:
        return True
    stdlib_modules = getattr(sys, "stdlib_module_names", None)
    if stdlib_modules and module_name in stdlib_modules:
        return True

    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        return False
    if spec.origin in {"built-in", "frozen"}:
        return True

    origin = Path(spec.origin)
    if "site-packages" in origin.parts or "dist-packages" in origin.parts:
        return False
    try:
        origin.relative_to(Path(sys.base_prefix))
    except ValueError:
        return False
    return True


def validate_text_risks(skill: str, issues: list[str]) -> None:
    for path in sorted((SKILLS_ROOT / skill).rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            scan_text_file(path, issues)


def scan_text_file(path: Path, issues: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in LOCAL_PATH_PATTERNS.items():
            if pattern.search(line):
                issues.append(
                    f"{rel(path)}:{line_number} contains local path risk: {pattern_name}"
                )
        for pattern_name, pattern in FORBIDDEN_RUNTIME_REFERENCE_PATTERNS.items():
            if pattern.search(line):
                issues.append(
                    f"{rel(path)}:{line_number} contains forbidden runtime "
                    f"reference: {pattern_name}"
                )
        lowered = line.lower()
        if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
            continue
        for pattern_name, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                issues.append(
                    f"{rel(path)}:{line_number} contains possible real secret: "
                    f"{pattern_name}"
                )


def run_skill_smoke(skill: str, issues: list[str]) -> None:
    if skill in SCRIPT_LEVEL_VALIDATORS:
        run_subprocess_smoke(
            [
                sys.executable,
                str(SCRIPT_LEVEL_VALIDATORS[skill]),
            ],
            f"{skill} script-level smoke",
            issues,
        )
        return
    if skill == "resolution":
        run_resolution_smoke(issues)
        return
    issues.append(f"No standalone smoke configured for Skill: {skill}")


def run_subprocess_smoke(command: list[str], label: str, issues: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        details = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part.strip()
        )
        issues.append(f"{label} failed with exit {completed.returncode}: {details}")


def run_resolution_smoke(issues: list[str]) -> None:
    script_path = SKILLS_ROOT / "resolution" / "scripts" / "build_label_rate_manual_tracking.py"
    with tempfile.TemporaryDirectory(prefix="label-rate-resolution-smoke-") as tmp:
        tmp_path = Path(tmp)
        notification_draft_path = tmp_path / "notification_draft.json"
        send_plan_path = tmp_path / "send_plan.json"
        output_path = tmp_path / "manual_tracking.json"
        write_json(notification_draft_path, build_resolution_notification_draft())
        write_json(send_plan_path, build_resolution_send_plan())
        run_subprocess_smoke(
            [
                sys.executable,
                str(script_path),
                "--notification-draft",
                str(notification_draft_path),
                "--send-plan",
                str(send_plan_path),
                "--output",
                str(output_path),
            ],
            "resolution CLI smoke",
            issues,
        )
        if output_path.exists():
            validate_resolution_output(load_json_object(output_path), issues)
        else:
            issues.append("resolution CLI smoke did not create manual_tracking.json.")


def build_resolution_notification_draft() -> dict[str, Any]:
    routing_rules = {
        level: {
            "reason_count": index + 1,
            "target_roles": ["label_rate_poc"],
            "action_required": "manual_follow_up",
            "recipient_resolution": {
                "status": "mapped_name_only",
                "requires_open_id_confirmation": True,
            },
        }
        for index, level in enumerate(("notice", "P2", "P1", "P0"))
    }
    return {
        "schema_version": "stage_2_notification_draft_detail.v1",
        "scenario_key": "efficiency-label-rate",
        "level_counts": {"notice": 4, "P2": 1, "P1": 1, "P0": 1},
        "data_link": {"sheet_url": "https://example.com/sheets/smoke"},
        "poc_routing": {
            "poc_routing_plan": "poc_routing_plan.json",
            "routing_rules": routing_rules,
        },
    }


def build_resolution_send_plan() -> dict[str, Any]:
    return {
        "schema_version": "stage_2_send_plan.v1",
        "requires_confirmation": True,
        "group_send_blocked": True,
        "sent": False,
        "real_group_send_executed": False,
        "content_source": {
            "notification_draft": "notification_draft.json",
            "card_json": "publish/low_efficiency_grading.card.json",
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_resolution_output(payload: dict[str, Any], issues: list[str]) -> None:
    if payload.get("schema_version") != "stage_2_manual_tracking.v1":
        issues.append("resolution smoke output schema_version mismatch.")
    if payload.get("tracking_mode") != "local_debug_only":
        issues.append("resolution smoke output must stay local_debug_only.")
    levels = [record.get("severity_level") for record in payload.get("tracking_records", [])]
    if levels != ["notice", "P2", "P1", "P0"]:
        issues.append(f"resolution smoke output levels mismatch: {levels}")
    safety = payload.get("safety", {})
    expected = {
        "requires_confirmation": True,
        "group_send_blocked": True,
        "group_send_sent": False,
        "real_group_send_executed": False,
        "online_write_executed": False,
        "online_state_write_allowed": False,
    }
    if safety != expected:
        issues.append(f"resolution smoke safety mismatch: {safety}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skills",
        nargs="+",
        choices=SKILLS,
        default=list(SKILLS),
        help="Subset of core Skills to validate.",
    )
    parser.add_argument(
        "--skip-dry-run",
        action="store_true",
        help="Only validate package shape, compilation, manifest, and dependency metadata.",
    )
    args = parser.parse_args()

    selected_skills = tuple(args.skills)
    issues: list[str] = []
    manifest = validate_manifest(selected_skills, issues)
    script_counts: dict[str, int] = {}

    for skill in selected_skills:
        validate_skill_layout(skill, issues)
        validate_skill_md_self_containment(skill, issues)
        script_counts[skill] = validate_python_compilation(skill, issues)
        validate_external_dependencies(skill, manifest, issues)
        validate_text_risks(skill, issues)
        if not args.skip_dry_run:
            run_skill_smoke(skill, issues)

    if issues:
        print("Skill standalone smoke FAILED")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)

    mode = "metadata-only" if args.skip_dry_run else "with dry-run"
    print(f"Skill standalone smoke OK ({mode})")
    for skill in selected_skills:
        print(f"- {skill}: scripts={script_counts.get(skill, 0)}")


if __name__ == "__main__":
    main()
