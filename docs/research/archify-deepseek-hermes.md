# HC-AIDW 工具调研:Archify / DeepSeek Harness / Hermes Agent

- 调研日期:2026-11-06
- 调研目的:为 HC-AIDW(AI 专业实现 + 非技术人员可视化审核)第一版选型,评估三个工具的复用价值、依赖、风险,重点是 **Archify 的逆向可行性**(审核闭环能否成立)。
- 标注约定:【已验证】= 本机文件或官方页面直接核实;【文档说明】= 官方文档/README 描述,未逐一运行验证;【推断】= 基于证据的分析判断,可能出错;【待验证】= 仅社区来源或未见可靠资料。

---

## 1. Archify(重点)

### 1.1 它是什么、解决什么问题【已验证 + 文档说明】

- 官方仓库:https://github.com/tt-a1i/archify ,官网 https://archify.si 。版本 v3.2.0,Apache-2.0(历史版本曾为 MIT)。2026 年 9 月曾登 GitHub Trending 周榜第一,skills.sh 安装量 130K+。【已验证,来自仓库页】
- 定位:一个**开源 AI Agent Skill**(面向 Claude Code、Codex CLI、Cursor、OpenCode、GitHub Copilot 等),把"一段描述 / 一个问题 / 一个代码仓库"变成**单文件交互式 HTML 图表**。核心工作流:自然语言或代码 → **Typed JSON IR(中间表示)** → 校验(schema/布局/HTML/SVG/路线/标签净空五道门禁)→ 原子交付单文件 HTML。【文档说明,README】
- 解决的问题:让 AI 产出的架构图"可信、可核对、可分享"——不是通用绘图工具(官方明确:自动 Mermaid 解析、通用自动布局、托管分享、WYSIWYG 编辑都在范围之外),而是"把技术意图变成沟通产物"。【文档说明】
- 10 种图表类型:architecture、workflow、sequence、dataflow、lifecycle、ERD、class、tree、timeline、waterfall(3.1 新增后五种)。另有"explainer 一页式问答页"和"Architecture Delta"(before/delta/after 对比,带机器回执,用于 PR/设计评审)。【文档说明】
- 与本机样例吻合:本地 `E:\LLM\architecture-showcase\` 各 HTML 的 `<meta name="generator" content="archify 3.2.0">`,与官方 stable 版本号一致。【已验证】

### 1.2 本地产物实证:schema 与渲染方式【已验证】

对 `01-l1-system-overview.architecture.json / .html`、`03a-publish.sequence.json`、`06-erd-public.erd.json`、`09-data-flow.dataflow.json` 的实地分析:

**四种 JSON 的公共字段:**

```json
{
  "schema_version": 1,
  "diagram_type": "architecture | sequence | erd | dataflow | ...",
  "meta": {
    "title": "...",
    "output": "对应 html 文件名",
    "quality_profile": "showcase",
    "viewBox": [w, h],          // sequence/dataflow 有
    "animation": "trace",        // 可选;"static" 则省略
    "locale": "zh-CN" 等         // 官方 settings,本样例未见
  }
}
```

**architecture**:
- `components[]`: `{id, type(external|security|backend|database|cloud…), label, sublabel, pos:[x,y], size:[w,h], tag?}` —— **布局是人工/AI 显式指定的**,非自动布局。
- `connections[]`: `{id, from, to, label, variant(emphasis|dashed), fromSide?, toSide?, labelAt?:[x,y]}`。
- `cards[]`: `{dot(cyan|emerald|rose|amber…), title, items[]}` —— 侧栏说明卡("这张图说明什么 / 现状 / 待验证")。

**sequence**:
- `participants[]`: `{id, type, label, sublabel}`(生命线,从左到右按数组序)。
- `segments[]`: `{from, to, label}`(y 区间分组)。
- `messages[]`: `{from, to, y, label, variant(emphasis|dashed|default|return)}` —— **每条消息的 y 坐标显式给出**。

**erd**:
- `meta.views[]`: `{id, label, focus:[entityId…], note}` —— 多视图聚焦。
- `layout`: `{mode:"grid", gapY, gapX}`。
- `entities[]`: `{id, label, tag, row, col, width, attributes:[{name, type, key(pk|uk|…)}]}`;关系在 entity 之后(本样例实体含完整列定义,README 称含基数 cardinality)。

**dataflow**:
- `stages[]`: `{label}`(泳道阶段)。
- `nodes[]`: `{id, type(frontend|backend|…), label, sublabel, stage, row, width, tag?}`。

**渲染方式【已验证】**:
- 每个图 = **一个 840–900KB 的自包含 HTML**,无外部 JS 库依赖(HTML 内 "d3" 命中全部来自 base64 字体数据,非 D3.js)。内嵌:JetBrains Mono WOFF2 子集字体(带 sha256 注释)、全套查看器 JS(数百个内联函数)、内联 CSS。
- 图形本体是**生成时就渲染好的静态内联 SVG**(viewBox 与 JSON `meta.viewBox` 一致),节点 `id` 与 JSON 的 `id` 一一对应(已验证 `id="users"/"caddy"/"platform"/"postgres"/"minio"` 等存在);边以 `data-edge-from / data-edge-to / data-edge-id / data-edge-label` 属性挂在节点上;卡片文本、`data-graph-role`、`data-detail(context|fine)`、`data-reader-*`(reader 布局契约,`archify-reader-contract="declared-wide-v1"`)等语义属性丰富。
- **关键事实:JSON 源并不内嵌在 HTML 里**(全文无 `schema_version`/`diagram_type` 字样)。HTML 是"已编译产物 + 交互查看器",JSON 是"源文件",二者分离。
- 交互(来自实测 aria-label 与 README【文档说明】):主题/视觉预设切换(classic / signal-flow 等)、明暗主题、缩放(+/-/0)、节点聚焦与上游/下游可达追溯(Upstream/Downstream)、定向路线追踪(R/PATH,journey 播放)、语义镜头对比(L/LENS)、总览雷达(M/MAP)、节点搜索(/)、Presentation Stage(F)、导出 PNG/WebP/JPG、Route/Reach Share Card(1200×630)、`#focus=<id>&reach=upstream` 等稳定 hash 链接、`?embed=1`/`?present=1` 模式、`prefers-reduced-motion` 尊重。README 称之为"truthful interaction"——交互只复用 authored 节点/关系,不发明拓扑。
- index.html(12KB)是用户手写的资料包目录页,非 archify 产物。

