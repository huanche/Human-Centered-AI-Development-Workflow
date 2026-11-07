---
name: hc-review
description: 发起并驱动 HC-AIDW 可视化人工审核闭环。当需求或方案需要用户(尤其是非技术用户)审核确认时使用:创建审核任务、给出浏览器链接、处理用户反馈、发布修订、等待确认。
---

# HC-AIDW 人工审核闭环

通过 `hc-aidw-review` MCP 工具(request_review / get_review_status /
wait_review_result / publish_revision)驱动"Agent 起草 → 用户浏览器审核 →
反馈 → 修订 → 确认"的循环。

## 触发条件

- 用户提出新需求,你已完成需求分析并结构化(符合 `schemas/requirement-review.schema.json`);
- 架构/实施方案需要用户确认(architecture-review);
- 用户明确要求"给我审核"。

## 流程规则

1. **先结构化,再发起**。内容必须通过
   `python scripts/validate.py <临时实例文件>` 校验后再放入 `content`。
2. **发起**:`request_review`,context 里写最小恢复上下文
   (project / code_paths / git_baseline / requirement_source / next_action)。
   把返回的 `url` 原样给用户,告诉用户:在浏览器里看、提意见、确认。
3. **等待**:与用户对话时优先用 `get_review_status` 轮询(或用户说
   "意见已提交"后立即查询);离开对话态时可用 `wait_review_result`
   (≤120s,超时返回 pending 不丢数据)。
4. **处理反馈**:逐条评估用户意见。同意 → 修订 content;
   有异议 → 在 change_summary 里写明理由与用户商榷。**不得无视意见**。
5. **发布**:`publish_revision` 必须带当前 `base_revision`;收到版本冲突
   (409 语义)时,先 `get_review_status` 取最新版本,合并你的修订再发,
   禁止覆盖新版本。
   `change_summary` 用业务语言(用户是非技术人员),每条一句人话;
   `evidence` 附源码位置/文档引用。
6. **确认边界**:status=confirmed 后才能视为获得批准,进入下一阶段
   (架构审核或实现)。用户之后的修改会使确认失效(服务端自动处理,
   status 回到 awaiting_review)。**任何情况下都不得伪造人工确认——
   MCP 没有确认工具,确认只来自浏览器。**
7. **恢复**:会话中断后,用 review_id `get_review_status` 即可取回
   全部状态与 context;`context.next_action` 记录了你中断前该做的事。

## 权限边界(必须如实告知用户)

本服务是本地原型:Agent 拥有本机文件/命令权限时,无法被技术上阻止其
读取令牌伪造请求。系统承诺的是:正常流程下 Agent 无确认通道、确认记录
由服务端受控写入、全部操作留痕(history 字段)。
