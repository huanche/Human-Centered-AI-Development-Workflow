#!/usr/bin/env python3
"""审核任务监视器:发现待处理意见即退出,让会话代理收到通知并及时回应。

用法:
    python scripts/watch_feedback.py <review_id> [间隔秒]

直接读状态文件(不走 HTTP,不受代理影响),每 20 秒检查一次;
发现 pending 意见或人工确认后打印摘要并以退出码 0 结束。
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
from store import ReviewStore  # noqa: E402


def main() -> int:
    rid = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    store = ReviewStore()
    seen_pending = None
    seen_decisions = None
    while True:
        s = store.get_review(rid)
        pending = [f for f in s["feedback"] if f["status"] == "pending"]
        if len(pending) != seen_pending or len(s["decisions"]) != seen_decisions:
            print(json.dumps({
                "review_id": rid,
                "revision": s["current_revision"],
                "status": s["status"],
                "pending_feedback": [f["text"][:100] for f in pending],
                "decisions": len(s["decisions"]),
            }, ensure_ascii=False), flush=True)
            # 首轮仅记录基线不退出;出现新增意见或新确认才退出
            if seen_pending is not None and (len(pending) != seen_pending):
                return 0
            if seen_decisions is not None and len(s["decisions"]) != seen_decisions:
                return 0
            seen_pending = len(pending)
            seen_decisions = len(s["decisions"])
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
