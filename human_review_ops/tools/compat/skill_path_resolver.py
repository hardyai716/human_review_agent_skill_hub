#!/usr/bin/env python3
"""Resolve scenario Skill paths across canonical and legacy layouts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
REGISTRY_PATH = HUMAN_REVIEW_OPS_ROOT / "configs" / "skill_path_registry.json"
VALID_PATH_MODES = {"auto", "canonical", "legacy"}


def load_registry() -> dict[str, Any]:
    """Load the path registry as a JSON object."""
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def active_path_mode(mode: str | None = None) -> str:
    """Return the effective path mode from the argument, env, or registry."""
    if mode:
        selected = mode
    else:
        env_mode = os.environ.get("HRO_SKILL_PATH_MODE")
        if env_mode:
            selected = env_mode
        else:
            selected = load_registry().get("default_path_mode", "auto")
    if selected not in VALID_PATH_MODES:
        raise ValueError(
            f"Unknown HRO_SKILL_PATH_MODE: {selected!r}. "
            f"Expected one of {sorted(VALID_PATH_MODES)}."
        )
    return selected


def _entry_candidates(entry: dict[str, Any], mode: str) -> list[str]:
    canonical = entry.get("canonical")
    legacy = entry.get("legacy", [])
    if not isinstance(canonical, str) or not canonical:
        raise ValueError(f"Registry entry missing canonical path: {entry}")
    if not isinstance(legacy, list) or not all(isinstance(item, str) for item in legacy):
        raise ValueError(f"Registry entry legacy paths must be strings: {entry}")

    if mode == "canonical":
        return [canonical]
    if mode == "legacy":
        return legacy
    return [canonical, *legacy]


def resolve_registered_path(
    scenario_key: str,
    section: str,
    key: str,
    mode: str | None = None,
) -> Path:
    """Resolve one registered path and require it to exist."""
    registry = load_registry()
    selected_mode = active_path_mode(mode)
    try:
        entry = registry["scenario_skills"][scenario_key][section][key]
    except KeyError as exc:
        raise KeyError(
            f"No registry entry for scenario={scenario_key!r}, "
            f"section={section!r}, key={key!r}."
        ) from exc
    if not isinstance(entry, dict):
        raise ValueError(
            f"Registry entry must be an object for scenario={scenario_key}, "
            f"section={section}, key={key}."
        )

    candidates = _entry_candidates(entry, selected_mode)
    for raw_path in candidates:
        path = REPO_ROOT / raw_path
        if path.exists():
            return path

    raise FileNotFoundError(
        f"No registered path exists for scenario={scenario_key}, section={section}, "
        f"key={key}, mode={selected_mode}, candidates={candidates}"
    )


def resolve_script_path(
    scenario_key: str,
    script_key: str,
    mode: str | None = None,
) -> Path:
    """Resolve a registered script path."""
    return resolve_registered_path(scenario_key, "scripts", script_key, mode)


def resolve_script_dir(
    scenario_key: str,
    script_key: str,
    mode: str | None = None,
) -> Path:
    """Resolve the directory that contains a registered script."""
    return resolve_script_path(scenario_key, script_key, mode).parent


def resolve_asset_path(
    scenario_key: str,
    asset_key: str,
    mode: str | None = None,
) -> Path:
    """Resolve a registered asset path."""
    return resolve_registered_path(scenario_key, "assets", asset_key, mode)


def resolve_reference_path(
    scenario_key: str,
    reference_key: str,
    mode: str | None = None,
) -> Path:
    """Resolve a registered reference path."""
    return resolve_registered_path(scenario_key, "references", reference_key, mode)
