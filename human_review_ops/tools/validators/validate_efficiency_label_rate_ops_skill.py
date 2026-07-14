#!/usr/bin/env python3
"""Validate the efficiency-label-rate scenario Skill bundle."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
SCENARIO_KEY = "efficiency-label-rate"
SKILL_NAME = "efficiency-label-rate-ops"
PLUS1_ASSET_FILENAME = "plus1_agreed_strategy_updates.json"
PLUS1_RELEASE_PATH = (
    f"{SKILL_NAME}/assets/{SCENARIO_KEY}/{PLUS1_ASSET_FILENAME}"
)
PLUS1_CANONICAL_PATH = f"human_review_ops/skills/{PLUS1_RELEASE_PATH}"
PLUS1_LEGACY_PATH = (
    f"human_review_ops/references/scenarios/{SCENARIO_KEY}/{PLUS1_ASSET_FILENAME}"
)
RELEASE_MANIFEST_PATH = HUMAN_REVIEW_OPS_ROOT / "skills" / "skill_release_manifest.json"
REGISTRY_PATH = HUMAN_REVIEW_OPS_ROOT / "configs" / "skill_path_registry.json"
PACKAGE_MANIFEST_PATH = (
    HUMAN_REVIEW_OPS_ROOT / "skills" / SKILL_NAME / "package_manifest.json"
)
SKILL_DIR = HUMAN_REVIEW_OPS_ROOT / "skills" / SKILL_NAME
STANDALONE_READABILITY_FILES = [
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "references" / "scenario_manifest.md",
    SKILL_DIR / "references" / "scenarios" / f"{SCENARIO_KEY}.md",
    SKILL_DIR / "references" / "metric_contract.md",
    SKILL_DIR / "references" / "dataset_reference.md",
    SKILL_DIR / "references" / "common.md",
    SKILL_DIR / "assets" / "README.md",
]
FORBIDDEN_STANDALONE_TEXT = [
    ".trae/skills/warehouse-skill",
    ".trae/skills/low-efficiency-strategy-analysis",
    "warehouse-skill",
    "low-efficiency-strategy-analysis",
    "由四个通用能力 Skill",
    "四个通用能力 Skill",
    "四能力 Skill",
    "根场景包生成",
    "根目录场景包",
    "canonical 路径",
    "通用 Skill assets",
]


COMMANDS = [
    [
        sys.executable,
        "human_review_ops/tools/validators/validate_skill_path_registry.py",
    ],
    [
        sys.executable,
        "human_review_ops/tools/validators/validate_skill_productization.py",
        "--strict",
        "--profile",
        "scenario_label_rate",
    ],
    [
        sys.executable,
        "human_review_ops/tools/validators/validate_skill_standalone_smoke.py",
        "--profile",
        "scenario_label_rate",
    ],
    [
        sys.executable,
        "human_review_ops/tools/packagers/build_skill_package.py",
        "efficiency-label-rate",
        "--target",
        "scenario-bundle",
        "--check-sync",
    ],
]


def load_json(path: Path, issues: list[str]) -> dict:
    if not path.exists():
        issues.append(f"missing JSON file: {path.relative_to(REPO_ROOT)}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"invalid JSON: {path.relative_to(REPO_ROOT)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        issues.append(f"JSON root must be object: {path.relative_to(REPO_ROOT)}")
        return {}
    return payload


def validate_plus1_asset_tracking() -> None:
    issues: list[str] = []
    for raw_path in (PLUS1_CANONICAL_PATH, PLUS1_LEGACY_PATH):
        if not (REPO_ROOT / raw_path).exists():
            issues.append(f"plus1 asset path missing: {raw_path}")

    release_manifest = load_json(RELEASE_MANIFEST_PATH, issues)
    skill_entry = release_manifest.get("skills", {}).get(SKILL_NAME, {})
    if not isinstance(skill_entry, dict):
        issues.append(f"release manifest missing skill: {SKILL_NAME}")
        skill_entry = {}
    for field in ("assets", "release_assets"):
        values = skill_entry.get(field)
        if not isinstance(values, list) or PLUS1_RELEASE_PATH not in values:
            issues.append(
                f"release manifest {SKILL_NAME}.{field} missing {PLUS1_RELEASE_PATH}"
            )

    registry = load_json(REGISTRY_PATH, issues)
    registry_entry = (
        registry.get("scenario_skills", {})
        .get(SCENARIO_KEY, {})
        .get("assets", {})
        .get("plus1_agreed_strategy_updates", {})
    )
    if not isinstance(registry_entry, dict):
        issues.append("registry missing assets.plus1_agreed_strategy_updates entry")
        registry_entry = {}
    if registry_entry.get("canonical") != PLUS1_CANONICAL_PATH:
        issues.append(
            "registry plus1 canonical mismatch: "
            f"expected {PLUS1_CANONICAL_PATH!r}, got {registry_entry.get('canonical')!r}"
        )
    legacy_paths = registry_entry.get("legacy")
    if not isinstance(legacy_paths, list) or PLUS1_LEGACY_PATH not in legacy_paths:
        issues.append(f"registry plus1 legacy missing {PLUS1_LEGACY_PATH}")

    package_manifest = load_json(PACKAGE_MANIFEST_PATH, issues)
    files = package_manifest.get("files")
    if not isinstance(files, list):
        issues.append("package manifest files must be an array")
        files = []
    package_record_found = any(
        isinstance(record, dict)
        and record.get("kind") == "copy"
        and (record.get("build_source") or record.get("source")) == PLUS1_LEGACY_PATH
        and record.get("target") == PLUS1_CANONICAL_PATH
        for record in files
    )
    if not package_record_found:
        issues.append(
            "package manifest missing plus1 copy record: "
            f"{PLUS1_LEGACY_PATH} -> {PLUS1_CANONICAL_PATH}"
        )

    if issues:
        raise SystemExit(
            "Efficiency-label-rate plus1 asset tracking validation failed:\n"
            + "\n".join(issues)
        )


def validate_standalone_readability() -> None:
    issues: list[str] = []
    texts: dict[Path, str] = {}
    for path in STANDALONE_READABILITY_FILES:
        if not path.exists():
            issues.append(f"standalone runtime file missing: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        texts[path] = text
        for token in FORBIDDEN_STANDALONE_TEXT:
            if token in text:
                issues.append(
                    "standalone runtime file contains non-portable text: "
                    f"{path.relative_to(REPO_ROOT)}: {token!r}"
                )

    mode_paths = [
        SKILL_DIR / "references" / "scenario_manifest.md",
        SKILL_DIR / "references" / "scenarios" / f"{SCENARIO_KEY}.md",
    ]
    mode_requirements = {
        "debug_only": ["debug_only", "仅生成本地", "不真实发送", "不写线上状态"],
        "readonly": ["只读", "SELECT", "受控只读查询"],
        "QueryPlan": ["QueryPlan", "字段", "口径", "权限"],
        "mock": ["mock", "不伪造业务结论"],
    }
    for path in mode_paths:
        text = texts.get(path, "")
        for label, tokens in mode_requirements.items():
            missing = [token for token in tokens if token not in text]
            if missing:
                issues.append(
                    f"{path.relative_to(REPO_ROOT)} lacks standalone {label} "
                    f"explanation tokens: {missing}"
                )

    if issues:
        raise SystemExit(
            "Efficiency-label-rate standalone readability validation failed:\n"
            + "\n".join(issues)
        )


def main() -> None:
    validate_plus1_asset_tracking()
    validate_standalone_readability()
    for command in COMMANDS:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            output = "\n".join(
                part.strip()
                for part in (completed.stdout, completed.stderr)
                if part.strip()
            )
            raise SystemExit(
                "Efficiency-label-rate scenario Skill validation failed:\n"
                f"command={' '.join(command)}\n{output}"
            )
    print("Efficiency-label-rate scenario Skill OK")


if __name__ == "__main__":
    main()
