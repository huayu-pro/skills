#!/usr/bin/env python3
"""Query the distilled design-pattern corpus.

Usage
  query_corpus.py --list                          all archetypes
  query_corpus.py --style minimal --genre saas    filter
  query_corpus.py --color dark --limit 5
  query_corpus.py --id arch-b63c5c                show one card (use --list)
  query_corpus.py --brands                        list bundled brand DESIGN.md files
  query_corpus.py --brand linear.app --section colors
  query_corpus.py --motion --family F3            list motion assets in one family
  query_corpus.py --motion --kind components      list motion components
  query_corpus.py --stats                         corpus-wide statistics

Matching is scored, not filtered: every archetype gets a score and the ranked
list is returned with the reasons. A filter that silently returns nothing is
worse than a ranked near-miss, because the caller then invents a design with no
reference at all.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "assets" / "patterns"
BRANDS = ROOT / "assets" / "brands.json"
MOTION = ROOT / "assets" / "motion"


def load() -> dict:
    p = PATTERNS / "archetypes.json"
    if not p.exists():
        sys.exit("archetypes.json missing — run the distill pipeline first")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit("archetypes.json invalid JSON: %s" % exc)


def load_methods() -> dict:
    p = PATTERNS / "methods.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def score(a: dict, style: str, genre: str, color: str, mood: str) -> tuple[float, list[str]]:
    s = 0.0
    why = []
    styles = dict(a.get("styles") or [])
    genres = dict(a.get("genres") or [])
    colors = dict(a.get("colors") or [])
    n = max(a["n"], 1)

    if style:
        hit = styles.get(style, 0)
        if hit:
            s += 3.0 * hit / n
            why.append(f"style={style} 出现 {hit}/{n}")
    if genre:
        hit = genres.get(genre, 0)
        if hit:
            s += 3.0 * hit / n
            why.append(f"genre={genre} 出现 {hit}/{n}")
    if color:
        hit = colors.get(color, 0)
        if hit:
            s += 2.5 * hit / n
            why.append(f"color={color} 出现 {hit}/{n}")

    p = a["profile"]
    if mood:
        m = mood.lower()
        if m in ("dark", "暗色", "深色"):
            s += 2.0 * p.get("dark", 0)
            why.append(f"暗色占比 {p.get('dark', 0):.2f}")
        elif m in ("light", "浅色", "亮色"):
            s += 2.0 * p.get("light", 0)
            why.append(f"浅色占比 {p.get('light', 0):.2f}")
        elif m in ("vivid", "高饱和", "鲜艳"):
            s += 2.0 * p.get("chroma", 0)
            why.append(f"饱和度 {p.get('chroma', 0):.2f}")
        elif m in ("muted", "低饱和", "克制"):
            s += 2.0 * (1 - p.get("chroma", 0))
            why.append(f"饱和度 {p.get('chroma', 0):.2f}")
        elif m in ("tight", "紧凑", "密集"):
            s += 1.5 * (1 - min(p.get("ratio", 1.25) / 1.6, 1))
            why.append(f"字阶比 {p.get('ratio', 0):.2f}")
        elif m in ("dramatic", "大跨度", "强对比"):
            s += 1.5 * min(p.get("ratio", 1.25) / 1.6, 1)
            why.append(f"字阶比 {p.get('ratio', 0):.2f}")

    # a larger sample is more trustworthy
    s += 0.4 * min(a["n"] / 60, 1)
    return s, why


def cmd_list(args) -> int:
    data = load()
    arch = data["archetypes"]
    if not any([args.style, args.genre, args.color, args.mood]):
        for a in arch:
            p = a["profile"]
            print(f"{a['id']}  {a['name']}  (n={a['n']}, "
                  f"dark={p['dark']:.2f}, chroma={p['chroma']:.2f}, "
                  f"ratio={p['ratio']:.2f})")
        return 0

    ranked = []
    for a in arch:
        s, why = score(a, args.style, args.genre, args.color, args.mood)
        ranked.append((s, a, why))
    ranked.sort(key=lambda x: -x[0])
    matched = [r for r in ranked if r[0] > 0.5]

    if not matched:
        # Print the banner and stop. Showing a ranked list underneath would
        # contradict the banner and invite the caller to use a non-match.
        print("# 无匹配原型\n")
        print("没有原型的特征与查询匹配。按 SKILL.md 的要求：明确说明"
              "「无匹配原型，走自由方向」，并在约束简报里写出自己的 token 系统。\n")
        print("最接近的（仅供参考，不要当作匹配）：")
        for s_, a, _why in ranked[:2]:
            print(f"  {a['id']}  {a['name']}  score={s_:.2f}  — 低于阈值 0.50")
        return 0
    top = matched[: args.limit]

    for s, a, why in top:
        p = a["profile"]
        print(f"\n{a['id']}  {a['name']}   score={s:.2f}  n={a['n']}")
        print(f"  {a['description']}")
        print(f"  明暗 dark={p['dark']:.2f} light={p['light']:.2f}　"
              f"饱和={p['chroma']:.2f}　字阶比={p['ratio']:.2f}")
        if why:
            print("  匹配理由：" + "；".join(why))
        print(f"  卡片：assets/patterns/patterns.md#{a['id']}")
    return 0


def cmd_show(args) -> int:
    consolidated = PATTERNS / "patterns.md"
    if consolidated.exists():
        text = consolidated.read_text(encoding="utf-8")
        import re
        m = re.search(rf"<!-- ARCH:{re.escape(args.id)} -->(.*?)<!-- /ARCH:{re.escape(args.id)} -->", text, re.S)
        if not m:
            sys.exit(f"no such archetype: {args.id} (try --list)")
        print(m.group(1).strip())
        return 0
    card = PATTERNS / f"{args.id}.md"
    if not card.exists():
        sys.exit(f"no such archetype: {args.id} (try --list)")
    print(card.read_text(encoding="utf-8"))
    return 0


def cmd_stats(args) -> int:
    m = load_methods()
    if not m:
        sys.exit("methods.json missing — run the distill pipeline first")
    print(f"语料：{m['sites_analyzed']} 个站点可分析 / 目录 {m['sites_in_catalog']} 条（抽取成功 412）\n")
    print("明暗分布：", m["dark_vs_light"])
    print("字阶比值：", m["type_scale_ratios"])
    print("主色色度：", m["chroma_distribution"])
    print("间距基数：", m["spacing_bases"])
    print("材质语言：", m["materials"])
    print("图像风格：", m["imagery"])
    for key, label in (("top_styles", "风格"), ("top_genres", "类型"),
                       ("top_colors", "颜色"), ("top_tech", "技术栈"),
                       ("top_typefaces", "字体"), ("top_sections", "区块")):
        vals = m.get(key) or []
        if vals:
            print(f"\n{label} Top {min(10, len(vals))}：")
            for name, n in vals[:10]:
                print(f"  {n:4d}  {name}")
    return 0


def cmd_brands(args) -> int:
    rows = []
    if BRANDS.is_file():
        payload = json.loads(BRANDS.read_text(encoding="utf-8"))
        rows = payload.get("brands", [])
        texts = {r["brand"]: r.get("content", "") for r in rows}
    else:
        idx = BRANDS / "index.json"
        rows = json.loads(idx.read_text(encoding="utf-8")) if idx.exists() else []
        texts = {}
    if not rows:
        sys.exit("assets/brands.json missing")
    if not args.brand:
        for r in rows:
            print(f"{r['brand']:<18} {r['color_tokens']:>3} color tokens  "
                  f"{r['name'][:40]}")
        return 0
    if args.brand not in texts:
        sys.exit(f"no such brand: {args.brand} (try --brands)")
    text = texts[args.brand]
    if args.section:
        # print only the requested top-level block
        import re
        m = re.search(rf"^{args.section}:\s*\n((?:[ \t]+.*\n|\n)*)", text, re.M)
        if m:
            print(f"{args.section}:")
            print(m.group(1).rstrip())
            return 0
        print(f"section {args.section!r} not found; printing whole file", file=sys.stderr)
    print(text)
    return 0


def cmd_motion(args) -> int:
    index_path = MOTION / "index.json"
    if not index_path.exists():
        sys.exit("motion/index.json missing")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    rows = []
    for kind in ("kits", "components", "merged", "prompts", "keyframes", "snippets"):
        for item in data.get(kind, []):
            item = dict(item)
            item["kind"] = kind
            rows.append(item)
    if args.family:
        rows = [r for r in rows if r.get("family") == args.family]
    if args.kind:
        rows = [r for r in rows if r.get("kind") == args.kind]
    if args.query:
        needle = args.query.lower()
        rows = [r for r in rows
                if needle in json.dumps(r, ensure_ascii=False).lower()]
    if not rows:
        print("# 无匹配动效资产\n")
        print("放宽 --family / --kind / --query；可先跑 `--motion` 看全部。")
        return 0
    for row in rows[: max(1, args.limit)]:
        path = row.get("path") or ""
        print("%-9s %-4s %-28s %s" % (
            row["kind"], row.get("family", "-"), row.get("id", "-"), path))
        if row.get("summary"):
            print("          %s" % row["summary"])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list archetypes (optionally filtered)")
    ap.add_argument("--id", help="print one archetype card")
    ap.add_argument("--style", help="design style slug, e.g. minimal")
    ap.add_argument("--genre", help="genre slug, e.g. saas")
    ap.add_argument("--color", help="color slug, e.g. dark")
    ap.add_argument("--mood", help="dark|light|vivid|muted|tight|dramatic")
    ap.add_argument("--limit", type=int, default=3,
                    help="max archetypes to print (>= 1)")
    ap.add_argument("--stats", action="store_true", help="corpus statistics")
    ap.add_argument("--brands", action="store_true", help="list bundled brands")
    ap.add_argument("--brand", help="print one brand DESIGN.md")
    ap.add_argument("--section", help="with --brand: print one top-level block")
    ap.add_argument("--motion", action="store_true", help="list motion assets")
    ap.add_argument("--family", help="with --motion: F1..F14")
    ap.add_argument("--kind", choices=["kits", "components", "merged", "prompts",
                                       "keyframes", "snippets"],
                    help="with --motion: asset kind")
    ap.add_argument("--query", help="with --motion: substring filter")
    args = ap.parse_args()
    if args.limit < 1:
        ap.error("--limit must be >= 1")

    if args.motion:
        return cmd_motion(args)
    if args.stats:
        return cmd_stats(args)
    if args.brands or args.brand:
        return cmd_brands(args)
    if args.id:
        return cmd_show(args)
    return cmd_list(args)


if __name__ == "__main__":
    sys.exit(main())
