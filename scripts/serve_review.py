#!/usr/bin/env python3
"""HC-AIDW 审核壳本地服务。

用法:
    python scripts/serve_review.py            # http://127.0.0.1:8765/
    python scripts/serve_review.py --port 9000
    python scripts/serve_review.py --selftest # 自检后退出

端点:
    GET  /…      静态文件(仓库根目录)
    GET  /ping   {"ok": true} —— 审核页据此判断是否处于服务模式
    POST /submit 把意见 JSON 保存为 reviews/<doc>/feedback/feedback-<时间戳>.json

治理约定(见 AGENTS.md):本服务只保存意见,绝不修改事实源 JSON。
"""
import datetime
import json
import sys
import threading
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):  # 静音访问日志
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/ping":
            self._send(200, json.dumps({"ok": True}).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/submit":
            self._send(404, b'{"error": "not found"}')
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            self._send(400, json.dumps({"error": f"bad json: {e}"}).encode())
            return
        doc = str(data.get("doc", "unknown")).replace("/", "_").replace("..", "_")
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        outdir = ROOT / "reviews" / doc / "feedback"
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"feedback-{ts}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._send(200, json.dumps({"ok": True, "saved": str(out.relative_to(ROOT))}).encode())


def selftest() -> int:
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    ping = json.loads(urllib.request.urlopen(base + "/ping").read())
    assert ping == {"ok": True}, ping
    body = json.dumps({"doc": "lab-module", "selftest": True}).encode()
    req = urllib.request.Request(base + "/submit", data=body,
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    assert resp["ok"], resp
    saved = ROOT / resp["saved"]
    assert json.loads(saved.read_text(encoding="utf-8"))["selftest"] is True
    saved.unlink()  # 清理自检产物
    srv.shutdown()
    print("selftest OK: ping + submit 均通过,产物已清理")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    port = 8765
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    srv = HTTPServer(("127.0.0.1", port), Handler)
    print(f"审核服务已启动: http://127.0.0.1:{port}/reviews/lab-module/requirement-review.v1.html")
    print("意见将保存到 reviews/lab-module/feedback/ ;Ctrl+C 停止。")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
