#!/usr/bin/env bash
# selfcheck.sh —— ascii-web-design 技能包完整性自检。
#
# 覆盖范围（如实描述；用户交付物的验收在 scripts/verify_deliverable.py，不在本脚本）：
#   ① SKILL.md §7 第 17 条  章节编号连续无洞
#   ② SKILL.md §7 第 18 条  frontmatter 版本字段齐套
#   ③ SKILL.md §7 第 11 条  ASCII-safe（ramp 落在 32–126；字符产物无 CR、无非 ASCII）
#   ④ SKILL.md §7 第 24 条  包内自检本身（本脚本 + 触发用例 + 管线 self-test + 三端模板）
#   ⑤ 视觉契约单一事实源：三端 ramp 字符串逐字一致、纵横比 / 帧间隔 / 索引公式一致
#   ⑥ 引用完整性：SKILL.md 与 references 内引用的包内资源均存在
#   ⑦ Remotion 确定性红线：references 内 Remotion/TSX 示例代码块禁用 Math.random
#      （网页端 JS 示例合法，按围栏语言区分，不一刀切）
#   ⑧ 文档同步：SKILL.md §7 第 18 条写的命令与脚本实际用法一致
#
# 用法：bash scripts/selfcheck.sh [--verbose]   （任意位置运行均可）
# 退出码：0 全部通过；1 存在失败项。
set -u
cd "$(dirname "$0")/.." || exit 1          # 定位到技能包根目录
VERBOSE=0
[ "${1:-}" = "--verbose" ] && VERBOSE=1

FAIL=0
ok()   { printf '[通过] %s\n' "$1"; }
bad()  { printf '[失败] %s\n' "$1"; FAIL=1; }
note() { [ "$VERBOSE" = "1" ] && printf '[信息] %s\n' "$1"; return 0; }

# ── 1. SKILL.md 章节编号连续无洞（§7 第 17 条：0,1,1.1,1.2,2,3,4,5,6,7） ───────────
chapters=$(grep '^## ' SKILL.md | sed -E 's/^## *([0-9]+(\.[0-9]+)?)\.? .*/\1/' | paste -sd' ')
expected="0 1 1.1 1.2 2 3 4 5 6 7"
if [ "$chapters" = "$expected" ]; then ok "SKILL.md 章节编号连续（$chapters）"
else bad "章节编号偏离预期：实际[$(echo $chapters)] 期望[$expected]"; fi

# ── 2. frontmatter 版本字段齐套（§7 第 18 条） ─────────────────────────────────────
# version 位于 metadata 嵌套下，故必须用 `^ *version:`；`^version:` 会漏掉并假失败。
n=$(grep -c '^ *version:\|^ *last_verified:' SKILL.md)
[ "$n" = "2" ] && ok "version / last_verified 字段齐套（共 $n 处）" || bad "version/last_verified 计数异常：$n（应为 2）"

# 2b. §7 第 18 条文档里写的命令必须与上面实际用法一致（防止照抄文档命令假失败）
doc_cmd=$(grep -o "grep -c '\^[^']*' SKILL.md" SKILL.md | head -1)
if [ -n "$doc_cmd" ] && [ "$doc_cmd" = "grep -c '^ *version:\\|^ *last_verified:' SKILL.md" ]; then
  ok "§7 第 18 条文档命令与脚本实际命令一致"
else
  bad "§7 第 18 条文档命令与脚本不同步：文档[${doc_cmd:-未找到}]"
fi