### 1.3 完整能力清单【文档说明,来自官方 README/llms.txt】

- CLI(`node archify/bin/archify.mjs`):`doctor`(安装体检)、`demo`、`guide`(按问题推荐图型)、`validate --json`(失败返回稳定规则码 + 证据 + 支持的修复动作,即"修复回执")、`preview`(仅回环 127.0.0.1 的桌面实时预览,失败保留 last-good)、`deliver --json --open`(候选文件过全部门禁后原子替换目标)、`compare`(architecture delta)。
- 源码证据模式:可对仓库某 commit 生成带 `SRC n` 标记的节点,点开为 Git 验证的文件+行号卡("code → diagram");默认产物不带源证据。
- 质量档位:`showcase`(本样例所用)等;`deployment-ownership` profile 缺事实时 fail-closed。
- 多语言:`meta.locale`(en/zh-CN/zh-TW/es/ko/ar 内置),只翻译 UI 文案不动 authored 内容。
- 更新检查:仅 GET 一个固定 stable manifest 提醒,不上报任何数据;`ARCHIFY_UPDATE_CHECK_DISABLED=1` 可彻底关闭网络。无遥测。【文档说明】
- 集成面:Claude Code(`~/.claude/skills/` 或项目 `.claude/skills/`)、Codex、Cursor、OpenCode、GitHub Copilot、Claude.ai(上传 zip)、**Hermes Agent**(社区 skill:`hermes skills install skills-sh/tt-a1i/archify/archify`)、**DeepSeek Harness**(社区插件:`dsh plugin --profile web add @tt-a1i/archify-dsh@1.0.0`)。

### 1.4 Archify 逆向可行性分析(核心问题)

