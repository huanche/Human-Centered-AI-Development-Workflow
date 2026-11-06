# HC-AIDW 工具调研笔记:Cline 代码审查 / Cloudflare Security Audit Skill / 跨工具兼容性

- 调研日期:2026-11-06
- 调研人:HC-AIDW 调研(Claude 代理)
- 标注约定:
  - **已验证** = 本次调研直接抓取了 GitHub 仓库 / 官方文档页面并逐条核对
  - **文档说明** = 来自官方文档的转述性内容,未在本地实际运行验证
  - **推断** = 基于公开信息的分析判断,需后续实测确认

---

## 1. Cline 的代码审查能力

仓库:https://github.com/cline/cline(Apache 2.0)
文档:https://docs.cline.bot

### 1.1 解决什么问题

Cline 是一个开源 AI 编程代理,现在以四种形态存在:**SDK(Node.js)、CLI(含 headless 模式)、VS Code 扩展、JetBrains 插件、桌面应用**。(已验证,来自 README)

它的"审查"能力不是一个独立的 code-review 产品,而是分散在几处机制里:

1. **Diff 审查面板**:在 VS Code / JetBrains 中,每次文件编辑以 diff 形式呈现,用户可逐条 review / 修改 / revert。(已验证,README)
2. **Checkpoints 机制**(docs.cline.bot/features/checkpoints,已验证):
   - 每次工具调用(文件编辑、命令)后自动创建 workspace 快照;
   - 实现方式是 **shadow Git repository**(影子 git 仓库),不干扰用户自己的 git;
   - 提供 Compare / Restore 按钮,三种恢复粒度:恢复任务+工作区 / 仅任务 / 仅工作区;
   - 存储在 VS Code globalStorage;大仓库有额外存储开销,可关闭。
   - **定位**:checkpoints 是"回滚安全网",不是审查工具——它不产出任何审查结论,只保证可撤销。
3. **Headless CLI 可做流水线审查**(README,已验证):官方示例 `git diff origin/main | cline "Review these changes for issues"`,输出 JSON 事件流,可 jq 过滤,面向 CI/CD。
4. **Plan/Act 模式 + 每步人工审批**:审批粒度是"每个编辑/每条命令",属于操作级 human-in-the-loop,不是阶段级的成果审核。

### 1.2 能否作为独立审查工具嵌入别的工作流

- **可以,但有条件**。两条路径:
  - **CLI headless**:`git diff ... | cline "Review ..." --json`,可被 HC-AIDW 的后端以子进程方式调用,模型可换(Anthropic/OpenAI/OpenRouter/Ollama 等任意 OpenAI 兼容端点)。(已验证)
  - **SDK**:`@cline/sdk` 提供 `new Agent({tools})`,可编程注册工具和生命周期钩子(README 明确提到钩子可用于 "logging, auditing, policy enforcement")。(已验证)
- 不再"只能活在 IDE 插件里"——README 当前定位就是 "as an SDK, IDE extension, or CLI assistant"。(已验证)
- 但注意:**JetBrains 插件未开源**(README 明示)。(已验证)

### 1.3 有没有官方或社区的 Cline review skill / 评测

- **官方**:Cline 官方没有发布一个名为 "code-review" 的第一方 skill;官方文档把 code review 列为 skill 的适用场景示例("Your team's specific review checklist")。(已验证,docs.cline.bot/features/skills)
- **社区**:agensi.io 的 Cline Marketplace 上有约 157 个社区 code-review skill(第三方聚合站,质量参差)。(文档说明,来自搜索结果)
- **评测**:针对 Cline 本身的 code-review 质量的权威 benchmark 未找到;存在通用 code-review 基准(GitHub ReviewBench、Martian Code Review Bench、arXiv c-CRAB)和一篇 Reddit 上"5 个 review skill 实测"帖,但都不是 Cline 官方评测。(文档说明/推断)

### 1.4 Skills 体系与格式

Cline 的 skill = 目录 + `SKILL.md`(YAML frontmatter:name + description),按需渐进加载。(已验证,docs.cline.bot/features/skills)

关键兼容点:**Cline 明确支持直接读取 `.claude/skills/` 目录,标注为 "for Claude Code compatibility"**。(已验证)也就是说 Anthropic 的 SKILL.md 格式 skill 可以零改动放进 Cline。

