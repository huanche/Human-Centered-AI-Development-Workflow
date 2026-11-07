#!/usr/bin/env python3
"""HC-AIDW 审核状态存储(唯一状态持有者)。

设计约定(见 AGENTS.md 与任务书):
- 单写者:所有状态变更经本模块原子落盘(temp + os.replace)。
- 版本乐观并发:publish 必须携带 base_revision,落后即拒绝(409 冲突)。
- 人工确认只能来自浏览器令牌接口;Agent 令牌无确认能力。
- 每次变更写入 history 审计日志。
"""
import copy
import datetime
import json
import os
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from diff_review import diff as human_diff  # noqa: E402  复用人话变更回执


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


class ReviewError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ReviewStore:
    """reviews/<review_id>/state.json 的受控读写。"""

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else ROOT / "reviews"

    # ---------- 基础 ----------
    def _dir(self, review_id: str) -> Path:
        if not re.fullmatch(r"rev-[a-z0-9]{8}", review_id):
            raise ReviewError(400, f"非法 review_id: {review_id!r}")
        return self.root / review_id

    def _path(self, review_id: str) -> Path:
        return self._dir(review_id) / "state.json"

    def _load(self, review_id: str) -> dict:
        p = self._path(review_id)
        if not p.exists():
            raise ReviewError(404, f"审核任务不存在: {review_id}")
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ReviewError(500, f"状态文件损坏: {e}")

    def _save(self, state: dict) -> None:
        d = self._dir(state["review_id"])
        d.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = now()
        tmp = d / "state.json.tmp"
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, d / "state.json")  # 原子替换

    def _log(self, state: dict, action: str, detail: dict) -> None:
        state.setdefault("history", []).append(
            {"time": now(), "action": action, **detail}
        )

    # ---------- Agent 侧 ----------
    def create_review(self, rtype: str, title: str, content: dict, context: dict | None) -> dict:
        if not title or not isinstance(content, dict):
            raise ReviewError(400, "title 与 content(dict) 必填")
        rid = "rev-" + secrets.token_hex(4)
        token = secrets.token_hex(16)  # 浏览器访问令牌:不可预测
        state = {
            "review_id": rid,
            "type": rtype or "requirement-review",
            "title": title,
            "status": "awaiting_review",  # awaiting_review | confirmed
            "created_at": now(),
            "url_token": token,
            "current_revision": 1,
            "revisions": [{
                "n": 1,
                "time": now(),
                "published_by": "agent",
                "content": copy.deepcopy(content),
                "change_summary": ["首次发布"],
                "evidence": [],
                "basis": "initial",
            }],
            "feedback": [],
            "decisions": [],  # {revision, time, action: confirmed}
            "context": context or {},
            "history": [{"time": now(), "action": "created", "revision": 1}],
        }
        self._save(state)
        return {"review_id": rid, "revision": 1, "status": state["status"],
                "url_token": token}

    def get_review(self, review_id: str) -> dict:
        return self._load(review_id)

    def agent_view(self, review_id: str, full: bool = False) -> dict:
        """Agent 状态视图。默认紧凑模式(省 token):状态+待处理意见+变化说明,
        不含全部版本内容;full=True 才返回完整文档(不含浏览器令牌)。"""
        s = self._load(review_id)
        s.pop("url_token", None)
        pending = [f for f in s["feedback"] if f["status"] == "pending"]
        if not full:
            return {
                "review_id": s["review_id"], "title": s["title"], "type": s["type"],
                "status": s["status"], "current_revision": s["current_revision"],
                "needs_action": bool(pending) or s["status"] == "awaiting_review",
                "pending_feedback": pending,
                "feedback_total": len(s["feedback"]),
                "latest_change_summary": s["revisions"][-1]["change_summary"],
                "decisions": s["decisions"],
                "context": s.get("context", {}),
                "history_tail": s.get("history", [])[-5:],
            }
        s["needs_action"] = bool(pending) or s["status"] == "awaiting_review"
        return s

    def publish_revision(self, review_id: str, base_revision: int, content: dict,
                         change_summary, evidence) -> dict:
        s = self._load(review_id)
        cur = s["current_revision"]
        if base_revision != cur:
            raise ReviewError(409, f"版本冲突: 你基于 r{base_revision} 提交,"
                                   f"但当前已是 r{cur},请先 get_review_status 重新获取")
        if not isinstance(content, dict):
            raise ReviewError(400, "content 必须是结构化 dict")
        if base_revision == cur and s["revisions"] and \
                content == s["revisions"][-1]["content"]:
            raise ReviewError(400, "新内容与当前版本相同,无需要发布")
        n = cur + 1
        summary = change_summary if isinstance(change_summary, list) and change_summary \
            else human_diff(s["revisions"][-1]["content"], content)
        rev = {"n": n, "time": now(), "published_by": "agent",
               "content": copy.deepcopy(content), "change_summary": summary,
               "evidence": evidence or [], "basis": base_revision}
        s["revisions"].append(rev)
        s["current_revision"] = n
        # 修改已确认内容 → 原确认不再生效,回到待审核
        if s["status"] == "confirmed":
            s["status"] = "awaiting_review"
            self._log(s, "confirmation_voided", {"reason": f"r{n} 修改了已确认内容"})
        s["status"] = "awaiting_review"
        self._log(s, "published", {"revision": n, "base_revision": base_revision})
        self._save(s)
        return {"review_id": review_id, "revision": n, "status": s["status"],
                "change_summary": summary}

    # ---------- 浏览器侧 ----------
    def add_feedback(self, review_id: str, token: str, text: str,
                     step: int | None = None, step_name: str = "",
                     target: str = "") -> dict:
        s = self._load(review_id)
        if token != s.get("url_token"):
            raise ReviewError(403, "访问令牌无效")
        text = (text or "").strip()
        if not text or len(text) > 5000:
            raise ReviewError(400, "意见内容需为 1~5000 字")
        fid = "f" + secrets.token_hex(3)
        item = {"id": fid, "step": step, "step_name": step_name or "",
                "target": target or "", "text": text, "time": now(),
                "revision": s["current_revision"], "status": "pending",
                "addressed_in": None}
        s["feedback"].append(item)
        self._log(s, "feedback_added", {"feedback_id": fid, "step": step})
        self._save(s)
        return item

    def mark_addressed(self, review_id: str, feedback_ids: list | None, revision: int) -> None:
        """发布新版本时回收意见:显式列出已回应的意见 id;未列出则视为全部回应。"""
        s = self._load(review_id)
        ids = set(feedback_ids) if feedback_ids is not None else \
            {f["id"] for f in s["feedback"] if f["status"] == "pending"}
        changed = False
        for f in s["feedback"]:
            if f["id"] in ids and f["status"] == "pending":
                f["status"] = "addressed"
                f["addressed_in"] = revision
                changed = True
        if changed:
            self._log(s, "feedback_addressed", {"revision": revision,
                                                "count": len(ids)})
            self._save(s)

    def confirm(self, review_id: str, token: str, ack_revision: int) -> dict:
        s = self._load(review_id)
        if token != s.get("url_token"):
            raise ReviewError(403, "访问令牌无效")
        if ack_revision != s["current_revision"]:
            raise ReviewError(409, f"确认的版本 r{ack_revision} 已过期,"
                                   f"当前为 r{s['current_revision']},请刷新页面后确认")
        rec = {"revision": ack_revision, "time": now(), "action": "confirmed"}
        s["decisions"].append(rec)
        s["status"] = "confirmed"
        self._log(s, "human_confirmed", {"revision": ack_revision})
        self._save(s)
        return rec

    # ---------- 长轮询辅助 ----------
    def wait_signal(self, review_id: str, since_revision: int, since_feedback: int,
                    timeout: float) -> dict:
        """有限等待:revision 变化或新反馈出现即返回;超时返回 pending。"""
        import time as _t
        deadline = _t.time() + min(timeout, 60.0)
        while _t.time() < deadline:
            s = self._load(review_id)
            pending = sum(1 for f in s["feedback"] if f["status"] == "pending")
            if s["current_revision"] != since_revision or pending != since_feedback \
                    or s["decisions"]:
                return {"status": "changed", "revision": s["current_revision"],
                        "pending_feedback": pending, "decision": bool(s["decisions"])}
            _t.sleep(0.4)
        return {"status": "pending", "revision": since_revision,
                "pending_feedback": since_feedback, "decision": False}
