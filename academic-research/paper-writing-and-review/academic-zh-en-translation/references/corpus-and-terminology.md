# Bilingual corpus and terminology evidence

Use this reference after classifying the manuscript field and before translating technical content.

## Corpus inclusion standard

Record at least 20 works: 10 Chinese-language and 10 English-language papers or reviews. A work may be used only if its relevance is explainable from its abstract, full text, venue record, or authoritative metadata. Prefer sources that directly match the manuscript's object, method, or disciplinary convention. Mix foundational and recent sources when terminology has changed over time.

For every record, capture:

| Field | Required content |
| --- | --- |
| `id` | Stable local identifier |
| `language` | `zh` or `en` |
| `type` | Article, review, standard, guideline, or other scholarly source |
| `citation` | Authors, year, title, venue |
| `doi_or_url` | DOI or stable authoritative URL |
| `field_relevance` | Why it supports this manuscript's field/direction |
| `terminology_evidence` | Terms/collocations actually observed or verified |
| `access_note` | Abstract-only, open full text, library access, etc. |

Do not fabricate a Chinese counterpart merely because an English paper exists, or vice versa. If the requested field cannot yield ten credible items in one language, document the gap, explain the search boundary, and ask whether to widen the date range, source type, or adjacent subfield.

## Terminology map

Build `terminology-map.csv` with one row per meaningful mapping. Required columns:

| Column | Purpose |
| --- | --- |
| `source_term` | Exact source-language form, including capitalization |
| `target_term` | Preferred target-language rendering |
| `term_type` | Concept, method, measure, abbreviation, variable, collocation, or proper name |
| `context` | Short source context or section label |
| `evidence_ids` | Corpus IDs supporting the choice |
| `alternatives` | Permissible alternatives and when they apply |
| `avoid` | Misleading, obsolete, or ambiguous rendering if known |
| `confidence` | High, medium, or low |
| `decision_note` | Rationale, including author override or unresolved ambiguity |

Use source usage, not dictionary frequency alone. For terms with multiple accepted translations, choose by field, grammatical role, surrounding method, and target audience. Keep acronym handling consistent: define an acronym once in the target language, preserve a standardized acronym when one exists, and never create a new acronym merely for brevity.

For Windows compatibility, save CSV evidence tables as UTF-8 with BOM. When Chinese rows will be reviewed in Excel, provide an `.xlsx` version with separate corpus and terminology sheets, wrapped text, frozen headers, source URLs, and readable column widths.

## Evidence limits

The corpus supports translation decisions; it does not authorize importing new facts, citations, arguments, or literature-review claims into the manuscript. Quote only the short evidence needed to justify terminology, retain links/metadata rather than copying full copyrighted papers, and keep user source content private.