### 1.5 与 Claude Code 自带 code-review 的重复度

重复度**高**。Claude Code 内置 `/code-review`(diff 审查、分级 effort、PR 评论)、`/security-review`;Cline 的 headless review 本质上也是"把 diff 喂给模型 + 通用 review 提示词",两者产出物同质。Cline 多出来的只有:shadow-git checkpoints(可回滚)、多模型自由、SDK 编排。对 HC-AIDW 的"代码生成结果核验"节点而言:

- **审查逻辑本身**:复用 Cline 与复用 Claude Code 基本等价,没有独有价值。
- **checkpoints**:HC-AIDW 自己管 git worktree/分支即可,shadow git 是插件内部机制,不产出可交付的审核材料。
- **多模型**:若 HC-AIDW 要求"同一工作流兼容 Codex/Claude Code/DeepSeek/Hermes",Cline 的价值在于它本身支持任意 OpenAI 兼容端点——但这个目标更适合用 AGENTS.md/SKILL.md 标准路线实现(见第 3 节),而不是引入整个 Cline 运行时。

### 1.6 依赖与权限风险

- 依赖:Node.js 运行时;所选 LLM 的 API key(Cline 会把代码上下文发给所选模型商)。(已验证/文档说明)
- 权限风险:默认每步人工审批,可开 auto-approve——一旦开启,agent 可执行任意 bash 命令、读写任意文件,权限面等同 Claude Code。headless 模式下无人审批,需要外部沙箱约束。(文档说明/推断)

### 1.7 结论:是否纳入 HC-AIDW 第一版

**不建议纳入。** 理由:与 Claude Code 自带 code-review + /security-review 功能高度重叠;引入第二个 agent 运行时会带来双份配置、双份审批流、双份 token 成本,却换不来审查质量的独立提升。若第一版后期需要"用另一个厂商的模型做交叉复核"(不同模型家族互审以降低同源盲区),Cline headless 是届时成本最低的接入方式之一——记为第二阶段备选。**[推断]**

---

## 2. Cloudflare Security Audit Skill

