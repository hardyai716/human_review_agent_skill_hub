#!/usr/bin/env python3
"""Validate AgentBuddy publish manifest and registered Skill directories."""

from __future__ import annotations

import argparse
import py_compile
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = REPO_ROOT / ".agentbuddy" / "publish.yaml"
SKILL_NAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")
LOCAL_PATH_PATTERNS = [
    "/Users/",
    "Desktop/人审运营",
]
REQUIRED_SKILL_FILES = [
    "SKILL.md",
    "references/common.md",
    "references/scenario-index.md",
]


class ValidationError(Exception):
    """Raised when the AgentBuddy publish package is invalid."""


def parse_publish_manifest(path: Path) -> dict[str, object]:
    """Parse the controlled subset of .agentbuddy/publish.yaml used by this repo."""
    if not path.exists():
        raise ValidationError(f"Missing AgentBuddy manifest: {path.relative_to(REPO_ROOT)}")

    schema_version: str | None = None
    metadata: dict[str, str] = {}
    skill_entries: list[dict[str, object]] = []
    current_entry: dict[str, object] | None = None
    in_metadata = False
    in_skills = False
    in_items = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not line.startswith(" "):
            in_metadata = stripped == "metadata:"
            if stripped == "registry:":
                in_metadata = False
            if stripped.startswith("schema_version:"):
                schema_version = stripped.split(":", 1)[1].strip()
            continue

        if in_metadata and line.startswith("  ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
            continue

        if stripped == "skills:":
            in_skills = True
            in_items = False
            continue

        if in_skills and stripped.startswith("- path:"):
            current_entry = {
                "path": stripped.split(":", 1)[1].strip().strip('"'),
                "items": [],
            }
            skill_entries.append(current_entry)
            in_items = False
            continue

        if in_skills and stripped == "items:":
            if current_entry is None:
                raise ValidationError("items must belong to a skills entry.")
            in_items = True
            continue

        if in_skills and in_items and stripped.startswith("- "):
            if current_entry is None:
                raise ValidationError("Skill item has no parent path.")
            current_entry["items"].append(stripped[2:].strip().strip('"'))  # type: ignore[index]

    return {
        "schema_version": schema_version,
        "metadata": metadata,
        "skills": skill_entries,
    }


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        raise ValidationError(f"Missing YAML frontmatter: {skill_md.relative_to(REPO_ROOT)}")

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def validate_skill_frontmatter(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    fields = parse_frontmatter(skill_md)
    name = fields.get("name", "")
    description = fields.get("description", "")

    if not SKILL_NAME_RE.fullmatch(name):
        raise ValidationError(
            f"Invalid Skill name in {skill_md.relative_to(REPO_ROOT)}: {name!r}"
        )
    if len(name) > 64:
        raise ValidationError(f"Skill name too long: {name}")
    if not description or len(description) > 1024:
        raise ValidationError(
            f"Invalid description length in {skill_md.relative_to(REPO_ROOT)}"
        )


def validate_no_local_paths(skill_dir: Path) -> None:
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern in text:
                raise ValidationError(
                    f"Local machine path pattern {pattern!r} found in {path.relative_to(REPO_ROOT)}"
                )


def validate_skill_dir(skill_dir: Path) -> None:
    if not skill_dir.exists():
        raise ValidationError(f"Skill directory does not exist: {skill_dir.relative_to(REPO_ROOT)}")
    if not skill_dir.is_dir():
        raise ValidationError(f"Skill path is not a directory: {skill_dir.relative_to(REPO_ROOT)}")

    for relative in REQUIRED_SKILL_FILES:
        required = skill_dir / relative
        if not required.exists():
            raise ValidationError(f"Missing required Skill file: {required.relative_to(REPO_ROOT)}")

    scenarios_dir = skill_dir / "references" / "scenarios"
    if not scenarios_dir.exists():
        raise ValidationError(f"Missing scenarios snapshot dir: {scenarios_dir.relative_to(REPO_ROOT)}")

    validate_skill_frontmatter(skill_dir)
    validate_no_local_paths(skill_dir)

    for script in (skill_dir / "scripts").glob("*.py") if (skill_dir / "scripts").exists() else []:
        py_compile.compile(str(script), doraise=True)


def validate_manifest(path: Path) -> None:
    manifest = parse_publish_manifest(path)
    if manifest["schema_version"] != "v1":
        raise ValidationError("schema_version must be v1.")

    skills = manifest["skills"]
    if not isinstance(skills, list) or not skills:
        raise ValidationError("registry.skills must contain at least one entry.")

    seen: set[str] = set()
    for entry in skills:
        if not isinstance(entry, dict):
            raise ValidationError("registry.skills entries must be mappings.")
        parent_value = entry.get("path")
        items_value = entry.get("items")
        if not isinstance(parent_value, str) or not parent_value:
            raise ValidationError("registry.skills[].path is required.")
        if ".." in Path(parent_value).parts:
            raise ValidationError("registry.skills[].path must not contain '..'.")
        if not isinstance(items_value, list) or not items_value:
            raise ValidationError("registry.skills[].items must be non-empty.")

        parent = REPO_ROOT / parent_value
        if not parent.exists():
            raise ValidationError(f"AgentBuddy parent path does not exist: {parent_value}")
        for item in items_value:
            if not isinstance(item, str) or not item:
                raise ValidationError("Skill item names must be non-empty strings.")
            if item in seen:
                raise ValidationError(f"Duplicate Skill item in publish manifest: {item}")
            seen.add(item)
            validate_skill_dir(parent / item)

    print(
        "AgentBuddy publish manifest OK: "
        f"{path.relative_to(REPO_ROOT)}; skills={', '.join(sorted(seen))}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "manifest",
        nargs="?",
        default=str(DEFAULT_MANIFEST),
        help="Path to .agentbuddy/publish.yaml.",
    )
    args = parser.parse_args()
    validate_manifest(Path(args.manifest).resolve())


if __name__ == "__main__":
    main()
