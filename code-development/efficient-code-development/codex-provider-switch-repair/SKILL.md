---
name: codex-provider-switch-repair
description: Diagnose and repair Codex tasks that stop working after a model provider switch, such as 401 Unauthorized from api.openai.com, "Unknown model ... fallback metadata" warnings, or existing tasks pinned to a provider that no longer exists. Use when resuming an older Codex conversation fails after changing model, model_provider, base_url, or the model catalog.
metadata:
  short-description: Repair Codex sessions broken by a provider switch
---

# Codex Provider Switch Repair

Switching `model_provider` in `$CODEX_HOME/config.toml` does not rewrite saved tasks. Each task records its own
`model_provider` and `model` when it is created, so resuming an old task sends requests to the provider that was
active back then. Two configuration changes made for the new provider usually break those tasks:

1. Auth is pinned to a login method the old provider cannot use. `forced_login_method = "api"` plus
   `preferred_auth_method = "apikey"` with no `OPENAI_API_KEY` present makes requests to `api.openai.com` go out
   with no `Authorization` header, so every old task fails with `401 Unauthorized: Missing bearer or basic
   authentication in header`.
2. `model_catalog_json` points at a catalog trimmed to the new provider's models. Old tasks then log
   `Unknown model <slug> is used. This will use fallback model metadata`, lose correct context-window and feature
   metadata, and disappear from the model picker.

Repair the configuration, never the saved history. Do not edit rollout files or the task database to make a task
"match" the new provider.

## Install and invoke

The skill is Markdown plus two Python 3.11+ scripts that use only the standard library, no MCP server or plugin,
so any harness that can run a shell can execute it:

- **Codex**: copy this folder to `$CODEX_HOME/skills/` (usually `~/.codex/skills/`), restart the app, then invoke
  `$codex-provider-switch-repair` or run the scripts directly.
- **Other harnesses** (Claude Code, OpenCode, Hermes Agent, ...): point the agent at this `SKILL.md` and let it run
  `python scripts/diagnose.py` and `python scripts/repair.py` from the skill directory.

`$CODEX_HOME` and the `codex` binary are the subject of the repair rather than harness coupling. The scripts accept
`--codex-home` and `--codex-bin` and otherwise discover both automatically, and they read every path relative to
the Codex home being inspected.

## Diagnose

Run the read-only diagnostic first:

```bash
python scripts/diagnose.py
```

It prints the environment and config summary, `codex login status`, catalog coverage against the models pinned by
existing tasks, recent auth/model/provider errors grouped by task id, and a findings list. Add `--codex-home PATH`
or `--codex-bin PATH` when they are not discoverable automatically.

The script only reads config, logs, and task metadata. Read
[references/diagnostics.md](references/diagnostics.md) when a finding is unclear, when the reported provider name is
not `openai` or a configured provider, or when a log table needs to be queried by hand.

## Repair

```bash
python scripts/repair.py            # dry run: print the plan
python scripts/repair.py --apply    # back up, then write
```

`repair.py` performs only the fixes the diagnosis justifies:

- Comments out root-level `preferred_auth_method` and `forced_login_method` so the built-in `openai` provider can
  use the credentials in `auth.json`, leaving provider-specific bearer tokens untouched.
- Merges the bundled catalog (`codex debug models --bundled`) into the catalog file referenced by
  `model_catalog_json`, so provider-specific models stay selectable and previously known models resolve again.

Because a merged catalog lists both providers' models, picking another provider's model inside a task whose
provider is the new default sends that model name to the new provider's endpoint. Existing tasks are unaffected
since they keep their own provider; mention the trade-off to the user rather than letting the picker surprise them.

Both files are backed up next to the originals before writing. Show the dry-run plan before applying, and apply only
when the user asked for a fix or approved the plan.

Invariants to preserve while repairing:

- Keep the new provider's `[model_providers.<name>]` block, `base_url`, and bearer token exactly as they are.
- Keep the user's current default `model` and `model_provider`; the goal is that old tasks work again, not that the
  default reverts.
- Never print API keys or access tokens in output.
- If a task is pinned to a provider name that is neither `openai` nor defined under `[model_providers]`, report it
  and ask which endpoint it should point at instead of inventing one.

## Verify

Config is read when a task starts, so restart the Codex app after applying changes. Then confirm both paths:

```bash
codex login status

# old task path: the provider and model the broken tasks pin
codex exec -C <scratch-dir> --skip-git-repo-check --sandbox read-only \
  -c model_provider=openai -m <old-model-slug> "Reply with exactly: OK"

# current default path
codex exec -C <scratch-dir> --skip-git-repo-check --sandbox read-only "Reply with exactly: OK"
```

A healthy run prints no `Unknown model` warning and no `401`. Re-run `scripts/diagnose.py` afterwards; the error
count for the affected task ids should not grow when those tasks are resumed.
