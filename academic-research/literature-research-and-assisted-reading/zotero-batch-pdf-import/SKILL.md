---
name: zotero-batch-pdf-import
description: Import selected local PDFs into Zotero in timestamped, traceable batches with metadata recognition.
---

# Zotero Batch PDF Import

Use `scripts/batch_import.py` with a workspace-relative source directory. Begin with `--dry-run`; require explicit confirmation before `--yes` writes to Zotero. Create or reuse the timestamp-named collection, retain the batch tag, and preserve the source manifest for traceability.

## Privacy and portable paths

- Never store or echo personal names, usernames, email addresses, absolute local paths, private project identifiers, API keys, tokens, signed URLs, or credentials in the skill, its examples, manifests, logs, or deliverables.
- Use active-workspace-relative paths or paths relative to the skill folder. Reduce externally supplied absolute paths to neutral filenames or user-approved relative labels before recording them.
- Keep credentials in environment variables or an explicitly supplied secret file outside the skill and generated outputs.
- Scan outputs for private identifiers before delivery and redact them without altering evidence.

## Dependency detection and MCP fallback

+- Check that Zotero Desktop and its local Connector endpoint are reachable before planning an import. This workflow does not require a remote MCP server.
- If the Connector is unavailable, report the prerequisite and provide setup guidance; never change Zotero configuration, create collections, or import files until the user explicitly authorizes the write.
