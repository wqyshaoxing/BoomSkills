#!/usr/bin/env python3
"""Validate structure, links, totals, and hashes in an evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


MAPPING_RE = re.compile(r"(?m)^## (C[^\s]+) × `([^`]+)`\s*$")
LOCATION_RE = re.compile(r"(?m)^- 正文位置：`[^`]+`\s*$")
SCREENSHOT_RE = re.compile(r"\]\(screenshots/([^\)]+)\)")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_package(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    inventory_path = root / "evidence_inventory.json"
    report_path = root / "reference_claim_evidence_audit.md"
    by_reference = root / "by_reference"
    if not inventory_path.is_file():
        return {"errors": ["missing evidence_inventory.json"]}
    if not report_path.is_file():
        errors.append("missing reference_claim_evidence_audit.md")
    if not by_reference.is_dir():
        errors.append("missing by_reference directory")

    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"errors": [f"invalid inventory: {exc}"]}

    listed_paths: set[str] = set()
    for item in inventory.get("files", []):
        relative = item.get("path")
        if not isinstance(relative, str) or not relative:
            errors.append("inventory contains an invalid file path")
            continue
        if relative in listed_paths:
            errors.append(f"duplicate inventory path: {relative}")
            continue
        listed_paths.add(relative)
        path = root / Path(relative)
        try:
            path.resolve().relative_to(root.resolve())
        except (OSError, ValueError):
            errors.append(f"inventory path escapes package: {relative}")
            continue
        if not path.is_file():
            errors.append(f"missing inventoried file: {relative}")
            continue
        if path.stat().st_size != item.get("bytes"):
            errors.append(f"size mismatch: {relative}")
        if sha256(path) != item.get("sha256"):
            errors.append(f"hash mismatch: {relative}")

    directory_count = 0
    mapping_count = 0
    screenshot_count = 0
    cited_count = 0
    uncited_count = 0
    if by_reference.is_dir():
        for ref_dir in sorted(path for path in by_reference.iterdir() if path.is_dir()):
            directory_count += 1
            mapping_path = ref_dir / "evidence_mapping.md"
            screenshot_dir = ref_dir / "screenshots"
            if not mapping_path.is_file():
                errors.append(f"missing mapping file: {ref_dir.name}")
                continue
            text = mapping_path.read_text(encoding="utf-8")
            mappings = MAPPING_RE.findall(text)
            locations = LOCATION_RE.findall(text)
            mapping_count += len(mappings)
            if mappings:
                cited_count += 1
            else:
                uncited_count += 1
                if "不构造章节、段落、原文摘录或截图映射" not in text:
                    errors.append(f"uncited reference lacks explicit no-mapping note: {ref_dir.name}")
            if len(locations) != len(mappings):
                errors.append(
                    f"manuscript locator count differs from mapping count: {ref_dir.name} "
                    f"({len(locations)} vs {len(mappings)})"
                )
            links = SCREENSHOT_RE.findall(text)
            actual_images: set[str] = set()
            if screenshot_dir.is_dir():
                actual_images = {
                    path.name
                    for path in screenshot_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
                }
            screenshot_count += len(actual_images)
            for filename in links:
                if filename not in actual_images:
                    errors.append(f"missing linked screenshot: {ref_dir.name}/{filename}")
            for filename in actual_images:
                if filename not in links:
                    errors.append(f"unlinked screenshot: {ref_dir.name}/{filename}")
            if mappings and not links and "**unresolved**" not in text:
                errors.append(f"cited reference has no screenshot: {ref_dir.name}")

    summary = inventory.get("summary", {})
    observed = {
        "references": directory_count,
        "cited_references": cited_count,
        "uncited_references": uncited_count,
        "mappings": mapping_count,
        "screenshots": screenshot_count,
    }
    for field, value in observed.items():
        if summary.get(field) != value:
            errors.append(f"summary mismatch for {field}: inventory={summary.get(field)} observed={value}")

    return {"observed": observed, "errors": errors}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="evidence package directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = validate_package(args.package.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
