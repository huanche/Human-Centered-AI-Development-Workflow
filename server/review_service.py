#!/usr/bin/env python3
"""HC-AIDW 审核本地服务(唯一状态持有者,状态逻辑见 server/store.py)。

用法:
    python server/review_service.py [--port 8765]

路由:
    GET  /ping
    GET  /rt/<id>?t=<token>                审核页(通用模板,页面 JS 用令牌调 API)
    GET  /api/review/<id>?t=               浏览器:完整状态 + 最新内容 + 差异摘要
         [&revision=&feedback=&timeout=]   长轮询(变化即返回,上限 60s)
    POST /api/review/<id>/feedback  {text, step, step_name, target}
    POST /api/review/<id>/confirm   {ack_revision}
    POST /api/agent/reviews                {type,title,content,context} → 创建
    GET  /api/agent/reviews/<id>           Agent 状态视图(不含浏览器令牌)
    POST /api/agent/reviews/<id>/publish   {base_revision, content, change_summary, evidence, addressed}
    GET  /api/agent/reviews/<id>?revision=&feedback=&timeout=   有限等待
    静态文件:仓库根目录

安全模型(本地原型威胁边界,详见模块尾注释):
    只监听 127.0.0.1;Host/Origin 校验;浏览器令牌与 Agent 令牌分离;
    确认接口仅浏览器令牌可用。已知边界:拥有本机全部权限的 Agent
    (读文件/执行命令)无法被绝对阻止——本地原型不做虚假安全承诺。
"""
import argparse
import json
import secrets
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
from store import ReviewStore, ReviewError  # noqa: E402

MAX_BODY = 2 * 1024 * 1024


def load_or_create_agent_token() -> str:
    p = ROOT / "reviews" / ".agent-token"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    p.parent.mkdir(parents=True, exist_ok=True)
    tok = secrets.token_hex(16)
    p.write_text(tok, encoding="utf-8")
    return tok


class Handler(SimpleHTTPRequestHandler):
    store = ReviewStore()
    agent_token = ""
    port = 8765

    def log_message(self, *a):
        pass

    # ---------- 基础 ----------
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, code, msg):
        self._json(code, {"ok": False, "error": msg})

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BODY:
            raise ReviewError(413, "请求体过大")
        try:
            obj = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError as e:
            raise ReviewError(400, f"JSON 解析失败: {e}")
        if not isinstance(obj, dict):
            raise ReviewError(400, "请求体必须是 JSON 对象")
        return obj

    def _check_origin_host(self):
        if self.headers.get("Host", "") != f"127.0.0.1:{self.port}":
            raise ReviewError(403, "非法 Host")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.port}":
            raise ReviewError(403, "非法 Origin")

    @staticmethod
    def _parts(path):
        return [p for p in urlparse(path).path.split("/") if p]

    # ---------- GET ----------
    def do_GET(self):
        try:
            parts = self._parts(self.path)
            q = parse_qs(urlparse(self.path).query)
            if self.path == "/ping":
                return self._json(200, {"ok": True, "service": "hc-aidw-review"})
            if len(parts) == 2 and parts[0] == "rt":
                body = (ROOT / "server" / "review-page.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")  # 防浏览器缓存旧页面
                self.end_headers()
                self.wfile.write(body)
                return
            if len(parts) == 3 and parts[:2] == ["api", "review"]:      # 浏览器
                rid, tok = parts[2], (q.get("t", [""])[0] or
                                      self.headers.get("X-Review-Token", ""))
                s = self.store.get_review(rid)
                if tok != s.get("url_token"):
                    raise ReviewError(403, "访问令牌无效")
                if "wait" in q:
                    sig = self.store.wait_signal(
                        rid, int(q.get("revision", [s["current_revision"]])[0]),
                        int(q.get("feedback", [self._pending(s)])[0]),
                        float(q.get("timeout", [25])[0]))
                    return self._json(200, {"ok": True, **sig})
                return self._json(200, {"ok": True, **self._browser_view(s)})
            if len(parts) == 4 and parts[:3] == ["api", "agent", "reviews"]:  # Agent
                self._require_agent()
                s = self.store.get_review(parts[3])
                if "wait" in q:
                    sig = self.store.wait_signal(
                        parts[3], int(q.get("revision", [s["current_revision"]])[0]),
                        int(q.get("feedback", [self._pending(s)])[0]),
                        float(q.get("timeout", [25])[0]))
                    return self._json(200, {"ok": True, **sig})
                return self._json(200, {"ok": True, **self.store.agent_view(parts[3])})
            return super().do_GET()
        except ReviewError as e:
            return self._fail(e.code, e.message)
        except (ValueError, KeyError) as e:
            return self._fail(400, f"参数错误: {e}")

    # ---------- POST ----------
    def do_POST(self):
        try:
            self._check_origin_host()
            parts = self._parts(self.path)
            body = self._body()
            # 创建审核任务:/api/agent/reviews
            if parts == ["api", "agent", "reviews"]:
                self._require_agent()
                r = self.store.create_review(body.get("type", "requirement-review"),
                                             body.get("title", ""),
                                             body.get("content", {}),
                                             body.get("context"))
                url = f"http://127.0.0.1:{self.port}/rt/{r['review_id']}?t={r['url_token']}"
                return self._json(200, {"ok": True, **r, "url": url})
            # 发布新版本:/api/agent/reviews/<id>/publish
            if len(parts) == 5 and parts[:3] == ["api", "agent", "reviews"] \
                    and parts[4] == "publish":
                self._require_agent()
                r = self.store.publish_revision(
                    parts[3], int(body.get("base_revision", 0)),
                    body.get("content", {}), body.get("change_summary") or [],
                    body.get("evidence") or [])
                self.store.mark_addressed(parts[3], body.get("addressed"), r["revision"])
                s = self.store.agent_view(parts[3])
                return self._json(200, {"ok": True, "revision": r["revision"],
                                        "status": s["status"],
                                        "change_summary": r["change_summary"]})
            # 浏览器:/api/review/<id>/{feedback,confirm}
            if len(parts) == 4 and parts[:2] == ["api", "review"]:
                rid, action, q = parts[2], parts[3], parse_qs(urlparse(self.path).query)
                tok = q.get("t", [""])[0] or self.headers.get("X-Review-Token", "")
                if action == "feedback":
                    item = self.store.add_feedback(
                        rid, tok, body.get("text", ""), step=body.get("step"),
                        step_name=body.get("step_name", ""), target=body.get("target", ""))
                    return self._json(200, {"ok": True, "feedback": item})
                if action == "confirm":
                    rec = self.store.confirm(rid, tok, int(body.get("ack_revision", 0)))
                    return self._json(200, {"ok": True, "decision": rec})
            return self._fail(404, "未知端点")
        except ReviewError as e:
            return self._fail(e.code, e.message)
        except (ValueError, KeyError) as e:
            return self._fail(400, f"参数错误: {e}")

    def _require_agent(self):
        if self.headers.get("X-Agent-Token") != self.agent_token:
            raise ReviewError(403, "Agent 令牌无效")

    @staticmethod
    def _pending(s):
        return sum(1 for f in s.get("feedback", []) if f["status"] == "pending")

    @staticmethod
    def _browser_view(s):
        """浏览器视图:全量状态 + 最新版本内容平铺为 content。"""
        v = dict(s)
        v["content"] = s["revisions"][-1]["content"] if s.get("revisions") else {}
        return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    Handler.agent_token = load_or_create_agent_token()
    Handler.port = args.port
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"HC-AIDW 审核服务: http://127.0.0.1:{args.port}/  (Ctrl+C 停止)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
