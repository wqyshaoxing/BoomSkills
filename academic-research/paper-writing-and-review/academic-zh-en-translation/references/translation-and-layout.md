# Translation fidelity and layout QA

Use this reference during translation review and final file preparation.

## Section-level alignment review

For every translated section, compare source and target for:

- research question, population/object, methods, data, findings, limitations, and conclusion;
- quantities, ranges, units, statistical notation, dates, names, citations, and cross-references;
- negation, hedging, modality, conditionals, causal wording, comparisons, and scope;
- terminology-map compliance and deliberate exceptions.

Polish target-language flow by repairing literal word order, cohesion, repeated subject chains, article use, punctuation, and field-appropriate register. Do not turn a possibility into a conclusion, an association into causation, an example into an exhaustive list, or a local observation into a general rule.

Keep a QA row for each section with source location, target location, terminology exceptions, semantic changes (`none` unless author-approved), and reviewer status. Any unresolvable source ambiguity belongs in `translation-qa.md` as a question for the author.

## Structural and typographic preservation

- Preserve heading levels, numbering, captions, figure/table identifiers, equations, variables, footnotes, citations, bibliography entries, hyperlinks, and cross-reference targets.
- Translate text inside tables and figures only when editable and authorized; do not crop, redraw, or silently replace a source figure. If text is embedded in a raster image, flag it or create an explicitly labeled translated figure asset.
- Keep equations editable in their native form. Do not translate symbols, variable names, or standard operators.
- Retain source typography, column mode, margins, font contract, and paragraph hierarchy unless the user asks for a new target template. If the source and target languages need different line breaks or punctuation, adjust the layout without changing hierarchy.
- For DOCX, render through an office-compatible renderer; for LaTeX, compile and render through a TeX/PDF workflow. Inspect overflow, orphan captions, clipped figures, broken tables, incorrect CJK/Latin font fallback, and broken references.

## Final QA record

`translation-qa.md` must state the source/target files, language direction, field classification, corpus count by language, terminology-map count, rendered files reviewed, unresolved questions, and a fidelity conclusion. A complete handoff has no unlogged ambiguity and no silently changed scholarly claim.
