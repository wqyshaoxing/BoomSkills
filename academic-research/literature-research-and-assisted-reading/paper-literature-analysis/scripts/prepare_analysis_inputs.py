#!/usr/bin/env python3
"""Resolve Zotero PDF attachments and prepare per-paper analysis manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


ZOTERO_ROOT = "http://127.0.0.1:23119"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.IGNORECASE)
REPO_HOSTS = {"github.com", "gitlab.com", "codeberg.org", "bitbucket.org", "huggingface.co"}
NON_REPO_SEGMENTS = {"issues", "pull", "pulls", "blob", "raw", "tree", "releases", "actions", "wiki", "topics", "search"}


class PrepareError(RuntimeError):
    pass


def local_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers, method=method), timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, UnicodeError, json.JSONDecodeError) as exc:
        raise PrepareError("Zotero local API is unavailable or returned invalid data") from exc


def local_text(url: str) -> str:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "text/plain"}), timeout=20) as response:
            return response.read().decode("utf-8").strip()
    except (urllib.error.HTTPError, urllib.error.URLError, UnicodeError) as exc:
        raise PrepareError("Zotero could not provide an attachment file URL") from exc


def selected_collection() -> str:
    payload = local_json(f"{ZOTERO_ROOT}/connector/getSelectedCollection", "POST", {})
    if isinstance(payload, dict) and payload.get("name"):
        return str(payload["name"])
    raise PrepareError("Zotero has no selected collection")


def collection_pdfs(selector: str) -> list[Path]:
    collections = local_json(f"{ZOTERO_ROOT}/api/users/0/collections?format=json&limit=100")
    if not isinstance(collections, list):
        raise PrepareError("Zotero returned an invalid collection list")
    collection = next((c for c in collections if c.get("key") == selector or c.get("data", {}).get("name") == selector), None)
    if not collection:
        raise PrepareError(f"Zotero collection not found: {selector}")
    key = str(collection.get("key"))
    items: list[dict[str, Any]] = []
    start = 0
    while True:
        page = local_json(f"{ZOTERO_ROOT}/api/users/0/collections/{key}/items?format=json&limit=100&start={start}")
        if not isinstance(page, list):
            raise PrepareError("Zotero returned an invalid collection item list")
        items.extend(x for x in page if isinstance(x, dict))
        if len(page) < 100:
            break
        start += len(page)
    paths: list[Path] = []
    for item in items:
        data = item.get("data", {})
        if data.get("itemType") != "attachment" or data.get("contentType") != "application/pdf":
            continue
        url = local_text(f"{ZOTERO_ROOT}/api/users/0/items/{item.get('key')}/file/view/url")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "file":
            continue
        raw_path = urllib.parse.unquote(parsed.path)
        if os.name == "nt" and raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
            raw_path = raw_path[1:]
        path = Path(raw_path)
        if path.is_file():
            paths.append(path.resolve())
    return list(dict.fromkeys(paths))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_candidates(text: str) -> list[str]:
    found: list[str] = []
    for raw in URL_RE.findall(text):
        value = raw.rstrip(".,;:!?)]}")
        parsed = urllib.parse.urlparse(value)
        host = (parsed.hostname or "").lower()
        pieces = [p for p in parsed.path.split("/") if p]
        if host not in REPO_HOSTS or len(pieces) < 2 or pieces[0].lower() in NON_REPO_SEGMENTS:
            continue
        base = f"{parsed.scheme}://{parsed.netloc}/{'/'.join(pieces[:2])}"
        if base not in found:
            found.append(base)
    return found


def prepare_one(pdf: Path, run_root: Path) -> dict[str, Any]:
    mineru_dir = pdf.parent / f"{pdf.stem}_mineru"
    mineru_md = mineru_dir / "full.md"
    text = mineru_md.read_text(encoding="utf-8", errors="replace") if mineru_md.is_file() else ""
    images = sum(1 for p in mineru_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS) if mineru_dir.is_dir() else 0
    paper_id = hashlib.sha256(str(pdf).encode("utf-8", "surrogatepass")).hexdigest()[:16]
    staging = pdf.parent / ".paper-analysis" / paper_id
    staging.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "id": paper_id,
        "pdf": str(pdf),
        "pdf_sha256": sha256(pdf),
        "mineru_dir": str(mineru_dir),
        "mineru_full_md": str(mineru_md),
        "mineru_present": mineru_md.is_file() and mineru_md.stat().st_size > 0,
        "mineru_image_count": images,
        "repo_candidates": repository_candidates(text),
        "staging_dir": str(staging),
    }
    (staging / "input.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--zotero-selected", action="store_true")
    group.add_argument("--zotero-collection")
    parser.add_argument("--manifest", type=Path, help="combined manifest path; defaults to a temporary file")
    args = parser.parse_args()
    selector = selected_collection() if args.zotero_selected else args.zotero_collection
    paths = collection_pdfs(selector)
    if not paths:
        raise PrepareError(f"No local PDF attachments found in Zotero collection: {selector}")
    run_root = Path(tempfile.mkdtemp(prefix="paper-analysis-"))
    manifest_path = args.manifest or (run_root / "manifest.json")
    records = [prepare_one(path, run_root) for path in paths]
    payload = {"version": 1, "collection": selector, "run_id": uuid.uuid4().hex, "papers": records}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "collection": selector, "papers": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PrepareError as exc:
        print(str(exc), file=__import__("sys").stderr)
        raise SystemExit(2)
