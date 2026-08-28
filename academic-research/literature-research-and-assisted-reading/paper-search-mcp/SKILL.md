---
name: paper-search
description: Search, download, and read academic papers through the available paper-search service.
---

# Paper Search

Use the available paper-search service to find, download, or inspect scholarly papers. Confirm the requested sources and licensing constraints, preserve stable public identifiers, and report unavailable sources honestly.

## Privacy and portable paths

- Never store or echo personal names, usernames, email addresses, absolute local paths, private project identifiers, API keys, tokens, signed URLs, or credentials in the skill, its examples, manifests, logs, or deliverables.
- Use active-workspace-relative paths or paths relative to the skill folder. Reduce externally supplied absolute paths to neutral filenames or user-approved relative labels before recording them.
- Keep credentials in environment variables or an explicitly supplied secret file outside the skill and generated outputs.
- Scan outputs for private identifiers before delivery and redact them without altering evidence.

## Dependency detection and MCP fallback

+- Check whether the paper-search MCP or CLI is callable before searching. If absent, report the missing dependency and offer its documented installation/configuration steps.
- Configure it only after explicit user approval; verify the connection with a harmless metadata query, then use it. Never place credentials in a skill file.