仓库:https://github.com/cloudflare/security-audit-skill(MIT License,约 2.1 万–2.6 万 star,2026 年末热榜项目)
性质:官方仓库已确认,名字就叫 `security-audit-skill`(不是 agentskills 下;Cloudflare 另有 https://github.com/cloudflare/skills 是 Workers 开发类 skill 集合)。(已验证)

### 2.1 解决什么问题

把通用编码 agent 变成安全审计员:对一个**已授权**的代码库做多阶段漏洞审计。它是 Cloudflare 内部 fleet 级漏洞发现 harness("Build your own vulnerability harness" 博文所述系统)的单仓种子版本。(已验证,README)

### 2.2 工作方式:AI 审查为主,零依赖脚本做结构校验(不是静态扫描器)

六个阶段(README 原文,已验证):

1. **Reconnaissance**:梳理架构、信任边界、输入面,产出 `architecture.md` 和 `coverage-ledger.json`;
2. **Coverage-led hunting**:从 ledger 单元派发相互隔离的 hunter 子 agent,记录每项检查,coverage critic 找盲区;
3. **Candidate validation**:每个候选发现交给一个"全新的 verifier agent"专门试图推翻它;
4. **Structured output**:写 `findings.json`(分 `confirmed` / `needs_validation` / `rejected` 三种 verdict),用 `validate-findings.cjs` 对照 `report-schema.json` 校验;
5. **Independent record verification**:再派全新 agent 核验最终记录;重要结论被替换后追加二次独立核验;
6. **Reporting**:产出 `REPORT.md`、`FINDINGS-DETAIL.md`、`NEEDS-VALIDATION.md`。

要点:
- **纯 AI 多 agent 审查 + Node 校验脚本**;校验脚本只是 JSON Schema 级的格式检查,**不是** Semgrep/CodeQL 式静态扫描。所有漏洞发现都来自模型推理。(已验证,由 README 的文件清单和阶段描述得出)
- **对抗式验证**是核心设计:"发现者和验证者永远不是同一个 agent",只在 verifier 试过且没能推翻时才记 confirmed。(已验证)
- **多种子运行可加性**:单次运行大约只能找到重复运行总量的约一半漏洞(README 原文)。(已验证)

### 2.3 审计类别(ATTACK-CLASSES 体系,README 文件清单,已验证)

覆盖面远超"注入+鉴权+secrets"三件套,按目标类型分 12 个 hunting 文件:

- 核心/通配攻击类(ATTACK-CLASSES.md)
- AI/LLM:**prompt-injection、agent/tool 滥用、output handling**(AI-AND-LLM.md)
- Web 协议与鉴权:HTTP 请求走私、缓存、认证协议(WEB-PROTOCOL-AND-AUTH.md)
- 客户端:DOM 注入、消息信任、UI 伪装、原型污染(CLIENT-SIDE.md)
- 供应链与发布:依赖、CI、签名、更新、插件(SUPPLY-CHAIN-AND-RELEASE.md)
- 云与部署:IAM、IaC、容器、serverless、运行时配置(CLOUD-AND-DEPLOYMENT.md)
- 协议/RPC/消息、资源耗尽、租户隔离/数据生命周期、桌面与移动/本地 IPC、内存安全/二进制/内核

secrets 硬编码扫描没有单独列为文件,但按"通配类+云部署类"的组织方式应能覆盖,属**推断**。

### 2.4 产出物

`REPORT.md`(报告)、`FINDINGS-DETAIL.md`(细节)、`NEEDS-VALIDATION.md`(待验证项)、`findings.json`(机器可读,schema 校验过)、`coverage-ledger.json`(覆盖账本,多次运行可增续)。默认输出到 `~/security-audit-skill/<repo>/run-<N>`,除非显式指定 gitignore 的目录,否则不写进目标仓库。(已验证)

### 2.5 依赖

- 一个支持工具调用 + **并行子 agent** 的编码 agent(README 原文;Claude Code 是目标平台);
- Node.js(仅用于两个零依赖校验脚本);
- **OS 级沙箱**:跑目标代码构建/测试/浏览器/模糊测试时必须有沙箱(断外网、白名单环境、资源限制、只许写指定 scratch 路径)。没有沙箱时,工作流会把相关发现降级为 `needs_validation` 而不执行目标代码。(已验证)

### 2.6 权限风险

- 安装即向 agent 注入大量指令(十几个 markdown 文件的全套审计流程),会显著消耗上下文并驱动 agent 大量创建子 agent——token 成本远高于普通 skill。**[推断,基于流程规模]**
- skill 内含可执行脚本(validate-*.cjs)且要求 agent 运行目标仓库的构建/测试,等于授权 agent 执行第三方仓库代码——**必须配合沙箱**;无沙箱环境的功能完整性会打折(部分发现永远停在 needs_validation)。(已验证,README Requirements)
- skill 本身 MIT 开源、内容为 markdown 指令,可人工审阅后再装;从"安装第三方 skill 即给 agent 下达行为指令"的一般风险看,Cloudflare 官方仓库可信度较高,但仍建议钉住 commit。**[推断]**
- 触发词较宽泛("find vulnerabilities"、"security review" 等),日常对话可能误触发全量审计。(文档说明,README trigger 说明)

### 2.7 与现有能力重复度 / 是否纳入第一版

- 与 Claude Code 内置 `/security-review` 有重叠:后者是轻量的"当前分支待提交改动"安全审查;security-audit-skill 是**全库、多 agent、带覆盖账本和独立复核**的深度审计。定位不同,重叠但不替代。
- 对 HC-AIDW:它审计的是"代码库的安全性",而第一版"代码生成结果核验"节点主要核验"生成结果是否符合需求/方案 + 基本质量"。全量六阶段审计对单次代码生成核验**过重**(多次子 agent、需要沙箱、单次仅覆盖一半漏洞)。
- **结论:第一版不默认纳入全流程;可作为可选的"发布前深度安全审计"步骤**(例如架构节点把安全要求写进方案、代码节点完成后、对外发布前跑一次),而且它的 `findings.json` schema + confirmed/needs_validation/rejected 三态 verdict + "独立复核后才算数"的设计**非常值得 HC-AIDW 直接抄进自己的审核节点协议**(非技术人员的可视化审核正好需要这种带置信分级的结构化结论)。**[推断]**
- 跨工具:README 未绑定 Claude Code,要求只是"支持工具调用与并行子 agent 的编码 agent",安装用 `npx skills add`(通用 skills CLI)。理论上 Codex 等也装载,但 Cloudflare 只在 Claude Code 上验证过,其他 harness 需实测。**[文档说明+推断]**

---

## 3. 跨工具兼容性速览(AGENTS.md 与 SKILL.md)

HC-AIDW 目标:同一套工作流兼容 Codex、Claude Code、DeepSeek Harness、Hermes。

### 3.1 AGENTS.md(agents.md)

- 定位:"agent 的 README",放项目级指令(构建、测试、约定),纯 markdown 无 schema。(已验证,agents.md 官网描述)
- 采纳情况:60000+ 开源项目使用;工具侧包括 **OpenAI Codex、Cursor、Gemini CLI、Zed、Devin、Jules** 等约 24+ 工具。(文档说明,agents.md + 搜索汇总)
- **Claude Code 自 2026-09-18 起原生读取 AGENTS.md(v2.1.277)**,但为**回退机制**:项目里同时有 CLAUDE.md 时 AGENTS.md 被忽略,可在 `/config` 开关。(文档说明,dev.to / HN,未本地实测)
- **Cline**:原生体系是 `.clinerules`;AGENTS.md 支持是逐步加上的(2025 年 issue #5033 → 官方文档已称可从 `~/.agents/` 读全局跨工具指令),项目级自动发现曾被 issue #7062 报告有缺口。用前需实测当前版本行为。(文档说明)
- DeepSeek Harness / Hermes(小众 harness):未查到明确支持声明,**推断**多数新 harness 为了生态会读 AGENTS.md,需逐个确认。

### 3.2 SKILL.md / Agent Skills(agentskills.io)

- Anthropic 开源的 skill 格式(目录 + SKILL.md,YAML frontmatter name/description),现已成为跨厂商开放标准:**27+ agent 支持,含 Claude Code、GitHub Copilot、OpenAI Codex、Gemini CLI、Cursor、Windsurf、Goose、Cline**;Codex 甚至有 `$skill-installer` 可直接装 Claude 系 skill。(文档说明,搜索汇总;Cline 支持部分已验证)
- Claude Code 也在向标准化的 `.agents/skills` 目录收敛(社区文章,文档说明)。
- **HC-AIDW 的可行路线:审核节点写成标准 SKILL.md skill,放 `.agents/skills/`(或每 harness 的等效目录各放一份软链/副本),项目级约定用 AGENTS.md**。这样 Claude Code 与 Codex 大概率零改动兼容,Cline 靠 `.claude/skills/` 兼容目录也能吃同一份文件。`.claude/` 下的 hooks、subagent 定义等仍是 Anthropic 专有,跨工具时只能退化为纯提示词指令。(已验证 Cline 部分;其余文档说明/推断)

### 3.3 对第一版的建议 **[推断]**

1. 三个审核节点的"审核提示词 + 输出 schema"写成标准 SKILL.md,输出统一为 JSON(参考 Cloudflare skill 的 findings.json 三态 verdict 思路);
2. 项目级上下文用单一 AGENTS.md(Claude Code 用户注意其 CLAUDE.md 优先,必要时 CLAUDE.md 只写一行指向 AGENTS.md 或同步维护);
3. 不为兼容性引入 Cline 运行时;DeepSeek Harness / Hermes 需各做一次"能否读 AGENTS.md 与 SKILL.md"的冒烟测试后再定。

---

## 来源

- https://github.com/cline/cline(README,已抓取)
- https://docs.cline.bot/features/checkpoints(已抓取)
- https://docs.cline.bot/features/skills(已抓取)
- https://github.com/cloudflare/security-audit-skill(README,已抓取)
- https://github.com/cloudflare/skills(搜索结果)
- https://agents.md 、https://agentskills.io/home(搜索结果)
- Claude Code 原生支持 AGENTS.md:https://dev.to/valyuai/claude-code-now-supports-agentsmd-natively-heres-how-it-actually-works-5nl 、https://news.ycombinator.com/item?id=49760187
- Cline AGENTS.md 支持:https://github.com/cline/cline/issues/5033 、https://github.com/cline/cline/issues/7062 、https://docs.cline.bot/customization/cline-rules
- 通用 review 基准:https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review 、https://codereview.withmartian.com
- 社区 skill 实测:https://tessl.io/blog/best-agent-skills-for-ai-code-review-8-evaluated-skills-for-dev-workflows
