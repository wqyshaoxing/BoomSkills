#!/usr/bin/env python3
"""Publish a reviewer-approved candidate beside its source PDF."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


HEADINGS = [
    "文献的领域和方向",
    "文献声明的创新点和解决的问题",
    "算法与源码分析",
    "Benchmark、评价指标与数据集",
    "摘要与结论",
    "行文风格与章节逻辑",
    "与引用文献的关系和联系",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--review-passed", action="store_true")
    args = parser.parse_args()
    if not args.review_passed:
        parser.error("publishing requires --review-passed")
    text = args.candidate.read_text(encoding="utf-8")
    missing = [heading for heading in HEADINGS if not re.search(rf"^#+\s+.*{re.escape(heading)}", text, re.MULTILINE | re.IGNORECASE)]
    if missing:
        raise SystemExit("candidate is missing required sections: " + ", ".join(missing))
    output = args.pdf.parent / "analysis.md"
    private = args.pdf.parent / ".paper-analysis"
    private.mkdir(parents=True, exist_ok=True)
    if output.exists():
        shutil.copy2(output, private / "previous-analysis.md")
    shutil.copy2(args.candidate, output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
