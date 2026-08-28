# Attention Is All You Need: English-to-Chinese translation demonstration

This is a bounded, auditable demonstration for `academic-zh-en-translation`. It uses the same public NeurIPS 2017 source paper used by the LaTeX/Word synchronization demonstration, but does not use an author-provided LaTeX source or any private manuscript.

## Scope

The deliverable translates the title and abstract and records the terminology decisions needed for a full manuscript translation. It is intentionally an excerpt demonstration rather than a redistributed full translated paper. The records contain a 10-item Chinese scholarly corpus and a 10-item English scholarly corpus in the Transformer/neural-machine-translation direction.

## Contents

- `input/attention-is-all-you-need.pdf`: public source PDF.
- `translation/source-abstract.md`: aligned English source excerpt.
- `translation/translated-abstract.tex`, `.docx`, and `.pdf`: polished Chinese translation sample with review layout.
- `records/bilingual-corpus.csv`: 20 verified, linked scholarly records (UTF-8 with BOM).
- `records/terminology-map.csv`: evidence-led English-to-Chinese technical mapping (UTF-8 with BOM).
- `records/translation-evidence.xlsx`: Excel-safe corpus and terminology tables.
- `records/translation-qa.md`: semantic, terminology, and render QA record.

## Provenance

The source paper is Vaswani et al., *Attention Is All You Need*, NeurIPS 2017: https://proceedings.neurips.cc/paper_files/paper/2017/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html . The source PDF is retained unchanged. Corpus entries are bibliographic/terminology evidence only; they are not imported as claims or text into the translation.
