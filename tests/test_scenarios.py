#!/usr/bin/env python3
"""HC-AIDW 审核闭环场景测试(任务书第十节 A–E)。

运行: python -m pytest tests/test_scenarios.py -v
服务在测试内以线程启动(随机端口、独立临时目录),不依赖外部进程。
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
import review_service  # noqa: E402
from review_service import Handler, load_or_create_agent_token  # noqa: E402


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr(review_service, "ROOT", tmp_path)
    monkeypatch.setattr(Handler, "store", review_service.ReviewStore(tmp_path / "reviews"))
    monkeypatch.setattr(Handler, "agent_token", "test-agent-token")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Handler.port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{Handler.port}"
    yield {"base": base, "root": tmp_path}
    srv.shutdown()


# 本地服务测试不走系统代理(环境可能设置 http_proxy)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def req(base, method, path, payload=None, headers=None):
    body = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(base + path, data=body, method=method,
                               headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with OPENER.open(r, timeout=10) as resp:
            return resp.status, _json_or_raw(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, _json_or_raw(e.read())


def _json_or_raw(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": "non-json response", "raw": raw[:200].decode("utf-8", "replace")}


def create(base, **kw):
    payload = {"type": "requirement-review", "title": "编程实验模块",
               "content": {"restatement": {"one_liner": "做编程实验"}},
               "context": {"project": "agentic-class-pilot"}}
    payload.update(kw)
    code, r = req(base, "POST", "/api/agent/reviews", payload,
                  headers={"X-Agent-Token": "test-agent-token"})
    assert code == 200 and r["ok"]
    return r


AG = {"X-Agent-Token": "test-agent-token"}


# ---------- 场景 A:正常审核闭环 ----------
def test_scenario_a_full_loop(svc):
    base = svc["base"]
    # 1-2. Agent 发起审核,拿到浏览器 URL
    r = create(base)
    rid, tok, url = r["review_id"], r["url_token"], r["url"]
    assert r["revision"] == 1 and f"/rt/{rid}?t={tok}" in url
    # 浏览器能按 URL 拉到状态
    code, v = req(base, "GET", f"/api/review/{rid}?t={tok}")
    assert code == 200 and v["content"]["restatement"]["one_liner"] == "做编程实验"
    # 3-4. 用户在页面提交意见(直接落盘,无下载)
    code, fb = req(base, "POST", f"/api/review/{rid}/feedback?t={tok}",
                   {"text": "学生不是手动标记已学,是自动完成", "step": 1,
                    "step_name": "需求理解"})
    assert code == 200 and fb["feedback"]["status"] == "pending"
    # 5. Agent 查询到未处理反馈
    code, st = req(base, "GET", f"/api/agent/reviews/{rid}", headers=AG)
    assert st["needs_action"] and st["feedback"][0]["status"] == "pending"
    # 6-7. Agent 修订并发布(base_revision 正确)
    new_content = {"restatement": {"one_liner": "做编程实验,学生自动完成学习标记"}}
    code, pub = req(base, "POST", f"/api/agent/reviews/{rid}/publish",
                    {"base_revision": 1, "content": new_content,
                     "change_summary": ["学习标记由手动改为自动完成"],
                     "evidence": ["docs/prd.md#L12"]}, headers=AG)
    assert code == 200 and pub["revision"] == 2
    # 意见被标记为已在 r2 回应
    code, st = req(base, "GET", f"/api/agent/reviews/{rid}", headers=AG)
    assert st["feedback"][0]["status"] == "addressed"
    assert st["feedback"][0]["addressed_in"] == 2
    # 8. 浏览器读到新版本+差异摘要
    code, v = req(base, "GET", f"/api/review/{rid}?t={tok}")
    assert v["current_revision"] == 2
    assert v["revisions"][-1]["change_summary"] == ["学习标记由手动改为自动完成"]
    # 9-10. 用户确认当前版本,服务记录人工决策
    code, c = req(base, "POST", f"/api/review/{rid}/confirm?t={tok}",
                  {"ack_revision": 2}, headers={"Origin": f"http://127.0.0.1:{Handler.port}",
                                                "Host": f"127.0.0.1:{Handler.port}"})
    assert code == 200 and c["decision"]["revision"] == 2
    code, st = req(base, "GET", f"/api/agent/reviews/{rid}", headers=AG)
    assert st["status"] == "confirmed" and st["decisions"][-1]["revision"] == 2


# ---------- 场景 B:版本冲突 ----------
def test_scenario_b_revision_conflict(svc):
    base = svc["base"]
    r = create(base)
    rid = r["review_id"]
    code, _ = req(base, "POST", f"/api/agent/reviews/{rid}/publish",
                  {"base_revision": 1, "content": {"v": 2}}, headers=AG)
    assert code == 200
    # 基于过期 r1 再发布 → 必须被拒绝,不得覆盖
    code, e = req(base, "POST", f"/api/agent/reviews/{rid}/publish",
                  {"base_revision": 1, "content": {"v": 3}}, headers=AG)
    assert code == 409 and "版本冲突" in e["error"]
    code, st = req(base, "GET", f"/api/agent/reviews/{rid}", headers=AG)
    assert st["current_revision"] == 2 and len(st["revisions"]) == 2


# ---------- 场景 C:长等待超时不丢任务 ----------
def test_scenario_c_wait_timeout_preserves_task(svc):
    base = svc["base"]
    r = create(base)
    rid, tok = r["review_id"], r["url_token"]
    t0 = time.time()
    code, sig = req(base, "GET", f"/api/review/{rid}?t={tok}&wait=1&revision=1&feedback=0&timeout=1")
    assert code == 200 and sig["status"] == "pending"
    assert time.time() - t0 >= 0.9  # 确实等待过,但被限制
    # 任务完好
    code, v = req(base, "GET", f"/api/review/{rid}?t={tok}")
    assert code == 200 and v["current_revision"] == 1


# ---------- 场景 D:服务重启后恢复 ----------
def test_scenario_d_recover_after_restart(svc):
    base, root = svc["base"], svc["root"]
    r = create(base)
    rid, tok = r["review_id"], r["url_token"]
    req(base, "POST", f"/api/review/{rid}/feedback?t={tok}", {"text": "改一下范围"})
    # 模拟重启:新实例指向同一存储目录
    old_store, old_tok = review_service.Handler.store, review_service.Handler.agent_token
    try:
        review_service.Handler.store = review_service.ReviewStore(root / "reviews")
        review_service.Handler.agent_token = "test-agent-token"
        code, st = req(base, "GET", f"/api/agent/reviews/{rid}", headers=AG)
        assert code == 200
        assert st["context"]["project"] == "agentic-class-pilot"
        assert st["feedback"][0]["text"] == "改一下范围"
        # 新 Agent 会话按 review_id 继续:发布修订
        code, pub = req(base, "POST", f"/api/agent/reviews/{rid}/publish",
                        {"base_revision": 1, "content": {"restatement": {"one_liner": "修订版"}}},
                        headers=AG)
        assert code == 200 and pub["revision"] == 2
    finally:
        review_service.Handler.store, review_service.Handler.agent_token = old_store, old_tok


# ---------- 场景 E:权限约束 ----------
def test_scenario_e_no_agent_confirm_and_bad_requests(svc):
    base, port = svc["base"], Handler.port
    r = create(base)
    rid, tok = r["review_id"], r["url_token"]
    # E1: 仅凭 Agent 令牌(无浏览器令牌)尝试确认 → 403
    code, _ = req(base, "POST", f"/api/review/{rid}/confirm",
                  {"ack_revision": 1}, headers=AG)
    assert code == 403
    # E2: 无令牌确认 → 401/403
    code, _ = req(base, "POST", f"/api/review/{rid}/confirm", {"ack_revision": 1})
    assert code in (401, 403)
    # E3: 错误浏览器令牌 → 403
    code, _ = req(base, "POST", f"/api/review/{rid}/confirm?t={'0' * 32}",
                  {"ack_revision": 1})
    assert code == 403
    # E4: 无效 review_id 形态 → 400
    code, _ = req(base, "GET", "/api/agent/reviews/../etc", headers=AG)
    assert code in (400, 404)
    # E5: Agent 错误令牌 → 403
    code, _ = req(base, "GET", f"/api/agent/reviews/{rid}",
                  headers={"X-Agent-Token": "wrong"})
    assert code == 403
    # E6: 非法 Host 的浏览器写请求 → 403
    code, _ = req(base, "POST", f"/api/review/{rid}/feedback?t={tok}",
                  {"text": "x"}, headers={"Host": "evil.example:9", "Origin": "http://evil"})
    assert code == 403
    # 正确令牌+当前版本的确认仍然成立(未伪造)
    code, _ = req(base, "POST", f"/api/review/{rid}/confirm?t={tok}",
                  {"ack_revision": 1}, headers={"Origin": f"http://127.0.0.1:{port}"})
    assert code == 200


# ---------- 补充:确认后修改 → 确认失效 ----------
def test_confirmation_voided_by_later_revision(svc):
    base = svc["base"]
    r = create(base)
    rid, tok = r["review_id"], r["url_token"]
    req(base, "POST", f"/api/review/{rid}/confirm?t={tok}", {"ack_revision": 1})
    code, pub = req(base, "POST", f"/api/agent/reviews/{rid}/publish",
                    {"base_revision": 1, "content": {"v": 2}}, headers=AG)
    assert code == 200
    code, st = req(base, "GET", f"/api/agent/reviews/{rid}", headers=AG)
    assert st["status"] == "awaiting_review"  # 原确认失效
    assert any(h["action"] == "confirmation_voided" for h in st["history"])
    # 过期确认被拒
    code, _ = req(base, "POST", f"/api/review/{rid}/confirm?t={tok}",
                  {"ack_revision": 1})
    assert code == 409