# ── 3. 正文引用的包内资源必须存在（含 assets/，支持 ascii.{html,py,c} 花括号写法） ─
missing=$(python3 - SKILL.md references/*.md <<'PYEOF'
import pathlib, re, sys
PAT = re.compile(r"(?:references|scripts|evals|assets)/[\w\-./]+(?:\{[\w.,]+\})?")
missing = set()
for f in sys.argv[1:]:
    for tok in PAT.findall(pathlib.Path(f).read_text(encoding="utf-8")):
        tok = tok.rstrip("。，：）(（")
        if "{" in tok:                                   # a/b.{x,y,z} → a/b.x / a/b.y / a/b.z
            stem, opts = tok.split("{", 1)
            for opt in opts.rstrip("}").split(","):
                if not pathlib.Path(stem + opt).exists():
                    missing.add(stem + opt)
            continue
        if not pathlib.Path(tok).exists():
            missing.add(tok)
print(" ".join(sorted(missing)))
PYEOF
)
[ -z "$missing" ] && ok "正文引用的资源文件均存在" || bad "引用了不存在的文件：$missing"

# ── 4. 视觉契约单一事实源：三端 ramp 字符串逐字一致（§1.2） ──────────────────────
# 不数「命中几个文件」，而是抽出每一处的实际字符串并比对——改成别的串仍会被抓出。
RAMP_EXPECT=' .:-=+*#%@'
ramp_of() {  # $1=文件 $2=抽取用的正则（ERE）
  grep -oE "$2" "$1" 2>/dev/null | head -1 | sed -E "s/^[^'\"]*['\"]//; s/['\"].*$//"
}
r_skill=$(ramp_of SKILL.md "\`' [^'\`]{9}'\`")
r_pipe=$(ramp_of scripts/ascii_pipeline.py 'DEFAULT_RAMP = "[^"]*"')
r_html=$(ramp_of assets/templates/ascii.html "RAMP = '[^']*'")
r_py=$(ramp_of assets/templates/ascii.py 'RAMP = "[^"]*"')
r_c=$(ramp_of assets/templates/ascii.c '#define RAMP "[^"]*"')
r_ref=$(ramp_of references/image-to-ascii.md "const RAMP = '[^']*'")

for pair in "SKILL.md:$r_skill" "ascii_pipeline.py:$r_pipe" "ascii.html:$r_html" "ascii.py:$r_py" "ascii.c:$r_c" "image-to-ascii.md:$r_ref"; do
  file="${pair%%:*}"; val="${pair#*:}"
  if [ "$val" = "$RAMP_EXPECT" ]; then note "ramp 一致：$file = [$val]"
  else bad "ramp 偏离契约：$file = [$val]（契约 [$RAMP_EXPECT]）"; fi
done
[ "$r_skill" = "$RAMP_EXPECT" ] && [ "$r_pipe" = "$RAMP_EXPECT" ] && [ "$r_html" = "$RAMP_EXPECT" ] \
  && [ "$r_py" = "$RAMP_EXPECT" ] && [ "$r_c" = "$RAMP_EXPECT" ] && [ "$r_ref" = "$RAMP_EXPECT" ] \
  && ok "经典 10 级 ramp 在 SKILL.md / 管线 / 三端骨架 / 图像内核 6 处逐字一致"

# 4b. 纵横比与帧间隔契约
grep -q "ASPECT = 0.55" scripts/ascii_pipeline.py && grep -q "ASPECT = 0.55" assets/templates/ascii.py \
  && grep -q "ASPECT_NUM 55" assets/templates/ascii.c && grep -q "ASPECT = 0.55" assets/templates/ascii.html \
  && ok "纵横比 0.55 在管线与三端骨架一致" || bad "纵横比偏离契约（应 0.55）"
grep -q "FPS_DELAY = 1 / 12" references/terminal-templates.md \
  && grep -q "FPS = 12" assets/templates/ascii.py && grep -q "FPS = 12" assets/templates/ascii.html \
  && grep -q "#define FPS 12" assets/templates/ascii.c \
  && ok "帧间隔 1/12s 在模板文档与三端骨架一致" || bad "帧间隔偏离契约（应 1/12s）"

# 4c. 亮度→字符索引公式 floor(lum×(n−1)) 三端 + 管线 + 文档一致（§1.2 明文公式）
idx_bad=""
grep -q 'int(lum \* (n - 1))' scripts/ascii_pipeline.py || idx_bad="$idx_bad 管线"
grep -q 'lum \* (n - 1)' references/terminal-templates.md || idx_bad="$idx_bad Python模板"
grep -q 'RAMP.length - 1' references/image-to-ascii.md || idx_bad="$idx_bad 图像内核"
grep -q 'RAMP.length - 1' references/web-implementation.md || idx_bad="$idx_bad GIF内核"
grep -q 'RAMP.length - 1' references/remotion-video.md || idx_bad="$idx_bad Remotion"
grep -q 'RAMP.length - 1' assets/templates/ascii.html || idx_bad="$idx_bad HTML骨架"
grep -q '(len(RAMP) - 1)' assets/templates/ascii.py || idx_bad="$idx_bad Python骨架"
grep -q '((int)strlen(RAMP) - 1)' assets/templates/ascii.c || idx_bad="$idx_bad C骨架"
grep -q 'floor(lum × (n−1))' SKILL.md || idx_bad="$idx_bad 契约表"
[ -z "$idx_bad" ] && ok "索引公式 floor(lum×(n−1)) 在契约表 + 管线 + 三端 + 4 篇文档一致" \
  || bad "索引公式偏离契约的位置：$idx_bad"
# 反例守卫：管线里不得再出现旧的 ×n 写法
grep -q 'int(lum \* n)' scripts/ascii_pipeline.py && bad "管线仍存在旧的 ×n 索引写法" || true

# ── 5. 管线脚本自检（§7 第 20 条后半，含索引公式断言） ───────────────────────────
if python3 scripts/ascii_pipeline.py self-test >/dev/null 2>&1; then
  ok "ascii_pipeline.py self-test 通过（含 ramp 索引公式断言）"
else bad "ascii_pipeline.py self-test 失败（python3 scripts/ascii_pipeline.py self-test 查看）"; fi

# ── 6. 触发用例 JSON 可解析（Production 档） ─────────────────────────────────────
if python3 -c "import json,sys; d=json.load(open('evals/trigger_cases.json')); sys.exit(0 if d.get('should_trigger') and d.get('should_not_trigger') else 1)" 2>/dev/null; then
  ok "evals/trigger_cases.json 可解析且正负例齐备"
else bad "trigger_cases.json 缺失/非法/正负例不齐"; fi

# ── 7. Remotion 确定性红线（§7 第 19 条精神） ─────────────────────────────────────
# 判定规则：扫描 references/ 下**全部** .md，只看 ```tsx / ```ts / ```jsx 围栏
# （Remotion 示例的语言）内、非注释行的 Math.random 调用。
# 网页端 ```js 示例里的 Math.random 是合法的（无跨帧确定性要求），刻意不拦——
# 一刀切会逼着作者把合法网页示例改成假确定性写法。
scan_math_random() {   # $1 = 目录；输出命中的 file:line
  python3 - "$1" <<'PY'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
REMOTION_LANGS = {"tsx", "ts", "jsx"}
hits, scanned = [], 0
for md in sorted(root.glob("*.md")):
    lang, line_no, in_block = None, 0, False
    for raw in md.read_text(encoding="utf-8").splitlines():
        line_no += 1
        s = raw.strip()
        if not in_block:
            m = re.match(r"^```(\S*)", s)
            if m:
                lang, in_block = m.group(1).lower(), True
            continue
        if s.startswith("```"):
            in_block, lang = False, None
            continue
        if lang in REMOTION_LANGS:
            scanned += 1
            if s.startswith(("//", "/*", "*")) or s.endswith("*/"):
                continue
            if "Math.random" in raw:
                hits.append(f"{md.name}:{line_no}")
print("\n".join(hits))
print(f"#scanned={scanned}", file=sys.stderr)
PY
}
mr_hits=$(scan_math_random references 2>/dev/null)
if [ -n "$mr_hits" ]; then
  bad "Remotion 示例代码块（tsx/ts/jsx）中出现 Math.random：$(echo $mr_hits)"
