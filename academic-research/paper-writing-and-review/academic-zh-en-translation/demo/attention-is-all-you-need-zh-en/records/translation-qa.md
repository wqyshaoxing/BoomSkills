# Translation QA

- Source/target files: `input/attention-is-all-you-need.pdf` and `translation/source-abstract.md` → `translation/translated-abstract.tex` and `.pdf`.
- Direction and field: English → Chinese; computer science / NLP; Transformer architectures and neural machine translation (high confidence).
- Corpus records: zh=10, en=10. Records are linked scholarly metadata and terminology evidence; no corpus text is copied into the translation.
- Terminology mappings: 20. All mappings used in the translated title/abstract are marked high or medium confidence with evidence IDs.
- Semantic alignment: checked title, model name, architecture components, task names, two BLEU values, two WMT language directions, 3.5-day duration, eight GPUs, comparative claims, and the generalization claim. No added result, citation, method, or causal claim.
- Language polish: changed English nominal chains to natural Chinese sentences; retained claim scope and the contrast between quality, parallelism, and training time.
- Layout review: rendered and inspected the final Chinese PDF; title hierarchy, Chinese font legibility, paragraph spacing, numeric/Latin-token integrity, and footer provenance passed.
- Unresolved questions: none for this bounded abstract translation. A full-paper translation would require section-by-section alignment records and figure-text authorization review.
- Fidelity conclusion: passed for the declared excerpt scope after PDF review.
