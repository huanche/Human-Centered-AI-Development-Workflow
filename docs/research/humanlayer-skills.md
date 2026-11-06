# HumanLayer skills 仓库调研笔记(HC-AIDW 工具调研)

- 调研日期: 2026-11-06
- 主仓库: https://github.com/humanlayer/skills (MIT, ~4.2k stars, 12 commits)
- 对比仓库: https://github.com/mattpocock/skills (Matt Pocock 的 skills)
- 工具: mcp__web_reader__webReader(GitHub 页面 / api.github.com 文件树 / raw.githubusercontent.com 原文均抓取成功)

## 0. 可靠性标注

- 【已验证】= 本次实际抓取到原文
- 【推断】= 基于旁证或公开常识推断,未抓到原文

---

## 1. humanlayer/skills 仓库结构与定位 【已验证】

定位: HumanLayer 出品的 Claude Code skills 集合,以 plugin marketplace 形式发布,安装 `npx skills add humanlayer/skills --skill SKILLNAME`。

文件树(api.github.com git tree 递归枚举):

```
.claude-plugin/marketplace.json   # 声明 6 个 plugin
plugins/
  improve-claude-md/              # 用 <important-if> 块重写 CLAUDE.md
  narrow-react-prop-types/        # 收窄 React prop 类型
  build-iterated-agentic-loop/    # 生成 repo 内 skill + 定时 coding-agent GitHub Actions
  design-control-loop/            # 面谈设计"控制回路"式 agent 自动化
  show-me/                        # 可视化解释当前话题
```

结构统一: `plugins/<name>/.claude-plugin/plugin.json` + `plugins/<name>/skills/<name>/SKILL.md` + 可选 `references/`。

异常点【已验证】: marketplace.json 声明了第 6 个 plugin `visual-pr`(给 PR 生成 reviewer 可视化大纲),但文件树中无对应目录——清单与文件不同步。

### 与任务预期的关键差异

1. **grill-me 不在 humanlayer/skills 里** 【已验证:文件树完整枚举无此路径】。它是 **Matt Pocock** 的 skill,托管在 mattpocock/skills(见 §3,原文已抓取)。
2. **RPI 不是该仓库的 skill** 【已验证:无同名目录/文件】。RPI(Research-Plan-Implement)是 HumanLayer 的**工作流方法论**,出自 Dex Horthy 的博客 "Advanced Context Engineering for Coding Agents"(2025-08-29,humanlayer.dev/blog 列表页已验证存在该文);仓库内 build-iterated-agentic-loop / design-control-loop 是其思想的产品化落地(见 §4/§5)。
3. humanlayer 博客列表【已验证】还有相关文章: "show-me: a coding agent skill for compact visual representations"(Dex, 2026-08-12)、"Getting Claude to Actually Read Your CLAUDE.md"、"Skill Issue: Harness Engineering for Coding Agents"、"Context Forking"、"Long-Context Isn't the Answer"、"Context-Efficient Backpressure"。show-me 博文原文本次抓取失败(500),结论以 SKILL.md 为准。

---

## 2. show-me 【已验证,SKILL.md 全文已抓取】

路径: `plugins/show-me/skills/show-me/SKILL.md`(单文件,无 references/,v1.0.1)
frontmatter: `name: show-me`,description "Help the user understand the current topic visually with concise diagrams, code-shape sketches, and focused HTML artifacts."

### 解决什么问题
让 agent 用**视觉形式而非散文**解释当前话题。三条硬约束: skip preamble / prose 要短 / **"Pick the smallest view that makes the key point clear"**。结尾明确 "unlikely you will use all of them"——防堆砌。

### 内部机制: 一份"视图选型菜单"(每条 = 场景 + 内嵌 few-shot 示例)

