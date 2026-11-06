# HC-AIDW 报告 01:现有能力盘点(Skills、MCP、工具)

> 调查日期:2026-11-06
> 调查方式:直接检查本机 Claude Code 环境(配置文件、插件缓存目录、运行时验证),非纯文档推断。
> 标注约定:【已验证】= 实际检查/运行确认;【文档说明】= 来源文档声称但未实测;【推断】= AI 分析结论;【建议引入】= 现在没有、值得引入。

---

## 一、当前已安装的 Skills

### 1.1 全局内置 Skills(Claude Code 自带)

【已验证】以下 skill 在当前会话可见且可调用:

| Skill | 实际功能 | 调用方式 | 对 HC-AIDW 的价值 |
|---|---|---|---|
| `code-review` | 审查当前 diff / 指定 PR,找**正确性 bug**,附带复用/简化/效率清理;支持分级(low~max)、`--fix` 直接修复、`--comment` 发 PR 评论 | `/code-review` 或模型按描述自动触发 | ★★★ 直接服务"代码生成结果核验"节点 |
| `security-review` | 对当前分支待提交改动做安全审查 | `/security-review` | ★★ 代码核验节点的安全维度 |
| `simplify` | 只做代码质量清理(复用/简化/效率),不找 bug | `/simplify` | ★ 辅助 |
| `codebase-design` | "深模块"设计词汇表(Ousterhout 风格):模块接口、加深机会、接缝选择。**注意:经逐字比对,这是 Matt Pocock 同名 skill 的内置收编版** | 模型自动触发为主 | ★★★ 服务"架构与实施方案审核"节点 |
| `dataviz` | 任何图表/可视化/仪表盘产出前的设计方法(形式启发、配色公式、mark 规范、交互规则) | 模型自动触发为主 | ★★★ 审核界面视觉规范的直接来源 |
| `run` | 启动并驱动本项目应用以验证改动(先找项目自有启动 skill,再按项目类型回退) | `/run` 或自动触发 | ★★ "代码核验"节点里展示实际功能效果 |
| `claude-api` | Claude API 参考(模型、定价、参数、工具调用) | 自动触发 | ★ 低(HC-AIDW 第一版不做 API 集成) |
| `init` | 生成 CLAUDE.md | `/init` | ★ 低 |
| `update-config` / `fewer-permission-prompts` / `plugin-authoring` / `workflow-authoring` / `loop` | harness 配置类 | — | ★ 与本项目目标无关 |

【已验证】限制说明:内置 skill 不能跨会话保存状态;`code-review` 依赖 ReportFindings 上报通道,输出到宿主 UI 而不是普通文件——做审核界面时需要让它落盘成文件,这是后续要解决的适配点。

### 1.2 项目本地 Skills(`E:\LLM\agentic-class-pilot\.claude\skills\`)

【已验证】存在两个目录:`codebase-design`、`improve-codebase-architecture`。内容与 Matt Pocock/skills 仓库同名字 skill 一致,是之前手动复制进来的本地副本。

- `improve-codebase-architecture`:扫描代码库,找可以"加深"的模块(接口小、功能多),输出 HTML 诊断报告。【已验证存在;【文档说明】功能描述来自 SKILL.md,未在本项目实测跑过完整流程】
- 影响:插件版 `mattpocock-skills:improve-codebase-architecture` 装好后,本地副本与它重复,后续应删除本地副本、统一用插件版,避免两个版本漂移。【推断】

### 1.3 插件一:EGM(Elephant-Goldfish Model,google/elephant-goldfish-model v0.1.0)

【已验证】用户级安装,缓存于 `~/.claude/plugins/cache/egm/egm/0.1.0`,含 7 个 skill + 9 个 subagent 定义。核心机制:**大象**(持有项目上下文的主会话)起草,**金鱼**(零上下文、无对话历史的子代理)只看草稿和源码做盲审,逼出未言明的假设。9 个审查视角:comprehension(天真实读)、design(设计批评)、structural、style、codebase-details、implementation-readiness、zoom-out、synthesizer、bootstrap-orchestrator。

