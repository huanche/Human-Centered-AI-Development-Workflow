#!/usr/bin/env python3
"""HC-AIDW 审核 MCP Server(stdio,薄客户端)。

所有工具转发到本地审核服务(server/review_service.py)——
服务是唯一状态持有者;MCP 进程随会话生灭,不影响审核任务持久性。

Claude Code 配置(.mcp.json):
    {"mcpServers": {"hc-aidw-review": {"command": "python",
                                        "args": ["-X", "utf8", "<本文件绝对路径>"]}}}

工具:
    request_review(type,title,content,context)     发起审核,返回 review_id+浏览器 URL
    get_review_status(review_id)                   非阻塞查询状态+未处理反馈
    wait_review_result(review_id,timeout)          有限等待(≤120s,超时返回 pending)
    publish_revision(review_id,base_revision,…)    发布新版本(版本冲突显式报错)

权限边界:本 Server 不提供任何"标记人工已确认"的工具——
确认只能由用户在浏览器审核页完成(见任务书第五节)。
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from mcp.server.mcpserver import MCPServer  # mcp>=2(FastMCP 在 2.x 更名)

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("HC_AIDW_SERVICE", "http://127.0.0.1:8765")
TOKEN_FILE = ROOT / "reviews" / ".agent-token"
MAX_WAIT = 120.0

mcp = MCPServer("hc-aidw-review")

# 直连本地服务,绕过系统代理(否则 http_proxy 会把 127.0.0.1 请求发去代理)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _agent_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"未找到 Agent 令牌 {TOKEN_FILE}——请先启动本地服务: "
            f"python server/review_service.py")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def _call(method: str, path: str, payload: dict | None = None,
          timeout: float = 30.0) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        method=method,
        headers={"Content-Type": "application/json",
                 "X-Agent-Token": _agent_token()})
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", "")
        except Exception:
            detail = e.reason
        raise RuntimeError(f"服务返回 {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"无法连接审核服务({BASE}): {e.reason}。"
            f"请先启动: python server/review_service.py")


@mcp.tool()
def request_review(type: str, title: str, content: dict, context: dict = None) -> str:
    """发起人工审核任务。

    type: 审核类型(如 requirement-review / architecture-review)
    title: 审核标题(给人看)
    content: 结构化审核内容(需符合对应 schema,如 schemas/requirement-review.schema.json)
    context: 最小恢复上下文(项目标识、代码路径、git 基线、需求来源、下一步建议)

    返回 JSON:review_id / revision / status / url(浏览器审核页地址,把 URL 给用户打开)。
    创建任务不等于获得批准;确认只能由用户在浏览器完成。
    """
    r = _call("POST", "/api/agent/reviews",
              {"type": type, "title": title, "content": content,
               "context": context or {}})
    return json.dumps(r, ensure_ascii=False)


@mcp.tool()
def get_review_status(review_id: str, include_full_content: bool = False) -> str:
    """非阻塞查询审核任务状态(默认紧凑模式,省 token)。

    默认返回:status、current_revision、needs_action、pending_feedback
    (待处理意见全文)、latest_change_summary、decisions、context(恢复上下文)。
    只有当你要修订内容时才传 include_full_content=true 取回完整文档。
    不含浏览器访问令牌。
    """
    q = "?full=1" if include_full_content else ""
    return json.dumps(_call("GET", f"/api/agent/reviews/{review_id}{q}"),
                      ensure_ascii=False)


@mcp.tool()
def wait_review_result(review_id: str, timeout: float = 30) -> str:
    """有限等待审核事件(新反馈 / 新版本 / 人工确认),超时返回 pending。

    timeout 上限 120 秒。注意:终端型 Agent 宿主可能中断长时间阻塞调用——
    推荐以 get_review_status 轮询为主,本工具用于短等待减少空转。
    返回:status=changed(有事件,revision/pending_feedback/decision 字段)
         或 pending(超时,任务仍在,无数据丢失)。
    """
    t = max(1.0, min(float(timeout), MAX_WAIT))
    s = _call("GET", f"/api/agent/reviews/{review_id}")
    cur_rev = s["current_revision"]
    cur_fb = sum(1 for f in s.get("feedback", []) if f["status"] == "pending")
    r = _call("GET", f"/api/agent/reviews/{review_id}"
                     f"?wait=1&revision={cur_rev}&feedback={cur_fb}&timeout={t}",
              timeout=t + 15)
    return json.dumps(r, ensure_ascii=False)


@mcp.tool()
def publish_revision(review_id: str, base_revision: int, content: dict,
                     change_summary: list = None, evidence: list = None,
                     addressed: list = None) -> str:
    """发布修订版本(核心工具)。

    base_revision: 你所基于的当前版本号;若服务端已前进,返回 409 版本冲突,
    此时必须 get_review_status 重新获取后再合并修订,禁止覆盖新版本。
    content: 修订后的完整结构化内容。
    change_summary: 给普通用户看的业务变化说明(每条一句人话);
    不传则自动从内容差异生成。
    evidence: 支撑本次修改的证据(源码位置/文档/测试)。
    addressed: 本轮已回应的意见 id 列表;不传则视为全部意见已回应。

    返回:revision / status / change_summary。发布后用户在浏览器继续审核。
    """
    r = _call("POST", f"/api/agent/reviews/{review_id}/publish",
              {"base_revision": base_revision, "content": content,
               "change_summary": change_summary or [], "evidence": evidence or [],
               "addressed": addressed}, timeout=60)
    return json.dumps(r, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