| 场景 | 视图 |
|---|---|
| 逻辑/算法 | 伪代码块(带缓存的 on(save) 示例) |
| 运行时控制流 | 缩进文本调用树(submitForm→createSession→...) |
| UI 结构 | 组件树,标注状态与模块边界,标注源文件路径 `(apps/example/src/routes/session.tsx)` |
| 文件职责/大重构 | 浅层文件树 + 行尾注释 `# parses user actions` |
| 组件交互/控制流/数据流 | **Mermaid**(示例 sequenceDiagram) |
| "变化点" | **diff,且 diff 形状匹配话题形状**(skill 给出 4 种模板: 组件变化 / 文件布局 / 调用树 / 状态控制流) |
| 大半全新、需可复制目标形状 | 全量代码块 |
| 视觉 UI、布局、状态对比、Mermaid 装不下的密集概念 | **单个聚焦 HTML 文件** |

### HTML 产物实现细节(HC-AIDW 审核界面最有价值部分,SKILL.md 原文要点)

- **单文件** `show-me-{description}.html`,一个话题一个文件,不是站点/多页;
- 形态三选一: **diagram / infographic / short slide deck**;
- **"Match the product's colors, type, spacing, and components"** —— 贴宿主产品设计 token;
- **"use real labels and data"** —— 真实标签与数据,禁止占位内容;
- **"support desktop and mobile"** —— 响应式;
- 生成后 `Bash(open path/to/show-me-{description}.html)` 直接打开浏览器预览;
- 不指定图表库/框架: HTML 分支恰恰用于"too dense for Mermaid"的场景,实现手段留给模型(裸 HTML/CSS/JS 或内联库均可),约束在格式与内容质量层面。

### 依赖与权限风险
依赖仅 Claude Code 内置(Write + Bash open),无 MCP/外部 API。风险低: 写文件 + 打开浏览器;未禁止 HTML 内引外链 CDN 脚本,受控环境打开时注意【推断】。

---

## 3. grill-me(Matt Pocock 版)与 humanlayer 侧的"盘问"能力对比

### 3.1 Matt Pocock 的 grill-me【已验证,原文已抓取】

托管: mattpocock/skills("Skills for Real Engineers",支持 Claude Code/Codex/Copilot/Gemini 等,分 engineering 与 productivity 两组;user-invoked 只能用户斜杠调用,model-invoked 可被模型自动触发)。

**grill-me**(skills/productivity/grill-me/SKILL.md)原文全文极短:

```
---
name: grill-me
description: A relentless interview to sharpen a plan or design.
disable-model-invocation: true
---
Call the Skill tool with "grilling".
```

即 grill-me 只是个**斜杠入口壳**,真正机制在 model-invoked skill **grilling**(skills/productivity/grilling/SKILL.md)【已验证】:

- 把待澄清事项建模为**设计树(design tree)**: 每个决策分支出子决策;
- 按**轮次(rounds)**工作,每轮问**当前 frontier**(前提已确定、现在就能问的全部问题)——一轮内把整个 frontier 一次问完,编号 + **每题给推荐答案**,措辞让"yes"即接受推荐;等用户答完再算下一轮 frontier;
- **事实自己查,决策问用户**: 需要环境事实(文件系统/工具)时派 fresh-context sub-agent 去查,不问用户;查询未返回时只让下游问题等待,其余照常问;
- **终止条件**: frontier 为空——设计树每个分支都访问过,没有沉默假设;用户确认达成共识前**不得动手**;
- 衍生: **grill-with-docs** = 同时调 grilling + domain-modeling(边盘问边更新 GLOSSARY.md 与 ADR)【已验证其 SKILL.md 同样是一行壳】;repo README 称 grill-me/grill-with-docs 是其最受欢迎的 skill,定位是解决"agent 没做我想要的"这一头号失败模式(对齐沟通鸿沟)。

### 3.2 humanlayer/skills 里对应的"盘问"能力【已验证,全文已抓取】

humanlayer 侧没有 grill-me,但 **design-control-loop** 就是一个结构化面谈 skill(见 §5),其 Phase B 明确写着 "This is an interview",且配套 **control-loop-taxonomy.md** 给出 9 条设计问句。

### 3.3 逐点对比(两侧 SKILL.md 均已验证)

