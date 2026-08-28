#!/usr/bin/env python3
"""Convert local PDFs with MinerU's official signed-upload API.

The API token is read from MINERU_API_KEY and is never written to output.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable


API_ROOT = "https://mineru.net/api/v4"
ZOTERO_API_ROOT = "http://127.0.0.1:23119"
MAX_FILES_PER_BATCH = 50
MAX_FILE_BYTES = 200 * 1024 * 1024


class MinerUError(RuntimeError):
    pass


def _local_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise MinerUError("Zotero local API is unavailable") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MinerUError("Zotero local API returned invalid JSON") from exc


def _local_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"Accept": "text/plain"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8").strip()
    except (urllib.error.HTTPError, urllib.error.URLError, UnicodeDecodeError) as exc:
        raise MinerUError("Zotero could not provide an attachment file URL") from exc


def _file_url_to_path(value: str) -> Path:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "file":
        raise MinerUError("Zotero attachment is not a local file")
    decoded = urllib.parse.unquote(parsed.path)
    if os.name == "nt" and decoded.startswith("/") and len(decoded) > 2 and decoded[2] == ":":
        decoded = decoded[1:]
    path = Path(decoded)
    if not path.is_file():
        raise MinerUError(f"Zotero attachment file is missing: {path}")
    return path


def _zotero_collection_name() -> str:
    selected = _local_json(f"{ZOTERO_API_ROOT}/connector/getSelectedCollection", "POST", {})
    if isinstance(selected, dict) and selected.get("name"):
        return str(selected["name"])
    raise MinerUError("Zotero has no selected collection")


def _zotero_pdf_paths(selector: str) -> list[Path]:
    collections = _local_json(f"{ZOTERO_API_ROOT}/api/users/0/collections?format=json&limit=100")
    if not isinstance(collections, list):
        raise MinerUError("Zotero returned an unexpected collection list")
    collection = next((c for c in collections if c.get("key") == selector or c.get("data", {}).get("name") == selector), None)
    if collection is None:
        raise MinerUError(f"Zotero collection not found: {selector}")
    collection_key = str(collection.get("key"))
    all_items: list[Any] = []
    start = 0
    while True:
        url = f"{ZOTERO_API_ROOT}/api/users/0/collections/{collection_key}/items?format=json&limit=100&start={start}"
        page = _local_json(url)
        if not isinstance(page, list):
            raise MinerUError("Zotero returned an unexpected collection item list")
        all_items.extend(page)
        if len(page) < 100:
            break
        start += len(page)
    paths: list[Path] = []
    for item in all_items:
        data = item.get("data", {}) if isinstance(item, dict) else {}
        if data.get("itemType") != "attachment" or data.get("contentType") != "application/pdf":
            continue
        attachment_key = str(item.get("key") or "")
        if not attachment_key:
            continue
        file_url = _local_text(f"{ZOTERO_API_ROOT}/api/users/0/items/{attachment_key}/file/view/url")
        try:
            paths.append(_file_url_to_path(file_url))
        except MinerUError:
            continue
    unique = list(dict.fromkeys(paths))
    if not unique:
        raise MinerUError(f"No local PDF attachments found in Zotero collection: {selector}")
    return unique


def _load_token(token_env: str, token_file: Path | None) -> str:
    token = os.environ.get(token_env, "").strip()
    if token:
        return token
    try:
        if token_file and token_file.is_file():
            return token_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise MinerUError("Could not read the MinerU secret file") from exc
    return ""


def _json_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}", "Accept": "*/*"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                detail = _safe_error_body(exc.read())
                raise MinerUError(f"MinerU API HTTP {exc.code}: {detail}") from exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = max(5.0, min(120.0, float(retry_after))) if retry_after else 15.0 * (attempt + 1)
            except ValueError:
                delay = 15.0 * (attempt + 1)
            exc.read()
            time.sleep(delay)
        except urllib.error.URLError as exc:
            raise MinerUError(f"MinerU API network error: {exc.reason}") from exc
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MinerUError("MinerU API returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise MinerUError("MinerU API returned an unexpected response")
    if result.get("code", 0) not in (0, None):
        raise MinerUError(f"MinerU API error {result.get('code')}: {result.get('msg', 'request failed')}")
    return result


def _safe_error_body(raw: bytes) -> str:
    try:
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            return str(data.get("msg") or data.get("message") or "request failed")[:500]
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return "request failed"


def _upload(url: str, path: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise MinerUError("MinerU returned an invalid signed-upload URL")
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_type(parsed.netloc, timeout=300)
    request_path = parsed.path or "/"
    if parsed.query:
        request_path += "?" + parsed.query
    try:
        connection.putrequest("PUT", request_path)
        connection.putheader("Content-Length", str(path.stat().st_size))
        connection.endheaders()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                connection.send(chunk)
        response = connection.getresponse()
        response.read()
        if response.status < 200 or response.status >= 300:
            raise MinerUError(f"file upload failed with HTTP {response.status}")
    except (OSError, http.client.HTTPException) as exc:
        raise MinerUError("file upload network error") from exc
    finally:
        connection.close()


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"Accept": "application/zip"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as out:
            shutil.copyfileobj(response, out)
    except urllib.error.HTTPError as exc:
        raise MinerUError(f"result download failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise MinerUError(f"result download network error: {exc.reason}") from exc


def _source_id(path: Path) -> str:
    stat = path.stat()
    digest = hashlib.sha256()
    digest.update(str(path.resolve()).encode("utf-8", "surrogatepass"))
    digest.update(str(stat.st_size).encode("ascii"))
    digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return digest.hexdigest()[:32]


def _existing_output(path: Path) -> tuple[bool, str]:
    output = path.parent / f"{path.stem}_mineru"
    full_md = output / "full.md"
    if full_md.is_file() and full_md.stat().st_size > 0:
        return True, str(output)
    return False, str(output)


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            target = (destination / info.filename).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise MinerUError("MinerU ZIP contained an unsafe path") from exc
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _find_full_md(root: Path) -> Path:
    candidates = [p for p in root.rglob("*") if p.is_file() and p.name.lower() == "full.md"]
    if not candidates:
        raise MinerUError("MinerU result ZIP did not contain full.md")
    return min(candidates, key=lambda p: (len(p.relative_to(root).parts), str(p)))


def _native_path(path: Path) -> str:
    """Return a Windows extended-length path when needed for result assets."""
    value = str(path.resolve())
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        return "\\\\?\\" + value
    return value


def _copy_result_file(source: Path, target: Path) -> None:
    """Copy without CopyFile2, whose legacy path handling rejects long targets."""
    os.makedirs(_native_path(target.parent), exist_ok=True)
    with source.open("rb") as src, open(_native_path(target), "wb") as dst:
        shutil.copyfileobj(src, dst)


def _install_result(staging: Path, output: Path, overwrite: bool) -> None:
    full_md = _find_full_md(staging)
    source_root = full_md.parent
    if output.exists():
        if not overwrite:
            raise MinerUError(f"output already exists: {output} (use --overwrite to replace it)")
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    os.makedirs(_native_path(output), exist_ok=False)
    for child in source_root.iterdir():
        entries = [child] if child.is_file() else child.rglob("*")
        for entry in entries:
            target = output / entry.relative_to(source_root)
            if entry.is_dir():
                os.makedirs(_native_path(target), exist_ok=True)
            elif entry.is_file():
                _copy_result_file(entry, target)
    final_md = output / "full.md"
    if not final_md.is_file() or final_md.stat().st_size == 0:
        raise MinerUError("installed MinerU result has no non-empty full.md")


def _result_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("extract_result", "results", "items"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
        if "file_name" in data or "data_id" in data or "state" in data:
            return [data]
    return []


def _poll_batch(token: str, batch_id: str, expected: dict[str, Path], interval: float, timeout: float) -> dict[str, dict[str, Any]]:
    deadline = time.monotonic() + timeout
    found: dict[str, dict[str, Any]] = {}
    by_name = {path.name: data_id for data_id, path in expected.items()}
    terminal_states = {"done", "failed"}
    while time.monotonic() < deadline:
        response = _json_request("GET", f"{API_ROOT}/extract-results/batch/{batch_id}", token)
        for item in _result_items(response.get("data")):
            key = str(item.get("data_id") or item.get("file_name") or "")
            if key not in expected:
                key = by_name.get(str(item.get("file_name") or ""), key)
            if key in expected:
                found[key] = item
        if len(found) >= len(expected) and all(str(item.get("state") or "") in terminal_states for item in found.values()):
            return found
        time.sleep(interval)
    raise MinerUError(f"timed out waiting for MinerU batch {batch_id}")


def _prepare_paths(paths: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = raw.expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise MinerUError(f"not a PDF file: {raw}")
        if path not in seen:
            result.append(path)
            seen.add(path)
    if not result:
        raise MinerUError("no PDF files were provided")
    for path in result:
        size = path.stat().st_size
        if size == 0:
            raise MinerUError(f"empty PDF file: {path}")
        if size > MAX_FILE_BYTES:
            raise MinerUError(f"PDF exceeds MinerU's 200 MB limit: {path}")
    return result


def _directory_pdfs(directory: Path, recursive: bool) -> list[Path]:
    if not directory.is_dir():
        raise MinerUError(f"not a directory: {directory}")
    iterator = directory.rglob("*.pdf") if recursive else directory.glob("*.pdf")
    return sorted(iterator)


def _convert_batch(paths: list[Path], token: str, model: str, interval: float, timeout: float, overwrite: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    pending: list[Path] = []
    for path in paths:
        exists, output = _existing_output(path)
        if exists and not overwrite:
            results.append({"source": str(path), "status": "skipped", "output": output})
        else:
            pending.append(path)
    if not pending:
        return results

    request_files = []
    expected: dict[str, Path] = {}
    for path in pending:
        data_id = _source_id(path)
        expected[data_id] = path
        request_files.append({"name": path.name, "data_id": data_id})
    response = _json_request("POST", f"{API_ROOT}/file-urls/batch", token, {"files": request_files, "model_version": model})
    data = response.get("data")
    if not isinstance(data, dict):
        raise MinerUError("MinerU did not return upload URLs")
    batch_id = str(data.get("batch_id") or "")
    urls = data.get("file_urls")
    if not batch_id or not isinstance(urls, list) or len(urls) != len(pending):
        raise MinerUError("MinerU returned an incomplete signed-upload response")
    for path, url in zip(pending, urls):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise MinerUError("MinerU returned an invalid signed-upload URL")
        _upload(url, path)

    completed = _poll_batch(token, batch_id, expected, interval, timeout)
    for data_id, path in expected.items():
        item = completed.get(data_id, {})
        state = str(item.get("state") or "")
        full_zip_url = item.get("full_zip_url")
        if state != "done" or not isinstance(full_zip_url, str):
            results.append({"source": str(path), "status": "failed", "batch_id": batch_id, "error": item.get("err_msg") or f"state={state or 'unknown'}"})
            continue
        output = path.parent / f"{path.stem}_mineru"
        # Keep the staging path short on Windows; long PDF titles plus extracted image names
        # can exceed the legacy path limit when staging below the Zotero storage directory.
        temp_parent = Path(tempfile.mkdtemp(prefix="mu-", dir=tempfile.gettempdir()))
        try:
            archive = temp_parent / "result.zip"
            extracted = temp_parent / "extracted"
            _download(full_zip_url, archive)
            _safe_extract(archive, extracted)
            _install_result(extracted, output, overwrite)
            manifest = {
                "source_name": path.name,
                "source_size": path.stat().st_size,
                "source_sha256": _sha256(path),
                "model_version": model,
                "batch_id": batch_id,
            }
            (output / ".mineru-source.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append({"source": str(path), "status": "converted", "output": str(output), "batch_id": batch_id})
        except (OSError, zipfile.BadZipFile, MinerUError) as exc:
            results.append({"source": str(path), "status": "failed", "batch_id": batch_id, "error": str(exc)})
        finally:
            shutil.rmtree(temp_parent, ignore_errors=True)
    return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert local PDFs with MinerU and save full.md beside each PDF")
    parser.add_argument("pdf", nargs="*", type=Path, help="PDF paths")
    parser.add_argument("--directory", type=Path, help="directory containing PDFs")
    parser.add_argument("--recursive", action="store_true", help="recurse when --directory is used")
    parser.add_argument("--overwrite", action="store_true", help="replace existing *_mineru output folders")
    parser.add_argument("--model-version", default="vlm", choices=("pipeline", "vlm", "MinerU-HTML"))
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--token-env", default="MINERU_API_KEY", help="environment variable containing the API token")
    parser.add_argument("--token-file", type=Path, help="optional user-supplied secret file; prefer --token-env")
    parser.add_argument("--zotero-collection", help="Zotero collection name or key")
    parser.add_argument("--zotero-selected", action="store_true", help="use the collection currently selected in Zotero")
    args = parser.parse_args()

    token = _load_token(args.token_env, args.token_file)
    if not token:
        print(f"Missing MinerU token in environment variable {args.token_env}", file=sys.stderr)
        return 2
    selectors = int(bool(args.zotero_collection)) + int(args.zotero_selected)
    if selectors > 1:
        print("Use either --zotero-collection or --zotero-selected, not both", file=sys.stderr)
        return 2
    if args.directory and (args.pdf or selectors):
        print("Use either filesystem paths, --directory, or a Zotero collection", file=sys.stderr)
        return 2
    if selectors and args.pdf:
        print("Use either PDF paths or a Zotero collection, not both", file=sys.stderr)
        return 2
    try:
        if args.zotero_selected:
            paths = _prepare_paths(_zotero_pdf_paths(_zotero_collection_name()))
        elif args.zotero_collection:
            paths = _prepare_paths(_zotero_pdf_paths(args.zotero_collection))
        else:
            paths = _prepare_paths(_directory_pdfs(args.directory, args.recursive) if args.directory else args.pdf)
        all_results: list[dict[str, Any]] = []
        for start in range(0, len(paths), MAX_FILES_PER_BATCH):
            batch = paths[start : start + MAX_FILES_PER_BATCH]
            all_results.extend(_convert_batch(batch, token, args.model_version, max(1.0, args.poll_interval), args.timeout, args.overwrite))
        print(json.dumps({"results": all_results}, ensure_ascii=False, indent=2))
        return 1 if any(item.get("status") == "failed" for item in all_results) else 0
    except MinerUError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