用户关注:正向是 代码 → JSON → HTML,能否反向?
(a) HTML 反推 JSON;(b) HTML+JSON 反推代码;(c) 或重新定位为"审核界面改动 → 写回 JSON → AI 改代码"的闭环。

#### (a) HTML → JSON:【推断】**大部分可恢复,但"直接可行"不成立,定级:AI 辅助可行 / 结构化脚本可恢复约八成**

依据(全部本机已验证):
1. **JSON 未内嵌**,HTML 里没有一份可 parse 的源 JSON。所以不存在"无损提取"。
2. 但 HTML 是确定性编译产物,保留了大量语义锚点:
   - 节点 DOM `id` 与 JSON `id` 完全同名(已验证);
   - `data-edge-from/to/id/label` 完整保存了 connections 的拓扑与标签;
   - SVG 内文本即 `label/sublabel`;`meta.title` 在 `<title>` 与 `#archify-diagram-title`;
   - cards 文本全文存在;`meta.animation`(`data-animation`)、preset(`data-preset`)、`quality_profile`(`data-quality-profile`)、viewBox(SVG)都可读回。
3. **能可靠恢复**:diagram_type、components/participants/entities 的 id+label+sublabel+type(部分)、全部拓扑与标签、cards、动画/主题设置。ERD 的列定义、sequence 的消息 y 序,均在 SVG 文本中可读出。
4. **不能精确恢复或需猜测**:手写 `pos/size/labelAt` 的"作者原始数值"(SVG transform 是渲染后的换算值,可反推但可能有舍入)、`variant`(emphasis/dashed 在视觉 class 里,需映射表)、被校验器规范化过的字段、JSON 中未渲染的字段(如 erd 的 `meta.views[].note` 若未展示、`layout.gapX/gapY`)。variant 与几何属"可映射但非无损"。
5. 结论:**写一个"HTML→JSON 重建器"约可恢复 80–90% 结构**,剩余差异需 AI 对照补齐并经 `archify validate` 校验闭环。但——**这一步通常根本不需要**:JSON 源文件本来就应该和 HTML 一起保存(本机样例就是成对保存的)。逆向 HTML 只在"JSON 丢失、只剩别人发来的 HTML"场景才需要。HC-AIDW 设计上应把 JSON 当一等公民持久化,而不是事后从 HTML 捞。

#### (b) HTML+JSON → 代码:【推断】**不可行(直接生成),定级:不可行 / 仅 AI 辅助做"增量改代码的线索"**

理由:
1. JSON IR 是**描述性视图**,不是功能规格:字段只有 label/sublabel/拓扑/视觉,没有接口签名、数据结构、业务逻辑、行为语义。`POS /api/v1/internal/...` 这样一个边的 label 可以对应几百行实现,信息量差 3–4 个数量级。
2. 本机样例恰好证明这点:03a sequence 里的每条消息都是对**已存在代码**的核实性描述(标注 commit `eeaceb9`、`FOR UPDATE SKIP LOCKED` 等)。图是代码的投影;投影不可逆。
3. 官方 scope 也佐证:archify 的源码证据是单向的(代码→SRC 标记),从不承诺反向。
4. 有价值的残余:JSON 变更(diff)可以作为**改动意图的精确清单**喂给编码 agent,即 (c)。

#### (c) 真正可行的定位:审核闭环 JSON→代码(与用户猜测一致)【推断,HC-AIDW 最应采纳】