else
  ok "references 全部 $(ls references/*.md | wc -l) 篇文档的 Remotion 示例代码块无 Math.random（网页 js 示例按规则放行）"
fi

# 7b. 红线门禁自证：喂一个必红样本，确认扫描器真的会失败
tmp_mr=$(mktemp -d)
printf '# probe\n\n```tsx\nconst x = Math.random();\n```\n' > "$tmp_mr/probe.md"
probe_hits=$(scan_math_random "$tmp_mr" 2>/dev/null)
rm -rf "$tmp_mr"
[ -n "$probe_hits" ] && ok "Math.random 门禁必红用例生效（注入 tsx 样本后被抓出）" \
  || bad "Math.random 门禁必红用例未生效——门禁永真，等于没有门禁"

# ── 8. ASCII-safe 断言（§7 第 11 条 + 第 24 条覆盖范围声明） ──────────────────────
# 8a. 契约 ramp 本身必须落在可打印 ASCII（32–126）
if python3 -c "import re,sys; s=' .:-=+*#%@'; sys.exit(0 if re.fullmatch(r'[\x20-\x7E]*', s) else 1)"; then
  ok "契约 ramp 落在可打印 ASCII 区间（32–126）"
else bad "契约 ramp 含非可打印 ASCII 字符"; fi

# 8b. 字符产物（.txt / .ascii / .art / 首帧产物）无 CR、无非 ASCII
bad_files=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if grep -q $'\r' "$f" 2>/dev/null; then bad_files="$bad_files $f(CR)"; continue; fi
  if LC_ALL=C grep -qP '[^\x20-\x7E\t\n]' "$f" 2>/dev/null; then bad_files="$bad_files $f(非ASCII)"; fi
done <<EOF
$(find . -type f \( -name '*.txt' -o -name '*.ascii' -o -name '*.art' \) -not -path './node_modules/*' 2>/dev/null)
EOF
if [ -z "$bad_files" ]; then ok "字符产物 ASCII-safe（无 CR、无非 ASCII 码位）"
else bad "字符产物违反 ASCII-safe：$bad_files"; fi

# 8c. 脚本源码换行符统一为 LF（禁止 CRLF 入库，§1.1 换行符陷阱）
crlf=$(find . -type f \( -name '*.md' -o -name '*.py' -o -name '*.sh' -o -name '*.c' -o -name '*.html' -o -name '*.json' \) -not -path './node_modules/*' -exec grep -lU $'\r' {} + 2>/dev/null)
[ -z "$crlf" ] && ok "包内文本文件均为 LF 换行" || bad "以下文件含 CRLF：$crlf"

