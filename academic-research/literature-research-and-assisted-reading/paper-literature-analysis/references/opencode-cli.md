# OpenCode CLI requirements

Use one fresh OpenCode CLI process per paper. The only configured model is the
multimodal `qwen38-free/qwen3.8-27b`. Every paper uses Qwen3.8, and papers with
MinerU images receive those images as repeated `--file` attachments.

The runner invokes the equivalent of:

```text
opencode run --pure --auto --model qwen38-free/qwen3.8-27b --format json --file <image-1> --file <image-2>
```

The paper-specific prompt is sent on stdin. Each process runs from a unique
working directory under that paper's private `.paper-analysis` folder. The
provider key `OPENCODE_QWEN_API_KEY` must be available to the process; the
runner also reads the persisted Windows user variable when its parent process
has a stale environment block.

The runner performs one initial attempt plus two retries per paper by default.
Use `--max-retries` to change that bound. A paper that still has no usable
candidate is returned as `opencode_retry_exhausted` with
`fallback_required: true`; the runner also rejects candidates missing any of
the seven required headings. Only then may Codex perform the fallback
analysis. If a candidate passes the structural check but fails evidence
review, retry it with `--review-feedback` while retry budget remains.
Do not continuously tail a running process. Wait and poll the batch roughly
every 3–5 minutes, then inspect the captured stdout/stderr and candidate files.

`--auto` is used because this authorized workflow requires unattended local
file reading, candidate-file writing, and repository download. The prompt
forbids executing downloaded source code or installing dependencies. Capture
stdout/stderr per paper, but publish only a candidate file after the existing
Codex review and `publish_analysis.py` schema check pass.
