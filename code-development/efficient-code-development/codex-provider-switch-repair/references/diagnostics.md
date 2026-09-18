# Codex state layout and error signatures

Read this when a diagnostic finding is ambiguous or when you need to inspect state that
`scripts/diagnose.py` does not print.

## Where the relevant state lives

Paths are relative to `$CODEX_HOME` (default `~/.codex`, on Windows usually
`C:\Users\<user>\.codex`).

| Path | What it holds |
| --- | --- |
| `config.toml` | Active `model`, `model_provider`, `model_catalog_json`, provider blocks under `[model_providers.<name>]`, and any auth-locking keys at root level. |
| `auth.json` | `auth_mode` (`chatgpt` or `apikey`), optional `OPENAI_API_KEY`, and ChatGPT `tokens` (JWT `access_token`/`id_token`, `refresh_token`). The `id_token` is short-lived and normally expired; `access_token` is the one that matters. |
| `models.json` (only when `model_catalog_json` is set) | The catalog the client uses instead of the bundled one. If it lists only the new provider's models, models pinned by older tasks become unknown. |
| `models_cache.json` | Raw catalog last fetched from the service. Useful to compare field names and to confirm the client could reach the service recently. |
| `state_*.sqlite` → `threads` | One row per task: `id`, `model`, `model_provider`, `title`, `cwd`, `archived`, `updated_at`. This is the authoritative record of what each task will use when resumed. |
| `logs_*.sqlite` → `logs` | Diagnostic events: `ts` (epoch seconds), `level`, `target`, `module_path`, `feedback_log_body` (the tracing span text). |
| `sessions/YYYY/MM/DD/rollout-*.jsonl` | Append-only task transcript. The first line is `session_meta` with `payload.model_provider`, `payload.cwd`, `payload.cli_version`; `turn_context` records carry the model actually used per turn. |
| `session_index.jsonl` | Task id → most recent `thread_name`. Handy for naming tasks in reports. |

The `threads` table exists in recent versions; on older ones fall back to the
`session_meta` line of each rollout file.

## Why a provider switch breaks old tasks

`model_provider` in `config.toml` only sets the default for **new** tasks. Resuming an
existing task reuses the `model_provider` and `model` stored with that task, so a task
created while the OpenAI provider was active keeps calling `api.openai.com` even after
the default moves to another provider. Anything the new provider setup changed globally
(login method, model catalog) therefore applies to those old tasks too, which is how a
working configuration can break tasks that were never touched.

## Error signatures

`401 Unauthorized: Missing bearer or basic authentication in header` with
`wss://api.openai.com/v1/responses`

: The request reached OpenAI without credentials. Almost always `forced_login_method = "api"`
  and/or `preferred_auth_method = "apikey"` while `auth.json` holds ChatGPT tokens and no
  `OPENAI_API_KEY`. Comment the keys out and confirm with `codex login status`. A different
  401 wording after that (for example invalid API key) points at an expired or revoked
  credential instead; re-run `codex login`.

`Unknown model <slug> is used. This will use fallback model metadata`

: The model a task pins is absent from the catalog in effect. The task still runs, but with
  default context-window and feature metadata, which can trigger premature compaction or
  unsupported-feature errors on long tasks. Merge the bundled catalog back in.

`unknown provider` / connection failures naming a provider that is not `openai`

: The task pins a provider name with no matching `[model_providers.<name>]` block. Names such
  as `custom` come from older client versions. Add a compatibility block only after asking
  the user which endpoint and auth it should use; a wrong `base_url` silently sends their
  conversation to the wrong service.

Requests failing only in old tasks while new tasks work

: The default provider and its credentials are fine; the old tasks need their own provider's
  credential. Diagnose by comparing `threads.model_provider` against the configured
  providers and the newest 401 entries in `logs`.

## Hand queries

Replace `<TASK_ID>` with an id from the diagnostic output. Close the app first if a database
appears locked; all of these are read-only.

```sql
-- what provider/model every task will use when resumed
select id, model_provider, model, title, updated_at
from threads
order by updated_at desc;

-- recent authentication and catalog problems, newest first
select ts, level, target, feedback_log_body
from logs
where feedback_log_body like '%401 Unauthorized%'
   or feedback_log_body like '%Unknown model%'
order by id desc
limit 50;

-- everything recorded for one task
select ts, level, target, feedback_log_body
from logs
where feedback_log_body like '%<TASK_ID>%'
order by id desc
limit 200;
```

The tracing span text in `feedback_log_body` carries the useful fields inline, for example
`thread_id=...:...model=gpt-5.6-luna codex.turn.reasoning_effort=high}` and, for connection
failures, `provider=OpenAI wire_api=responses api.path="/responses"`. Parse those rather than
the log level alone.

## Repair boundary

Configuration is read when a task starts, so the app must restart before a fix takes effect.
Task transcripts, `state_*.sqlite`, and `session_index.jsonl` are history: read them to
diagnose, leave them unchanged. When a task genuinely needs a different provider or model
from now on, change it through the model picker for that task rather than rewriting stored
history.

A merged catalog contains both providers' model names while `model_provider` still selects a
single endpoint per task. Picking the other provider's model in a new task therefore sends
that slug to the wrong endpoint. Either keep new tasks on their provider's own models, or set
the task's provider explicitly when it genuinely needs a model from the other provider.
