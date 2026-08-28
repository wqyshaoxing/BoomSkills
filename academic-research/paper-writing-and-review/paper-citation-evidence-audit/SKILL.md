---
name: paper-citation-evidence-audit
description: Audit citation-backed claims after drafting a paper's Introduction or Related Work and create per-reference evidence directories with exact manuscript locations, source passages, translations, and highlighted screenshots. Use for claim-evidence verification and submission-risk review, not ordinary citation formatting or literature search alone.
---

# Paper Citation Evidence Audit

Create a traceable evidence package after literature commentary has been drafted. Treat the manuscript as read-only unless the user separately authorizes wording or citation changes.

## Required outcome

For every cited source, create an isolated directory:

```text
reference_evidence_audit/
|-- reference_claim_evidence_audit.md
|-- evidence_inventory.json
`-- by_reference/
    `-- <BibTeX-key>/
        |-- evidence_mapping.md
        `-- screenshots/
```

Each claim-reference pair must identify the manuscript location, exact claim, source location, verbatim source passage, translation, support level, risk note, and a readable screenshot with the supporting passage visibly highlighted. Create a directory for uncited bibliography entries too, but explicitly state that no mapping exists instead of inventing evidence.

## Evidence boundaries

- Split a sentence with multiple citations into separate claim-reference pairs. Do not assume that every cited paper supports the complete sentence.
- Prefer the primary paper PDF or official source. Label evidence from a review, abstract, citation context, or other intermediary as `secondary`; never report a fabricated primary-source section or paragraph.
- Use `full`, `partial`, `secondary`, or `unresolved` support. Preserve qualifications, datasets, experimental settings, and author-attributed limitations.
- A screenshot proves only what is visible. Capture enough surrounding text to identify the section and meaning; highlight the exact passage without obscuring it.
- Keep Zotero `storage` read-only. Copy evidence out to the audit directory; never add, rename, edit, or delete files in `storage`.
- Do not silently rewrite unsupported manuscript claims. Report the discrepancy and ask for or use separate authorization before editing the paper.

## Privacy and de-identification

- Treat author names, affiliations, email addresses, student or project identifiers, reviewer information, API keys, and local account names as sensitive unless the user explicitly authorizes disclosure.
- Do not copy a manuscript, reference PDF, Zotero metadata, or local absolute path into the evidence package. Use a neutral display title, stable public URL, repository-relative path, or file name only.
- Before delivery, scan generated Markdown, JSON, screenshot captions, and filenames for local usernames, absolute paths, contact details, and private identifiers. Replace them with neutral labels such as `manuscript.tex`, `source.pdf`, or `Reference-01` while keeping the audit locator reproducible.
- Preserve the source evidence and the claim wording; de-identification may remove provenance details that identify a person or local machine, but must not change a support classification or invent missing evidence.

## Workflow

1. Inventory bibliography entries and all in-text citation occurrences. Record uncited entries.
2. Extract externally verifiable literature claims from the drafted sections. Assign stable IDs such as `C001`; reuse the claim ID when one claim cites multiple papers.
3. Locate each cited paper's primary PDF. When local project rules assign paper analysis to another worker, give each paper a private staging directory and review that worker's result before packaging.
4. For every claim-reference pair, verify the quote in the original source and record PDF page, printed page when different, section/subsection, and paragraph or figure/table identifier.
5. Produce a highlighted source screenshot for each evidence passage. Use multiple screenshots when one mapping needs distinct passages.
6. Read [references/evidence_manifest_schema.md](references/evidence_manifest_schema.md), create `evidence_manifest.json`, then run:

```bash
python scripts/build_evidence_package.py evidence_manifest.json --output reference_evidence_audit
python scripts/validate_evidence_package.py reference_evidence_audit
```

7. Review every `partial`, `secondary`, and `unresolved` item manually. Report counts and actual output paths; do not describe the package as complete while unresolved items remain.

## Manuscript locations

- LaTeX: record `relative/path/file.tex:<line>` and verify the quoted sentence still occurs near that line.
- Word: record the document name, heading path, paragraph ordinal, and a distinctive text anchor. Rendered page numbers may be added but are not stable enough to be the sole locator.
- PDF-only manuscript: record PDF page, section, paragraph, and a distinctive text anchor.

## Quality gate

Before delivery, require all of the following:

- bibliography count equals the number of per-reference directories;
- every cited source has at least one mapping, and every uncited source has an explicit no-mapping note;
- every mapping has a manuscript locator and support classification;
- all non-`unresolved` mappings contain at least one located quote, translation, and highlighted screenshot;
- every Markdown screenshot link resolves, no unexplained screenshot remains, and copied files match the inventory hashes;
- totals in the report, inventory, and directories agree.

The package builder refuses to write into a non-empty output directory. Preserve previous audits and use a new or deliberately cleared destination for each run.
