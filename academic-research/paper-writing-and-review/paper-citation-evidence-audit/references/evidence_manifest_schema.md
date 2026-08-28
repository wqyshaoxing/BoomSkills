# Evidence manifest contract

Use UTF-8 JSON. Paths may be absolute or relative to the manifest file. Relative screenshot paths are resolved from the manifest directory.

## Minimal structure

```json
{
  "manuscript": {
    "title": "Paper title",
    "path": "paper/manuscript/main.tex"
  },
  "references": [
    {
      "key": "Author2025Method",
      "title": "Method title",
      "source": {
        "kind": "primary",
        "path": "papers/Author2025Method.pdf",
        "note": "Original conference PDF"
      },
      "claims": [
        {
          "id": "C001",
          "manuscript_location": "01_introduction.tex:42",
          "claim_text": "Author et al. introduce ...",
          "claim_translation": "作者等提出……",
          "support_level": "full",
          "risk": "No material qualification omitted.",
          "evidence": [
            {
              "location": "PDF p. 3, Sec. 2.1, paragraph 2",
              "quote": "Exact source passage.",
              "translation": "原文片段的准确翻译。",
              "screenshot": "screenshots/C001_source.png",
              "note": "Passage highlighted in yellow."
            }
          ]
        }
      ]
    }
  ]
}
```

## Field rules

### Top level

- `manuscript.title`: optional display title.
- `manuscript.path`: optional neutral manuscript label used for audit provenance. Use a repository-relative path or filename; never put a local absolute path, account name, contact detail, or private project identifier here.
- `references`: one entry for every bibliography item, including uncited items.

### Reference

- `key`: required unique BibTeX key; also used as the directory name. Allowed characters are letters, digits, dot, underscore, and hyphen.
- `title`: required source title.
- `source.kind`: `primary`, `secondary`, or `unavailable`.
- `source.path`: optional stable public URL, repository-relative path, or filename. Never provide a local absolute path, account name, contact detail, or private project identifier; the packager reduces accidental absolute paths to their filename.
- `source.note`: optional provenance or access limitation.
- `claims`: list of claim-reference mappings. Use an empty list for a bibliography entry not cited in the manuscript.

### Claim-reference mapping

- `id`: stable claim ID such as `C001`. The same ID may occur under several references when one manuscript claim cites several papers.
- `manuscript_location`: required LaTeX line locator, Word heading/paragraph anchor, or PDF page/section anchor.
- `claim_text`: exact manuscript wording, not a paraphrase created during auditing.
- `claim_translation`: translation of the manuscript wording when requested; an empty string is allowed only when manuscript and report language are the same.
- `support_level`: `full`, `partial`, `secondary`, or `unresolved`.
- `risk`: required for `partial`, `secondary`, and `unresolved`; recommended for `full`.
- `evidence`: one or more evidence passages. Only `unresolved` may have an empty list.

### Evidence passage

- `location`: precise source locator. Prefer PDF page plus section and paragraph, figure, table, theorem, or appendix identifier.
- `quote`: verbatim source text. Preserve qualifiers and do not silently repair wording.
- `translation`: faithful translation of the quoted passage.
- `screenshot`: path to a readable image showing and highlighting the quoted passage.
- `note`: optional clarification, such as printed-page/file-page differences.

## Support levels

| Level | Meaning |
| --- | --- |
| `full` | The source directly supports the complete scoped claim. |
| `partial` | The source supports only part of the wording or requires a qualification. |
| `secondary` | Evidence is available only through a secondary source or citation context. |
| `unresolved` | No reliable passage has yet been obtained; do not infer a location or quote. |

## Screenshot preparation

The packager copies screenshots; it does not create or highlight them. Prepare screenshots before building the package. Keep enough page context to identify the passage, use a visible non-opaque box or highlight, and verify legibility at normal zoom.

Do not place source PDFs inside the generated package unless the user requests it and redistribution is permitted.
