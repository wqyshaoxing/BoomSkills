---
name: literature-search
description: Search open academic literature across configured providers and build an evidence-aware literature matrix during research planning.
---

# Literature Search

Use configured open-access providers to locate, compare, and record relevant literature. Preserve source URLs, publication metadata, query terms, and uncertainty; do not invent access or bibliographic facts. Write outputs relative to the active workspace, such as `docs/literature/literature-matrix.md`.

## Privacy and portable paths

- Never store or echo personal names, usernames, email addresses, absolute local paths, private project identifiers, API keys, tokens, signed URLs, or credentials in the skill, its examples, manifests, logs, or deliverables.
- Use active-workspace-relative paths or paths relative to the skill folder. Reduce externally supplied absolute paths to neutral filenames or user-approved relative labels before recording them.
- Keep credentials in environment variables or an explicitly supplied secret file outside the skill and generated outputs.
- Scan outputs for private identifiers before delivery and redact them without altering evidence.

## Dependency detection and MCP fallback

+- Check available tools first: use configured scholarly-search MCP tools when present; otherwise use the approved public providers directly.
- Report which provider/tool will be used and which optional credentials are unavailable. Do not create provider configuration or request secrets unless the user asks for setup.
