---
name: agent-cluster-management
description: Coordinate the local Zotero literature workflow across import, MinerU extraction, and isolated paper analysis workers.
---

# Agent Cluster Management

Route each paper through a separate staging area and execution owner. Track download, import, extraction, analysis, review, and failure state without mixing evidence between papers. Keep Zotero storage read-only except for explicitly authorized imports.

## Privacy and portable paths

- Never store or echo personal names, usernames, email addresses, absolute local paths, private project identifiers, API keys, tokens, signed URLs, or credentials in the skill, its examples, manifests, logs, or deliverables.
- Use active-workspace-relative paths or paths relative to the skill folder. Reduce externally supplied absolute paths to neutral filenames or user-approved relative labels before recording them.
- Keep credentials in environment variables or an explicitly supplied secret file outside the skill and generated outputs.
- Scan outputs for private identifiers before delivery and redact them without altering evidence.

## Dependency detection and MCP fallback

+- At workflow start, check the available Zotero, MinerU, paper-search/arXiv, and isolated-worker capabilities. Return a compact dependency matrix with route, status, and fallback.
- Do not configure MCP servers, start workers, or write credentials automatically. With explicit approval, configure one dependency at a time using portable settings, validate it with a harmless probe, and preserve a fallback route.
