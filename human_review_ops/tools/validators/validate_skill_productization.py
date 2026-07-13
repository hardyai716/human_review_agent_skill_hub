#!/usr/bin/env python3
"""Validate productization baseline assets for core human-review operation Skills."""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
SKILLS_ROOT = HUMAN_REVIEW_OPS_ROOT / "skills"
MANIFEST_PATH = SKILLS_ROOT / "skill_release_manifest.json"
REGISTRY_PATH = HUMAN_REVIEW_OPS_ROOT / "configs" / "skill_path_registry.json"
AEOLUS_FIELD_CONTRACT_VALIDATOR = (
    HUMAN_REVIEW_OPS_ROOT / "tools" / "validators" / "validate_aeolus_field_contracts.py"
)
DEFAULT_SKILLS = ("perception", "analysis", "notification", "resolution")
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt"}
ALLOWED_CATEGORIES = {"should-trigger", "should-not-trigger"}
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
STRICT_REQUIRED_SECTIONS = {
    "trigger": ("触发条件", "Use When", "When to Use", "Trigger"),
    "do-not-use": ("禁止使用", "不适用", "Do Not Use", "Do-not-use", "Do not use"),
    "inputs": ("输入", "Inputs"),
    "outputs": ("输出", "Outputs"),
    "workflow": ("工作流", "Workflow"),
    "reference-loading": ("参考资料", "Reference Loading", "场景索引"),
    "scripts": ("脚本", "Scripts"),
    "failure-modes": ("失败处理", "Failure Modes", "失败分支"),
    "validation": ("验证", "Validation"),
}


class ValidationError(Exception):
    """Raised when a JSON asset cannot be parsed."""


def rel(path: Path) -> str:
    """Return a repository-relative path for readable validator output."""
    return str(path.relative_to(REPO_ROOT))


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{rel(path)} JSON parse failed: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{rel(path)} must be a JSON object.")
    return data


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        return load_json_object(REGISTRY_PATH)
    except ValidationError:
        return {}


def load_manifest_skill_names() -> tuple[str, ...]:
    if not MANIFEST_PATH.exists():
        return DEFAULT_SKILLS
    try:
        manifest = load_json_object(MANIFEST_PATH)
    except ValidationError:
        return DEFAULT_SKILLS
    skills = manifest.get("skills")
    if not isinstance(skills, dict) or not skills:
        return DEFAULT_SKILLS
    return tuple(sorted(skills))


def profile_skills(profile: str) -> tuple[str, ...]:
    registry = load_registry()
    profiles = registry.get("validation_profiles", {})
    if isinstance(profiles, dict):
        skills = profiles.get(profile)
        if isinstance(skills, list) and all(isinstance(skill, str) for skill in skills):
            return tuple(skills)
    if profile == "legacy_core":
        return DEFAULT_SKILLS
    return load_manifest_skill_names()


def manifest_path(raw_path: str, issues: list[str]) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        issues.append("Release manifest path must be a non-empty string.")
        return None
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        issues.append(f"Release manifest path must be relative: {raw_path}")
        return None
    return SKILLS_ROOT / path


def validate_release_manifest(skills: list[str], issues: list[str]) -> None:
    if not MANIFEST_PATH.exists():
        issues.append(f"Missing release manifest: {rel(MANIFEST_PATH)}")
        return

    scan_forbidden_runtime_references(MANIFEST_PATH, issues)

    try:
        manifest = load_json_object(MANIFEST_PATH)
    except ValidationError as exc:
        issues.append(str(exc))
        return

    if manifest.get("schema_version") != "human_review_ops_skill_release_manifest.v1":
        issues.append(f"{rel(MANIFEST_PATH)} schema_version mismatch.")
    if manifest.get("package_root") != "human_review_ops/skills":
        issues.append(f"{rel(MANIFEST_PATH)} package_root must be human_review_ops/skills.")

    manifest_skills = manifest.get("skills")
    if not isinstance(manifest_skills, dict):
        issues.append(f"{rel(MANIFEST_PATH)} skills must be an object.")
        return

    for skill in skills:
        entry = manifest_skills.get(skill)
        if not isinstance(entry, dict):
            issues.append(f"{rel(MANIFEST_PATH)} missing skill entry: {skill}")
            continue
        validate_release_manifest_entry(skill, entry, issues)


