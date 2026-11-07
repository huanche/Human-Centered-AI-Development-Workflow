# 审核闭环运行演示记录(2026-11-07)

环境:Windows 11 · Python 3.10.11 · mcp 2.x · 服务 `server/review_service.py`(127.0.0.1:8765)
演示通过 MCP server 同一代码路径(`server/mcp_server.py::_call`)执行 Agent 侧操作,浏览器侧用 HTTP 直调(与页面 JS 完全相同的端点)。

> 说明:演示任务原为 rev-0849d7e1,因一次误删 reviews 目录(已从 git 恢复试点文件)而丢失;当前可打开的演示任务为 **rev-5e10e6a4**(含完整 r1→r2 历史与人工确认记录):
> `http://127.0.0.1:8765/rt/rev-5e10e6a4?t=f25f94d10e35d7307a9bfe896f1f37c7`

## 实测输出

```
[1 request_review] review_id = rev-0849d7e1 | revision = 1
[1 浏览器 URL] http://127.0.0.1:8765/rt/rev-0849d7e1?t=d9db…(随机 32 位令牌)
[2 浏览器提交意见] 直接落盘,无下载文件
[3 get_review_status] needs_action = True | pending = ['学生不是手动标记已学,是看完视频自动完成']
[4 publish_revision] revision = 2 | summary = ["学习完成方式:手动'标记已学'改为看完视频自动完成"]
[5 版本冲突] 服务返回 409: 版本冲突: 你基于 r1 提交,但当前已是 r2,请先 get_review_status 重新获取
[6 浏览器确认] {'revision': 2, 'time': '2026-11-07T20:54:48', 'action': 'confirmed'}
[7 最终状态] confirmed | decisions = [{'revision': 2, ...}]
DEMO OK
```

## 对应任务书场景

| 场景 | 结果 | 覆盖方式 |
|---|---|---|
| A 正常审核闭环 | ✅ 全 10 步走通 | 演示 + `test_scenario_a_full_loop` |
| B 版本冲突 | ✅ 409 + 明确错误信息,不覆盖新版本 | 演示 + `test_scenario_b_revision_conflict` |
| C 长等待超时 | ✅ 有界等待(≤60s),超时返回 pending,任务无损 | `test_scenario_c_wait_timeout_preserves_task` |
| D 中断恢复 | ✅ 服务"重启"与新 Agent 会话均能按 review_id 取回状态/反馈/上下文并继续发布 | `test_scenario_d_recover_after_restart` |
| E 权限约束 | ✅ 仅 Agent 令牌确认被拒(403);无/错令牌被拒;非法 Host/Origin 被拒;伪造 review_id 被拒;确认后修改 → 确认自动失效 | `test_scenario_e_no_agent_confirm_and_bad_requests` + `test_confirmation_voided_by_later_revision` |

自动化测试:`python -m pytest tests/test_scenarios.py -v` → **6 passed**。

## 已验证 vs 宿主限制

已验证:
- 4 个 MCP 工具注册成功(mcp 2.x `MCPServer`,stdio);
- 服务重启后状态恢复(文件持久化,原子写);
- 版本乐观并发与人工确认的浏览器独占;
- 长轮询有界等待(浏览器页面 8s 心跳 + ≤25s 长轮询自动刷新;Agent 端 ≤120s)。

宿主限制(如实记录,部分待你在真实会话实测):
1. Claude Code 的 MCP 连接在会话启动时建立——需重启会话后 `.mcp.json` 才生效;本演示用 MCP server 的 `_call` 同路径验证,逻辑等价但非"真 MCP 握手"。
2. `wait_review_result` 依赖宿主允许工具调用阻塞 ≤120s;若 Claude Code 中断该调用,任务不丢(持久化),用 `get_review_status` 轮询即可恢复。哪种情形能在同会话继续,需你实测后在此回填。
3. 会话中断后,`review_id` 能恢复审核任务与 `context.next_action`,但**不能**恢复 Agent 原对话记忆——新会话需人工把 review_id 告诉它(最少操作:一句"继续审核 rev-xxxxxxxx")。

## 已知安全边界

本地原型威胁模型:Agent 拥有本机全部权限(读文件、执行命令)时,技术上无法阻止其读取令牌伪造请求;系统承诺的是正常流程下 Agent 无确认通道、确认由服务端受控写入、操作全留痕。不做虚假安全承诺。
