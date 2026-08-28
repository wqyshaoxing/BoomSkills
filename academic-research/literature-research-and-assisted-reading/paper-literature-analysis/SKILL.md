---
name: paper-literature-analysis
description: Analyze Zotero papers with MinerU extraction, source-repository inspection, isolated worker staging, and evidence-reviewed analysis artifacts.
---

# Paper Literature Analysis

Analyze each paper in an isolated staging directory. Preserve the source PDF and MinerU `full.md`; write a reviewed `analysis.md` beside the paper only after claims are traced to extracted text, figures, and source observations. Use the bundled references and scripts when their relevant workflow applies.

## Privacy and portable paths

- Never store or echo personal names, usernames, email addresses, absolute local paths, private project identifiers, API keys, tokens, signed URLs, or credentials in the skill, its examples, manifests, logs, or deliverables.
- Use active-workspace-relative paths or paths relative to the skill folder. Reduce externally supplied absolute paths to neutral filenames or user-approved relative labels before recording them.
- Keep credentials in environment variables or an explicitly supplied secret file outside the skill and generated outputs.
- Scan outputs for private identifiers before delivery and redact them without altering evidence.

## Dependency detection and MCP fallback

+- Before dispatch, check Zotero availability, MinerU extraction capability, and the configured isolated analysis worker. Report each as available, missing, or replaceable.
- Do not configure MCP servers or start background workers without explicit approval. If a required dependency is missing, stop before analysis and offer setup or an approved fallback.
