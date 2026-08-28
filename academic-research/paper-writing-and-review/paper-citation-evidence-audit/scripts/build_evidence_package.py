#!/usr/bin/env python3
"""Build a per-reference manuscript evidence package from a JSON manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SUPPORT_LEVELS = {"full", "partial", "secondary", "unresolved"}
SOURCE_KINDS = {"primary", "secondary", "unavailable"}
KEY_RE = re.compile(r"^[A-Za-z0-9._-]+$")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class ManifestError(ValueError):
    pass


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} must be a non-empty string")
    return value.strip()


def optional_text(value: Any, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ManifestError(f"{field} must be a string")
    return value.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "evidence"


def redact_local_path(value: str) -> str:
    """Prevent machine-specific absolute paths from entering the evidence package."""
    if not value:
        return ""
    if re.match(r"^[A-Za-z]:[\\\\/]", value) or value.startswith(("/", "\\\\")):
        return Path(value.replace("\\\\", "/")).name or "source-file"
    return value


def validate_manifest(manifest: Any, manifest_dir: Path) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict):
        raise ManifestError("manifest root must be an object")
    references = manifest.get("references")
    if not isinstance(references, list) or not references:
        raise ManifestError("references must be a non-empty list")

    seen_keys: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for ref_index, raw_ref in enumerate(references, start=1):
        prefix = f"references[{ref_index - 1}]"
        if not isinstance(raw_ref, dict):
            raise ManifestError(f"{prefix} must be an object")
        key = require_text(raw_ref.get("key"), f"{prefix}.key")
        if not KEY_RE.fullmatch(key):
            raise ManifestError(f"{prefix}.key contains unsafe directory characters: {key}")
        if key in seen_keys:
            raise ManifestError(f"duplicate reference key: {key}")
        seen_keys.add(key)
        title = require_text(raw_ref.get("title"), f"{prefix}.title")

        raw_source = raw_ref.get("source", {})
        if not isinstance(raw_source, dict):
            raise ManifestError(f"{prefix}.source must be an object")
        source_kind = raw_source.get("kind", "unavailable")
        if source_kind not in SOURCE_KINDS:
            raise ManifestError(f"{prefix}.source.kind must be one of {sorted(SOURCE_KINDS)}")
        source = {
            "kind": source_kind,
            "path": redact_local_path(optional_text(raw_source.get("path"), f"{prefix}.source.path")),
            "note": optional_text(raw_source.get("note"), f"{prefix}.source.note"),
        }

        raw_claims = raw_ref.get("claims", [])
        if not isinstance(raw_claims, list):
            raise ManifestError(f"{prefix}.claims must be a list")
        seen_claims: set[str] = set()
        claims: list[dict[str, Any]] = []
        for claim_index, raw_claim in enumerate(raw_claims, start=1):
            cp = f"{prefix}.claims[{claim_index - 1}]"
            if not isinstance(raw_claim, dict):
                raise ManifestError(f"{cp} must be an object")
            claim_id = require_text(raw_claim.get("id"), f"{cp}.id")
            if claim_id in seen_claims:
                raise ManifestError(f"duplicate claim ID {claim_id} under {key}")
            seen_claims.add(claim_id)
            support = raw_claim.get("support_level")
            if support not in SUPPORT_LEVELS:
                raise ManifestError(f"{cp}.support_level must be one of {sorted(SUPPORT_LEVELS)}")
            risk = optional_text(raw_claim.get("risk"), f"{cp}.risk")
            if support != "full" and not risk:
                raise ManifestError(f"{cp}.risk is required for support level {support}")
            raw_evidence = raw_claim.get("evidence", [])
            if not isinstance(raw_evidence, list):
                raise ManifestError(f"{cp}.evidence must be a list")
            if support != "unresolved" and not raw_evidence:
                raise ManifestError(f"{cp}.evidence is required for support level {support}")

            evidence: list[dict[str, Any]] = []
            for evidence_index, raw_item in enumerate(raw_evidence, start=1):
                ep = f"{cp}.evidence[{evidence_index - 1}]"
                if not isinstance(raw_item, dict):
                    raise ManifestError(f"{ep} must be an object")
                screenshot_value = require_text(raw_item.get("screenshot"), f"{ep}.screenshot")
                screenshot = Path(screenshot_value)
                if not screenshot.is_absolute():
                    screenshot = (manifest_dir / screenshot).resolve()
                if not screenshot.is_file() or screenshot.stat().st_size == 0:
                    raise ManifestError(f"{ep}.screenshot does not exist or is empty: {screenshot}")
                if screenshot.suffix.lower() not in IMAGE_EXTENSIONS:
                    raise ManifestError(f"{ep}.screenshot has unsupported extension: {screenshot.suffix}")
                evidence.append(
                    {
                        "location": require_text(raw_item.get("location"), f"{ep}.location"),
                        "quote": require_text(raw_item.get("quote"), f"{ep}.quote"),
                        "translation": require_text(raw_item.get("translation"), f"{ep}.translation"),
                        "screenshot": screenshot,
                        "note": optional_text(raw_item.get("note"), f"{ep}.note"),
                    }
                )

            claims.append(
                {
                    "id": claim_id,
                    "manuscript_location": require_text(
                        raw_claim.get("manuscript_location"), f"{cp}.manuscript_location"
                    ),
                    "claim_text": require_text(raw_claim.get("claim_text"), f"{cp}.claim_text"),
                    "claim_translation": optional_text(
                        raw_claim.get("claim_translation"), f"{cp}.claim_translation"
                    ),
                    "support_level": support,
                    "risk": risk,
                    "evidence": evidence,
                }
            )
        normalized.append({"key": key, "title": title, "source": source, "claims": claims})
    return normalized


def build_package(manifest: dict[str, Any], manifest_dir: Path, output: Path) -> dict[str, Any]:
    references = validate_manifest(manifest, manifest_dir)
    manuscript = manifest.get("manuscript", {})
    if manuscript is None:
        manuscript = {}
    if not isinstance(manuscript, dict):
        raise ManifestError("manuscript must be an object")
    manuscript_title = optional_text(manuscript.get("title"), "manuscript.title")
    manuscript_path = redact_local_path(optional_text(manuscript.get("path"), "manuscript.path"))
    if output.exists() and any(output.iterdir()):
        raise ManifestError(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    by_reference = output / "by_reference"
    by_reference.mkdir()

    inventory_files: list[dict[str, Any]] = []
    level_counts: Counter[str] = Counter()
    mapping_total = 0
    screenshot_total = 0
    report_rows: list[str] = []

    for ref in references:
        key = ref["key"]
        ref_dir = by_reference / key
        screenshot_dir = ref_dir / "screenshots"
        ref_dir.mkdir()
        screenshot_dir.mkdir()
        claims = ref["claims"]
        mapping_total += len(claims)
        lines = [
            f"# `{key}` 专属引用校对记录",
            "",
            f"- 文献：{ref['title']}",
            f"- 当前正文映射数：{len(claims)}",
            f"- 证据类型：{ref['source']['kind']}",
        ]
        if ref["source"]["path"]:
            lines.append(f"- 来源：`{ref['source']['path']}`")
        if ref["source"]["note"]:
            lines.append(f"- 来源说明：{ref['source']['note']}")
        lines.append("")

        if not claims:
            lines.extend(
                [
                    "## 当前状态",
                    "",
                    "该条目存在于参考文献库，但当前稿件没有对应引用或论述。",
                    "本目录不构造章节、段落、原文摘录或截图映射。",
                    "",
                ]
            )

        ref_shots = 0
        for claim in claims:
            level_counts[claim["support_level"]] += 1
            lines.extend(
                [
                    f"## {claim['id']} × `{key}`",
                    "",
                    f"- 正文位置：`{claim['manuscript_location']}`",
                    f"- 支持等级：**{claim['support_level']}**",
                    f"- 风险说明：{claim['risk'] or '未发现超出原文证据边界的表述。'}",
                    "",
                    f"**正文原句**：{claim['claim_text']}",
                    "",
                    f"**正文译文**：{claim['claim_translation'] or '未单独提供；正文与报告使用同一语言。'}",
                    "",
                ]
            )
            for evidence_index, item in enumerate(claim["evidence"], start=1):
                source = item["screenshot"]
                filename = (
                    f"{safe_component(claim['id'])}_{safe_component(key)}_"
                    f"{evidence_index:02d}_{safe_component(source.stem)}{source.suffix.lower()}"
                )
                destination = screenshot_dir / filename
                if destination.exists():
                    raise ManifestError(f"generated screenshot filename collision: {destination}")
                shutil.copy2(source, destination)
                relative = destination.relative_to(output).as_posix()
                inventory_files.append(
                    {
                        "path": relative,
                        "sha256": sha256(destination),
                        "bytes": destination.stat().st_size,
                        "source": str(source),
                    }
                )
                screenshot_total += 1
                ref_shots += 1
                lines.extend(
                    [
                        f"### 证据 {evidence_index}",
                        "",
                        f"- 定位：{item['location']}",
                        f"- 原文摘录：{item['quote']}",
                        f"- 中文翻译：{item['translation']}",
                    ]
                )
                if item["note"]:
                    lines.append(f"- 说明：{item['note']}")
                lines.extend(
                    [
                        "- 截图框选：已由人工或上游流程核验",
                        "",
                        f"![{claim['id']} {key} evidence {evidence_index}](screenshots/{filename})",
                        "",
                    ]
                )

        mapping_path = ref_dir / "evidence_mapping.md"
        mapping_path.write_text("\n".join(lines), encoding="utf-8")
        mapping_relative = mapping_path.relative_to(output).as_posix()
        inventory_files.append(
            {
                "path": mapping_relative,
                "sha256": sha256(mapping_path),
                "bytes": mapping_path.stat().st_size,
            }
        )
        report_rows.append(
            f"| `{key}` | {ref['title']} | {len(claims)} | {ref_shots} | "
            f"[记录]({mapping_relative}) |"
        )

    report_lines = [
        "# 论文引用论述—原文证据审计",
        "",
        f"- 稿件：{manuscript_title or '未命名稿件'}",
        f"- 稿件路径：`{manuscript_path or '未提供'}`",
        f"- 参考文献：{len(references)}",
        f"- 正文已引用文献：{sum(bool(ref['claims']) for ref in references)}",
        f"- 论述—文献映射：{mapping_total}",
        f"- 证据截图：{screenshot_total}",
        f"- 完整支持：{level_counts['full']}",
        f"- 部分支持：{level_counts['partial']}",
        f"- 二手支持：{level_counts['secondary']}",
        f"- 未解决：{level_counts['unresolved']}",
        "",
        "| BibTeX key | 文献 | 映射 | 截图 | 专属记录 |",
        "| --- | --- | ---: | ---: | --- |",
        *report_rows,
        "",
    ]
    report_path = output / "reference_claim_evidence_audit.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    inventory_files.append(
        {
            "path": report_path.relative_to(output).as_posix(),
            "sha256": sha256(report_path),
            "bytes": report_path.stat().st_size,
        }
    )

    inventory = {
        "schema_version": 1,
        "summary": {
            "references": len(references),
            "cited_references": sum(bool(ref["claims"]) for ref in references),
            "uncited_references": sum(not ref["claims"] for ref in references),
            "mappings": mapping_total,
            "screenshots": screenshot_total,
            "support": {level: level_counts[level] for level in sorted(SUPPORT_LEVELS)},
        },
        "files": inventory_files,
    }
    inventory_path = output / "evidence_inventory.json"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return inventory["summary"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="UTF-8 evidence manifest JSON")
    parser.add_argument("--output", required=True, type=Path, help="new or empty output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest_path = args.manifest.resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary = build_package(manifest, manifest_path.parent, args.output.resolve())
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
