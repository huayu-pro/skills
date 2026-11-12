#!/usr/bin/env python3
"""触发边界冒烟评测：用词法概念匹配检验 description 覆盖与触发用例。

算法移植自 qiaomu-meta-skill 的 trigger_eval.py：概念组命中取「用例命中 ∩ description 命中」，
按阈值打分，负向模式一票否决。词法评分只是冒烟测试——模型级触发仍需人工或子代理走查。

用法：python3 run_trigger_eval.py [技能目录] [--cases evals/trigger_cases.json] [--output 报告路径]
退出码：0 全部通过；2 存在失败项、用例文件缺失或用例文件格式非法（含空桶空转）；未捕获异常以非零退出。
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text, flags=re.UNICODE)
    # 中英文交界处补空格，否则「写个skill」这类混排无法命中词边界匹配的英文关键词
    text = re.sub(r"([\u4e00-\u9fff])([a-z0-9])", r"\1 \2", text)
    text = re.sub(r"([a-z0-9])([\u4e00-\u9fff])", r"\1 \2", text)
    return re.sub(r"\s+", " ", text).strip()


def phrase_present(text, phrase):
    phrase = normalize(phrase)
    if not phrase:
        return False
    if re.search(r"[\u4e00-\u9fff]", phrase):
        return phrase in text
    return f" {phrase} " in f" {text} "


def parse_description(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text
    lines = text.splitlines()
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return text
    frontmatter_text = "\n".join(lines[1:end])
    if yaml is not None:
        payload = yaml.safe_load(frontmatter_text) or {}
        if isinstance(payload, dict):
            return str(payload.get("description", ""))
    match = re.search(r"description:\s*\|?\s*(.*)", frontmatter_text)
    return match.group(1).strip() if match else text


def concept_hits(text, concepts):
    normalized = normalize(text)
    return [name for name, phrases in concepts.items()
            if any(phrase_present(normalized, p) for p in phrases)]


def negative_hit(text, patterns):
    normalized = normalize(text)
    for pattern in patterns:
        if phrase_present(normalized, pattern):
            return pattern
    return None


def case_items(cases, bucket):
    items = []
    for raw in cases.get(bucket, []):
        if isinstance(raw, str):
            items.append({"text": raw, "family": "default"})
        elif isinstance(raw, dict):
            item = dict(raw)
            item.setdefault("family", "default")
            items.append(item)
    return items


def evaluate(root, cases_path):
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(cases, dict):
        return {"ok": False, "fatal": f"用例文件顶层必须是 JSON 对象，实际为 {type(cases).__name__}",
                "summary": {"total": 0, "passed": 0, "pass_rate": 0},
                "failures": [], "results": {}}
    concepts = cases.get("positive_concepts") or {}
    try:
        threshold = float(cases.get("recommended_threshold", 0.34))
    except (TypeError, ValueError):
        return {"ok": False,
                "fatal": f"recommended_threshold 不是数字：{cases.get('recommended_threshold')!r}",
                "summary": {"total": 0, "passed": 0, "pass_rate": 0},
                "failures": [], "results": {}}
    negative_patterns = list(cases.get("negative_patterns", []))
    description = parse_description(root / "SKILL.md")
    description_hits = set(concept_hits(description, concepts))
    required = set(cases.get("description_required_concepts", ["skill"]))
    missing_description = sorted(required - description_hits)

    buckets = ["should_trigger", "should_not_trigger", "near_neighbor"]
    failures, total, passed = [], 0, 0
    results = {}
    denominator = max(3, min(5, len(description_hits) or len(concepts)))

    for bucket in buckets:
        expected = bucket == "should_trigger"
        results[bucket] = []
        for item in case_items(cases, bucket):
            prompt = str(item.get("text", ""))
            hits = set(concept_hits(prompt, concepts))
            matched = sorted(hits & description_hits)
            neg = negative_hit(prompt, negative_patterns)
            score = min(1.0, len(matched) / denominator)
            predicted = score >= threshold and neg is None
            ok = predicted == expected
            record = {
                "prompt": prompt,
                "family": item.get("family", "default"),
                "expected_trigger": expected,
                "predicted_trigger": predicted,
                "passed": ok,
                "score": round(score, 3),
                "matched_concepts": matched,
                "negative_pattern": neg,
            }
            results[bucket].append(record)
            total += 1
            if ok:
                passed += 1
            else:
                failures.append({"bucket": bucket,
                                 "kind": "false_negative" if expected else "false_positive",
                                 **record})

    # 空桶空转 = 没有评测：0 条用例的「全过」与全绿不可区分，按失败处理
    return {
        "ok": not missing_description and not failures and total > 0,
        "empty": total == 0,
        "fatal": None,
        "threshold": threshold,
        "description_concepts": sorted(description_hits),
        "missing_description_concepts": missing_description,
        "summary": {"total": total, "passed": passed,
                    "pass_rate": round(passed / total, 3) if total else 0},
        "failures": failures,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="触发边界冒烟评测（词法）")
    parser.add_argument("skill_dir", nargs="?", default=".", help="技能目录")
    parser.add_argument("--cases", default="evals/trigger_cases.json", help="用例 JSON 路径")
    parser.add_argument("--output", "-o", help="JSON 报告写出路径")
    args = parser.parse_args()

    root = Path(args.skill_dir).resolve()
    cases_path = Path(args.cases)
    if not cases_path.is_absolute():
        cases_path = root / cases_path
    if not cases_path.exists():
        print(f"[失败] 找不到用例文件：{cases_path}")
        sys.exit(2)

    result = evaluate(root, cases_path)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")

    summary = result["summary"]
    if result.get("fatal"):
        print(f"[失败] {result['fatal']}")
        print("结论：触发冒烟评测未通过（用例文件格式非法）")
        sys.exit(2)
    print(f"用例 {summary['total']} 条，通过 {summary['passed']} 条"
          f"（通过率 {summary['pass_rate']:.0%}）")
    if result.get("empty"):
        print("[失败] 用例为 0 条——评测空转不等于通过，先补真实正负用例")
    if result["missing_description_concepts"]:
        print("[失败] description 缺少必需概念组："
              + ", ".join(result["missing_description_concepts"]))
    for f in result["failures"]:
        kind = "漏触发" if f["kind"] == "false_negative" else "误触发"
        print(f"[失败] {kind}（{f['bucket']}/{f['family']}）：{f['prompt']}"
              f"｜命中概念 {f['matched_concepts']}｜负向 {f['negative_pattern']}")
    if result["ok"]:
        print("结论：触发冒烟评测通过")
        sys.exit(0)
    print("结论：触发冒烟评测未通过（注意：词法评分是冒烟测试，"
          "模型级触发仍需人工或子代理走查）")
    sys.exit(2)


if __name__ == "__main__":
    main()
