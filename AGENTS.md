# HC-AIDW — Human-Centered AI Development Workflow

规范化、可组合、跨 AI 编程工具的人机协同开发工作流。核心:让 AI 专业地理解需求、设计架构、实施代码,让非技术人员通过可视化界面审核 AI 的工作。三个审核节点:**需求理解审核、架构与实施方案审核**(核心研究对象)、**代码生成结果核验**(形成闭环)。

## 铁律

1. **JSON 是唯一事实源,HTML 只是投影视图。** 任何审核界面必须由审核 JSON 生成,禁止手写 HTML 内容。
2. **结论必须有证据。** 审核文档中的结论/风险字段携带 `source_ref` / `evidence`;无法给出证据的,verdict 标 `needs_validation`。
3. **架构图复用 Archify schema**(`architecture/sequence/erd/dataflow`),本项目的信封 schema 只承载审核特有信息。
4. 未经独立复核的结论不得标 `confirmed`(借 cloudflare/security-audit-skill 三态协议)。

## 目录

- `schemas/` — 三份审核 JSON Schema(`requirement-review` / `architecture-review` / `verification-report`),`examples/` 为示例实例
- `scripts/` — `validate.py`(schema 校验 + id 唯一性检查)、`diff_review.py`(两版变更回执)
- `docs/` — 启动调研四份报告与 `research/` 调研笔记
- `reviews/` — (实施阶段)每个试点需求的审核文档与渲染 HTML
- `skills/` — (M4)hc-aidw 主控 skill

## 工作约定

- **沟通规范(面向非技术审核者,2026-11-06 用户反馈确立)**:
  1. 先可视化呈现"AI 对现状的理解",用户确认理解无误后再谈决策——不允许上来就连环文字提问
  2. 决策分层:业务决策(支持语言/评分方式/范围边界)才问用户;技术选型(组件、沙箱形态等)由 AI 决定,理由写进方案审核界面,用户有否决权但无须从零判断
  3. 每轮最多 3 个问题;每题必须说明"这个选择对你的影响是什么"
  4. 零裸术语:任何专业词汇带人话解释或直接不出现
  5. 涉及增删改既有代码,用前后对比可视化呈现"怎么改"
- 提交审核 JSON 前必须跑:`python scripts/validate.py <file>`;修改后跑 `python scripts/diff_review.py <old> <new>` 生成变更回执
- 用户意见必须锚定到节点 id(写入 `feedback` 数组),不许只留在聊天记录里
- 面向用户的界面文案用业务语言,技术概念按 `glossary` 翻译;界面示例数据必须真实,禁止占位假数据(show-me 范式)
- 每个里程碑结束暂停,等人工审核后再继续

## 环境

- GitHub 网络操作走本地代理 `http://127.0.0.1:33210`
- Python 3.10(需 `jsonschema` 包);详细能力盘点见 `docs/tool-capability-inventory.md`
