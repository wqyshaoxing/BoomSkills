#!/usr/bin/env python3
"""Create non-destructive, auditable records for an academic translation run."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FILES = {
    "bilingual-corpus.csv": [
        "id", "language", "type", "citation", "doi_or_url", "field_relevance",
        "terminology_evidence", "access_note",
    ],
    "terminology-map.csv": [
        "source_term", "target_term", "term_type", "context", "evidence_ids",
        "alternatives", "avoid", "confidence", "decision_note",
    ],
}


def write_csv(path: Path, headers: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.DictWriter(stream, fieldnames=headers).writeheader()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source-lang", choices=("zh", "en"), required=True)
    parser.add_argument("--target-lang", choices=("zh", "en"), required=True)
    args = parser.parse_args()
    if args.source_lang == args.target_lang:
        parser.error("source and target languages must differ")

    args.out.mkdir(parents=True, exist_ok=True)
    outputs = [args.out / "translation-brief.json", args.out / "translation-qa.md"]
    outputs.extend(args.out / name for name in FILES)
    existing = [path.name for path in outputs if path.exists()]
    if existing:
        parser.error("refusing to overwrite existing workspace files: " + ", ".join(existing))

    brief = {
        "source_language": args.source_lang,
        "target_language": args.target_lang,
        "field_classification": {"discipline": "", "subfield": "", "confidence": ""},
        "source_of_truth": "",
        "target_output": "",
        "status": "planned",
    }
    (args.out / "translation-brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name, headers in FILES.items():
        write_csv(args.out / name, headers)
    (args.out / "translation-qa.md").write_text(
        "# Translation QA\n\n- Source/target files: \n- Field classification: \n"
        "- Corpus records: zh=0, en=0\n- Terminology mappings: 0\n"
        "- Rendered files reviewed: \n- Unresolved questions: \n- Fidelity conclusion: \n",
        encoding="utf-8",
    )
    print(f"Created translation workspace: {args.out}")


if __name__ == "__main__":
    main()