| Skill | 功能 | 输出产物 | 对 HC-AIDW 的价值 |
|---|---|---|---|
| `egm-bootstrap` | 为目录树批量生成符合 EGM 规范的 README(Peanuts 叶级文件契约 + Hay 父级蓝图) | 各级 README.md | ★★ 给"架构审核"提供可校验的模块契约文本 |
| `egm-brainstorm` | 交互式澄清提问 + 金鱼盲审,把半成品想法打磨成 RFC 摘要(`concepts_brief.md`) | concepts_brief.md | ★★★ 直接服务"需求理解审核"节点 |
| `egm-draft` | 基于 brief 分节起草设计文档(`design_draft.md`),强制落盘不刷屏 | design_draft.md | ★★★ 服务"架构与实施方案审核"节点 |
| `egm-review` / `egm-review-loop` | 并发金鱼评审草稿,产出扁平化缺陷报告 | 评审报告 | ★★★ 审核节点的"机器初审"层 |
| `egm-resolve` | 大象吞下缺陷报告,自动修复/逐条协商(PROPOSE FIX 多选门) | 修订后文档 | ★★ 人机协商机制,可借鉴为"用户修改意见回流" |
| `egm-drift-report` | 逐份比对设计文档 ↔ 实际源码,输出漂移报告 | 漂移报告 | ★★★ **这就是"文档与代码一致性核验"的现成实现**,直接对应 HC-AIDW"可视化内容与实际设计、源码证据保持一致"的要求 |

【已验证】跨工具兼容:EGM 官方同时支持 Claude Code、Codex、Antigravity(agy CLI)、ChatGPT Work、Claude Cowork——它是现成的跨 harness 工作流范例,其 `docs/harnesses.md` 记录了各 harness 的适配层写法。【文档说明,适配细节未逐一实测】

【已验证】限制:brainstorm/review 需要能创建子代理的会话;EGM 全程产出 Markdown,没有可视化层——这正是 HC-AIDW 要补的空档。

### 1.4 插件二:mattpocock-skills v1.3.2(2026-11-06 刚安装)

【已验证】用户级安装,含 38 个 skill(19 engineering + 7 productivity + 4 misc + 8 in-progress)。与本任务直接相关的:

| Skill | 功能 | 对 HC-AIDW 的价值 |
|---|---|---|
| `grill-me` / `grill-with-docs` | 开工前让 AI 反复盘问用户,把需求树问透;docs 版还产出术语表 GLOSSARY.md 和 ADR | ★★★ 需求理解审核的提问引擎 |
| `to-spec` → `to-tickets` → `implement` | 讨论→规格→工单→(多子代理)实现的流水线,末尾自动接 code-review | ★★★ 提供了"结构化中间产物驱动开发"的完整参照 |
| `tdd` | 红-绿-重构强制循环 | ★★ 代码核验节点的质量保障 |
| `diagnosing-bugs` | 纪律化 bug 诊断(复现→最小化→假设→插桩→修复→回归) | ★ |
| `code-review`(插件版) | 与内置版**不重复**:两轴审查——① Standards(是否符合仓库文档化规范 + Fowler 坏味道);② Spec(是否忠实实现了 issue/规格) | ★★★ 核验节点"实现是否符合已确认方案"的现成工具 |
| `handoff` | 把当前会话压缩成交接文档 | ★★ 跨会话工作流的粘合剂 |
| `wayfinder` / `to-questionnaire` / `wait-what` / `retro` | 大任务拆解为工单地图 / 把决策变成问卷 / 换方式重讲 / 会话复盘 | ★★ to-questionnaire 天然适合"收集非技术人员审核意见" |
| `improve-codebase-architecture` | 架构诊断,出 HTML 报告 | ★★★(见 2.2 与本地副本重复问题) |

【已验证】安装方式:`mattpocock/skills` 仓库自带 marketplace 定义(`.claude-plugin/marketplace.json`),`claude plugin marketplace add mattpocock/skills` + `claude plugin install mattpocock-skills@mattpocock`。官方 marketplace(claude-plugins-official)本地未配置且其中无此插件。

---

## 二、已有工具与 MCP 盘点

### 2.1 MCP Server

【已验证】当前环境仅挂载一个 MCP:`web_reader`(网页抓取与正文提取)。本报告调研期间实测,GitHub 页面与 raw 文件抓取稳定。

【已验证】以下常见 MCP **均未配置**:浏览器自动化(playwright/chrome-devtools)、截图、数据库、容器、文件系统增强等。`~/.claude.json` 与项目 `.mcp.json` 中均无条目。