def validate_release_manifest_entry(
    skill: str,
    entry: dict[str, Any],
    issues: list[str],
) -> None:
    for field in ("skill_md", "test_prompts"):
        raw_path = entry.get(field)
        path = manifest_path(raw_path, issues)
        if path is None:
            continue
        if not raw_path.startswith(f"{skill}/"):
            issues.append(f"{rel(MANIFEST_PATH)} {skill}.{field} points outside Skill.")
        if not path.exists():
            issues.append(f"{rel(MANIFEST_PATH)} missing path: {raw_path}")

    for field in ("references", "assets", "release_assets"):
        values = entry.get(field)
        if not isinstance(values, list) or not values:
            issues.append(f"{rel(MANIFEST_PATH)} {skill}.{field} must be non-empty.")
            continue
        for raw_path in values:
            path = manifest_path(raw_path, issues)
            if path is not None and not path.exists():
                issues.append(f"{rel(MANIFEST_PATH)} missing path: {raw_path}")

    scripts = entry.get("scripts")
    if not isinstance(scripts, list) or not scripts:
        issues.append(f"{rel(MANIFEST_PATH)} {skill}.scripts must be non-empty.")
    else:
        for index, script in enumerate(scripts):
            if not isinstance(script, dict):
                issues.append(
                    f"{rel(MANIFEST_PATH)} {skill}.scripts[{index}] must be an object."
                )
                continue
            raw_path = script.get("path")
            path = manifest_path(raw_path, issues)
            if path is None:
                continue
            if not raw_path.startswith(f"{skill}/scripts/"):
                issues.append(
                    f"{rel(MANIFEST_PATH)} {skill}.scripts[{index}] points outside scripts."
                )
            if not path.exists():
                issues.append(f"{rel(MANIFEST_PATH)} missing script path: {raw_path}")

    dependencies = entry.get("external_dependencies")
    if not isinstance(dependencies, list) or not all(
        isinstance(item, str) for item in dependencies
    ):
        issues.append(f"{rel(MANIFEST_PATH)} {skill}.external_dependencies must be strings.")


def parse_frontmatter(text: str, skill_md: Path, issues: list[str]) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        issues.append(f"{rel(skill_md)} missing YAML frontmatter.")
        return {}

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def validate_skill_md(skill_dir: Path, issues: list[str], strict: bool) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        issues.append(f"Missing SKILL.md: {rel(skill_md)}")
        return

    text = skill_md.read_text(encoding="utf-8")
    fields = parse_frontmatter(text, skill_md, issues)
    for required in ("name", "description"):
        if not fields.get(required):
            issues.append(f"{rel(skill_md)} frontmatter missing {required!r}.")

    if not strict:
        return

    headings = [
        match.group(1).strip()
        for match in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE)
    ]
    missing: list[str] = []
    for section_key, aliases in STRICT_REQUIRED_SECTIONS.items():
        if not any(
            alias.lower() in heading.lower()
            for alias in aliases
            for heading in headings
        ):
            missing.append(section_key)
    if missing:
        issues.append(
            f"{rel(skill_md)} missing strict sections: {', '.join(sorted(missing))}"
        )


