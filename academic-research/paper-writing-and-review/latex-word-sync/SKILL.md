---
name: latex-word-sync
description: "Synchronize an academic manuscript between LaTeX and Word by building a reusable structural mapping for sections, tables, figures, equations, citations, and Word layout. Use when converting or updating an existing .tex/.docx pair; not for a one-off plain-text export."
---

# LaTeX-Word Sync

Maintain one manuscript in two editable representations without treating either as disposable output. The source of truth is the file identified for the current synchronization. Preserve all unaffected mapped content and never silently rewrite the other representation from scratch. This skill is agent- and platform-neutral: resolve the skill directory and tool executables at runtime; do not embed machine-specific absolute paths.

## Privacy and publication safety

Do not place personal, project-specific, or confidential information in this skill or its examples. This includes names, usernames, email addresses, local paths, repository URLs, manuscript titles, unpublished text, data values, screenshots, document metadata, and file hashes from a real project. If an example is needed, create an abstract synthetic manuscript with neutral placeholder names and invented content. Apply the same rule to every new or updated skill intended for sharing.

## Start with a mapping

Before a first conversion or any bidirectional update, generate a compact manifest beside the working output, never inside the submission/archive directory. Supply both paths when both representations exist; for a Word-first conversion, run it with only `--docx`, create the LaTeX draft, then rerun it with both paths:

```text
python <skill-root>/scripts/build_sync_manifest.py --tex-root <latex-root> --docx <word.docx> --word-layout <single-column|two-column> --output <work>/sync-manifest.json
```

The manifest records hashes and stable anchors for LaTeX inputs, tables, graphics, bibliography entries, Word headings, paragraphs, tables, drawings, equations, citation fields, and layout. Reuse it for subsequent work. When either side has changed, regenerate it with `--previous <work>/sync-manifest.json`; act only on the reported changed anchors unless the user asks for a full conversion.

Read [mapping](references/mapping.md) before deciding what to synchronize. Read [Word layout](references/word-layout.md) before creating or formatting a DOCX, [equation fidelity](references/equation-format.md) whenever the manuscript contains mathematics, and [dependencies](references/dependencies.md) before choosing tools.

## Choose Word geometry explicitly

Before creating a new Word counterpart, ask the author one consequential question: **should the Word manuscript use a single-column or two-column body?** Do not infer a choice from the LaTeX PDF, because the Word version may serve a different editing or submission workflow. Record the answer as `single-column` or `two-column` in the synchronization manifest. If the user supplies a Word template, ask whether its existing geometry should be retained instead.

- **Single-column:** use one real Word text column. Keep formulas centered with numbers independently right-aligned, use the full text width for ordinary figures and tables, and reserve landscape sections only for genuinely wide material.
- **Two-column:** create real Word page columns with section properties (`w:cols`); never simulate columns with a borderless table, text boxes, tabs, or manual line breaks. Keep the same font family, font colors, type scale, margins, heading hierarchy, table treatment, captions, and reference system as the single-column version. Only the body column geometry, column-constrained image sizing, and necessary continuous one-column transitions for full-width figures or wide tables may differ. Keep titles and author blocks in their own full-width section when required, and preserve every section-transition anchor in the manifest.

For Word-to-LaTeX synchronization, keep the selected mode as a layout decision: map a two-column Word body to the target LaTeX two-column mechanism and map any full-width Word section to the corresponding wide figure/table or one-column transition. Do not change a maintained document from one mode to the other without an explicit author request.

## Conversion modes

### LaTeX to Word

Use Pandoc only to create an initial semantic draft when no maintained Word counterpart exists. Supply a reference DOCX whose styles match the target manuscript. Do not regard Pandoc output as submission-ready: restore mapped table emphasis, editable display equations, captions, references, and figure placement from the manifest and source.

When a maintained DOCX exists, update the mapped section/table/figure/equation targets in that file instead of regenerating the entire document. Preserve existing Word styles, fields, bookmarks, section breaks, and embedded-media relationships unless the relevant anchor changed.

### Word to LaTeX

Use the manifest to locate the corresponding LaTeX section or table file, and update only that target. Export equation content from editable OMML; do not transcribe equations from rendered text. Keep figures as source assets and preserve the existing `\includegraphics` path where possible. Preserve citation keys and bibliography order unless the user explicitly changes citation content.

Pandoc may produce a draft when no mapping exists, but then split it according to the source project structure and rebuild the mapping before considering it synchronized.

## Word fidelity contract

Derive concrete point sizes, margins, heading hierarchy, caption styles, and reference behavior from the maintained Word file or a user-provided template; do not hard-code values from another manuscript. Enforce these invariants:

- Prose fonts, heading sizes, and paragraph spacing must follow the target style contract. When the author explicitly selects Times New Roman, apply it consistently to title, author metadata, headings, prose, captions, tables, and references. Preserve native editable OMML math typography unless a tested, schema-valid OMML font override is available; never damage equation structure merely to force a prose font. Do not leave Pandoc default styles in any of those editable Word components.
- Preserve mathematical semantics, not only visible characters: retain exact symbol case; distinguish scalars, vectors, and matrices; preserve bold, italic, upright operators, subscripts, superscripts, transposes, and blackboard-bold sets in editable OMML.
- Use real Word heading styles for headings; subordinate headings must not visually exceed their parent heading. Remove accidental bullets, black markers, and list formatting from ordinary headings and paragraphs.
- Center figures and their captions in the available text geometry. Preserve image aspect ratio, apply a layout-specific maximum width and height so images neither touch the text edges nor dominate a page, and check for clipping.
- Recreate tables as the template requires. For a three-line-table template, use only top, header, and bottom rules; retain only source-authorized bold values.
- Keep display equations editable as OMML, centered with the equation number aligned independently at the right when numbers are present. Do not substitute screenshots or plain-text equations.
- Center the formula itself in the current text geometry; place a number independently at the right only when it exists. For multi-line equations, align internal relation signs without left-shifting the whole display.
- Preserve the manuscript's existing reference system. If it uses native Word fields/bookmarks, maintain valid targets; do not turn citations into detached bracket text. If it uses a citation manager field system, preserve its fields rather than flattening them.

## Validate before handoff

Use the manifest as the comparison contract. Check changed anchors, all table numeric sequences, equation counts/numbers, bibliography count/order, citation targets, and figure count/captions. For Word, also verify the selected column mode in every affected section: exactly one text column for `single-column`, or genuine two-column section properties and intentional full-width transitions for `two-column`. Render the DOCX to PDF/pages using an available office renderer, then compile and render the LaTeX with an available TeX engine and PDF renderer. Inspect every changed page and all pages containing tables, figures, equations, or reference transitions.

Do not overwrite the identified source of truth. Write a new output until the user authorizes replacement. Keep compiler files, render images, Pandoc scratch files, and manifests outside a clean archive or submission package.

For every changed equation, compare the LaTeX and OMML symbol-by-symbol for case, boldness, scripts, operators, and alignment. When Word formatting marks are visible, reject unexplained black margin squares; inspect and remove unrequested list or pagination properties from both direct paragraph formatting and styles.