闭环链条:
```
AI 生成 代码 + architecture/sequence JSON → archify 渲染 HTML
→ 非技术人员在 HTML(或轻量编辑层)上提审核意见
→ 意见落为 JSON 变更(新增/删除节点、改连接、改 cards 批注)
→ AI 读取 JSON diff(而非 HTML),把每处结构变更翻译成代码任务
→ 重新生成代码与 JSON,再次渲染,新一轮审核
```
可行性要点:
- **改 JSON 写回:AI 辅助可行。** 非技术人员不太会手编 JSON,合理形态是:HTML 里已具备丰富的语义锚点(id/data-edge-*),可做一个极薄的"审核壳"页面(iframe 原 HTML + 侧栏表单),把"加一个节点/连线/批注"翻译成 JSON patch;或者干脆用对话:"把审批流加到图里" → agent 改 JSON → `validate` → 重渲染。后者零开发成本,今天就能用。
- **JSON diff → 代码意图:AI 辅助可行且这正是 agent 擅长的**——JSON 是 typed、经校验的、稳定的中间表示,diff 明确到"哪个节点/哪条边",比"看截图改代码"可靠得多。配合 archify 的 Architecture Delta(compare 命令)可自动产出变更回执。
- **瓶颈不在工具,在语义**:非技术人员的视觉拖拽改动(挪位置)对代码无意义(布局本来就是作者表达的一部分),真正驱动代码的是拓扑/卡片/批注的语义变更;壳层设计时应把"布局微调"与"结构意见"分开。

#### 逆向可行性分级汇总

| 方向 | 定级 | 关键理由 |
| --- | --- | --- |
| HTML → 恢复 JSON | **需人工/AI 辅助可行**(脚本可恢复 80–90%) | JSON 不内嵌,但 id/data-edge-*/文本锚点完整;恢复后可过 validate 闭环;正常流程根本不需要(应成对保存 JSON) |
| HTML(+JSON)→ 代码 | **不可行**(直接);仅可作 AI 改码线索 | IR 是描述性投影,无接口/逻辑/行为信息;信息量差数量级 |
| 审核改动 → JSON patch → AI 改码 | **AI 辅助可行(推荐路线)** | JSON 是 typed 中间表示,diff 即意图清单;对话式改图零成本,表单壳层低成本 |

### 1.5 HC-AIDW 纳入评估

- **解决什么问题**:非技术人员可交互审核的架构/流程/ERD 可视化;带校验的图表中间表示;Architecture Delta 可做"评审前后对比"——与 HC-AIDW"可视化成果参与审核"高度同构。
- **与现有能力重复度**:低。本项目(agentic-class-pilot)当前没有等价物;index.html 是手写静态页,无交互无校验。Mermaid 类方案(若有考虑)交互性与校验远弱。
- **复用方式**:直接安装为 Claude Code skill(官方支持),`npx -y skills@latest add https://archify.si --skill archify --agent claude-code` 到 `~/.claude/skills/` 或项目级;产出与现有 `architecture-showcase` 完全同构,零迁移。
- **依赖**:Node ≥18(CLI 校验/渲染);查看器零依赖;无网络要求(可关更新检查)。与现有栈(FastAPI/Next.js)无冲突,产物可直接被 Caddy/前端托管。
- **权限/风险**:低。本地产物,无遥测(官方声明+可禁网验证);安装器行为有明确契约(llms.txt 要求 agent 安装前确认 scope、不越权)。风险点:① 第三方"archify 收费服务"冒名(官方 README 明确撇清,注意只认 github.com/tt-a1i/archify 与 archify.si);② skill 内容会随更新变化,锁定版本更稳;③ WYSIWYG 编辑不在 scope,审核壳层需要自研(或用对话式)。
- **结论:值得纳入 HC-AIDW 第一版(强烈推荐)。** 它实际上可以承担 HC-AIDW 中"需求/架构可视审核"这一环的整套底座;逆向闭环按 1.4(c) 路线设计:JSON 为一等公民 + 对话式/表单式审核意见 → JSON patch → AI 改码。

---

## 2. DeepSeek Harness

### 2.1 它是什么【已验证,官方页 https://www.deepseek.com/en/harness】

- DeepSeek 官方的**开源 AI agent 运行时(harness)**,公开预览、MIT、`github.com/deepseek-ai/deepseek-harness`;桌面应用(Windows/macOS)或 `npx @deepseek-ai/dsh web` 起 Web UI。架构口号"Everything is a plugin",自述基于 "Cordis" 的插件架构(官方页链接了一篇 Cordis paper)。
- 能力面:日常文档/表格/PPT、编码(读仓库、修 bug、跑测试)、研究、后台任务、**插件体系**(官方插件含 Agent teams、Auto approval review、Scheduled tasks、Voice input、Terminal、Agent loop、Subagents 等,部分标注 Experimental);"Creator mode" 里通过对话现场写插件;执行轨迹(trajectory)查看器可逐 turn 检查工具调用。
- 使用的模型是 DeepSeek 系(页面示例为 DeepSeek-V4x Flash),运行时与模型可分离。【推断】

