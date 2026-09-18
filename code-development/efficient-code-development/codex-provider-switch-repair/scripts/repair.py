#!/usr/bin/env python3
"""Repair Codex configuration so tasks pinned to a previous model provider work again.

Two fixes, each applied only when the diagnosis justifies it:

  1. Comment out root-level auth-locking keys (`preferred_auth_method`,
     `forced_login_method`) so the built-in `openai` provider can use the credentials
     stored in auth.json. Provider-specific bearer tokens are left untouched.
  2. Merge the bundled model catalog into the catalog file referenced by
     `model_catalog_json`, so provider-specific models stay selectable and models that
     existing tasks pin resolve again.

Dry run by default; pass --apply to write. Both files are backed up first.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import diagnose as dg


def comment_out(text: str, keys: set[str]) -> tuple[str, list[str]]:
    """Comment out root-level `key = value` lines, returning the new text and the keys changed."""
    lines = text.splitlines()
    changed: list[str] = []
    in_section = False
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            in_section = True
            continue
        if in_section:
            continue
        match = re.match(r"([A-Za-z0-9_\-\.]+)\s*=", stripped)
        if match and match.group(1) in keys:
            lines[idx] = (
                f"# {raw.rstrip()}  # disabled by codex-provider-switch-repair: "
                "it forced a login method with no usable credential, breaking tasks pinned to another provider"
            )
            changed.append(match.group(1))
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix, changed


def merge_catalog(
    codex_bin: str | None, codex_home: Path | None, custom_path: Path
) -> tuple[dict | None, list[str], list[str]]:
    """Return (merged payload, added slugs, kept custom slugs)."""
    if not codex_bin:
        return None, [], []
    bundled = dg.catalog_slugs(codex_bin, codex_home, bundled=True)
    if not bundled:
        return None, [], []
    custom_models = json.loads(custom_path.read_text(encoding="utf-8"))["models"]
    custom_slugs = {entry["slug"] for entry in custom_models}
    merged = dict(bundled)
    for entry in custom_models:
        merged[entry["slug"]] = entry
    added = [slug for slug in merged if slug not in custom_slugs]
    return {"models": list(merged.values())}, added, sorted(custom_slugs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", help="path to CODEX_HOME (default: $CODEX_HOME or ~/.codex)")
    parser.add_argument("--codex-bin", help="path to the codex executable")
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    parser.add_argument("--no-catalog-merge", action="store_true", help="skip the catalog merge fix")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    codex_home = dg.find_codex_home(args.codex_home)
    config_path = codex_home / "config.toml"
    codex_bin = dg.find_codex_bin(args.codex_bin)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    if not config_path.exists():
        print(f"error: {config_path} not found")
        return 2

    config_text = config_path.read_text(encoding="utf-8", errors="replace")
    config = dg.load_toml(config_path)
    root_keys = dg.root_level_keys(config_text)
    current_provider = config.get("model_provider", dg.BUILTIN_PROVIDER)
    catalog_override = config.get("model_catalog_json")

    plan: list[str] = []
    notes: list[str] = []

    # ---- fix 1: auth lock
    lock_keys = {key for key in dg.AUTH_LOCK_KEYS if key in root_keys}
    new_config_text = config_text
    changed_keys: list[str] = []
    if lock_keys:
        new_config_text, changed_keys = comment_out(config_text, lock_keys)
        plan.append(
            "config.toml: comment out "
            + ", ".join(sorted(changed_keys))
            + f" so the `openai` provider can use auth.json credentials"
        )
        if not (codex_home / "auth.json").exists():
            notes.append("auth.json is missing: run `codex login` after applying, or old tasks will still fail.")
        else:
            auth = json.loads((codex_home / "auth.json").read_text(encoding="utf-8", errors="replace"))
            if not auth.get("OPENAI_API_KEY") and not (auth.get("tokens") or {}).get("access_token"):
                notes.append("auth.json has neither an API key nor access tokens: run `codex login` after applying.")

    # ---- fix 2: catalog merge
    merged_payload = None
    added_slugs: list[str] = []
    catalog_path = Path(catalog_override).expanduser() if catalog_override else None
    if catalog_path and not args.no_catalog_merge:
        if not catalog_path.exists():
            notes.append(f"model_catalog_json points at {catalog_path}, which does not exist.")
        else:
            threads = dg.load_threads(codex_home)
            pinned = Counter(t.get("model") for t in threads if t.get("model"))
            live = dg.catalog_slugs(codex_bin, codex_home, bundled=False) or {}
            missing = sorted(slug for slug in pinned if live and slug not in live)
            merged_payload, added_slugs, _kept = merge_catalog(codex_bin, codex_home, catalog_path)
            if merged_payload and added_slugs:
                reason = (
                    f"existing tasks pin models this catalog omits ({', '.join(missing)})"
                    if missing
                    else "every bundled model should stay resolvable alongside the provider-specific entries"
                )
                plan.append(
                    f"{catalog_path.name}: merge the bundled catalog so {reason}; "
                    f"{len(added_slugs)} model(s) added "
                    f"({', '.join(added_slugs[:5])}{', ...' if len(added_slugs) > 5 else ''})"
                )
            elif merged_payload:
                notes.append(f"{catalog_path.name} already contains every bundled model.")

    # ---- report
    print("=== repair plan ===")
    print(f"codex home : {codex_home}")
    print(f"codex bin  : {codex_bin or 'NOT FOUND (pass --codex-bin)'}")
    print(f"default    : model={config.get('model')} provider={current_provider} (left unchanged)")
    print()
    if plan:
        for i, item in enumerate(plan, start=1):
            print(f"[{i}] {item}")
    else:
        print("nothing to change")
    for note in notes:
        print(f"note: {note}")

    if not plan:
        return 0
    if not args.apply:
        print()
        print("dry run: nothing written. Re-run with --apply to write these changes.")
        return 0

    # ---- apply
    print()
    backups: list[Path] = []
    if changed_keys:
        backup = config_path.with_name(f"{config_path.name}.bak-{stamp}")
        shutil.copy2(config_path, backup)
        backups.append(backup)
        config_path.write_text(new_config_text, encoding="utf-8")
    if merged_payload and catalog_path:
        backup = catalog_path.with_name(f"{catalog_path.name}.bak-{stamp}")
        shutil.copy2(catalog_path, backup)
        backups.append(backup)
        catalog_path.write_text(json.dumps(merged_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    for backup in backups:
        print(f"backup: {backup}")
    print("applied.")
    print()
    print("--- verify ---")
    print("restart the Codex app so the new config is read, then:")
    print("  codex login status")
    threads = dg.load_threads(codex_home)
    foreign = [t for t in threads if (t.get("model_provider") or dg.BUILTIN_PROVIDER) != current_provider]
    foreign.sort(key=lambda t: t.get("updated_at") or 0, reverse=True)
    for task in foreign[:3]:
        print(
            f"  codex exec -C <scratch> --skip-git-repo-check --sandbox read-only "
            f"-c model_provider={task.get('model_provider')} -m {task.get('model')} \"Reply with exactly: OK\""
        )
    print('  codex exec -C <scratch> --skip-git-repo-check --sandbox read-only "Reply with exactly: OK"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
