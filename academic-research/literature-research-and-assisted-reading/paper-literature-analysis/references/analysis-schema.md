# Analysis output and review schema

The published file must be Markdown and must contain these sections in this order:

1. **文献的领域和方向** — identify the research area, task, application setting, and method family. Distinguish the authors' framing from the reviewer's classification.
2. **文献声明的创新点和解决的问题** — state the problem, limitations of prior work claimed by the paper, and each claimed contribution. Mark claims that are only asserted and not experimentally supported.
3. **算法与源码分析** — explain the algorithm in enough detail to connect inputs, modules, losses/objectives, training/inference, and outputs to source files/functions. State repository provenance (`official implementation verified`, `official candidate unverified`, `third-party reproduction`, `no public source found`, or `access/clone failure`) and the commit SHA/tag or explicitly unavailable version identifier. For every source-derived claim, cite a relative file path plus a class/function/method/configuration key/line range, and map the paper component to its implementation. Explicitly answer whether the source agrees, extends, or conflicts with the paper; list untraced components and implementation details absent from the paper. **必需加入“可复现的输入—逐层计算—输出形状示例”子节：声明具体或符号化输入，写清预处理，逐层/逐模块列出计算、关键参数和输出形状/基数，展开特殊结构的中间张量与算法计算，并追踪到预测和相关 loss。**
4. **Benchmark、评价指标与数据集** — list every benchmark/protocol, metric definition or reported use, dataset, split/size where available, and whether a download link is public, restricted, missing, or not applicable. Do not infer availability from a citation alone.
5. **摘要与结论** — summarize the paper's abstract and conclusion separately, noting any gap between them.
6. **行文风格与章节逻辑** — describe tone, rhetorical style, section-by-section progression, and how evidence is used. Do not judge language ability without textual evidence.
7. **与引用文献的关系和联系** — connect the paper to cited methods/datasets/theory by citation and role. Separate direct baselines from background citations.

End with:

- **证据与核验记录** — MinerU sections and paths/images inspected, repository provenance, URL, commit/tag/archive identifier, and the exact source file/symbol observations examined.
- **不确定性与限制** — incomplete or ambiguous MinerU extraction, unreadable figures, unavailable code/data, source/paper mismatches, or claims that cannot be verified.

Rules:

- Never invent experimental numbers, repository ownership, dataset access, or algorithmic steps.
- Cite MinerU headings, figures, tables, and equations when possible. Source references must include paths and line/function names when a source repository was inspected.
- The worked example must include a compact shape/state ledger. Use an explicit
  illustrative input only when the paper/source does not provide a concrete
  size, and label that assumption; never present it as an experimental fact.
  For non-tensor methods, track state dimensions, units, counts, or
  cardinalities instead. Omission of this trace is a fatal-review failure
  unless the unavailable evidence and a symbolic trace are both recorded.
- Preserve equations, metric names, and dataset names accurately; explain rather than silently normalize ambiguous notation.
- A result is fatal-review failure if it omits a required section, fails to inspect the complete MinerU output or relevant images, claims code agreement without file-and-symbol evidence, omits a provenance disposition for a supplied repository candidate, fails to record an accessible verified source, confuses citations with baselines, or states unsupported facts as certain.
