#!/usr/bin/env python3
"""Read-only diagnosis for Codex tasks that stopped working after a provider switch.

Reports the active provider/auth configuration, login status, model-catalog coverage
against the models pinned by existing tasks, and recent auth/model errors from the app
logs grouped by task id. Nothing is written; use repair.py to apply fixes.
"""

from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

AUTH_LOCK_KEYS = ("preferred_auth_method", "forced_login_method")
BUILTIN_PROVIDER = "openai"
MAX_LISTED = 20

LOG_PATTERNS = (
    ("401/unauthorized", re.compile(r"401 Unauthorized|Missing bearer or basic authentication", re.I)),
    ("unknown model", re.compile(r"Unknown model ([A-Za-z0-9._:\-]+) is used", re.I)),
    ("transport", re.compile(r"connection refused|dns error|failed to connect to websocket", re.I)),
)
THREAD_RE = re.compile(r"thread[_\.]id[=:]([0-9a-fA-F\-]{36})")
MODEL_RE = re.compile(r"model[=:]([A-Za-z0-9._:\-]+)")


def out(text: str = "") -> None:
    print(text)


def section(title: str) -> None:
    out()
    out(f"--- {title} ---")


def find_codex_home(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".codex"


def find_codex_bin(explicit: str | None) -> str | None:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    for env_name in ("CODEX_BIN", "CODEX_CLI_PATH"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(value)
    which = shutil.which("codex")
    if which:
        candidates.append(which)

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.extend(sorted(glob.glob(str(Path(local_appdata) / "OpenAI/Codex/bin/*/codex.exe")), reverse=True))
    home = Path.home()
    candidates.extend(sorted(glob.glob(str(home / ".codex/bin/*/codex")), reverse=True))
    candidates.extend(["/usr/local/bin/codex", "/opt/homebrew/bin/codex", str(home / ".local/bin/codex")])
    candidates.extend(sorted(glob.glob("/Applications/Codex.app/Contents/Resources/*/codex")))

    for cand in candidates:
        if cand and Path(cand).exists():
            return cand
    return None


def codex_env(codex_home: Path | None) -> dict[str, str]:
    env = dict(os.environ)
    if codex_home is not None:
        env["CODEX_HOME"] = str(codex_home)
    return env


def run(cmd: list[str], codex_home: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=codex_env(codex_home),
    )


def jw_exp(token: str | None) -> int | None:
    if not token or token.count(".") < 2:
        return None
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None
    return claims.get("exp")


def format_ts(value: float | int | None) -> str:
    if not value:
        return "?"
    return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def one_line(text: str | None, width: int = 64) -> str:
    flat = re.sub(r"\s+", " ", text or "").strip()
    return flat if len(flat) <= width else flat[: width - 1] + "\u2026"


def query(db: Path, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def table_names(db: Path) -> list[str]:
    return [r[0] for r in query(db, "select name from sqlite_master where type='table'")]


def root_level_keys(text: str) -> dict[str, int]:
    """Return root-table keys (outside any [section]) mapped to their 1-based line number."""
    keys: dict[str, int] = {}
    in_section = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            in_section = True
            continue
        if in_section:
            continue
        match = re.match(r"([A-Za-z0-9_\-\.]+)\s*=", line)
        if match:
            keys[match.group(1)] = lineno
    return keys


def load_toml(path: Path) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def catalog_slugs(
    codex_bin: str | None, codex_home: Path | None = None, bundled: bool = False
) -> dict[str, dict] | None:
    if not codex_bin:
        return None
    cmd = [codex_bin, "debug", "models"] + (["--bundled"] if bundled else [])
    try:
        result = run(cmd, codex_home)
    except Exception:
        return None
    if result.returncode != 0:
        return None
    try:
        models = json.loads(result.stdout)["models"]
    except Exception:
        return None
    return {m["slug"]: m for m in models}


def newest_state_db(codex_home: Path) -> Path | None:
    candidates = [p for p in codex_home.glob("state_*.sqlite") if p.is_file()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for cand in candidates:
        try:
            if "threads" in table_names(cand):
                return cand
        except sqlite3.Error:
            continue
    return None


def newest_logs_db(codex_home: Path) -> Path | None:
    candidates = [p for p in codex_home.glob("logs_*.sqlite") if p.is_file()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for cand in candidates:
        try:
            if "logs" in table_names(cand):
                return cand
        except sqlite3.Error:
            continue
    return None


def load_threads(codex_home: Path) -> list[dict]:
    db = newest_state_db(codex_home)
    if not db:
        return []
    try:
        rows = query(
            db,
            "select id, model_provider, model, title, cwd, archived, updated_at from threads",
        )
    except sqlite3.Error:
        return []
    return [dict(r) for r in rows]


def scan_logs(codex_home: Path, limit: int) -> tuple[Path | None, list[dict], Counter, Counter, int]:
    db = newest_logs_db(codex_home)
    if not db:
        return None, [], Counter(), Counter(), 0
    rows = query(
        db,
        """
        select id, ts, level, target, feedback_log_body
        from logs
        where feedback_log_body is not null
        order by id desc limit ?
        """,
        (limit,),
    )
    findings: list[dict] = []
    per_signature: Counter = Counter()
    per_task: Counter = Counter()
    for row in rows:
        body = row["feedback_log_body"] or ""
        for name, pattern in LOG_PATTERNS:
            if not pattern.search(body):
                continue
            task = THREAD_RE.search(body)
            model = MODEL_RE.search(body)
            findings.append(
                {
                    "ts": row["ts"],
                    "level": row["level"],
                    "target": row["target"],
                    "signature": name,
                    "task": task.group(1) if task else None,
                    "model": model.group(1) if model else None,
                }
            )
            per_signature[name] += 1
            if task:
                per_task[task.group(1)] += 1
            break
    return db, findings, per_signature, per_task, len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", help="path to CODEX_HOME (default: $CODEX_HOME or ~/.codex)")
    parser.add_argument("--codex-bin", help="path to the codex executable")
    parser.add_argument("--log-limit", type=int, default=50000, help="max log rows to scan (newest first)")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    codex_home = find_codex_home(args.codex_home)
    config_path = codex_home / "config.toml"
    auth_path = codex_home / "auth.json"
    codex_bin = find_codex_bin(args.codex_bin)
    findings: list[str] = []

    out("=== Codex provider-switch diagnosis ===")
    out(f"codex home   : {codex_home}")
    out(f"codex binary : {codex_bin or 'NOT FOUND (pass --codex-bin)'}")
    if codex_bin:
        try:
            version = run([codex_bin, "--version"], codex_home).stdout.strip()
            out(f"version      : {version}")
        except Exception:
            pass
    out(f"config       : {config_path} ({'present' if config_path.exists() else 'MISSING'})")

    # ---------------------------------------------------------------- config
    config = load_toml(config_path)
    config_text = config_path.read_text(encoding="utf-8", errors="replace") if config_path.exists() else ""
    root_keys = root_level_keys(config_text)
    current_model = config.get("model")
    current_provider = config.get("model_provider", BUILTIN_PROVIDER)
    catalog_override = config.get("model_catalog_json")
    providers = config.get("model_providers", {}) or {}

    section("config.toml")
    out(f"model              : {current_model}")
    out(f"model_provider     : {current_provider}")
    out(f"model_catalog_json : {catalog_override or '(not set - bundled catalog is used)'}")
    out(f"providers defined  : {', '.join(sorted(providers)) or '(none beyond built-in openai)'}")
    locked = {key: config.get(key) for key in AUTH_LOCK_KEYS if key in root_keys}
    if locked:
        out("auth-locking keys  : " + ", ".join(f"{k}={v!r}" for k, v in locked.items()))
    else:
        out("auth-locking keys  : none")

    # ------------------------------------------------------------------ auth
    section("auth.json / login")
    api_key_present = False
    if auth_path.exists():
        try:
            auth = json.loads(auth_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            auth = {}
        api_key_present = bool(auth.get("OPENAI_API_KEY"))
        tokens = auth.get("tokens") or {}
        exp = jw_exp(tokens.get("access_token"))
        exp_note = ""
        if exp:
            expired = exp < datetime.now(tz=timezone.utc).timestamp()
            exp_note = f", access_token {'EXPIRED ' if expired else 'valid until '}{format_ts(exp)}"
        out(f"auth_mode          : {auth.get('auth_mode')!r}")
        out(f"OPENAI_API_KEY     : {'present' if api_key_present else 'null/absent'}")
        out(f"stored tokens      : {'yes' if tokens else 'no'}{exp_note}")
    else:
        out("auth.json missing")

    if codex_bin:
        try:
            status = run([codex_bin, "login", "status"], codex_home)
            text = (status.stdout or status.stderr).strip() or "(no output)"
            out(f"login status       : {text}")
        except Exception as exc:  # noqa: BLE001
            out(f"login status       : unavailable ({exc})")

    # --------------------------------------------------------------- catalog
    live = catalog_slugs(codex_bin, codex_home, bundled=False) or {}
    bundled = catalog_slugs(codex_bin, codex_home, bundled=True) or {}
    threads = load_threads(codex_home)
    thread_models = Counter(t.get("model") for t in threads if t.get("model"))

    section("model catalog")
    out(f"live catalog models    : {len(live) if live else 'unavailable'}")
    out(f"bundled catalog models : {len(bundled) if bundled else 'unavailable'}")
    if live:
        out("live slugs             : " + ", ".join(sorted(live)))
    missing_from_live = sorted(slug for slug in thread_models if live and slug not in live)
    if missing_from_live:
        out("pinned by tasks but ABSENT from live catalog:")
        for slug in missing_from_live:
            out(f"  {slug} (used by {thread_models[slug]} task(s))")
    elif live and thread_models:
        out("every model pinned by an existing task resolves in the live catalog")

    # --------------------------------------------------------------- threads
    section("task inventory")
    unknown_provider: list[str] = []
    if threads:
        provider_counts = Counter(t.get("model_provider") for t in threads)
        out(f"tasks              : {len(threads)}")
        out("providers in use   : " + ", ".join(f"{k or '?'}={v}" for k, v in provider_counts.most_common()))
        foreign = [t for t in threads if (t.get("model_provider") or BUILTIN_PROVIDER) != current_provider]
        out(f"tasks NOT on the current default provider ({current_provider}): {len(foreign)}")
        unknown_provider = sorted(
            {t.get("model_provider") for t in foreign if t.get("model_provider") not in (BUILTIN_PROVIDER, *providers)}
        )
        if unknown_provider:
            out(f"providers with no config block: {', '.join(unknown_provider)}")
        foreign.sort(key=lambda t: t.get("updated_at") or 0, reverse=True)
        for task in foreign[:MAX_LISTED]:
            out(
                f"  {task['id']}  provider={task.get('model_provider')} model={task.get('model')}"
                f"  updated={format_ts(task.get('updated_at'))}  {one_line(task.get('title'))}"
            )
        if len(foreign) > MAX_LISTED:
            out(f"  ... and {len(foreign) - MAX_LISTED} more")
    else:
        out("no task database found (state_*.sqlite with a threads table)")

    # ------------------------------------------------------------------ logs
    section("recent log errors")
    db, log_findings, per_signature, per_task, scanned = scan_logs(codex_home, args.log_limit)
    if db is None:
        out("no logs database found (logs_*.sqlite with an logs table)")
    else:
        out(f"scanned {scanned} newest rows from {db.name}")
        if not log_findings:
            out("no auth/model/provider errors found")
        for name, count in per_signature.most_common():
            newest = max((f["ts"] for f in log_findings if f["signature"] == name), default=None)
            models = sorted({f["model"] for f in log_findings if f["signature"] == name and f["model"]})
            detail = f", models: {', '.join(models)}" if models else ""
            out(f"  {count:5} x {name:16} newest={format_ts(newest)}{detail}")
        if per_task:
            out("  affected tasks:")
            for task, count in per_task.most_common(MAX_LISTED):
                out(f"    {task}  {count} hit(s)")

    # ------------------------------------------------------------- findings
    if locked and not api_key_present:
        findings.append(
            "Auth is pinned to API-key login ("
            + ", ".join(f"{k}={v!r}" for k, v in locked.items())
            + ") but no OpenAI API key is stored. Tasks pinned to the built-in `openai` provider cannot "
            "authenticate and fail with 401."
        )
    if per_signature.get("401/unauthorized"):
        findings.append(
            f"{per_signature['401/unauthorized']} recent 401/authentication errors across "
            f"{len(per_task) or 'unknown'} task(s); those tasks need a usable credential for their pinned provider."
        )
    if missing_from_live:
        findings.append(
            "The model catalog is missing models pinned by existing tasks ("
            + ", ".join(missing_from_live)
            + "); those tasks run with fallback metadata and can lose context-window settings."
        )
    if per_signature.get("unknown model"):
        findings.append(
            f"{per_signature['unknown model']} `Unknown model` warnings: the custom catalog does not define a model "
            "an existing task uses."
        )
    if unknown_provider:
        findings.append(
            "Tasks reference provider name(s) with no matching [model_providers.<name>] block: "
            + ", ".join(unknown_provider)
            + ". Ask the user which endpoint these should use before adding a compatibility entry."
        )

    section("findings")
    if findings:
        for i, item in enumerate(findings, start=1):
            out(f"[{i}] {item}")
        out()
        out("next step: python scripts/repair.py   (dry run; add --apply to write)")
    else:
        out("no provider-switch breakage detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