| 维度 | Matt Pocock grilling/grill-me | HumanLayer design-control-loop |
|---|---|---|
| 目标 | 把用户的计划/设计盘问到无沉默假设,不改代码 | 面谈后**设计并构建**可运行的 agent 自动化回路 |
| 问题组织 | 动态 design tree + frontier,按轮次批量出题 | 固定组件清单(set point/sensor/controller/actuator/disturbance)逐项问 |
| 推荐答案 | 每题必附推荐,措辞偏向 yes 即采纳 | "带 proposal 来,不带空白表格"——先读仓库再给基于证据的选项与 trade-off |
| 事实获取 | 派 sub-agent 查环境,不劳烦用户 | agent 先自查仓库(CI/包管理/校验命令/既有 skills)再开问 |
| 产物 | 无固定产物(共识即产物);grill-with-docs 产出 GLOSSARY/ADR | sensor/controller 脚本 + actuator skill + workflow yml + memory 文件,全落盘 |
| 终止条件 | frontier 为空 + 用户确认共识 | 每阶段有 completion criterion,书面设计定稿后才构建 |
| 触发方式 | 用户斜杠调用(disable-model-invocation) | 用户主动调用 |
| 工具依赖 | Skill 工具 + sub-agent | gh CLI、GitHub Actions、coding agent secret |

对 HC-AIDW 的启示: 两套可**叠加**——用 grilling 的 frontier/轮次/推荐答案机制做交互节奏,用 design-control-loop 的"每题带仓库证据、每阶段有完成判据、设计书面化"做质量门。

---

## 4. RPI(Research-Plan-Implement)工作流

【已验证】humanlayer/skills 无 RPI 文件。【推断】RPI 出自 Dex Horthy 的 "Advanced Context Engineering for Coding Agents"(2025-08,博客列表已验证存在,正文本次未抓)。要点(记忆+旁证):

1. **Research**: 并行 subagent 探索代码库,各自把 findings 写成文件,压缩检索噪声;
2. **Plan**: 主 agent 汇总 research 产物写实现计划(plan.md),可插入人类确认(HumanLayer 主产品 HIL API 即做这个);
3. **Implement**: 以干净的 context 只装载 plan 逐步实现,每步可验证。

核心洞察: 阶段间用**文件作为上下文压缩接口(compaction)**——implement 阶段不背 research 原始噪声。同仓库 build-iterated-agentic-loop / design-control-loop 是该思想无人值守化的落地: explore→问用户→写 skill/prompt/memory→定时 workflow→PR 人审→memory 沉淀反馈。

**引用前建议补抓博客原文;上段为推断级。**

---

## 5. build-iterated-agentic-loop 与 design-control-loop 【已验证,两份 SKILL.md 全文均已抓取】

### 5.1 build-iterated-agentic-loop(13.5KB)

产物四件套: repo-local `.claude/skills/<name>/SKILL.md`、`.github/workflows/agent-<name>.yml`、`.github/agent-memory/<name>.md`、可选 references/。

9 步: 探索仓库 → 8 项设置问答(agent 选型 Claude Code/Codex/OpenCode/CodeLayer、cadence、task、scope、validation、**PR bounding(默认每 loop 1 个 open PR,防止产出快过审核)**、PR 元数据、response 模板、/iterate)→ 定义 agent job(找什么/改什么/怎么验证三问)→ 写 skill → 写 workflow prompt → 装 memory → 生成 workflow → YAML 校验 → dry-run bootstrap(临时 push 触发器首跑)。

值得抄的设计:
- **one source of truth per rule**(skill/prompt/memory 不重复);
- memory 只放跨 run 有效内容(永久 scope 排除、已知误报、应改变未来选择的评审反馈),删了会丢未来上下文才算合格;
- 每步 completion criterion;
- response-template 决定 PR body 结构(summary stats / risk levels / verification steps / file lists)= 面向 reviewer 的结构化报告。

### 5.2 design-control-loop(15.5KB)+ control-loop-taxonomy.md(5.6KB)【均已验证】

控制论心智模型: **Set point**(目标状态: 不变量/阈值/方向)→ **Sensor**(度量差距: lint/AST/测试/类型检查/遥测/agent 检查)→ **Controller**(决定下一个低风险小增量,可从确定性脚本到全 agent,是**长期调优对象**)→ **Actuator**(coding agent + repo skill,开 PR)→ **Disturbance**(队友提交/依赖升级/生成代码);**人始终 on the loop**。

