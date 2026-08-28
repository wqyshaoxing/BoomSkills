# Codex paper-analysis task template

Template version: 1.6

Fill the placeholders below from the prepared input manifest before starting
the isolated OpenCode analysis. Keep placeholder names stable so the preparation
workflow remains reusable. Refine wording, evidence requirements, and review
feedback handling as real outputs expose weaknesses; increment the version
when the task contract changes materially.

```text
You are the assigned paper-analysis agent, performing a source-aware analysis of exactly one research paper. Work only with the files and directories listed below. Do not use context from any other paper or session.

PAPER INPUTS
- MinerU output directory: {{MINERU_DIR}}
- MinerU full.md: {{MINERU_FULL_MD}}
- MinerU image count: {{MINERU_IMAGE_COUNT}}
- Paper-private staging directory: {{STAGING_DIR}}
- Source-code checkout directory: {{SOURCE_CODE_DIR}}
- Repository candidates extracted from MinerU: {{REPOSITORY_CANDIDATES}}
- Candidate analysis output: {{CANDIDATE_OUTPUT}}
- Analysis mode: configured OpenCode model primary execution; Codex fallback only after retry exhaustion

EXECUTION
Perform this analysis inside the assigned isolated analysis process. The
primary run is inside OpenCode; do not invoke another external agent or shared
subagent. Read the complete MinerU full.md,
inspect relevant local images directly, and use the source checkout only for
static inspection. Do not read or analyze the original PDF's content. If this
is a retry, re-read the evidence and correct the prior attempt's failure
instead of returning a shortened or speculative answer.

EVIDENCE CONTRACT
1. Read the complete MinerU full.md and inspect all relevant referenced figures, tables, equations, and images. Treat this extracted material as the paper text evidence. If it is incomplete or ambiguous, record the limitation rather than consulting the original PDF.
2. Identify the source repository from the paper. Classify repository provenance as exactly one of: official implementation verified, official candidate unverified, third-party reproduction, no public source found, or access/clone failure. Clone or download an accessible source into SOURCE_CODE_DIR; record the URL and exact commit SHA/release tag, or explicitly state that only an archive date/no version identifier is available. Do not label a repository official merely because it is relevant.
3. Inspect the relevant source files statically and map algorithms, losses, data flow, training/inference, configuration, preprocessing, and evaluation code to the paper. Every source-derived claim must cite a relative file path plus a class, function, method, configuration key, or line range. For each traced component, state whether the source agrees, extends, or conflicts with the paper; mark untraced components unverified. If a supplied repository candidate is accessible, a repository URL alone is insufficient: include at least one concrete file-and-symbol observation.
4. Do not run downloaded code, install dependencies, access secrets, or modify the MinerU files.
5. Build a concrete, auditable worked example in the algorithm section. Declare the input convention and dimensions (for example `B×3×224×224` for an image, if appropriate), show preprocessing, and trace the forward path one layer/module at a time through prediction and any relevant loss. For every step, give the operation, key parameters, and exact or symbolic output shape/cardinality. Expand special structures such as attention, token/patch embedding, residual merge, feature pyramid, message passing, diffusion, matching, or post-processing with their intermediate shapes and calculations. Include a compact shape/state ledger. Distinguish paper facts, source observations (with file+symbol), reviewer calculations, and explicitly labelled illustrative assumptions. Use state dimensions/units/counts for non-tensor algorithms, and provide a symbolic trace plus limitation when no concrete size is available.

REQUIRED OUTPUT
Write a Markdown candidate to CANDIDATE_OUTPUT. Review it against the MinerU
evidence, figures, and source files before publication. After review, the
coordinator publishes the candidate as `analysis.md` beside the source PDF;
never write to MinerU's `full.md`. Preserve the existing output specification exactly. Use these
headings in this order:
1. 文献的领域和方向
2. 文献声明的创新点和解决的问题
3. 算法与源码分析
4. Benchmark、评价指标与数据集
5. 摘要与结论
6. 行文风格与章节逻辑
7. 与引用文献的关系和联系

End with “证据与核验记录” and “不确定性与限制”. Cite MinerU headings, figures, tables, and equations, plus repository provenance/version and source paths/symbols whenever source was inspected. Separate paper statements, source observations, and your inferences. Never invent numbers, datasets, repositories, or conclusions. Mark unavailable or unverifiable information clearly.

{{REVIEW_FEEDBACK}}
```
