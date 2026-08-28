#!/usr/bin/env python3
"""Batch-import local PDFs into Zotero through the desktop Connector server.

The default mode is a dry run. Use --yes only after confirming the source,
target, and timestamp batch with the user.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


DEFAULT_BASE_URL = "http://127.0.0.1:23119"
CONNECTOR_HEADERS = {"X-Zotero-Connector-API-Version": "3"}
BATCH_RE = re.compile(r"^\d{12}$")


class ConnectorError(RuntimeError):
    pass


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: bytes | str | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, str], bytes]:
    req_headers = dict(CONNECTOR_HEADERS)
    req_headers.update(headers or {})
    payload: bytes | None
    if isinstance(body, dict):
        payload = json_text(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    elif isinstance(body, str):
        payload = body.encode("utf-8")
    else:
        payload = body
    if payload is not None:
        req_headers.setdefault("Content-Length", str(len(payload)))

    url = base_url.rstrip("/") + path
    req = urllib.request.Request(url, data=payload, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()
    except urllib.error.URLError as exc:
        raise ConnectorError(f"无法连接 Zotero Connector：{exc.reason}") from exc


def parse_json(payload: bytes) -> Any:
    if not payload:
        return None
    try:
        return json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return payload.decode("utf-8", errors="replace")


def connector_json(
    base_url: str,
    path: str,
    *,
    method: str = "POST",
    body: dict[str, Any] | None = None,
    timeout: float = 30.0,
    accepted: set[int] | None = None,
) -> tuple[int, Any]:
    status, _, raw = request(
        base_url,
        path,
        method=method,
        body=body or {},
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    if accepted is None:
        accepted = {200}
    if status not in accepted:
        detail = parse_json(raw)
        raise ConnectorError(f"{path} 返回 HTTP {status}: {detail}")
    return status, parse_json(raw)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_pdfs(source: Path, recursive: bool, min_age_seconds: float) -> list[Path]:
    if source.is_file():
        candidates = [source] if source.suffix.lower() == ".pdf" else []
    elif source.is_dir():
        candidates = list(source.rglob("*.pdf") if recursive else source.glob("*.pdf"))
    else:
        raise ConnectorError(f"源路径不存在：{source}")

    now = datetime.now().timestamp()
    result: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        if min_age_seconds > 0 and now - path.stat().st_mtime < min_age_seconds:
            continue
        result.append(path.resolve())
    return sorted(set(result), key=lambda item: str(item).lower())


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "files": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectorError(f"无法读取 manifest：{path} ({exc})") from exc
    if not isinstance(value, dict) or not isinstance(value.get("files", {}), dict):
        raise ConnectorError(f"manifest 格式不受支持：{path}")
    return value


def write_manifest(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def batch_id(value: str | None) -> str:
    result = value or datetime.now().strftime("%Y%m%d%H%M")
    if not BATCH_RE.fullmatch(result):
        raise ConnectorError("batch-id 必须是 12 位本地时间戳，格式为 YYYYMMDDHHmm")
    return result


def target_info(base_url: str, explicit_target: str | None) -> tuple[str, str, dict[str, Any]]:
    _, selected = connector_json(base_url, "/connector/getSelectedCollection", accepted={200})
    if not isinstance(selected, dict):
        raise ConnectorError(f"无法读取 Zotero 当前目标：{selected}")
    targets = {item.get("id"): item for item in selected.get("targets", []) if item.get("id")}
    default_target = selected.get("id") or f"L{selected.get('libraryID')}"
    target_id = explicit_target or default_target
    if target_id not in targets:
        raise ConnectorError(f"目标不存在或不可写：{target_id}")
    return target_id, targets[target_id].get("name") or target_id, selected


def recognized_item(base_url: str, session_id: str, timeout: float) -> Any:
    status, value = connector_json(
        base_url,
        "/connector/getRecognizedItem",
        body={"sessionID": session_id},
        timeout=timeout,
        accepted={200, 204},
    )
    return value if status == 200 else None


def import_one(
    base_url: str,
    path: Path,
    *,
    target_id: str,
    tags: list[str],
    recognize: bool,
    timeout: float,
) -> dict[str, Any]:
    session_id = f"codex-pdf-{uuid.uuid4().hex}"
    metadata = {
        "sessionID": session_id,
        "title": path.stem,
        "url": path.as_uri(),
    }
    data = path.read_bytes()
    status, _, raw = request(
        base_url,
        "/connector/saveStandaloneAttachment",
        method="POST",
        body=data,
        headers={
            "Content-Type": "application/pdf",
            "X-Metadata": json_text(metadata),
        },
        timeout=timeout,
    )
    if status != 201:
        raise ConnectorError(f"保存附件失败 HTTP {status}: {parse_json(raw)}")

    recognized = None
    if recognize:
        recognized = recognized_item(base_url, session_id, timeout)

    connector_json(
        base_url,
        "/connector/updateSession",
        body={"sessionID": session_id, "target": target_id, "tags": tags, "note": ""},
        timeout=timeout,
        accepted={200},
    )
    return {
        "path": str(path),
        "recognized": bool(recognized),
        "recognizedItem": recognized,
        "session": session_id,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="按时间戳批次将本地 PDF 导入 Zotero")
    parser.add_argument("--source", required=True, help="PDF 文件或文件夹")
    parser.add_argument("--batch-id", help="12 位批次时间戳 YYYYMMDDHHmm；默认使用当前本地时间")
    parser.add_argument("--target-id", help="已有 Zotero 目标 ID，例如 L1 或 C123；默认使用当前选中目标")
    parser.add_argument("--tag", action="append", help="额外标签；默认自动添加 batch:<batch-id>")
    parser.add_argument("--manifest", help="manifest 路径；默认放在源文件夹内")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-existing", action="store_true", help="忽略 manifest，重新导入已记录文件")
    parser.add_argument("--min-age-seconds", type=float, default=0, help="跳过最近修改的文件，避免导入尚未下载完成的 PDF")
    parser.add_argument("--no-recognize", action="store_true", help="不等待 Zotero 自动识别 PDF 元数据")
    parser.add_argument("--timeout", type=float, default=180, help="每个 Connector 请求的超时秒数")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=argparse.SUPPRESS)
    parser.add_argument("--yes", action="store_true", help="确认写入 Zotero，并更新 manifest")
    parser.add_argument("--dry-run", action="store_true", help="只预览；默认行为")
    parser.add_argument("--stop-on-error", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = Path(args.source).expanduser().resolve()
    batch = batch_id(args.batch_id)
    manifest_path = (
        Path(args.manifest).expanduser().resolve()
        if args.manifest
        else (source if source.is_dir() else source.parent) / ".zotero-batch-import.json"
    )
    files = list_pdfs(source, args.recursive, args.min_age_seconds)
    manifest = load_manifest(manifest_path)
    recorded = manifest.setdefault("files", {})

    selected_target = None
    target_name = None
    selected_payload = None
    if files:
        target_id, target_name, selected_payload = target_info(args.base_url, args.target_id)
    else:
        target_id = args.target_id or "unknown"

    planned: list[tuple[Path, str]] = []
    skipped: list[dict[str, Any]] = []
    for path in files:
        fingerprint = sha256(path)
        old = recorded.get(fingerprint)
        if old and not args.include_existing:
            skipped.append({"path": str(path), "reason": "manifest", "previous": old})
        else:
            planned.append((path, fingerprint))

    tags = [f"batch:{batch}"] + [tag for tag in (args.tag or []) if tag]
    result: dict[str, Any] = {
        "batchId": batch,
        "batchTag": f"batch:{batch}",
        "source": str(source),
        "manifest": str(manifest_path),
        "targetId": target_id,
        "targetName": target_name,
        "selected": selected_payload,
        "dryRun": not args.yes,
        "planned": [str(path) for path, _ in planned],
        "skipped": skipped,
        "imported": [],
        "failed": [],
    }

    if not args.yes or args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    for path, fingerprint in planned:
        try:
            item_result = import_one(
                args.base_url,
                path,
                target_id=target_id,
                tags=tags,
                recognize=not args.no_recognize,
                timeout=args.timeout,
            )
            result["imported"].append(item_result)
            recorded[fingerprint] = {
                "path": str(path),
                "batchId": batch,
                "importedAt": datetime.now(timezone.utc).isoformat(),
                "recognized": item_result["recognized"],
            }
            write_manifest(manifest_path, manifest)
        except (OSError, ConnectorError) as exc:
            result["failed"].append({"path": str(path), "error": str(exc)})
            if args.stop_on_error:
                break

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
