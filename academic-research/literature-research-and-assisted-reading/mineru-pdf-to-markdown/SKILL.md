---
name: mineru-pdf-to-markdown
description: Convert selected local PDF papers or Zotero attachments through MinerU and save full.md with extracted resources beside each PDF.
---

# MinerU PDF to Markdown

Convert only user-selected PDFs. Prefer a configured MinerU MCP service; otherwise invoke `scripts/mineru_convert.py` from this skill folder with workspace-relative paths. Save results beside the source as `<pdf-stem>_mineru/full.md`; do not overwrite the PDF or an existing complete result. MinerU uploads PDFs to an external service, so confirm scope before upload.

## Privacy and portable paths

- Never store or echo personal names, usernames, email addresses, absolute local paths, private project identifiers, API keys, tokens, signed URLs, or credentials in the skill, its examples, manifests, logs, or deliverables.
- Use active-workspace-relative paths or paths relative to the skill folder. Reduce externally supplied absolute paths to neutral filenames or user-approved relative labels before recording them.
- Keep credentials in environment variables or an explicitly supplied secret file outside the skill and generated outputs.
- Scan outputs for private identifiers before delivery and redact them without altering evidence.

## Dependency detection and MCP fallback

+- Check for a callable MinerU MCP service before using the bundled script. Report the selected route and whether it uploads PDFs externally.
- If neither route is available, explain the missing dependency and offer portable setup steps. Apply any MCP configuration only after explicit approval, use an environment-variable token, and verify with a non-sensitive connectivity check before uploading a PDF.
