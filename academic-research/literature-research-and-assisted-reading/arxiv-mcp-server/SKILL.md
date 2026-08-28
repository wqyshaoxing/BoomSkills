---
name: arxiv-mcp-server
description: Find, compare, read, or monitor arXiv papers, including abstracts, citation graphs, source LaTeX, and section-level details.
---

# arXiv MCP Server

Use the available arXiv tools for bounded, source-aware retrieval. Prefer official arXiv records and source archives, distinguish metadata from full-text evidence, and avoid downloading unrelated papers.

## Privacy and portable paths

- Never store or echo personal names, usernames, email addresses, absolute local paths, private project identifiers, API keys, tokens, signed URLs, or credentials in the skill, its examples, manifests, logs, or deliverables.
- Use active-workspace-relative paths or paths relative to the skill folder. Reduce externally supplied absolute paths to neutral filenames or user-approved relative labels before recording them.
- Keep credentials in environment variables or an explicitly supplied secret file outside the skill and generated outputs.
- Scan outputs for private identifiers before delivery and redact them without altering evidence.

## Dependency detection and MCP fallback

+- Check for the arXiv MCP tools before use. If they are unavailable, state that fact and use the official arXiv public interface only when it can meet the request.
- Do not add or alter MCP configuration automatically. With explicit approval, provide or apply a portable configuration that uses environment variables and relative paths only, then run a harmless connectivity check.