# ── 9. 三端骨架可编译可运行（§7 第 9 条的包内兑现） ───────────────────────────────
tpl=assets/templates
if [ -f "$tpl/ascii.c" ] && [ -f "$tpl/ascii.py" ] && [ -f "$tpl/ascii.html" ]; then
  ok "三端骨架齐套：$tpl/ascii.{html,py,c}"
  if python3 -m py_compile "$tpl/ascii.py" 2>/dev/null; then ok "ascii.py py_compile 通过"
  else bad "ascii.py py_compile 失败"; fi
  cbin=$(mktemp -d)/ascii_c
  if command -v gcc >/dev/null 2>&1; then
    if gcc -O2 -std=c99 "$tpl/ascii.c" -o "$cbin" 2>/dev/null; then ok "ascii.c gcc -O2 -std=c99 编译通过"
    else bad "ascii.c 编译失败"; fi
  else note "gcc 不可用，跳过 C 编译"; fi
  if command -v python3 >/dev/null 2>&1; then
    py_out=$(python3 "$tpl/ascii.py" --dump 7 2>/dev/null)
    py_rc=$?
    if [ "$py_rc" = "0" ] && [ -n "$py_out" ]; then ok "ascii.py --dump 可运行（$(echo "$py_out" | wc -l) 行）"
    else bad "ascii.py --dump 运行失败"; fi
    if [ -x "$cbin" ]; then
      c_out=$("$cbin" --dump 7 2>/dev/null)
      if [ "$py_out" = "$c_out" ]; then ok "Python / C 两端同帧输出逐字节一致"
      else bad "Python / C 两端同帧输出不一致"; fi
    fi
    # HTML 内核标记必须存在（verify_deliverable.py 据此做三端比对）
    grep -q "ASCII KERNEL BEGIN" "$tpl/ascii.html" && grep -q "ASCII KERNEL END" "$tpl/ascii.html" \
      && ok "ascii.html 含 ASCII KERNEL 标记（三端比对锚点）" || bad "ascii.html 缺少 ASCII KERNEL 标记"
  fi
  rm -rf "$(dirname "$cbin")"
else
  bad "assets/templates 三端骨架不全（§7 第 9 条）"
fi

# ── 10. 速查表（§1.0）每行目的地文件真实存在 ─────────────────────────────────────
miss2=""
for f in $(grep -oE '(image-to-ascii|web-implementation|terminal-ui|ascii-charts|remotion-video|animation-patterns|audio-visual|scroll-and-pointer|walkthrough|faq|terminal-templates)\.md' SKILL.md | sort -u); do
  [ -e "references/$f" ] || miss2="$miss2 $f"
done
[ -z "$miss2" ] && ok "速查表/路由表指向的 references 文件全部存在" || bad "速查表指向缺失文件：$miss2"

# ── 11. 交叉引用落地：跨文件 §x.y 引用必须指向真实存在的小节标题 ─────────────────
xref_bad=""
while IFS= read -r ref; do
  [ -z "$ref" ] && continue
  file="${ref%%.md*}"; sec="${ref##* §}"
  [ -e "references/$file.md" ] || { xref_bad="$xref_bad $ref(文件不存在)"; continue; }
  # 小节标题形态：`### 3.8 xxx`、`## §F 图表类型库`、`### F.1 饼图家族`、`## 2.5 xxx`
  pat="^#+ *§?${sec//./\\.}([ .:：－-]|$)"
  if ! grep -qE "$pat" "references/$file.md"; then
    xref_bad="$xref_bad $ref(小节缺失)"
  fi
done <<EOF
$(grep -ohE '(image-to-ascii|web-implementation|terminal-ui|ascii-charts|remotion-video|animation-patterns|audio-visual|scroll-and-pointer|walkthrough|faq|terminal-templates)\.md §[A-Z0-9]+(\.[0-9]+)?' SKILL.md references/*.md | sort -u)
EOF
[ -z "$xref_bad" ] && ok "跨文件 §x.y 引用均指向真实存在的小节" || bad "悬空引用：$xref_bad"

# ── 12. 包内不得留占位 stub（SKILL.md 无 TODO/FIXME，代码块无裸 `...` 占位） ──────
if grep -qE '\b(TODO|FIXME)\b' SKILL.md; then bad "SKILL.md 含 TODO/FIXME"
else ok "SKILL.md 无 TODO/FIXME"; fi

echo
if [ "$FAIL" = "0" ]; then echo "结论：包内自检全部通过"; exit 0
else echo "结论：自检存在失败项，修复后重跑"; exit 1; fi