def validate_test_prompts(skill_dir: Path, skill: str, issues: list[str]) -> int:
    candidates = [
        skill_dir / "test-prompts.json",
        skill_dir / "assets" / "test-prompts.json",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    if not path.exists():
        issues.append(
            "Missing test prompts: "
            + " or ".join(rel(candidate) for candidate in candidates)
        )
        return 0

    try:
        data = load_json_object(path)
    except ValidationError as exc:
        issues.append(str(exc))
        return 0

    if data.get("schema_version") != "v1":
        issues.append(f"{rel(path)} schema_version must be 'v1'.")
    if data.get("skill") != skill:
        issues.append(f"{rel(path)} skill must be {skill!r}.")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        issues.append(f"{rel(path)} cases must be a non-empty array.")
        return 0

    seen_ids: set[str] = set()
    has_label_rate_trigger = False
    has_adjacent_not_trigger = False
    has_unauthorized_not_trigger = False

    for index, case in enumerate(cases):
        case_ref = f"{rel(path)} cases[{index}]"
        if not isinstance(case, dict):
            issues.append(f"{case_ref} must be an object.")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            issues.append(f"{case_ref}.id must be a non-empty string.")
        elif case_id in seen_ids:
            issues.append(f"{case_ref}.id duplicates {case_id!r}.")
        else:
            seen_ids.add(case_id)

        category = case.get("category")
        if category not in ALLOWED_CATEGORIES:
            issues.append(
                f"{case_ref}.category must be one of {sorted(ALLOWED_CATEGORIES)}."
            )

        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            issues.append(f"{case_ref}.prompt must be a non-empty string.")

        coverage = case.get("coverage")
        if not isinstance(coverage, list) or not all(
            isinstance(item, str) and item for item in coverage
        ):
            issues.append(f"{case_ref}.coverage must be a non-empty string array.")
            coverage_set: set[str] = set()
        else:
            coverage_set = set(coverage)

        expected = case.get("expected")
        if not isinstance(expected, dict):
            issues.append(f"{case_ref}.expected must be an object.")
            expected_trigger = None
        else:
            expected_trigger = expected.get("trigger")
            if not isinstance(expected_trigger, bool):
                issues.append(f"{case_ref}.expected.trigger must be boolean.")

        if category == "should-trigger" and expected_trigger is False:
            issues.append(f"{case_ref} should-trigger case cannot expect trigger=false.")
        if category == "should-not-trigger" and expected_trigger is True:
            issues.append(f"{case_ref} should-not-trigger case cannot expect trigger=true.")

        if category == "should-trigger" and "efficiency-label-rate" in coverage_set:
            has_label_rate_trigger = True
        if category == "should-not-trigger" and "adjacent-misfire" in coverage_set:
            has_adjacent_not_trigger = True
        if category == "should-not-trigger" and "unauthorized-action" in coverage_set:
            has_unauthorized_not_trigger = True

    if not has_label_rate_trigger:
        issues.append(f"{rel(path)} missing should-trigger coverage: efficiency-label-rate.")
    if not has_adjacent_not_trigger:
        issues.append(f"{rel(path)} missing should-not-trigger coverage: adjacent-misfire.")
    if not has_unauthorized_not_trigger:
        issues.append(f"{rel(path)} missing should-not-trigger coverage: unauthorized-action.")

    return len(cases)


def validate_python_scripts(skill_dir: Path, issues: list[str]) -> int:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return 0

    count = 0
    for script in sorted(scripts_dir.rglob("*.py")):
        count += 1
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as exc:
            issues.append(f"{rel(script)} failed to compile: {exc.msg}")
    return count


def validate_no_local_paths(skill_dir: Path, issues: list[str]) -> None:
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern_name, pattern in LOCAL_PATH_PATTERNS.items():
                if pattern.search(line):
                    issues.append(
                        f"{rel(path)}:{line_number} contains local path risk: {pattern_name}"
                    )
            if path.name == "package_manifest.json":
                continue
            for pattern_name, pattern in FORBIDDEN_RUNTIME_REFERENCE_PATTERNS.items():
                if pattern.search(line):
                    issues.append(
                        f"{rel(path)}:{line_number} contains forbidden runtime "
                        f"reference: {pattern_name}"
                    )


def scan_forbidden_runtime_references(path: Path, issues: list[str]) -> None:
    if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in FORBIDDEN_RUNTIME_REFERENCE_PATTERNS.items():
            if pattern.search(line):
                issues.append(
                    f"{rel(path)}:{line_number} contains forbidden runtime "
                    f"reference: {pattern_name}"
                )


def validate_skill(skill: str, strict: bool, issues: list[str]) -> dict[str, int | str]:
    skill_dir = HUMAN_REVIEW_OPS_ROOT / "skills" / skill
    if not skill_dir.exists():
        issues.append(f"Missing Skill directory: {rel(skill_dir)}")
        return {"skill": skill, "test_prompts": 0, "scripts": 0}

    validate_skill_md(skill_dir, issues, strict)
    case_count = validate_test_prompts(skill_dir, skill, issues)
    script_count = validate_python_scripts(skill_dir, issues)
    validate_no_local_paths(skill_dir, issues)
    return {"skill": skill, "test_prompts": case_count, "scripts": script_count}


def validate_aeolus_field_contracts(issues: list[str]) -> None:
    if not AEOLUS_FIELD_CONTRACT_VALIDATOR.exists():
        issues.append(f"Missing Aeolus field validator: {rel(AEOLUS_FIELD_CONTRACT_VALIDATOR)}")
        return
    result = subprocess.run(
        [sys.executable, str(AEOLUS_FIELD_CONTRACT_VALIDATOR)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()
        issues.append("Aeolus field contract validation failed:\n" + output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also require full SKILL.md productization sections for Task 2+.",
    )
    parser.add_argument(
        "--skills",
        nargs="+",
        default=None,
        help="Explicit Skill names to validate. Overrides --profile.",
    )
    parser.add_argument(
        "--profile",
        choices=("legacy_core", "scenario_label_rate", "all_releaseable"),
        default="legacy_core",
        help="Skill set from configs/skill_path_registry.json.",
    )
    args = parser.parse_args()

    issues: list[str] = []
    selected_skills = tuple(args.skills) if args.skills else profile_skills(args.profile)
    summaries = [validate_skill(skill, args.strict, issues) for skill in selected_skills]
    if args.strict:
        validate_release_manifest(list(selected_skills), issues)
        if "analysis" in selected_skills:
            validate_aeolus_field_contracts(issues)

    if issues:
        print("Skill productization baseline FAILED")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)

    mode = "strict" if args.strict else "default"
    print(f"Skill productization baseline OK ({mode})")
    for summary in summaries:
        print(
            "- {skill}: test_prompts={test_prompts}, scripts={scripts}".format(
                **summary
            )
        )


if __name__ == "__main__":
    main()
