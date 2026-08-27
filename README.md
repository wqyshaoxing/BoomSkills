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

## 贡献

新增或更新 skill 时，请将其放入对应的三级目录，并确保其文档符合上述组织与兼容性要求。
