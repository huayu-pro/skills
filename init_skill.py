#!/usr/bin/env python3
"""脚手架：按 skill-creator-cn 规范初始化一个新技能目录。

只创建最小有用集（SKILL.md + evals/trigger_cases.json 骨架），脚手架开箱即通过
validate_skill.py；references/scripts/assets 不预建，挣到时再建。

用法：python3 init_skill.py <skill-name> [--path <父目录>]
退出码：0 成功；1 失败；2 参数错误。
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_TEMPLATE = """---
name: {name}
description: 做什么（一句话）。Use when（用户会怎么说的原话措辞，中英文各至少一条）。Exclude（不该触发的相邻场景）。
metadata:
  version: 0.1.0
---

# {title}

两三句定位：让 agent 能做什么，核心原则是什么。

## 步骤

1. **第一步**——做什么、怎么做（祈使句，解释 why，命令放 bash 代码块）。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 待补 | 待补 |

## 验证清单

- [ ] 待补：可观察的验收项
"""

CASES_TEMPLATE = {
    "recommended_threshold": 0.34,
    "description_required_concepts": ["skill"],
    "positive_concepts": {
        "skill": ["skill", "技能", "技能包", "SKILL.md"],
        "domain_action": ["待补：领域动词"],
    },
    "negative_patterns": ["翻译一下", "只要总结"],
    "should_trigger": [
        {"text": "待补：应触发的一条真实用户原话", "family": "todo"},
        {"text": "待补：应触发的第二条原话", "family": "todo"},
    ],
    "should_not_trigger": [
        {"text": "待补：不应触发的一条近邻原话", "family": "todo"},
    ],
    "near_neighbor": [],
}


def validate_name(name):
    if not name or not re.fullmatch(r"[a-z0-9-]+", name):
        return False, f"name 不符合 kebab-case：{name!r}"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"name 连字符使用不合规：{name}"
    if len(name) > 64:
        return False, f"name 超过 64 字符：{len(name)}"
    return True, ""


def main():
    parser = argparse.ArgumentParser(description="初始化新技能脚手架")
    parser.add_argument("name", help="技能名（kebab-case）")
    parser.add_argument("--path", type=Path, default=Path.cwd(), help="父目录（默认当前目录）")
    args = parser.parse_args()

    ok, error = validate_name(args.name)
    if not ok:
        print(f"[失败] {error}")
        sys.exit(2)

    parent = args.path.expanduser().resolve()
    if not parent.exists():
        print(f"[失败] 父目录不存在：{parent}")
        sys.exit(2)
    skill_dir = parent / args.name
    if skill_dir.exists():
        print(f"[失败] 目录已存在：{skill_dir}")
        sys.exit(1)

    title = " ".join(w.capitalize() for w in args.name.split("-"))
    (skill_dir / "evals").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        SKILL_TEMPLATE.format(name=args.name, title=title), encoding="utf-8")
    (skill_dir / "evals" / "trigger_cases.json").write_text(
        json.dumps(CASES_TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[通过] 脚手架已生成：{skill_dir}")
    validator = Path(__file__).resolve().parent / "validate_skill.py"
    if validator.exists():
        result = subprocess.run([sys.executable, str(validator), str(skill_dir)],
                                capture_output=True, text=True)
        print(result.stdout.strip())

    print(f"""
下一步：
  1. 编辑 {args.name}/SKILL.md：替换所有「待补」，description 写触发条件式（Use when + Exclude）
  2. 填写 evals/trigger_cases.json 的真实正负触发原话与领域关键词
  3. 出现确定性逻辑时建 scripts/，出现深度内容（逼近 500 行）时建 references/
  4. 跑校验与触发冒烟评测：
     python3 {validator} {skill_dir}
     python3 {Path(__file__).resolve().parent / 'run_trigger_eval.py'} {skill_dir}
""")


if __name__ == "__main__":
    main()