影响:【推断】审核界面的"用户点击行为采集"暂时做不了(没有浏览器控制通道),第一版界面应以**静态单文件 HTML + 用户口头/文字反馈**为主。

### 2.2 基础能力逐项核对

| 能力 | 状态 | 说明 |
|---|---|---|
| 文件读写 | 【已验证】可用 | Read/Write/Edit + Bash,无限制 |
| 项目源码分析 | 【已验证】可用 | Grep/Glob/Read/子代理,本项目(agentic-class-pilot,FastAPI+React)已多次实际使用 |
| Git 操作与 diff | 【已验证】可用 | git 2.34.1,注意 GitHub 网络操作需走本地代理 `127.0.0.1:33210` |
| 自动化测试 | 【已验证】可用(项目内) | 本项目有 pytest 套件,可直接跑;通用能力=通过 Bash 执行任意测试命令 |
| HTML 预览 | 【已验证部分可用】 | 可用 `cmd start` 在默认浏览器打开本地 HTML(本机已有 architecture-showcase 实际操作先例);**无**浏览器自动化/截图 MCP,不能程序化验证渲染效果;VSCode 环境下用户可自行预览 |
| 图表/可视化生成 | 【已验证可用】 | 两条路线:① `dataviz` skill 指导下生成单文件 HTML/ECharts/SVG——`E:\LLM\architecture-showcase\` 已有 10 组成品(architecture/sequence/erd/dataflow 四类 JSON + HTML);② Matt 插件 `improve-codebase-architecture` 自带 HTML 报告模板 |
| JSON Schema 校验 | 【未具备,建议引入】 | Python 3.10.11 / Node 24.13.0 都在,但 `jsonschema` 包未安装(已实测确认缺失)。理论上 pip 安装即得,第一版需要它来校验审核中间产物(需求理解 JSON、架构方案 JSON)的结构 |
| 浏览器自动化/截图 | 【未具备,建议引入】 | 若要"程序确认页面渲染正常"或采集用户交互,需要 playwright MCP;第一版可不做 |

### 2.3 运行时

【已验证】Python 3.10.11、Node v24.13.0、git 2.34.1 均可用。生成静态 HTML 不需要任何运行时(纯文件产物),脚本类工具(Python/Node)按需可用。

---

## 三、能力 → HC-AIDW 三审核节点的映射总结

| 审核节点 | 现有可复用能力 | 缺口 |
|---|---|---|
| ① 需求理解审核 | `grill-me`/`grill-with-docs`(盘问)、`egm-brainstorm`(澄清+盲审→brief)、`to-questionnaire`(收集意见) | **缺可视化载体**:产出全是 Markdown,非技术人员不友好 |
| ② 架构与实施方案审核 | `egm-draft`(分节草稿)、`egm-review`+`egm-resolve`(盲审+协商)、`codebase-design`(设计词汇)、`egm-drift-report`(文档↔代码一致性)、`dataviz`+architecture-showcase 模式(JSON→HTML) | 缺交互式架构审核界面(方案对比、点击展开、批注);EGM 只会写 Markdown |
| ③ 代码生成结果核验 | 内置 `code-review`(找 bug)、插件版 `code-review`(查规范+查 spec 符合度)、`egm-drift-report`(漂移检测)、`tdd`、`run`(实际运行验证)、`security-review` | 基本齐备;缺"需求→实现对应关系"的结构化呈现 |

【推断】总体结论:**"后台智能层"基本齐备(盘问、起草、盲审、漂移检测、代码审查都有现成实现),真正的空缺集中在"前台呈现层"**——把结构化结论转成非技术人员可交互、可批注、可回写的 HTML 审核界面,这正是 HC-AIDW 第一版应该聚焦的自研点,而不是再造提问/审查逻辑。

---

## 四、跨任务组合能力

【已验证】同一会话内 skill 可串联(例如 mattpocock 的 `implement` 内部就显式调用 `tdd` 和 `code-review`);子代理(Agent tool)与 Workflow 编排可并行多审查者(EGM 的并发金鱼即用此机制)。【推断】限制:组合逻辑目前散落在各 skill 的 prompt 里,HC-AIDW 需要定义自己的编排约定(JSON 中间产物 + 各节点读取/写入契约),而不是依赖某个插件的内部流程。
