#!/usr/bin/env python3
"""Validate scenario Skill path registry consistency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from human_review_ops.tools.compat.skill_path_resolver import (  # noqa: E402
    VALID_PATH_MODES,
    active_path_mode,
    load_registry,
    resolve_registered_path,
)


REGISTRY_PATH = HUMAN_REVIEW_OPS_ROOT / "configs" / "skill_path_registry.json"
MANIFEST_PATH = HUMAN_REVIEW_OPS_ROOT / "skills" / "skill_release_manifest.json"


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry(require_all_legacy: bool = True) -> list[str]:
    issues: list[str] = []
    if not REGISTRY_PATH.exists():
        return [f"Missing registry: {rel(REGISTRY_PATH)}"]

    registry = load_registry()
    manifest_skills = load_manifest_skills(issues)

    if registry.get("schema_version") != "human_review_ops_skill_path_registry.v1":
        issues.append(f"{rel(REGISTRY_PATH)} schema_version mismatch.")
    if registry.get("default_path_mode") not in VALID_PATH_MODES:
        issues.append(
            f"{rel(REGISTRY_PATH)} default_path_mode must be one of "
            f"{sorted(VALID_PATH_MODES)}."
        )

    validate_profiles(registry, manifest_skills, issues)
    validate_scenario_skills(registry, manifest_skills, issues, require_all_legacy)
    return issues


def load_manifest_skills(issues: list[str]) -> set[str]:
    if not MANIFEST_PATH.exists():
        issues.append(f"Missing release manifest: {rel(MANIFEST_PATH)}")
        return set()
    manifest = load_json(MANIFEST_PATH)
    skills = manifest.get("skills")
    if not isinstance(skills, dict):
        issues.append(f"{rel(MANIFEST_PATH)} skills must be an object.")
        return set()
    return set(skills)


def validate_profiles(
    registry: dict[str, Any],
    manifest_skills: set[str],
    issues: list[str],
) -> None:
    profiles = registry.get("validation_profiles")
    if not isinstance(profiles, dict) or not profiles:
        issues.append(f"{rel(REGISTRY_PATH)} validation_profiles must be non-empty.")
        return
    for profile, skills in profiles.items():
        if not isinstance(skills, list) or not skills:
            issues.append(f"validation_profiles.{profile} must be a non-empty array.")
            continue
        for skill in skills:
            if not isinstance(skill, str):
                issues.append(f"validation_profiles.{profile} contains non-string skill.")
            elif skill not in manifest_skills:
                issues.append(
                    f"validation_profiles.{profile} references skill not in manifest: {skill}"
                )


def validate_scenario_skills(
    registry: dict[str, Any],
    manifest_skills: set[str],
    issues: list[str],
    require_all_legacy: bool,
) -> None:
    scenarios = registry.get("scenario_skills")
    if not isinstance(scenarios, dict) or not scenarios:
        issues.append(f"{rel(REGISTRY_PATH)} scenario_skills must be non-empty.")
        return

    for scenario_key, scenario in scenarios.items():
        if not isinstance(scenario, dict):
            issues.append(f"scenario_skills.{scenario_key} must be an object.")
            continue
        canonical_skill = scenario.get("canonical_skill")
        if canonical_skill not in manifest_skills:
            issues.append(
                f"{scenario_key}.canonical_skill is not in release manifest: "
                f"{canonical_skill!r}"
            )
        validate_declared_root(
            f"{scenario_key}.canonical_root",
            scenario.get("canonical_root"),
            issues,
        )
        legacy_roots = scenario.get("legacy_capability_roots")
        if not isinstance(legacy_roots, dict) or not legacy_roots:
            issues.append(f"{scenario_key}.legacy_capability_roots must be non-empty.")
        else:
            for capability, raw_path in legacy_roots.items():
                validate_declared_root(
                    f"{scenario_key}.legacy_capability_roots.{capability}",
                    raw_path,
                    issues,
                )

        for section in ("scripts", "assets", "references"):
            entries = scenario.get(section)
            if not isinstance(entries, dict) or not entries:
                issues.append(f"{scenario_key}.{section} must be a non-empty object.")
                continue
            for key, entry in entries.items():
                validate_entry_shape(scenario_key, section, key, entry, issues)
                validate_resolved_modes(
                    scenario_key,
                    section,
                    key,
                    entry,
                    issues,
                    require_all_legacy,
                )


def validate_declared_root(label: str, raw_path: Any, issues: list[str]) -> None:
    if not isinstance(raw_path, str) or not raw_path:
        issues.append(f"{label} must be a non-empty string.")
        return
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        issues.append(f"{label} must be a relative path: {raw_path}")
        return
    if not (REPO_ROOT / raw_path).is_dir():
        issues.append(f"{label} directory missing: {raw_path}")


def validate_entry_shape(
    scenario_key: str,
    section: str,
    key: str,
    entry: Any,
    issues: list[str],
) -> None:
    label = f"{scenario_key}.{section}.{key}"
    if not isinstance(entry, dict):
        issues.append(f"{label} must be an object.")
        return
    canonical = entry.get("canonical")
    if not isinstance(canonical, str) or not canonical:
        issues.append(f"{label}.canonical must be a non-empty string.")
    elif Path(canonical).is_absolute() or ".." in Path(canonical).parts:
        issues.append(f"{label}.canonical must be repository-relative: {canonical}")

    legacy = entry.get("legacy")
    if not isinstance(legacy, list) or not legacy:
        issues.append(f"{label}.legacy must be a non-empty array.")
    else:
        for raw_path in legacy:
            if not isinstance(raw_path, str) or not raw_path:
                issues.append(f"{label}.legacy contains invalid path.")
            elif Path(raw_path).is_absolute() or ".." in Path(raw_path).parts:
                issues.append(f"{label}.legacy must be repository-relative: {raw_path}")


def validate_resolved_modes(
    scenario_key: str,
    section: str,
    key: str,
    entry: Any,
    issues: list[str],
    require_all_legacy: bool,
) -> None:
    if not isinstance(entry, dict):
        return

    canonical = entry.get("canonical")
    if isinstance(canonical, str) and not (REPO_ROOT / canonical).exists():
        issues.append(f"{scenario_key}.{section}.{key}.canonical missing: {canonical}")

    legacy = entry.get("legacy")
    if require_all_legacy and isinstance(legacy, list):
        for raw_path in legacy:
            if isinstance(raw_path, str) and not (REPO_ROOT / raw_path).exists():
                issues.append(f"{scenario_key}.{section}.{key}.legacy missing: {raw_path}")

    for mode in ("canonical", "legacy", "auto"):
        try:
            resolve_registered_path(scenario_key, section, key, mode)
        except Exception as exc:  # noqa: BLE001 - validator should report all failures.
            issues.append(
                f"resolve failed for {scenario_key}.{section}.{key} "
                f"mode={mode}: {exc}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-missing-legacy",
        action="store_true",
        help="Only require canonical paths. Use during early migration drafts.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_PATH_MODES),
        default=None,
        help="Validate that this path mode is accepted by the resolver.",
    )
    args = parser.parse_args()

    if args.mode:
        active_path_mode(args.mode)

    issues = validate_registry(require_all_legacy=not args.allow_missing_legacy)
    if issues:
        print("Skill path registry FAILED")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)

    registry = load_registry()
    scenario_count = len(registry.get("scenario_skills", {}))
    print(
        "Skill path registry OK: "
        f"{rel(REGISTRY_PATH)}; scenarios={scenario_count}; "
        f"default_mode={registry.get('default_path_mode')}"
    )


if __name__ == "__main__":
    main()
