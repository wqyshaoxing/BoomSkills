# Word layout contract

Inspect the target DOCX before formatting it. Record the paragraph styles, direct formatting overrides, page sections, margins, font families and sizes, caption alignment, table border pattern, equation construction, and citation-field mechanism in the manifest.

## Column-mode contract

Before creating a new Word document, ask the author to choose `single-column` or `two-column`; record the choice in the manifest. Do not guess from a LaTeX PDF. When an existing Word template is authoritative, ask whether to retain its geometry.

- `single-column`: use one real Word text column. Figures and normal tables use the available text width; use an explicit landscape section only for a truly wide object.
- `two-column`: use real `w:cols` section properties, not tables, text boxes, tab stops, or manual line breaks. It must retain the single-column version's font family, font colors, type scale, margins, heading hierarchy, table treatment, caption style, and reference system; only column geometry, column-constrained image sizing, and necessary full-width transitions may differ. Preserve a full-width title/author block as a distinct section when needed. To place a full-width figure or table, enter an explicit continuous one-column section, keep the caption with its object, then resume the two-column body in another explicit section.

Record every section transition and its column count. A Word-to-LaTeX update must map those transitions to the target's two-column or full-width mechanism rather than flattening the document into one mode.

## Required object handling

- Body text: preserve the target's font, size, line spacing, indentation, and justification. Do not apply a manuscript-specific font globally without checking the template. When the author explicitly selects Times New Roman, apply it consistently to title, author/date metadata, headings, prose, captions, table text, and references; remove residual Pandoc default fonts.
- Typography hierarchy: derive the type scale from the target template, then inspect the first rendered page. The title must be clearly dominant; author/date metadata must be subordinate; first- and second-level headings must remain visually distinct from one another and from body text. Do not let a converted subtitle inherit the full title size.
- Headings: use real Word styles, not manually bolded body paragraphs. Preserve outline levels and the target's numbering scheme. Clear accidental list/bullet properties from headings that are not lists. If black margin squares appear in Word’s editing view, remove unrequested list and pagination properties from both styles and direct formatting.
- Tables: retain merged cells, alignment, repeat-header behavior, no-row-split rules, and source-authorized emphasis. Apply a three-line table only if it is the target's convention.
- Figures and captions: center the figure paragraph and its caption, retain aspect ratio, anchoring mode, and alt text. Size figures to remain legible while leaving consistent text margins and caption spacing; do not mechanically fill the available width or page height. Captions must remain associated with their object during pagination.
- Equations: use editable OMML. Preserve source symbol case and semantic font distinctions, including bold vectors/matrices and upright operators. For numbered display equations, use a center/right tab or the template's equation-table layout so the formula remains centered independently of the number. For multi-line equations, align relation signs without left-shifting the display block. See [equation fidelity](equation-format.md).
- References: retain hyperlinks and genuine Word/citation-manager fields. Do not replace fields by cached display text.

## Visual QA

Render the complete DOCX after every meaningful formatting pass. Inspect first page, every changed page, all figure/table/equation pages, and section/reference transitions. Reject clipped figures, blank pages caused by keep settings, inconsistent heading sizes, gridlined tables when the contract calls for three lines, left-aligned equations, missing fields, stray bullets or black margin squares, fake two-column layouts, and unintended one-column/two-column transitions.