Phase A-H: 探索仓库 → 面谈设计(逐组件+trade-off)→ 写 actuator skill(golden patterns 先行)→ **每个组件先本地可独立运行**再接 CI → workflow 编排(sensor→controller→actuator 离散步骤)→ **Phase F "Put a human on the loop"**(双通道: memory 文件每次 run 确定性注入 actuator context;PR 上评论 `/iterate` 触发 agent 更新 memory 与 PR)→ Flow control(PR bounding + dampener 回归闸门: 比较 sensor 输出与 baseline,防问题恶化)→ 校验/dry-run/提速。

taxonomy 额外概念: sensor+controller 可融合、controller+actuator 可融合("don't manufacture separation");scope gate、batch size、dampener。

---

## 6. 附: improve-claude-md 【已验证】

用 `<important-if condition="...">` XML 块包裹 CLAUDE.md 中条件相关指令(利用 Claude Code 系统提示同款 XML 模式对抗"may or may not be relevant"注入语);基础上下文(项目身份/目录图/技术栈/全部 commands)裸写;原则: 90%+ 任务相关的裸写、条件要窄、less is more(几百词内)、linter 能管的删掉、代码片段换文件路径引用、模糊指令("follow best practices")删掉。

对 HC-AIDW 价值: 这是"如何让 agent 稳定遵守审核规则"的成熟 prompt 组织法,可直接用于撰写三节点审核 agent 的指令文件。

---

## 7. 对 HC-AIDW 三个审核节点的复用建议

### 节点1: 需求理解审核
- 直接复用: **grilling 的机制整体搬用**(design tree + frontier 轮次 + 每题推荐答案 + 事实自查/决策问用户 + frontier 为空才结束)——这是现成的需求盘问引擎;design-control-loop 的"带证据的 proposal、书面化设计、completion criterion"做质量门。
- 非技术人员适配需自研: 两侧都是开发者向;HC-AIDW 需把问题转成非技术语言、把"确认共识"做成可视化界面动作。
- 不必造轮子: 盘问交互协议、 Glossary/ADR 产物模式(grill-with-docs + domain-modeling)。

### 节点2: 架构与实施方案审核
- **show-me 是最大直接参考**: 视图选型菜单(伪代码/调用树/组件树/文件树/Mermaid/diff/单文件 HTML)+ 单文件 HTML 规范(贴产品设计 token、真实数据、响应式、diagram/infographic/slide deck 三态)。HC-AIDW 审核界面渲染 show-me 式单文件 HTML 即可,无需重型可视化框架。
- build-iterated-agentic-loop 的 response-template(统计/风险等级/验证步骤/文件清单)可作"方案审核单"骨架。

### 节点3: 代码生成结果核验
- 可复用: agent job 三问(找什么/改什么/怎么验证)+"同一工具报告问题、同一工具确认解决"闭环;dampener 基线对比思想(核验 = 新产物 vs 基线);PR bounding 防审核积压;memory 通道沉淀审核反馈到未来 run。
- 需自研: 该仓库无代码核验专用 skill,核验主逻辑(对照 spec 检查代码)不在其中。
- 重复造轮子风险: `<important-if>` 指令组织、one-source-of-truth 规则、completion criterion 模式直接采用,勿另发明。

---

## 8. 已验证 / 待补验证清单

已验证(均抓到原文):
- humanlayer/skills 完整文件树、README、marketplace.json
- show-me、improve-claude-md、build-iterated-agentic-loop、design-control-loop 四份 SKILL.md 全文
- design-control-loop/references/control-loop-taxonomy.md 全文
- mattpocock/skills 首页 README、grill-me、grilling、grill-with-docs 三份 SKILL.md 原文
- humanlayer.dev/blog 列表页

待补验证:
1. RPI 原文(humanlayer 博客 "Advanced Context Engineering for Coding Agents",2025-08-29)——§4 为推断级
2. show-me 博客原文(2026-08-12,抓取时 500)
3. mattpocock/skills 其余相关 skill 全文(tdd、code-review、research、wayfinder、to-spec 等,README 摘要已验证但正文未抓)
4. plugins/visual-pr 清单与文件树不同步的原因
5. HumanLayer 主仓库 HIL API 形态(humanlayer/humanlayer)
