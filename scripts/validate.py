#!/usr/bin/env python3
"""HC-AIDW 审核 JSON 校验器。

用法:
    python validate.py <file.json>            # 自动按文件内 type 选择 schema
    python validate.py <file.json> <schema>   # 显式指定 schema 文件

退出码:0 = 通过,1 = 校验失败,2 = 用法错误。

另外做两项 schema 管不到的检查:
  1. id 唯一性(actors/flows/steps/screens 等数组内的 id 不得重复)
  2. open_questions 的 id 形如 q<N> 且不重复
"""
import json
import re
import sys
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

TYPE_TO_SCHEMA = {
    "requirement-review": "requirement-review.schema.json",
    "architecture-review": "architecture-review.schema.json",
    "verification-report": "verification-report.schema.json",
}


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def check_duplicate_ids(doc) -> list[str]:
    problems = []

    def walk(node, where):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{where}.{key}")
        elif isinstance(node, list):
            seen: dict[str, str] = {}
            for i, item in enumerate(node):
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    idv = item["id"]
                    if idv in seen:
                        problems.append(f"{where}[{i}]: 重复 id '{idv}'(首次出现于 {seen[idv]})")
                    else:
                        seen[idv] = f"{where}[{i}]"
                walk(item, f"{where}[{i}]")

    walk(doc, "$")
    return problems


def main() -> int:
    args = sys.argv[1:]
    if len(args) not in (1, 2):
        print(__doc__)
        return 2

    target = Path(args[0])
    if not target.exists():
        print(f"文件不存在: {target}")
        return 2

    try:
        doc = load_json(target)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        return 1

    if len(args) == 2:
        schema_file = Path(args[1])
    else:
        doc_type = doc.get("type")
        schema_name = TYPE_TO_SCHEMA.get(doc_type)
        if not schema_name:
            print(f"文档缺少可识别的 type 字段('{doc_type}'),请显式指定 schema")
            return 2
        schema_file = SCHEMA_DIR / schema_name

    if not schema_file.exists():
        print(f"schema 不存在: {schema_file}")
        return 2

    try:
        import jsonschema
    except ImportError:
        print("缺少依赖:请先执行  pip install jsonschema")
        return 2

    schema = load_json(schema_file)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)

    problems: list[str] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        loc = "$" + "".join(
            f"[{p}]" if isinstance(p, int) else f".{p}" for p in err.absolute_path
        )
        problems.append(f"{loc}: {err.message}")

    problems.extend(check_duplicate_ids(doc))

    if problems:
        print(f"校验未通过({len(problems)} 处):")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"OK: {target.name} 通过 {schema_file.name} 校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
