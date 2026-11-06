# HC-AIDW 报告 02:候选工具评估

> 调查日期:2026-11-06
> 每个工具按统一框架评估:解决什么问题 / 能否直接复用 / 与现有能力重复度 / 依赖 / 权限风险 / 是否纳入第一版。
> 标注约定同报告 01:【已验证】【文档说明】【推断】【建议引入】。

---

## 一、Archify(tt-a1i/archify,v3.2.0,Apache-2.0)

**定位**:开源 Claude Code skill,把架构描述渲染成自包含单文件 HTML 可视化。官网 archify.si,支持 10 种图型。

**解决什么问题**:HC-AIDW 最核心的痛点——把结构化架构知识变成非技术人员看得懂、可交互的界面。这正是"后台 JSON、前台 HTML"模式的现成实现。

**实证细节**【已验证,基于本地 `E:\LLM\architecture-showcase\` 样例 + 官方仓库调研】:
- 中间表示:`schema_version: 1` + `diagram_type`(architecture / sequence / erd / dataflow 等),字段为 components/connections/messages/entities;**布局坐标由作者显式指定**(不是自动布局),这让 JSON 完全决定渲染结果,是可复现性的关键
- 渲染产物:840–900KB 自包含单文件 HTML(内联 SVG + 内嵌字体 + 自研查看器 JS,零外部依赖)——可以放进 git、可以离线发给评审人
- 内置交互:节点聚焦、上下游可达追溯、路线追踪、主题切换、导出、share card

**能否直接复用**:能,且建议作为第一版可视化层的基座。【已验证】

**与现有能力重复度**:与 `dataviz` skill(通用图表设计方法)互补不重复——dataviz 管"怎么画好看",Archify 管"架构图型的标准 schema 和查看器"。

**依赖**:无运行时依赖(纯文件产物);作为 skill 安装即可。

**权限风险**:低。产出是静态 HTML;不联网、不执行外部代码。【推断】

### 1.1 逆向能力分析(用户重点关注的问题)

正向链路:**代码 →(AI 分析)→ 架构 JSON →(renderer)→ HTML**。

**(a) HTML → JSON:部分可行,定级"需人工 / AI 辅助可行"**
【已验证】JSON 并不内嵌在 HTML 里,所以**无损提取不成立**。但 HTML 是从 JSON 确定性地生成的:节点 id、`data-edge-*` 属性、全部文本、标题都一一对应 JSON 字段。【推断】写脚本可机械恢复约八成结构(节点、连线、文本),布局坐标也能从 SVG 属性读回;语义分组、注释等会丢失,需要 AI 补全 + 人工校对。
**但要点是:正常流程不需要逆向。** JSON 源文件本来就应该与 HTML 成对保存进仓库。逆向只在"只有 HTML、JSON 丢失"的场景有价值(例如接手别人只发了 HTML 的评审包)。

**(b) HTML + JSON → 代码:不可行**
【推断】JSON 是架构的**描述性投影**,不包含接口签名、业务逻辑、行为语义——信息量与源码差几个数量级。它能告诉你"有这三个模块、这么连",不能告诉你"函数怎么实现"。方向应该反过来:代码变了 → AI 重新分析生成新 JSON → 重新渲染。

**(c) 真正有价值的"逆向":HTML 审核意见 → JSON patch → 代码变更**
这是 HC-AIDW 应该采纳的闭环,分两步:
1. **意见回写 JSON**(可行):用户在审核界面上的动作——改节点名、拖动分组、批注"这个模块职责不清"——都可以结构化为 JSON patch(如 `{op: "annotate", target: "component-12", comment: "..."}` 或直接改 components 字段)。【已验证】Archify 自带 `archify compare`,可对两个版本的 JSON 出评审变更回执,天然适合"用户改了什么"的回执展示。
2. **JSON 变更 → 代码变更**(AI 辅助可行):JSON diff 描述的是**架构意图的变化**(拆模块、改依赖、改数据流),AI 拿着 diff + 源码去实施重构——这不是机械转换,是"AI 读结构化反馈改代码",与 HC-AIDW 核验节点的工作方式一致。

### 1.2 纳入建议

**纳入第一版,JSON 为唯一事实源。** 起步方式:对话式改图(用户用自然语言说"把通知模块拆成两个",AI 改 JSON 重渲染),零开发成本;交互式 HTML 批注壳作为第二阶段。

---

## 二、EGM(Elephant-Goldfish Model,google/elephant-goldfish-model v0.1.0,Apache-2.0)

**解决什么问题**:设计文档的"起草-盲审-协商"流程。大象(有上下文的主会话)起草,金鱼(零上下文子代理)只读草稿+源码做盲审,暴露未言明的假设。据官方称数千 Google 工程师在用。【文档说明】

**能否直接复用**:能,已在本机安装。【已验证】四个直接对口:
- `egm-brainstorm` → 需求理解审核(澄清提问 + 盲审 → concepts_brief.md)
- `egm-draft` → 架构方案草稿(design_draft.md)
- `egm-review` + `egm-resolve` → 方案审核(多视角盲审 + 逐条协商)
- `egm-drift-report` → "文档与代码一致性"核验(HC-AIDW 反幻觉要求——可视化与源码证据一致——的现成检测器)

**与现有能力重复度**:与 mattpocock 的 grill/流水线部分重叠(都做需求盘问),但 EGM 的**零上下文盲审**机制独有——这是"AI 审 AI"质量的保障。【推断】

**依赖**:能创建子代理的会话;无外部服务。

**权限风险**:低。纯 prompt + 子代理,产出 Markdown。【已验证,读源码确认】

**缺口**:全程 Markdown,无可视化——EGM 负责 HC-AIDW 的"后台智能层",呈现层交给 Archify。

**纳入建议**:**纳入第一版**,作为需求/架构两个审核节点的引擎。

---

## 三、HumanLayer(humanlayer/skills)

**先澄清一个重要事实**【已验证,逐一核对该仓库文件树】:humanlayer/skills 实际只含 5 个 skill,**grill-me 与 RPI 都不在其中**——grill-me 是 Matt Pocock 的 skill(已随 mattpocock-skills 插件装好),RPI 是 HumanLayer 博客提出的方法论(Research-Plan-Implement),不是仓库里的 skill。原任务清单中把它们归到 HumanLayer 名下,需要修正。

**仓库里真正值得用的:**

**1. `show-me`**(已全文验证 SKILL.md)——HC-AIDW 界面层最有价值的外部参照:
- 机制:先让用户从视图菜单选型(伪代码 / 调用树 / 文件树 / Mermaid 图 / diff),再产出**单文件聚焦 HTML**
- 产物三态:diagram / infographic / slide deck;贴宿主产品的设计 token、用**真实数据**(不用占位假数据)、响应式
- 不指定图表库、依赖极低 → 可以整体搬进 HC-AIDW:需求审核页的"预期效果对比"、架构审核页的方案卡片,都适合用 show-me 的生成范式
- 与 Archify 分工:Archify 管标准架构图型(有 schema、有 compare 工具链),show-me 管"自由发挥的解释性页面"(无 schema、更美观)。【推断】建议架构类图用 Archify,需求/解释类页面用 show-me 范式

**2. Matt 版 grilling 机制**(已全文验证):design tree + frontier 的轮次盘问——每题带推荐答案、事实性问题自查、需要决策的才问用户、frontier 清空才算问完。这解释了为什么 grill-me 比"让 AI 提问"的朴素 prompt 强:它有**终止条件和覆盖度追踪**。需求审核节点的 open_questions 生成就按这个机制做。【已验证 SKILL.md;效果推断】

**3. `build-iterated-agentic-loop` 与 `design-control-loop`**(已全文验证):其 PR bounding(限制单次变更规模)、memory 沉淀(经验固化)、completion criterion(完成判据)、response-template(回复模板)等设计,可复用于方案审核与代码核验节点的流程控制。【文档说明+已验证 SKILL.md;效果推断】

**依赖 / 权限风险**:纯 prompt skill,无外部服务,风险低。【已验证】

**纳入建议**:**纳入第一版**——show-me 作为界面生成范式,grilling 作为需求盘问机制;两者都随 skill 安装即可获得,不需要自研。待补调研:RPI 博客原文、show-me 配套博文、HumanLayer HIL API(人工审批 API,若未来审核流程要接外部人,可能有用)。

---

## 四、Cline(cline/cline,Apache-2.0)

**解决什么问题**:开源 AI 编程代理(原 VS Code 插件,现已不限 IDE),审查能力由 diff 面板、shadow-git checkpoints(回滚安全网,不产审查结论)、headless CLI(`git diff | cline "Review..."` 可接 CI)和 SDK 组成。【文档说明】

**能否直接复用**:技术上可以,但**不建议第一版纳入**。

**与现有能力重复度**:高。Claude Code 内置 `code-review`(找正确性 bug)+ mattpocock 插件版 `code-review`(查规范符合度 + spec 符合度)已覆盖其审查价值。【已验证,两者 SKILL.md 均在本地】

**依赖 / 权限风险**:支持任意 OpenAI 兼容模型;官方无 review skill,社区约 157 个 skill 质量参差(引入第三方 skill 有 prompt 注入面)。【文档说明】

**纳入建议**:第一版不纳入;第二阶段若要做"异构模型交叉复核"(用非 Claude 模型复核 Claude 的产出再交叉对比),Cline headless 是候选。【推断】

---

## 五、Cloudflare Security Audit Skill(cloudflare/security-audit-skill,MIT)

**解决什么问题**:对代码库做六阶段 AI 多 agent 安全审计:recon → coverage-led 狩猎 → 独立 verifier 对抗复核 → findings.json 结构化输出 → 再核验 → REPORT.md。覆盖注入、prompt-injection、鉴权协议、供应链、IaC 等 12 类。**注意:不是静态扫描器**,Node 仅做 schema 校验。【文档说明】

**能否直接复用**:能安装,但第一版**全量审计过重**——它是发布前工具,不是每轮迭代的审核节点。

**真正值得抄的**:它的两个协议设计应直接搬进 HC-AIDW 核验节点:
1. **三态 verdict**(confirmed / needs_validation / false_positive)+ 独立 verifier 复核——防 AI 审查的幻觉发现
2. **findings.json 结构化输出**——审核结论必须结构化落盘,才能进可视化界面【推断,机制描述来自官方文档】

**依赖**:支持并行子 agent 的 agent 运行时 + OS 级沙箱(无沙箱则发现降级为 needs_validation)。

**纳入建议**:第一版不装;把"三态 verdict + 独立复核 + JSON 落盘"协议吸收进核验 skill 的设计;安全审计作为发布前可选步骤(第二阶段装)。

---

## 六、DeepSeek Harness

**解决什么问题**:DeepSeek 开源的插件化 agent 运行时(MIT,RC 预览,"everything is a plugin"),角色与 Claude Code 重叠。【已验证官方页存在】

**能否直接复用**:与 Claude Code skills 的兼容靠社区桥接插件(dsh-skills-bridge 等),【文档说明,未经实测】。

**纳入建议**:第一版不纳入(运行时未稳定、桥接未验证)。兼容策略上**不为它写专门代码**:只要 HC-AIDW 的节点是标准 SKILL.md + JSON 产物,桥接成熟后即可跑。第二阶段做冒烟实测。

---

## 七、Hermes Agent(Nous Research)

**解决什么问题**:自改进 agent,内置技能沉淀机制(把成功做法自动固化为技能)——这个机制对 HC-AIDW 有启发:审核节点的经验(什么需求容易误解、什么设计被反复打回)应该结构化沉淀。【已验证官方文档存在】

**兼容性**:SKILL.md 范式与 Claude Code 兼容(支持 external_dirs / .agents/skills)。【文档说明】

**纳入建议**:第一版不纳入运行时;借鉴其"技能自动沉淀"思想,在 v0.1 的回顾环节(参考 mattpocock `retro`)人工沉淀。

---

## 八、跨工具兼容现状(支撑"同一套工作流跑在多个 harness"目标)

【已验证(来源可靠,细节见 research 笔记)】
- **SKILL.md 已成跨厂商事实标准**:27+ agent 支持,含 Codex、GitHub Copilot、Cline(直接读 `.claude/skills/`)
- **AGENTS.md**:24+ 工具支持(Codex、Cursor、Gemini CLI 等);Claude Code 自 v2.1.277(2026-09)原生回退读取(CLAUDE.md 优先)
- **结论**:HC-AIDW 的每个审核节点写成标准 SKILL.md、中间产物统一 JSON schema、项目上下文用单一 AGENTS.md,即可获得跨 harness 能力,无需为每个工具写适配层。DeepSeek Harness 与 Hermes 的实际运行为待冒烟实测项。

---

## 九、汇总决策表

| 候选 | 第一版 | 角色 | 理由 |
|---|---|---|---|
| **Archify** | ✅ 纳入 | 可视化基座(JSON→HTML) | 现成的"后台 JSON、前台 HTML"实现,零依赖单文件产物 |
| **EGM** | ✅ 纳入 | 需求/架构审核引擎 | 盲审+协商+漂移检测,直击前两个审核节点 |
| **mattpocock-skills**(已装) | ✅ 纳入 | 盘问/工单/TDD/双轴审查 | grill-me、to-spec→to-tickets→implement、code-review |
| **Claude Code 内置** | ✅ 已有 | code-review、dataviz、run、security-review | 代码核验与视觉规范 |
| **HumanLayer skills(show-me、grilling、控制环)** | ✅ 纳入 | 界面生成范式 + 需求盘问机制 | show-me 单文件 HTML 范式可直接复用;grilling 有终止条件的盘问 |
| **Cloudflare audit skill** | ⏸ 第二阶段 | 发布前安全审计 | 全量过重;抄其三态 verdict + 独立复核协议 |
| **Cline** | ⏸ 第二阶段 | 异构模型交叉复核备选 | 与内置 code-review 重复 |
| **DeepSeek Harness** | ⏸ 待冒烟 | 目标运行时之一 | RC 预览,桥接未验证;SKILL.md 标准即可兼容 |
| **Hermes** | ⏸ 借鉴思想 | 技能沉淀机制参考 | 运行时不纳入 |
| **jsonschema(Py 包)** | ✅ 建议引入 | 校验审核 JSON 产物 | 结构化审核的守门员,一条 pip 命令(本次按边界未装) |
| **playwright MCP** | ⏸ 视需要 | 渲染验证/交互采集 | 第一版界面可先不采集交互 |
