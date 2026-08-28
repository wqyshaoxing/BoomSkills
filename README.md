# BoomSkills

一个用于开发、迭代、整合和共享科研与项目开发实用 skills 的仓库。

## 目录结构

```text
academic-research/                         # 学术研究
├── literature-research-and-assisted-reading/       # 文献调研和辅助阅读
├── innovation-exploration-and-rapid-validation/    # 创新点探索和快速验证
└── paper-writing-and-review/                       # 小论文撰写和审查

code-development/                          # 代码开发
├── requirements-understanding/                     # 需求理解
├── framework-design/                               # 框架设计
├── efficient-code-development/                     # 代码高效开发
└── test-cases-and-iteration/                       # 测试用例和迭代
```

## Skill 组织规则

- 每个 skill 实例必须保存在其功能所属的三级目录中。
- 一个 skill 使用独立目录保存；目录名称应使用清晰、稳定的 kebab-case 标识。
- skill 的说明、配置、脚本、参考资料和示例等相关文件均放在该 skill 的独立目录内。

## 跨 Harness 兼容性

所有 skill 都应采用 harness-agnostic（与具体运行框架解耦）的设计，目标兼容当前主流的 agent harness，包括但不限于：

- Claude Code
- Codex
- Hermes Agent
- OpenCode

为实现可移植性，skill 应遵循以下原则：

- 使用清晰的 Markdown 文档说明用途、输入、输出、前置条件和执行步骤。
- 将核心流程与某一 harness 专属的命令、工具名称或环境变量解耦；若需要适配层，应单独说明。
- 明确所需的运行时、外部依赖、权限与可选配置，避免隐式依赖特定客户端状态。
- 为不同 harness 提供必要的调用或安装说明，并在提交前验证其核心功能可以按文档复现。

## 本次更新

### 论文撰写与审查

- `latex-word-sync`：支持 LaTeX 与 Word 的结构化同步；Word 可选择单栏或双栏版式，统一 Times New Roman、居中且等比缩放的图片、可编辑公式与公式编号，并包含版式质量检查。
- `academic-zh-en-translation`：先建立领域双语语料与术语映射，再进行忠实的中英学术互译、表达润色和版式检查；中文表格同时提供 Excel 友好的 UTF-8 BOM CSV 与 `.xlsx` 输出。
- `paper-citation-evidence-audit`：为引言、相关工作等论断创建逐参考文献的证据包，记录正文定位、原文摘录、翻译、支持等级和高亮截图；支持对未引用条目显式标注。

### 文献调研与辅助阅读

- 新增 `literature-search`、`paper-search-mcp`、`arxiv-mcp-server`、`paper-literature-analysis`、`mineru-pdf-to-markdown`、`zotero-batch-pdf-import` 和 `agent-cluster-management`。
- 覆盖开放论文检索、arXiv 源码获取、MinerU PDF 解析、Zotero 批量入库、隔离式论文分析与多智能体调度。
- 每个技能会先检测 MCP、CLI、Zotero、MinerU 或分析工作进程等依赖，报告可用性与降级方案；仅在用户明确授权后才配置 MCP、启动服务或执行外部写入。

### 隐私与可移植性

- 技能示例、清单、日志和交付物不得包含用户名、绝对本机路径、私有项目标识、联系方式、密钥或 Token。
- 统一采用工作区/技能目录相对路径；凭据仅通过环境变量或用户显式提供的技能外 secret 文件使用。
- 对外部上传、Zotero 写入和 MCP 配置均要求先确认范围与授权，并保留可用的降级路径。

## 贡献

新增或更新 skill 时，请将其放入对应的三级目录，并确保其文档符合上述组织与兼容性要求。