### 2.2 Skills / 工作流能力与 Claude Code 兼容性

- 插件 vs 技能的分工(社区口径):plugin 决定 agent"能碰到什么",skill 决定"怎么做事"。【文档说明,第三方(Zentor/MindStudio/DataCamp),非官方文档,采纳需谨慎】
- **Claude Code skills 兼容性:基本兼容,路径为社区桥接/通用格式**:
  - Archify 官方为 DSH 打了专门插件包 `@tt-a1i/archify-dsh`(非直接复用 SKILL.md),Node 引擎要求 `^22.19.0 || >=24`,声明"非 DeepSeek 官方产品、无遥测"。【已验证,archify README】
  - 社区存在 `dsh-skills-bridge`(把 Claude Code 的 SKILL.md 挂为 DSH SkillProvider,frontmatter 归一化)与 `dsh-plugin-claude-bridge`(读 Claude Code 标准目录,零迁移)。【待验证,仅社区来源(GitHub Discussion #5213、open-design.ai),未核实可用性与维护状态】
  - Upstash Skills 等仓库已发布"同一份 skill 同时适配 Claude Code/Codex/Cursor/DSH"的通用格式。【文档说明】
- 依赖:Node;`@deepseek-ai/dsh@0.1.2-rc.1`(developer preview,官方页与 archify 对 DSH 的描述都标注 preview/API 可能变)。
- 权限风险:中。DSH 是完整 agent 运行时(终端、文件、调度),接入即赋予其本机执行能力;官方页有 Auto approval review 插件说明审批面尚在演进;deepseek-ai 组织源码可审,MIT。
- **HC-AIDW 结论:第一版不建议纳入。** 与 Claude Code 角色完全重叠(同为 agent 运行时),迁移无增益;其价值在于"DeepSeek 模型 + 开源可自审 + 插件市场"这条备选路线,以及 archify 官方已证明"一份 skill 可多 harness 分发"的模式。可观察其 RC 稳定后再评估作为学生端/教师端 agent 的第二运行时。注意:网上大量第三方"教程/对比"内容( Udemy/DataCamp blog/Medium/Reddit)质量参差,采信前应以官方页与仓库为准。

---

## 3. Hermes Agent

### 3.1 它是什么【已验证,官方文档 https://hermes-agent.nousresearch.com/docs】

- **Nous Research 的 Hermes Agent**:自述"self-improving AI agent",带学习闭环——从经验中自动沉淀技能(skill)、在使用中改进。形态包括 CLI、Desktop、TUI、dashboard,以及 Telegram/Discord/Slack 等消息网关,支持 cron/定时任务、24/7 常驻。
- 与"AI 编程代理 + skills"主题匹配度高(用户提示中担心的同名歧义基本解除:官方文档明确是带 Skills 系统的 agent;Reddit r/hermesagent 讨论的也是它)。候选混淆项:一些通用同名产品(如搜索中出现过的"memory/skills/recurring workflows"营销文与 DeepSeek 对比帖),不影响判断。【已验证为主】

### 3.2 Skills 机制细节【已验证,官方 skills 文档】

- SKILL.md + `references/ templates/ scripts/ assets/ examples/` 目录结构,**声称兼容 agentskills.io 开放标准**;技能目录 `~/.hermes/skills/`;**支持外部技能目录 `external_dirs` 与项目级技能(`.hermes/skills/`、跨工具约定 `.agents/skills/`)——即能直接读 Claude Code/Codex 生态的技能目录**;预置信任 tap 里明确包含 `anthropics/skills`、`openai/skills` 等。
- 渐进披露三级加载(skills_list ≈3k token → skill_view → 引用文件),slash 命令 `/skill-name`、最多 5 个技能链式堆叠、skill bundles(YAML 组合命令)、`/learn`(把文档/对话流程蒸馏成技能)、agent 自建技能(`skill_manage`,即"程序性记忆",带 write_approval 审批门与 linter)、技能安装安全扫描(quarantine、NVIDIA SkillEvaluator/SkillSpector 可选二扫)、平台过滤(platforms)、条件激活(fallback/requires toolsets)、项目技能 trust 机制。
- 兼容性判断:**与 Claude Code 的 skills 机制高度兼容(同一 SKILL.md 范式)**,官方还内置把 anthropics/skills 当可信源;差异在周边(审批门、bundles、hub 生态、自改进 curator)。【文档说明】
- 权限风险:中偏高。agent 可改/删任何技能(可开审批门、可锁技能)、可装第三方 hub 技能(有扫描但 community 源可 `--force` 绕非 dangerous 阻断)、常驻+cron+消息网关意味着攻击面大;Nous 开源可自审。HC-AIDW 若引入,应关闭自动写技能/收紧信任源。
- **HC-AIDW 结论:第一版不纳入,列为第二阶段候选。** 其"agent 从经验中自动沉淀可复用技能"的机制与 HC-AIDW"需求→设计→实现"流程沉淀高度契合,且 SKILL.md 兼容意味着 HC-AIDW 的技能资产在两边通用;但引入一个常驻自改进 agent 对第一版是纯增量风险。可先借它的机制设计(审批门、技能蒸馏、渐进披露)反哺 Claude Code 侧的工作流设计,运行时后议。

---

## 4. 汇总决策表

| 工具 | 解决的问题 | 直接复用? | 与现有重复度 | 关键依赖 | 权限/风险 | 第一版建议 |
| --- | --- | --- | --- | --- | --- | --- |
| Archify v3.2.0 | 架构/流程/ERD 的可信交互可视化 + typed JSON IR + delta 对比 | 是,装成 Claude Code skill 即用 | 低 | Node ≥18,无网络 | 低(无遥测可禁网;防第三方冒名站) | **纳入(核心可视化底座)** |
| DeepSeek Harness | 开源插件化 agent 运行时(DeepSeek 系) | 部分(需桥接插件跑 CC skills) | 高(与 Claude Code 同角色) | Node 22/24,DSH 尚 RC | 中(完整本机执行权,预览期) | 不纳入,观察 |
| Hermes Agent | 自改进 agent,技能自动沉淀 + 多网关常驻 | 技能格式兼容 CC | 中(技能机制可互通) | Python/Node 生态、hermes CLI | 中偏高(自写技能+cron+网关) | 不纳入,机制借鉴 |

## 5. 对 HC-AIDW 第一版的具体落地建议

1. 安装 archify 为项目级 skill,把现有 `architecture-showcase` 的产物规范(成对保存 JSON+HTML、`schema_version:1` 四类图型)固化为 HC-AIDW 的"架构审核工件"标准。【已验证可行】
2. 审核闭环采用 1.4(c) 路线:**JSON 为唯一事实源**;第一版用"对话式改图"(零开发),第二版再做 iframe 审核壳(表单→JSON patch→validate→重渲染→AI diff 改码)。
3. 用 `archify compare`(Architecture Delta)作为非技术人员评审的变更回执,接入 HC-AIDW 的评审记录。
4. 明确不做:从 HTML 反推代码;把 archify 当通用绘图/编辑器。

## 主要来源

- 本机实证:`E:\LLM\architecture-showcase\`(01/03a/06/09 四类 JSON + HTML)
- Archify:https://github.com/tt-a1i/archify 、https://archify.si 、https://raw.githubusercontent.com/tt-a1i/archify/main/llms.txt
- DeepSeek Harness:https://www.deepseek.com/en/harness (官方);社区线索:GitHub Discussion #5213 (dsh-skills-bridge)、open-design.ai (dsh-plugin-claude-bridge)、upstash.com/blog、zentor.ai、datacamp.com 对比文【均待验证】
- Hermes Agent:https://hermes-agent.nousresearch.com/docs 及 /docs/user-guide/features/skills 、/docs/reference/skills-catalog
