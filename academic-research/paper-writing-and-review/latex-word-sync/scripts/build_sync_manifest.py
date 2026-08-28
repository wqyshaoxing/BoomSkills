#!/usr/bin/env python3
"""Build a compact, reusable LaTeX <-> Word synchronization manifest.

The script intentionally inventories structure rather than converting content.
It can be run before the first conversion and rerun with --previous to identify
the smallest safe set of anchors that changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
GRAPHIC_RE = re.compile(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^}]+)\}")
BIB_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
HEADING_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\s*\{([^}]+)\}")
CITE_RE = re.compile(r"\\cite\w*?(?:\[[^]]*\])?\s*\{([^}]+)\}")
EQUATION_RE = re.compile(r"\\begin\{equation\}(.*?)\\end\{equation\}", re.S)
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def norm(text: str) -> str:
    text = re.sub(r"\\[A-Za-z]+(?:\s*\{[^}]*\})?", " ", text)
    text = re.sub(r"^[IVXLC]+\.\s*|^[A-Z]\.\s*|^\d+\)\s*", "", text.strip(), flags=re.I)
    return re.sub(r"\s+", " ", text).strip().casefold()


def resolve_tex(root: Path, current: Path, target: str) -> Path | None:
    root_candidate = (root / target).resolve()
    local_candidate = (current.parent / target).resolve()
    options = [root_candidate, root_candidate.with_suffix(".tex"), local_candidate, local_candidate.with_suffix(".tex")]
    for option in options:
        if option.is_file() and option.is_relative_to(root):
            return option
    return None


def resolve_asset(root: Path, current: Path, target: str) -> Path | None:
    root_candidate = (root / target).resolve()
    local_candidate = (current.parent / target).resolve()
    options = [root_candidate, local_candidate]
    if not root_candidate.suffix:
        options.extend(root_candidate.with_suffix(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"))
        options.extend(local_candidate.with_suffix(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"))
    for option in options:
        if option.is_file() and option.is_relative_to(root):
            return option
    return None


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def tex_inventory(root: Path, main: Path) -> dict[str, Any]:
    visited: set[Path] = set()
    source_files: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    graphics: list[dict[str, Any]] = []
    bibliography_files: list[dict[str, Any]] = []
    citation_keys: list[str] = []
    equations: list[dict[str, Any]] = []

    def walk(path: Path, role: str) -> None:
        path = path.resolve()
        if path in visited:
            return
        visited.add(path)
        text = path.read_text(encoding="utf-8")
        source_files.append({"path": rel(root, path), "role": role, "sha256": sha256(path)})
        for level, title in HEADING_RE.findall(text):
            headings.append({"path": rel(root, path), "level": level, "title": title.strip(), "key": norm(title)})
        for match in CITE_RE.findall(text):
            citation_keys.extend(key.strip() for key in match.split(",") if key.strip())
        for body in EQUATION_RE.findall(text):
            label = LABEL_RE.search(body)
            equations.append({"path": rel(root, path), "ordinal": len(equations) + 1, "label": label.group(1) if label else None})
        for graphic in GRAPHIC_RE.findall(text):
            asset = resolve_asset(root, path, graphic)
            graphics.append({
                "source": rel(root, path), "requested_path": graphic,
                "path": rel(root, asset) if asset else None,
                "sha256": sha256(asset) if asset else None,
                "resolved": asset is not None,
            })
        for bib_group in BIB_RE.findall(text):
            for name in bib_group.split(","):
                bib = (root / name.strip()).with_suffix(".bib")
                bibliography_files.append({
                    "path": rel(root, bib) if bib.is_file() else f"{name.strip()}.bib",
                    "sha256": sha256(bib) if bib.is_file() else None,
                    "resolved": bib.is_file(),
                })
        for include in INPUT_RE.findall(text):
            child = resolve_tex(root, path, include)
            if child:
                walk(child, "included")

    walk(main, "main")
    table_files = [item for item in source_files if item["path"].startswith("tables/")]
    unresolved = [item for item in graphics + bibliography_files if not item["resolved"]]
    return {
        "root": ".", "main": rel(root, main), "files": source_files,
        "headings": headings, "graphics": graphics, "tables": table_files,
        "bibliography_files": bibliography_files,
        "citation_keys": sorted(set(citation_keys)), "equations": equations,
        "unresolved_assets": unresolved,
    }


def text_of(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.iter(f"{W}t"))


def docx_inventory(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        styles = ET.fromstring(archive.read("word/styles.xml")) if "word/styles.xml" in archive.namelist() else None

    paragraphs: list[dict[str, Any]] = []
    for ordinal, paragraph in enumerate(document.findall(f".//{W}body/{W}p"), start=1):
        ppr = paragraph.find(f"{W}pPr")
        style = ppr.find(f"{W}pStyle") if ppr is not None else None
        text = text_of(paragraph).strip()
        if text:
            paragraphs.append({"ordinal": ordinal, "text": text, "key": norm(text), "style": style.get(f"{W}val") if style is not None else None})

    style_rows: list[dict[str, Any]] = []
    if styles is not None:
        for style in styles.findall(f"{W}style"):
            name = style.find(f"{W}name")
            if name is None:
                continue
            style_rows.append({"id": style.get(f"{W}styleId"), "name": name.get(f"{W}val"), "type": style.get(f"{W}type")})

    body = document.find(f".//{W}body")
    sect = body.find(f"{W}sectPr") if body is not None else None
    page_size = sect.find(f"{W}pgSz") if sect is not None else None
    margins = sect.find(f"{W}pgMar") if sect is not None else None
    reference_start = next((row["ordinal"] for row in paragraphs if row["key"] in {"reference", "references"}), None)
    references = 0
    if reference_start is not None:
        references = sum(1 for row in paragraphs if row["ordinal"] > reference_start and re.match(r"^\[\d+\]", row["text"]))
    drawing_paragraphs = len(document.findall(f".//{W}drawing"))
    display_equations = []
    for ordinal, paragraph in enumerate(document.findall(f".//{W}p"), start=1):
        math_paragraphs = paragraph.findall(f".//{M}oMathPara")
        number = re.search(r"\((\d+)\)\s*$", text_of(paragraph).strip())
        for math_paragraph in math_paragraphs:
            alignment = math_paragraph.find(f"{M}oMathParaPr/{M}jc")
            display_equations.append({
                "ordinal": ordinal,
                "number": int(number.group(1)) if number else None,
                "centered": alignment is not None and alignment.get(f"{M}val") == "center",
            })
    marker_names = ("numPr", "keepNext", "keepLines")
    direct_format_markers = {
        name: len(document.findall(f".//{W}pPr/{W}{name}"))
        for name in marker_names
    }
    style_format_markers = {
        name: len(styles.findall(f".//{W}style/{W}pPr/{W}{name}")) if styles is not None else 0
        for name in marker_names
    }
    text_font_faces = sorted({
        face
        for font in document.findall(f".//{W}rPr/{W}rFonts")
        for face in font.attrib.values()
        if face
    })
    fields = len(document.findall(f".//{W}fldSimple"))
    sections = []
    for ordinal, section in enumerate(document.findall(f".//{W}sectPr"), start=1):
        columns = section.find(f"{W}cols")
        count = int(columns.get(f"{W}num", "1")) if columns is not None else 1
        sections.append({
            "ordinal": ordinal,
            "columns": count,
            "column_space": columns.get(f"{W}space") if columns is not None else None,
        })
    return {
        "path": path.name, "sha256": sha256(path),
        "paragraphs": paragraphs, "tables": len(document.findall(f".//{W}tbl")),
        "drawings": drawing_paragraphs, "omml_math_objects": len(document.findall(f".//{M}oMath")),
        "display_equations": display_equations,
        "format_markers": {"direct": direct_format_markers, "styles": style_format_markers},
        "text_font_faces": text_font_faces,
        "simple_fields": fields, "references": references, "sections": sections,
        "styles": style_rows,
        "page": {
            "width": page_size.get(f"{W}w") if page_size is not None else None,
            "height": page_size.get(f"{W}h") if page_size is not None else None,
            "margins": margins.attrib if margins is not None else {},
        },
    }


def build_bindings(tex: dict[str, Any] | None, word: dict[str, Any] | None) -> dict[str, Any]:
    if tex is None:
        return {"headings": [], "object_counts": {"word_tables": word["tables"] if word else 0, "word_drawings": word["drawings"] if word else 0}}
    if word is None:
        return {"headings": [], "object_counts": {"tex_graphics": len(tex["graphics"]), "tex_tables": len(tex["tables"]), "tex_display_equations": len(tex["equations"])}}
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in word["paragraphs"]:
        by_key.setdefault(row["key"], []).append(row)
    bindings = []
    used: set[int] = set()
    for heading in tex["headings"]:
        candidates = [row for row in by_key.get(heading["key"], []) if row["ordinal"] not in used]
        heading_style_candidates = [
            row
            for row in candidates
            if row["style"].replace(" ", "").lower().startswith("heading")
        ]
        selected = heading_style_candidates or candidates
        if len(selected) == 1:
            word_heading = selected[0]
            used.add(word_heading["ordinal"])
            bindings.append({"tex": heading, "word_paragraph": word_heading, "status": "mapped"})
        else:
            bindings.append({"tex": heading, "word_paragraph": None, "status": "unmapped" if not candidates else "ambiguous"})
    return {
        "headings": bindings,
        "object_counts": {
            "tex_graphics": len(tex["graphics"]), "word_drawings": word["drawings"],
            "tex_tables": len(tex["tables"]), "word_tables": word["tables"],
            "tex_display_equations": len(tex["equations"]), "word_display_equations": len(word["display_equations"]),
            "word_references": word["references"],
        },
    }


def file_hashes(manifest: dict[str, Any]) -> dict[str, str | None]:
    tex = manifest.get("latex")
    rows: dict[str, str | None] = {}
    if tex:
        rows.update({f"tex:{row['path']}": row["sha256"] for row in tex["files"]})
        rows.update({f"asset:{row.get('path') or row['requested_path']}": row["sha256"] for row in tex["graphics"]})
        rows.update({f"bib:{row['path']}": row["sha256"] for row in tex["bibliography_files"]})
    if manifest.get("word"):
        rows["word:document"] = manifest["word"]["sha256"]
    return rows


def delta(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, list[str]]:
    old, new = file_hashes(previous), file_hashes(current)
    return {
        "added": sorted(key for key in new if key not in old),
        "removed": sorted(key for key in old if key not in new),
        "modified": sorted(key for key in new if key in old and new[key] != old[key]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tex-root", type=Path)
    parser.add_argument("--main", default="main.tex")
    parser.add_argument("--docx", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--word-layout", choices=("single-column", "two-column"))
    parser.add_argument("--toolchain-note")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    if not args.tex_root and not args.docx:
        raise SystemExit("Supply --tex-root, --docx, or both")
    root = args.tex_root.resolve() if args.tex_root else None
    main_tex = (root / args.main).resolve() if root else None
    if main_tex is not None and not main_tex.is_file():
        raise SystemExit(f"LaTeX main file not found: {main_tex}")
    if args.docx and not args.docx.is_file():
        raise SystemExit(f"DOCX file not found: {args.docx}")

    latex = tex_inventory(root, main_tex) if root and main_tex else None
    word = docx_inventory(args.docx) if args.docx else None
    manifest: dict[str, Any] = {
        "schema": "latex-word-sync/v1", "generated_at": datetime.now(timezone.utc).isoformat(),
        "latex": latex, "word": word, "bindings": build_bindings(latex, word),
        "run": {"word_layout": args.word_layout, "toolchain_note": args.toolchain_note},
    }
    if args.previous:
        if not args.previous.is_file():
            raise SystemExit(f"Previous manifest not found: {args.previous}")
        manifest["delta"] = delta(json.loads(args.previous.read_text(encoding="utf-8")), manifest)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    mapped = sum(1 for row in manifest["bindings"]["headings"] if row["status"] == "mapped")
    print(f"Wrote {args.output}")
    if latex:
        print(f"LaTeX: {len(latex['files'])} source files, {len(latex['tables'])} table inputs, {len(latex['graphics'])} graphics, {len(latex['citation_keys'])} cited keys")
    if word:
        print(f"Word: {word['tables']} tables, {word['drawings']} drawings, {len(word['display_equations'])} display equations, {word['references']} references")
        print(f"Heading bindings: {mapped}/{len(manifest['bindings']['headings'])}")
    if "delta" in manifest:
        counts = {key: len(value) for key, value in manifest['delta'].items()}
        print(f"Delta: +{counts['added']} ~{counts['modified']} -{counts['removed']}")
    if args.print_json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
