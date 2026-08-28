---
name: academic-zh-en-translation
description: "Translate academic manuscripts between Chinese and English with field-specific bilingual evidence, terminology mapping, faithful scholarly editing, and source-format-preserving layout QA. Use for manuscript translation or bilingual revision, not informal or literary translation."
---

# Academic Chinese ↔ English Translation

Produce a publication-ready Chinese or English counterpart of an academic manuscript without changing its scholarly meaning. Translation quality is evidence-led: identify the research field, build a bilingual terminology basis, translate faithfully, then restore and verify the source document's layout.

## Start by setting the translation contract

Confirm or infer the source language, target language, intended audience, target venue/style guide, and authoritative source file. Identify whether the input is LaTeX, DOCX, Markdown, or PDF. Treat PDF as a review source, not the preferred editable source. Ask for an editable source if only a PDF is available and substantive revision is expected.

Create a translation workspace before making changes. Use `scripts/create_translation_workspace.py` when its standard ledger is useful. Keep the original unchanged and place the translated manuscript, corpus record, terminology map, QA record, and render output in separate named locations.

## Required workflow

1. **Classify field and direction.** Determine the discipline, subfield, research problem, methods, and genre (for example, empirical article, review, clinical report, or theoretical paper). State the evidence and confidence. If classification is uncertain enough to affect terminology, ask the author rather than guessing.
2. **Build a bilingual evidence corpus.** Collect and record at least ten Chinese-language and ten English-language scholarly papers or reviews relevant to the same field and direction. Prefer peer-reviewed or authoritative scholarly sources, recent work when terminology is changing, and papers with accessible abstracts/full text. Record bibliographic metadata, stable URL/DOI, language, relevance, and the terminology evidence used; do not claim the twenty works are literal translations of each other. Do not bypass paywalls or bulk-copy copyrighted full text. Read [corpus and terminology guidance](references/corpus-and-terminology.md).
3. **Create the terminology map.** Before translating technical prose, map important terms, abbreviations, named methods, variables, units, and recurring collocations. Give every preferred mapping an evidence source, context, and confidence. Keep alternatives and forbidden/ambiguous renderings where they matter. Do not force a one-to-one mapping when the target language needs a contextual phrase.
4. **Translate and polish without semantic drift.** Preserve claims, evidence strength, uncertainty, methods, numerical values, equations, variables, units, citations, figure/table labels, and reference keys. Polish logic, cohesion, register, and natural academic expression only when it does not add, remove, or strengthen meaning. Flag source ambiguity instead of silently resolving it.
5. **Restore and validate layout.** Preserve the source file type and structural mapping wherever practical. Keep headings, captions, tables, figures, equations, citations, cross-references, and bibliography order functional. Render the translated output and inspect every changed page plus all pages containing figures, tables, equations, or references. Read [translation and layout QA](references/translation-and-layout.md).

## Tool routing

- For bilingual scholarly discovery, use available research tools such as `paper-search`, `literature-search`, or `arxiv-mcp-server`; use primary publisher, DOI, or repository records to verify metadata.
- For PDF inspection and rendering, use `pdf`; for editable Word source and output, use `documents`; for LaTeX/Word pairs, use `latex-word-sync` after the translation map is complete.
- Use browser search only to fill a documented evidence gap. Never treat search snippets as terminology evidence.

## Non-negotiable fidelity rules

- Never invent references, translations, data, results, author intent, or terminology evidence.
- Do not translate proper nouns, model names, symbols, variables, URLs, DOIs, file names, code, or citation keys unless the author or field convention requires it.
- Preserve hedging, modality, negation, causal strength, scope, tense where meaningful, and statistical interpretation. A fluent but stronger or broader claim is an error.
- Keep an alignment trail for each changed section. For potentially ambiguous terminology, include the source sentence, target sentence, preferred term, evidence, and reviewer decision.
- If the user supplies a glossary, venue style guide, or existing bilingual manuscript, it takes precedence over corpus frequency unless it creates a factual error; record the conflict.

## Handoff

Deliver the translated editable manuscript, a rendered review copy, `bilingual-corpus.csv`, `terminology-map.csv`, and `translation-qa.md` (or equivalent clearly named records). Encode CSV files as UTF-8 with BOM for Windows spreadsheet compatibility; when the author is likely to inspect or edit Chinese tables in Excel, also provide a formatted `.xlsx` workbook. Summarize unresolved ambiguities separately; do not hide them in polished prose.
