#!/usr/bin/env python3
"""HC-AIDW 审核 JSON 变更回执(评审 diff)。

用法:
    python diff_review.py <old.json> <new.json>

输出两版审核文档之间的变更清单(人话,可直接贴给用户):
  - restatement/scope 变化
  - 角色增删改
  - 流程步骤增删改
  - 待确认问题的新增/已答
  - 用户意见的新增/已解决
  - 方案/步骤/风险变化(architecture-review)
  - 勾稽表状态变化(verification-report)

退出码:0 = 有差异或无差异(正常完成),2 = 用法/文件错误。
"""
import json
import sys
from pathlib import Path


def load(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"文件不存在: {p}")
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def by_id(items, key="id"):
    return {x[key]: x for x in items or [] if isinstance(x, dict) and key in x}


def set_diff(old_items, new_items, name, key="id", label=str):
    lines = []
    old, new = by_id(old_items, key), by_id(new_items, key)
    for id_ in new.keys() - old.keys():
        lines.append(f"+ {name}新增 [{id_}]: {label(new[id_])}")
    for id_ in old.keys() - new.keys():
        lines.append(f"- {name}删除 [{id_}]: {label(old[id_])}")
    for id_ in new.keys() & old.keys():
        if old[id_] != new[id_]:
            lines.append(f"~ {name}修改 [{id_}]: {label(new[id_])}")
    return lines


def field_changed(old, new, field, note):
    if (old or {}).get(field) != (new or {}).get(field):
        return f"~ {note} 变化"
    return None


def diff(old, new):
    lines = []
    if old.get("type") != new.get("type"):
        return [f"type 变化: {old.get('type')} -> {new.get('type')},无法比对"]
    lines.append(f"status: {old.get('status')} -> {new.get('status')}" if old.get("status") != new.get("status") else None)

    if new.get("type") == "requirement-review":
        for f, note in [("restatement", "需求重述"), ("expected_effect", "预期效果"), ("prototype", "原型")]:
            lines.append(field_changed(old, new, f, note))
        lines += set_diff(old.get("actors"), new.get("actors"), "角色", label=lambda x: x.get("name", ""))
        for f_old, f_new in [(old.get("flows") or [], new.get("flows") or [])]:
            steps_old = [s for fl in f_old for s in fl.get("steps", [])]
            steps_new = [s for fl in f_new for s in fl.get("steps", [])]
            lines += set_diff(steps_old, steps_new, "流程步骤", label=lambda x: x.get("action", ""))
        oq_old, oq_new = by_id(old.get("open_questions")), by_id(new.get("open_questions"))
        for id_ in oq_new.keys() - oq_old.keys():
            lines.append(f"+ 待确认问题新增 [{id_}]: {oq_new[id_].get('question', '')}")
        for id_ in oq_new.keys() & oq_old.keys():
            was, now = oq_old[id_].get("answer"), oq_new[id_].get("answer")
            if was != now:
                lines.append(f"~ 问题 [{id_}] 已作答: {now}" if now else f"~ 问题 [{id_}] 答案被清空")
    elif new.get("type") == "architecture-review":
        lines += set_diff(old.get("options"), new.get("options"), "候选方案", label=lambda x: x.get("summary", ""))
        lines.append(f"推荐方案: {old.get('recommended')} -> {new.get('recommended')}" if old.get("recommended") != new.get("recommended") else None)
        lines += set_diff(old.get("steps"), new.get("steps"), "实施步骤", label=lambda x: x.get("name", ""))
        lines += set_diff(old.get("risks"), new.get("risks"), "风险", label=lambda x: x.get("desc", ""))
    elif new.get("type") == "verification-report":
        lines += set_diff(old.get("traceability"), new.get("traceability"), "勾稽条目", label=lambda x: f"{x.get('requirement_item','')} -> {x.get('status','')}")
        lines += set_diff(old.get("open_items"), new.get("open_items"), "遗留问题", label=lambda x: x.get("desc", ""))

    fb_old, fb_new = by_id((old.get("feedback") or []), "target"), by_id((new.get("feedback") or []), "target")
    for id_ in fb_new.keys() - fb_old.keys():
        lines.append(f"+ 新增用户意见 @[{id_}]: {fb_new[id_].get('comment', '')}")
    for id_ in fb_new.keys() & fb_old.keys():
        if not fb_old[id_].get("resolved") and fb_new[id_].get("resolved"):
            lines.append(f"√ 意见已处理 @[{id_}]")

    return [l for l in lines if l]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    old, new = load(sys.argv[1]), load(sys.argv[2])
    lines = diff(old, new)
    if not lines:
        print("两版文档无差异")
    else:
        print(f"变更回执({len(lines)} 条):")
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
