#!/usr/bin/env python3
"""Run isolated OpenCode CLI processes per paper, with bounded retries."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "references" / "paper-prompt-template.md"
REQUIRED_HEADINGS = [
    "文献的领域和方向",
    "文献声明的创新点和解决的问题",
    "算法与源码分析",
    "Benchmark、评价指标与数据集",
    "摘要与结论",
    "行文风格与章节逻辑",
    "与引用文献的关系和联系",
]


PROVENANCE_TERMS = (
    "official implementation verified",
    "official candidate unverified",
    "third-party reproduction",
    "no public source found",
    "access/clone failure",
)
SOURCE_SUFFIXES = {".py", ".ipynb", ".cpp", ".cc", ".c", ".h", ".hpp", ".java", ".js", ".ts", ".yaml", ".yml", ".json"}
SHAPE_TRACE_TERMS = ("示例", "输入", "输出", "形状")
SHAPE_TRACE_DETAIL_TERMS = ("逐层", "逐模块", "数据流", "shape", "张量", "中间")


def candidate_is_structurally_complete(candidate: Path) -> bool:
    if not candidate.is_file() or candidate.stat().st_size == 0:
        return False
    text = candidate.read_text(encoding="utf-8", errors="replace")
    if not all(re.search(rf"^#+\s+.*{re.escape(heading)}", text, re.MULTILINE | re.IGNORECASE) for heading in REQUIRED_HEADINGS):
        return False
    if not any(term in text.lower() for term in PROVENANCE_TERMS):
        return False
    normalized = text.lower()
    if not all(term.lower() in normalized for term in SHAPE_TRACE_TERMS):
        return False
    if not any(term.lower() in normalized for term in SHAPE_TRACE_DETAIL_TERMS):
        return False
    source_dir = candidate.parent / "source_code"
    source_files = [path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES] if source_dir.exists() else []
    if source_files:
        path_mention = re.search(r"\b[\w./-]+\.(?:py|ipynb|cpp|cc|c|h|hpp|java|js|ts|yaml|yml|json)\b", text, re.IGNORECASE)
        symbol_mention = re.search(r"\b(?:class|function|method|def|symbol|config(?:uration)?\s+key)\b|类|函数|方法|配置键", text, re.IGNORECASE)
        if not (path_mention and symbol_mention):
            return False
    return True


def load_user_environment(name: str) -> None:
    """Load a persisted Windows user variable for processes from stale parents."""
    if os.environ.get(name) or os.name != "nt":
        return
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
        if value:
            os.environ[name] = str(value)
    except OSError:
        return


def prompt_for(
    record: dict[str, Any],
    candidate: Path,
    source_code_dir: Path,
    review_feedback: str,
    template_path: Path,
    model_role: str,
) -> str:
    template = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{MINERU_DIR}}": str(Path(record["mineru_dir"]).resolve()),
        "{{MINERU_FULL_MD}}": str(Path(record["mineru_full_md"]).resolve()),
        "{{MINERU_IMAGE_COUNT}}": str(record.get("mineru_image_count", 0)),
        "{{STAGING_DIR}}": str(Path(record["staging_dir"]).resolve()),
        "{{SOURCE_CODE_DIR}}": str(source_code_dir.resolve()),
        "{{REPOSITORY_CANDIDATES}}": json.dumps(record.get("repo_candidates", []), ensure_ascii=False),
        "{{CANDIDATE_OUTPUT}}": str(candidate.resolve()),
        "{{MODEL_ROLE}}": model_role,
        "{{REVIEW_FEEDBACK}}": review_feedback or "No previous review feedback; this is the first attempt.",
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def resolve_command(spec: str) -> list[str]:
    parts = shlex.split(spec, posix=False)
    if not parts:
        raise ValueError("OPENCODE_COMMAND must not be empty")
    if os.name == "nt" and not Path(parts[0]).suffix:
        resolved = shutil.which(parts[0]) or shutil.which(parts[0] + ".cmd") or shutil.which(parts[0] + ".exe")
    else:
        resolved = shutil.which(parts[0])
    if resolved:
        parts[0] = resolved
    return parts


def run_one(
    record: dict[str, Any],
    opencode_command: str,
    model: str,
    timeout: float,
    review_feedback: str,
    attempt: int,
    template_path: Path,
    max_vision_attachments: int,
) -> dict[str, Any]:
    staging = Path(record["staging_dir"])
    attempt_dir = staging / f"attempt-{attempt}"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    candidate = attempt_dir / "candidate.md"
    source_code_dir = attempt_dir / "source_code"
    source_code_dir.mkdir(parents=True, exist_ok=True)
    command = resolve_command(opencode_command)
    command.extend(["run", "--pure", "--auto"])
    if model:
        command.extend(["--model", model])
    command.extend(["--format", "json"])
    environment = os.environ.copy()
    prompt = (
        "Before taking any action, load and follow the registered OpenCode skill "
        "`paper-literature-analysis`. This is a production batch: write only the "
        "assigned candidate and satisfy every evidence/review gate in that skill.\n\n"
        + prompt_for(record, candidate, source_code_dir, review_feedback, template_path, "opencode/default-model")
    )
    attached_image_count = 0
    image_paths = sorted(
        path
        for path in Path(record["mineru_dir"]).rglob("*")
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    )
    if max_vision_attachments > 0:
        image_paths = image_paths[:max_vision_attachments]
    for image_path in image_paths:
        option = ["--file", str(image_path.resolve())]
        # Windows command-line parsing has a practical limit well below
        # the nominal CreateProcess limit because opencode.ps1/npm adds
        # its own arguments. Keep a conservative budget and let the agent
        # inspect any remaining images through the local workspace.
        if os.name == "nt" and len(" ".join(command + option)) > 7000:
            break
        command.extend(option)
        attached_image_count += 1
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            cwd=str(attempt_dir),
            timeout=timeout,
            check=False,
            env=environment,
        )
    except FileNotFoundError:
        return {"id": record["id"], "status": "backend_missing", "error": f"OpenCode executable not found: {command[0]}"}
    except subprocess.TimeoutExpired:
        return {"id": record["id"], "status": "timeout", "attempt": attempt}

    (attempt_dir / "opencode.stdout.jsonl").write_text(completed.stdout or "", encoding="utf-8")
    (attempt_dir / "opencode.stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
    status = "candidate" if completed.returncode == 0 and candidate_is_structurally_complete(candidate) else "failed"
    error = None
    if status != "candidate":
        error = "OpenCode did not produce a successful candidate with all required sections"
    return {
        "id": record["id"],
        "status": status,
        "backend": "opencode",
        "model": model or "configured-default",
        "model_role": "opencode/default-model",
        "attached_image_count": attached_image_count,
        "attempt": attempt,
        "candidate": str(candidate),
        "returncode": completed.returncode,
        "error": error,
    }


def run_with_retries(
    record: dict[str, Any],
    opencode_command: str,
    model: str,
    timeout: float,
    review_feedback: str,
    first_attempt: int,
    max_retries: int,
    template_path: Path,
    max_vision_attachments: int,
) -> dict[str, Any]:
    """Retry OpenCode per paper before handing the paper back to Codex."""
    feedback = review_feedback
    last_result: dict[str, Any] | None = None
    for retry_index in range(max_retries + 1):
        attempt = first_attempt + retry_index
        result = run_one(
            record,
            opencode_command,
            model,
            timeout,
            feedback,
            attempt,
            template_path,
            max_vision_attachments,
        )
        result["retry_index"] = retry_index
        last_result = result
        if result.get("status") == "candidate":
            result["attempts_used"] = retry_index + 1
            return result
        if result.get("status") in {"api_key_missing", "backend_missing"}:
            result["attempts_used"] = retry_index + 1
            result["fallback_required"] = True
            return result
        feedback = (
            (review_feedback + "\n\n") if review_feedback else ""
        ) + (
            "The previous OpenCode attempt did not produce a usable candidate. "
            f"Retry number {retry_index + 1} failed with status "
            f"{result.get('status', 'unknown')} and return code "
            f"{result.get('returncode', 'unavailable')}. Re-read the evidence "
            "and write a complete candidate with all seven required sections "
            "to the assigned path."
        )
    assert last_result is not None
    last_result["status"] = "opencode_retry_exhausted"
    last_result["attempts_used"] = max_retries + 1
    last_result["fallback_required"] = True
    return last_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--opencode-command", default=os.environ.get("OPENCODE_COMMAND", "opencode"))
    parser.add_argument("--model", default=os.environ.get("OPENCODE_MODEL", ""), help="OpenCode model override; omit to use the configured default")
    parser.add_argument("--max-vision-attachments", type=int, default=int(os.environ.get("OPENCODE_MAX_VISION_ATTACHMENTS", "8")))
    parser.add_argument("--max-active", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=7200.0)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument(
        "--max-retries",
        type=int,
        default=int(os.environ.get("OPENCODE_MAX_RETRIES", "2")),
        help="additional OpenCode retries per paper before Codex fallback (default: 2)",
    )
    parser.add_argument("--template", type=Path, default=TEMPLATE_PATH)
    parser.add_argument("--item-id", action="append", help="run only these manifest item IDs")
    parser.add_argument("--review-feedback", default="")
    args = parser.parse_args()
    if not 1 <= args.max_active <= 5:
        parser.error("--max-active must be between 1 and 5")
    if args.max_vision_attachments < 0:
        parser.error("--max-vision-attachments must be non-negative")
    if args.max_retries < 0:
        parser.error("--max-retries must be non-negative")

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = payload.get("papers", [])
    if args.item_id:
        wanted = set(args.item_id)
        records = [record for record in records if record.get("id") in wanted]

    started = time.time()
    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=args.max_active) as pool:
        futures = []
        for record in records:
            futures.append(
                pool.submit(
                    run_with_retries,
                    record,
                    args.opencode_command,
                    args.model,
                    args.timeout,
                    args.review_feedback,
                    args.attempt,
                    args.max_retries,
                    args.template,
                    args.max_vision_attachments,
                )
            )
        for future in as_completed(futures):
            results.append(future.result())
    print(json.dumps({"elapsed_seconds": round(time.time() - started, 1), "results": results}, ensure_ascii=False, indent=2))
    return 1 if any(result.get("status") != "candidate" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
