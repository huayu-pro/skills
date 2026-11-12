#!/usr/bin/env python3
"""verify_deliverable.py —— ascii-web-design 交付物验收器（落地 SKILL.md §7 的【自动】断言）。

SKILL.md §7 里标【自动】的条目分两类：
  * 包自身完整性 → scripts/selfcheck.sh（章节/引用/ramp/红线扫描）
  * 用户交付物     → 本脚本（逐条对应 §7 的第 5/9/11/13/14/16/19/20 条）

用法：
    python3 scripts/verify_deliverable.py <子命令> <目标目录或文件> [选项]
    python3 scripts/verify_deliverable.py all <项目目录>      # 自动识别并跑适用的全部子命令
    python3 scripts/verify_deliverable.py self-test           # 必红用例自测（每条断言都证明会失败）

子命令与 §7 条目对应：
    gif-frames    §7.5  GIF 完整帧（数据层逐帧同尺寸 + 源码层含帧合成守卫）
    three-ends    §7.9  三端齐套（同 slug 的 html/py/c 存在、ramp 一致、可编译、输出逐字节一致）
    ascii-safe    §7.11 ASCII-safe（ramp 落在 32–126；Unicode 档码位在白名单；换行已归一为 \\n）
    float-meta    §7.13 浮点元数据（width/height/channels/colorspace 四件套 + premultiplied + rowOrder=top-down）
    chart-data    §7.14 图表数据三端同源（data.json md5 唯一）+ niceCeil 实跑 1-2-5 序列
    sanitize      §7.16 回显消毒（抽源码里的 sanitize 正则，喂控制字符实跑，必须剥干净）
    remotion      §7.19 Remotion 交付（out/*.mp4 存在且时长 > 0；src 内无 Math.random 调用）
    network       §7.20 网络加载卫生（除 loadWithRetry 内部外无裸 await fetch）

退出码：0 全部通过；1 存在失败；2 用法/目标问题；3 环境缺依赖（node/gcc/ffprobe）。
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAMP_DEFAULT = " .:-=+*#%@"
# Unicode 档允许的码位白名单（SKILL.md §1.1：box-drawing / 方块 / 盲文 / 半角片假名）
UNICODE_RANGES = [
    (0x2500, 0x257F),   # box-drawing
    (0x2580, 0x259F),   # block elements
    (0x2800, 0x28FF),   # braille
    (0xFF66, 0xFF9F),   # halfwidth katakana
    (0x25A0, 0x25FF),   # geometric shapes（◆ ◈ 等装饰角）
    (0x2190, 0x21FF),   # arrows
]
SOURCE_EXTS = {".js", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".htm"}
CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


class Report:
    def __init__(self, title):
        self.title = title
        self.fails = []
        self.passes = []
        self.skips = []

    def ok(self, msg):
        self.passes.append(msg)
        print(f"  [通过] {msg}")

    def bad(self, msg):
        self.fails.append(msg)
        print(f"  [失败] {msg}")

    def skip(self, msg):
        self.skips.append(msg)
        print(f"  [跳过] {msg}")

    def verdict(self):
        if self.fails:
            print(f"[{self.title}] 结论：未通过（失败 {len(self.fails)} 项，通过 {len(self.passes)} 项）")
            return 1
        if not self.passes and self.skips:
            print(f"[{self.title}] 结论：无可验证内容（跳过 {len(self.skips)} 项）")
            return 0
        print(f"[{self.title}] 结论：通过（通过 {len(self.passes)} 项，跳过 {len(self.skips)} 项）")
        return 0


# ── 通用工具 ────────────────────────────────────────────────────────────────

def walk(root, exts=None):
    root = Path(root)
    if root.is_file():
        return [root]
    out = []
    for p in sorted(root.rglob("*")):
        if any(part in ("node_modules", ".git", "__pycache__", "out", ".venv") for part in p.parts):
            continue
        if p.is_file() and (exts is None or p.suffix.lower() in exts):
            out.append(p)
    return out


def have(binary):
    return shutil.which(binary) is not None


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def node_run(code, tmpdir):
    """在临时目录跑一段 ESM/脚本，返回 (rc, stdout, stderr)。"""
    f = Path(tmpdir) / "probe.mjs"
    f.write_text(code, encoding="utf-8")
    return run(["node", str(f)])


def extract_block(text, begin, end):
    """抽出 begin/end 标记之间的正文；标记所在行的剩余字符（如 ====）一并跳过。"""
    i = text.find(begin)
    if i < 0:
        return None
    nl = text.find("\n", i)
    if nl < 0:
        return None
    j = text.find(end, nl)
    if j < 0:
        return None
    # end 标记前的整行尾随字符（如 `==== */`）不进入正文
    tail = text.rfind("\n", nl, j)
    return text[nl + 1:tail if tail > nl else j]


def extract_braced_function(text, name):
    """抽 function name(...) { ... } 的完整函数体（括号配平，跳过字符串与行注释）。"""
    m = re.search(r"(?:function\s+%s\s*\(|const\s+%s\s*=\s*\()" % (re.escape(name), re.escape(name)), text)
    if not m:
        return None
    i = text.find("{", m.end())
    if i < 0:
        return None
    depth, j = 0, i
    while j < len(text):
        ch = text[j]
        if ch in "'\"`":
            q = ch
            j += 1
            while j < len(text) and text[j] != q:
                j += 2 if text[j] == "\\" else 1
        elif ch == "/" and text[j:j + 2] == "//":
            j = text.find("\n", j)
            if j < 0:
                return None
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():j + 1]
        j += 1
    return None


def md5(data):
    return hashlib.md5(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def strip_frame(s):
    return s.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


# ── §7.5 GIF 完整帧 ─────────────────────────────────────────────────────────

def check_gif_frames(root, rep):
    data_checked = 0
    for p in walk(root, {".json"}):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        frames = doc.get("frames") if isinstance(doc, dict) else None
        if not isinstance(frames, list) or not frames:
            continue
        data_checked += 1
        shapes = {len(f.split("\n")) for f in frames}
        widths = {len(line) for f in frames for line in f.split("\n")}
        if len(shapes) == 1 and len(widths) == 1:
            rep.ok(f"{p.name}：{len(frames)} 帧尺寸一致（{widths.pop()} 列 × {shapes.pop()} 行）")
        else:
            rep.bad(f"{p.name}：帧尺寸不一致（行数 {sorted(shapes)}，列宽 {sorted(widths)}）——增量帧未合成，"
                    f"按 web-implementation.md §3.1 走合成路径后重跑")

    src_checked = 0
    for p in walk(root, SOURCE_EXTS):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "decompressFrames" not in text and "parseGIF" not in text:
            continue
        src_checked += 1
        # 守卫：局部帧判定表达式 或 显式调用合成函数
        guard = ("dims.left" in text and "dims.width" in text) or re.search(
            r"\b(compose|composite|mergeFrames|composeFrames)\w*\s*\(", text)
        if guard:
            rep.ok(f"{p.name}：gifuct 路径含局部帧合成守卫（dims.left/dims.width 判定或合成函数）")
        else:
            rep.bad(f"{p.name}：用了 gifuct-js 解帧但没有局部帧守卫——增量 GIF 会丢背景破边"
                    f"（需 `f.dims.left || f.dims.top || f.dims.width !== W || f.dims.height !== H` 判定后合成）")
    if not data_checked and not src_checked:
        rep.skip("目标内既无 frames JSON 也无 gifuct 源码，GIF 断言不适用")


# ── §7.9 三端齐套 ───────────────────────────────────────────────────────────

RAMP_PATTERNS = {
    ".html": [re.compile(r"RAMP\s*=\s*'([^'\\]*(?:\\.[^'\\]*)*)'"), re.compile(r'RAMP\s*=\s*"([^"]*)"')],
    ".py": [re.compile(r"^RAMP\s*=\s*[\"']([^\"']*)[\"']", re.M)],
    ".c": [re.compile(r'#define\s+RAMP\s+"([^"]*)"'), re.compile(r'RAMP\s*\[\s*\]\s*=\s*"([^"]*)"')],
    ".js": [re.compile(r"RAMP\s*=\s*'([^'\\]*(?:\\.[^'\\]*)*)'"), re.compile(r'RAMP\s*=\s*"([^"]*)"')],
}


def ramp_of(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    pats = RAMP_PATTERNS.get(path.suffix.lower(), [])
    for pat in pats:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


def find_three_ends(root, slug=None):
    root = Path(root)
    if slug:
        cand = [root / f"{slug}{ext}" for ext in (".html", ".py", ".c")]
        return cand if all(c.is_file() for c in cand) else None
    stems = {}
    for p in walk(root, {".html", ".py", ".c"}):
        stems.setdefault(p.stem, {})[p.suffix.lower()] = p
    for stem, got in sorted(stems.items()):
        if {".html", ".py", ".c"} <= set(got):
            return [got[".html"], got[".py"], got[".c"]]
    return None


def check_three_ends(root, rep, slug=None, frame=7, lenient=False):
    trio = find_three_ends(root, slug)
    if not trio:
        msg = "未找到同 slug 的 html/py/c 三件套（§7.9 要求 <slug>.html + <slug>.py + <slug>.c 同目录并存）"
        if lenient:
            rep.skip(msg + "；本项目未选择三端交付")
        else:
            rep.bad(msg)
        return
    html, py, c = trio
    rep.ok(f"三端齐套：{html.name} / {py.name} / {c.name}")

    ramps = {}
    for p in trio:
        ramps[p.suffix] = ramp_of(p)
    if any(v is None for v in ramps.values()):
        rep.bad(f"无法从三端抽出 RAMP：{ {k: v for k, v in ramps.items()} }")
        return
    if len(set(ramps.values())) == 1:
        rep.ok(f"三端 RAMP 一致：{ramps['.html']!r}")
    else:
        rep.bad(f"三端 RAMP 不一致：{ramps}（§1.2 单一事实源）")

    if not have("python3"):
        rep.skip("python3 不可用，跳过 py_compile")
    else:
        r = run(["python3", "-m", "py_compile", str(py)])
        if r.returncode == 0:
            rep.ok(f"{py.name} py_compile 通过")
        else:
            rep.bad(f"{py.name} py_compile 失败：{r.stderr.strip()[:200]}")

    if not have("gcc"):
        rep.skip("gcc 不可用，跳过 C 编译")
        c_bin = None
    else:
        c_bin = Path(tempfile.mkdtemp(prefix="vd_c_")) / c.stem
        r = run(["gcc", "-O2", "-std=c99", str(c), "-o", str(c_bin)])
        if r.returncode == 0:
            rep.ok(f"{c.name} gcc -O2 -std=c99 编译通过")
        else:
            rep.bad(f"{c.name} 编译失败：{r.stderr.strip()[:300]}")
            c_bin = None

    # 逐字节一致性：py --dump / c --dump / html 内核标记
    outs = {}
    if "--dump" in py.read_text(encoding="utf-8", errors="ignore"):
        r = run(["python3", str(py), "--dump", str(frame)])
        if r.returncode == 0:
            outs["py"] = strip_frame(r.stdout)
        else:
            rep.bad(f"{py.name} --dump 失败：{r.stderr.strip()[:200]}")
    else:
        rep.bad(f"{py.name} 未提供 --dump N（terminal-templates.md 三端契约要求，用于三端逐字节比对）")

    if c_bin is not None:
        r = run([str(c_bin), "--dump", str(frame)])
        if r.returncode == 0:
            outs["c"] = strip_frame(r.stdout)
        else:
            rep.bad(f"{c.name} --dump 失败：{r.stderr.strip()[:200]}")
    elif have("gcc"):
        rep.bad(f"{c.name} 未提供 --dump N（三端契约要求）")

    kernel = extract_block(html.read_text(encoding="utf-8", errors="ignore"),
                           "ASCII KERNEL BEGIN", "ASCII KERNEL END")
    if kernel is None:
        rep.bad(f"{html.name} 缺少 `ASCII KERNEL BEGIN/END` 标记（三端契约要求，校验器据此跑 node 比对）")
    elif not have("node"):
        rep.skip("node 不可用，跳过 HTML 内核比对")
    else:
        with tempfile.TemporaryDirectory(prefix="vd_js_") as td:
            r = node_run(kernel + f"\nprocess.stdout.write(renderFrame({frame}) + '\\n');\n", td)
            if r.returncode == 0:
                outs["html"] = strip_frame(r.stdout)
            else:
                rep.bad(f"{html.name} 内核在 node 下执行失败：{r.stderr.strip().splitlines()[:2]}")

    if len(outs) == 3:
        if len(set(outs.values())) == 1:
            rep.ok(f"三端第 {frame} 帧逐字节一致（md5 {md5(outs['py'])}，{len(outs['py'].split(chr(10)))} 行）")
        else:
            detail = ", ".join(f"{k}={md5(v)[:8]}" for k, v in outs.items())
            rep.bad(f"三端输出不一致（{detail}）——同一契约必须产出同一帧")


# ── §7.11 ASCII-safe ────────────────────────────────────────────────────────

def grid_violations(text, mode):
    """返回 text 中不符合目标码位档的字符（去重、排序）。"""
    if mode == "ascii-safe":
        return sorted({ch for ch in text if not ("\x20" <= ch <= "\x7E" or ch == "\n")})
    return sorted({ch for ch in text
                   if not ("\x20" <= ch <= "\x7E" or ch == "\n"
                           or any(lo <= ord(ch) <= hi for lo, hi in UNICODE_RANGES))})


def check_ascii_safe(target, rep, mode="ascii-safe", ramp=None):
    ramps = [ramp] if ramp else [RAMP_DEFAULT]
    for p in walk(target, SOURCE_EXTS | {".py", ".c", ".txt", ".json"}):
        text = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"RAMP\s*=\s*['\"]([^'\"]*)['\"]|RAMP\s*\[\s*\]\s*=\s*\"([^\"]*)\"|#define\s+RAMP\s+\"([^\"]*)\"", text)
        if m:
            ramps.append(next(g for g in m.groups() if g is not None))
    for r in sorted(set(ramps)):
        if re.fullmatch(r"[\x20-\x7E\n]*", r):
            rep.ok(f"ramp 落在可打印 ASCII 区间：{r!r}")
        elif mode == "unicode":
            rep.skip(f"ramp 含非 ASCII 字符（Unicode 档，按码位白名单另行校验）：{r!r}")
        else:
            rep.bad(f"ramp 含非 ASCII 字符，ASCII-safe 档不允许：{r!r}")

    # 字符产物：.txt / .ascii / .art 全文校验；.json 只校验其中的字符网格
    # （frames 数组 / firstFrame 字段）——图表 data.json 的中文标题与图例本就合法，
    # 一刀切扫全文会把正常数据判红（假失败比漏检更糟）。
    checked = 0
    for p in walk(target, {".txt", ".ascii", ".art"}):
        raw = p.read_bytes()
        if b"\r" in raw:
            rep.bad(f"{p.name} 含 CR（\\r）——入库前须统一为 \\n（SKILL.md §1.1 换行符陷阱）")
            continue
        text = raw.decode("utf-8", errors="ignore")
        bad_chars = grid_violations(text, mode)
        if bad_chars:
            rep.bad(f"{p.name} 含 {mode} 不允许的码位：{bad_chars[:8]}")
        else:
            checked += 1

    for p in walk(target, {".json"}):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        grids = []
        if isinstance(doc, dict):
            if isinstance(doc.get("frames"), list):
                grids += [g for g in doc["frames"] if isinstance(g, str)]
            for key in ("firstFrame", "frame", "grid"):
                if isinstance(doc.get(key), str):
                    grids.append(doc[key])
        if not grids:
            continue
        if p.read_bytes().find(b"\r") >= 0:
            rep.bad(f"{p.name} 含 CR（\\r）——字符帧入库前须统一为 \\n")
            continue
        bad = {}
        for g in grids:
            v = grid_violations(g, mode)
            if v:
                bad.update({c: True for c in v})
        if bad:
            rep.bad(f"{p.name} 的字符帧含 {mode} 不允许的码位：{sorted(bad)[:8]}")
        else:
            checked += 1
    if checked:
        rep.ok(f"{checked} 个字符产物通过 {mode} 码位校验")


# ── §7.13 浮点元数据 ────────────────────────────────────────────────────────

FLOAT_KEYS = ("width", "height", "channels", "colorspace")


def check_float_meta(root, rep):
    found = 0
    for p in walk(root, {".json"}):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else doc
        if not any(k in meta for k in ("channels", "colorspace", "rowOrder")):
            continue
        found += 1
        missing = [k for k in FLOAT_KEYS if k not in meta]
        if missing:
            rep.bad(f"{p.name}：浮点元数据缺 {missing}（四件套 width/height/channels/colorspace）")
        elif meta.get("rowOrder") != "top-down":
            rep.bad(f"{p.name}：rowOrder={meta.get('rowOrder')!r}，必须是 'top-down'（PFM 底向上行序翻转后落盘）")
        else:
            rep.ok(f"{p.name}：浮点元数据四件套 + rowOrder=top-down 齐备")
        src_w = meta.get("sourceWidth")
        if isinstance(src_w, int) and src_w > 512:
            width = meta.get("width")
            if isinstance(width, int) and width <= 512 and meta.get("downsampled") is not False:
                rep.ok(f"{p.name}：大图（{src_w}px）已降采样到 {width}px")
            else:
                rep.bad(f"{p.name}：源图 {src_w}px > 512 却未降采样到 ≤512px（image-to-ascii.md §2.3 体积红线）")
        # PFM 与元数据同目录同名（img.meta.json → img.meta.pfm 或 img.pfm 都认）
        pfm = p.with_suffix(".pfm")
        if not pfm.exists():
            pfm = p.parent / (p.name.split(".")[0] + ".pfm")
        if pfm.exists():
            head = pfm.read_bytes()[:200].split(b"\n")
            try:
                magic, dims = head[0].strip(), head[1].split()
                w, h = int(dims[0]), int(dims[1])
                if magic in (b"PF", b"Pf") and (w, h) == (meta.get("width"), meta.get("height")):
                    rep.ok(f"{p.name}：PFM 头尺寸与元数据一致（{w}×{h}，{magic.decode()}）")
                else:
                    rep.bad(f"{p.name}：PFM 头（{magic!r} {w}×{h}）与元数据（{meta.get('width')}×{meta.get('height')}）不符")
            except (IndexError, ValueError):
                rep.bad(f"{p.name}：PFM 头无法解析（{pfm.name}）")
    if not found:
        rep.skip("目标内无浮点元数据 JSON，§7.13 不适用")


# ── §7.14 图表数据同源 + niceCeil ───────────────────────────────────────────

def nice_ceil_ref(v):
    if v <= 0:
        return 0
    import math
    pow10 = 10 ** math.floor(math.log10(v))
    n = v / pow10
    return (1 if n <= 1 else 2 if n <= 2 else 5 if n <= 5 else 10) * pow10


def check_chart_data(root, rep, name="data.json"):
    datas = [p for p in walk(root, {".json"}) if p.name == name]
    if not datas:
        rep.skip(f"目标内无 {name}，§7.14 不适用")
        return
    digests = {md5(p.read_bytes()) for p in datas}
    if len(digests) == 1:
        rep.ok(f"{len(datas)} 份 {name} md5 完全一致（{next(iter(digests))[:12]}…）——三端同源")
    else:
        rep.bad(f"{len(datas)} 份 {name} md5 不一致：{sorted(d[:12] for d in digests)}——三端各读各的数据，"
                f"违反 ascii-charts.md §B 统一数据契约")
    for p in datas:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            rep.bad(f"{p}：不是合法 JSON：{e}")
            continue
        if "series" not in doc:
            rep.bad(f"{p}：缺 series 字段（ascii-charts.md §B 数据契约）")

    sources = [p for p in walk(root, SOURCE_EXTS | {".py", ".c"})
               if "niceCeil" in p.read_text(encoding="utf-8", errors="ignore")]
    if not sources:
        rep.bad("图表交付物里找不到 niceCeil —— 刻度必须是 1/2/5×10^n 友好值（ascii-charts.md §A）")
        return
    if not have("node"):
        rep.skip("node 不可用，跳过 niceCeil 实跑")
        return
    probes = [1, 1.2, 1.9, 2.1, 3.7, 4.9, 5.1, 9.9, 12, 37, 99, 0.7, 250]
    expected = [nice_ceil_ref(v) for v in probes]
    for p in sources:
        fn = extract_braced_function(p.read_text(encoding="utf-8", errors="ignore"), "niceCeil")
        if not fn:
            rep.bad(f"{p.name}：niceCeil 定义无法抽取（需写成 function niceCeil(v) {{...}}）")
            continue
        with tempfile.TemporaryDirectory(prefix="vd_nc_") as td:
            code = fn + "\nconsole.log(JSON.stringify(%s.map(niceCeil)));\n" % json.dumps(probes)
            r = node_run(code, td)
        if r.returncode != 0:
            rep.bad(f"{p.name}：niceCeil 执行失败：{r.stderr.strip().splitlines()[:2]}")
            continue
        try:
            got = json.loads(r.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            rep.bad(f"{p.name}：niceCeil 输出无法解析：{r.stdout.strip()[:120]}")
            continue
        if got == expected:
            rep.ok(f"{p.name}：niceCeil 实跑 {len(probes)} 个探针全部落在 1-2-5 序列")
        else:
            diff = [(v, e, g) for v, e, g in zip(probes, expected, got) if e != g][:4]
            rep.bad(f"{p.name}：niceCeil 输出非 1-2-5 友好值（值,期望,实得）：{diff}")


# ── §7.16 回显消毒 ──────────────────────────────────────────────────────────

SANITIZE_PAYLOADS = ["\x1b[31mRED\x07", "\x00nul\x08bs\x7Fdel", "正常文本\tok"]


def check_sanitize(root, rep, sample=None):
    sources = []
    for p in walk(root, SOURCE_EXTS):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(?:const|let|var|function)\s+sanitize", text):
            sources.append(p)
    if not sources:
        rep.skip("目标内无 sanitize 定义，§7.16 不适用")
    elif not have("node"):
        rep.skip("node 不可用，跳过 sanitize 实跑")
    else:
        for p in sources:
            text = p.read_text(encoding="utf-8", errors="ignore")
            fn = extract_braced_function(text, "sanitize")
            if fn is None:
                m = re.search(r"(?:const|let)\s+sanitize\s*=\s*[^;]*?\.replace\((/.*?/g?)[,)]", text)
                if not m:
                    rep.bad(f"{p.name}：sanitize 既不是函数也抽不出正则字面量，无法验证")
                    continue
                fn = "const sanitize = s => String(s).replace(%s, '');" % m.group(1)
            with tempfile.TemporaryDirectory(prefix="vd_san_") as td:
                code = fn + "\nconsole.log(JSON.stringify(%s.map(sanitize)));\n" % json.dumps(SANITIZE_PAYLOADS)
                r = node_run(code, td)
            if r.returncode != 0:
                rep.bad(f"{p.name}：sanitize 执行失败：{r.stderr.strip().splitlines()[:2]}")
                continue
            got = json.loads(r.stdout.strip().splitlines()[-1])
            leaked = [s for s in got if CTRL_RE.search(s)]
            if leaked:
                rep.bad(f"{p.name}：sanitize 后仍残留控制字符 {[repr(x) for x in leaked]}——ANSI 注入风险（§0.2 输出卫生）")
            else:
                rep.ok(f"{p.name}：sanitize 实跑剥离了 ESC/BEL/NUL/BS/DEL（保留 \\t）")

    if sample:
        raw = Path(sample).read_bytes().decode("utf-8", errors="ignore")
        if CTRL_RE.search(raw):
            rep.bad(f"{Path(sample).name}：回显样本含控制字符（§7.16 断言 /[\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F\\u007F]/ 命中）")
        else:
            rep.ok(f"{Path(sample).name}：回显样本无控制字符")


# ── §7.19 Remotion 交付 ─────────────────────────────────────────────────────

def check_remotion(root, rep, expected_duration=None, lenient=False):
    root = Path(root)
    has_project = (root / "src").is_dir() or (root / "package.json").is_file()
    mp4s = sorted(p for p in root.rglob("*.mp4")
                  if "node_modules" not in p.parts and ".git" not in p.parts)
    if not has_project and not mp4s and lenient:
        rep.skip("本项目不是 Remotion 项目（无 src/、package.json、*.mp4），§7.19 不适用")
        return
    if not mp4s:
        rep.bad("未找到 *.mp4（§7.19 要求 out/*.mp4 存在）")
    elif not have("ffprobe"):
        rep.skip("ffprobe 不可用，跳过时长校验")
    else:
        for p in mp4s:
            r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=nw=1:nk=1", str(p)])
            try:
                dur = float(r.stdout.strip())
            except ValueError:
                rep.bad(f"{p.name}：ffprobe 读不出时长（文件可能损坏）：{r.stderr.strip()[:120]}")
                continue
            if dur <= 0:
                rep.bad(f"{p.name}：时长 {dur}s，视频为空")
            elif expected_duration and abs(dur - expected_duration) > 0.5:
                rep.bad(f"{p.name}：时长 {dur:.2f}s 与期望 {expected_duration}s 不符")
            else:
                rep.ok(f"{p.name}：时长 {dur:.2f}s")

    srcs = [p for p in walk(root / "src", SOURCE_EXTS)] if (root / "src").is_dir() else []
    if not srcs:
        rep.bad("未找到 src/ 源码目录（§7.19 要求检查 src/ 内无 Math.random）")
        return
    hits = []
    for p in srcs:
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            if "Math.random" in line:
                hits.append(f"{p.relative_to(root)}:{i}")
    if hits:
        rep.bad(f"src/ 内出现 Math.random 调用（多线程渲染必出鬼影，改用 random(seed)）：{hits[:6]}")
    else:
        rep.ok(f"src/ 内 {len(srcs)} 个源文件无 Math.random 调用（确定性红线）")


# ── §7.20 网络加载卫生 ──────────────────────────────────────────────────────

def enclosing_function(text, pos):
    """返回 pos 之前最近一个 `function NAME(` / `NAME = (...) =>` 的名字（粗略但够用）。"""
    head = text[:pos]
    best = None
    for m in re.finditer(r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(", head):
        best = m.group(1) or m.group(2)
    return best


def check_network(root, rep):
    hits = []
    checked = 0
    for p in walk(root, {".html", ".htm", ".js", ".mjs"}):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "fetch(" not in text:
            continue
        checked += 1
        for m in re.finditer(r"await\s+fetch\s*\(", text):
            fn = enclosing_function(text, m.start())
            line = text[:m.start()].count("\n") + 1
            if fn and "loadWithRetry" in fn:
                continue                       # 重试封装内部唯一允许的裸 fetch
            hits.append(f"{p.name}:{line}（所在函数 {fn or '顶层'}）")
    if hits:
        rep.bad(f"存在裸 await fetch（须经 loadWithRetry 封装，web-implementation.md §3.0）：{hits[:6]}")
    elif checked:
        rep.ok(f"{checked} 个含 fetch 的源文件均经 loadWithRetry 封装")
    else:
        rep.skip("目标内无 fetch 调用，§7.20 网络卫生不适用")


# ── 汇总入口 ────────────────────────────────────────────────────────────────

CHECKS = {
    "gif-frames": lambda root, a, rep: check_gif_frames(root, rep),
    "three-ends": lambda root, a, rep: check_three_ends(root, rep, a.slug, a.frame, getattr(a, "lenient", False)),
    "ascii-safe": lambda root, a, rep: check_ascii_safe(root, rep, a.mode, a.ramp),
    "float-meta": lambda root, a, rep: check_float_meta(root, rep),
    "chart-data": lambda root, a, rep: check_chart_data(root, rep, a.data_name),
    "sanitize": lambda root, a, rep: check_sanitize(root, rep, a.echo_file),
    "remotion": lambda root, a, rep: check_remotion(root, rep, a.expected_duration, getattr(a, "lenient", False)),
    "network": lambda root, a, rep: check_network(root, rep),
}


def run_all(root, a):
    a.lenient = True          # all 模式下：本项目未采用的路线记为「跳过」，不算失败
    rc = 0
    for name, fn in CHECKS.items():
        rep = Report(name)
        fn(root, a, rep)
        rc |= rep.verdict()
        print()
    return rc


# ── 必红用例自测：每条断言都必须在一个应失败的输入上真的失败 ──────────────

def _fixture(td, name, content, binary=False):
    p = Path(td) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        p.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    else:
        p.write_text(content, encoding="utf-8")
    return p


def _expect(td, name, root, fn, should_pass, desc, **kw):
    """跑一条断言并断言其结论符合预期（should_pass=False 即必红用例）。"""
    rep = Report(name)
    fn(Path(root), rep, **kw)
    got_pass = not rep.fails
    if got_pass == should_pass:
        print(f"  [自测通过] {desc}：{'绿' if should_pass else '红'}如预期")
        return True
    print(f"  [自测失败] {desc}：期望{'绿' if should_pass else '红'}，实际{'绿' if got_pass else '红'}"
          f"（fails={rep.fails[:2]}）")
    return False


def self_test():
    class A:
        slug = None
        frame = 7
        mode = "ascii-safe"
        ramp = None
        data_name = "data.json"
        echo_file = None
        expected_duration = None
    a = A()
    all_ok = True
    print("[self-test] 每条门禁的必红用例：")

    # 1. GIF 完整帧
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "good.json", json.dumps({"frames": ["abc\ndef", "ghi\njkl"]}))
        all_ok &= _expect(td, "gif-frames", td, check_gif_frames, True, "帧尺寸一致 → 绿")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "bad.json", json.dumps({"frames": ["abc\ndef", "gh\njkl"]}))
        all_ok &= _expect(td, "gif-frames", td, check_gif_frames, False, "某帧列宽不同 → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "a.js", "const frames = decompressFrames(parseGIF(buf), true);\n")
        all_ok &= _expect(td, "gif-frames", td, check_gif_frames, False, "gifuct 解帧无合成守卫 → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "a.js", "const W = 10;\nif (frames.some(f => f.dims.left || f.dims.width !== W)) { compose(); }\n")
        all_ok &= _expect(td, "gif-frames", td, check_gif_frames, True, "含局部帧守卫 → 绿")

    # 2. 三端齐套（用包内模板做绿例，破坏一份做红例）
    tpl = Path(__file__).resolve().parent.parent / "assets" / "templates"
    if tpl.is_dir() and have("gcc") and have("node"):
        all_ok &= _expect(tpl, "three-ends", tpl, check_three_ends, True, "包内三端模板 → 绿")
        with tempfile.TemporaryDirectory() as td:
            for ext in (".html", ".py", ".c"):
                (Path(td) / f"x{ext}").write_bytes((tpl / f"ascii{ext}").read_bytes())
            p = Path(td) / "x.py"
            p.write_text(p.read_text(encoding="utf-8").replace("RAMP = \" .:-=+*#%@\"", "RAMP = \" .:-=+*#%$\""),
                         encoding="utf-8")
            all_ok &= _expect(td, "three-ends", td, check_three_ends, False, "三端 ramp 不同 → 红")
        with tempfile.TemporaryDirectory() as td:
            for ext in (".html", ".py", ".c"):
                (Path(td) / f"x{ext}").write_bytes((tpl / f"ascii{ext}").read_bytes())
            p = Path(td) / "x.py"
            p.write_text(p.read_text(encoding="utf-8").replace('"--dump"', '"--nosuchflag"'), encoding="utf-8")
            all_ok &= _expect(td, "three-ends", td, check_three_ends, False, "缺 --dump 契约 → 红")
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "only.html").write_text("x", encoding="utf-8")
            all_ok &= _expect(td, "three-ends", td, check_three_ends, False, "只有 html 缺 py/c → 红")
    else:
        print("  [跳过] 三端自测（缺 gcc/node 或模板目录）")

    # 3. ASCII-safe
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "ok.txt", " .:-=+*#%@\n")
        all_ok &= _expect(td, "ascii-safe", td, check_ascii_safe, True, "纯 ASCII + LF → 绿")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "crlf.txt", "abc\r\ndef\r\n", binary=True)
        all_ok &= _expect(td, "ascii-safe", td, check_ascii_safe, False, "含 CR → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "fullwidth.txt", "ｱｲｳ\n")
        all_ok &= _expect(td, "ascii-safe", td, check_ascii_safe, False, "ASCII-safe 档含全角字符 → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "uni.txt", "ｱｲｳ ░▒▓█\n")
        all_ok &= _expect(td, "ascii-safe", td, check_ascii_safe, True, "Unicode 档白名单内 → 绿", mode="unicode")
        _fixture(td, "bad_uni.txt", "😀 emoji 宽度不定\n")
        all_ok &= _expect(td, "ascii-safe", td, check_ascii_safe, False, "Unicode 档含 emoji → 红", mode="unicode")

    # 4. 浮点元数据
    good_meta = {"width": 320, "height": 200, "channels": 4, "colorspace": "srgb",
                 "premultiplied": False, "rowOrder": "top-down", "sourceWidth": 1600, "downsampled": True}
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "img.meta.json", json.dumps(good_meta))
        all_ok &= _expect(td, "float-meta", td, check_float_meta, True, "四件套 + rowOrder + 降采样 → 绿")
    with tempfile.TemporaryDirectory() as td:
        bad = dict(good_meta); bad.pop("colorspace")
        _fixture(td, "img.meta.json", json.dumps(bad))
        all_ok &= _expect(td, "float-meta", td, check_float_meta, False, "缺 colorspace → 红")
    with tempfile.TemporaryDirectory() as td:
        bad = dict(good_meta); bad["rowOrder"] = "bottom-up"
        _fixture(td, "img.meta.json", json.dumps(bad))
        all_ok &= _expect(td, "float-meta", td, check_float_meta, False, "rowOrder=bottom-up → 红")
    with tempfile.TemporaryDirectory() as td:
        bad = dict(good_meta); bad["width"] = 1600; bad["downsampled"] = False
        _fixture(td, "img.meta.json", json.dumps(bad))
        all_ok &= _expect(td, "float-meta", td, check_float_meta, False, "大图未降采样 → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "img.meta.json", json.dumps(good_meta))
        _fixture(td, "img.pfm", b"PF\n320 200\n-1.0\n" + b"\x00" * 16, binary=True)
        all_ok &= _expect(td, "float-meta", td, check_float_meta, True, "PFM 头与元数据一致 → 绿")
        _fixture(td, "img.pfm", b"PF\n200 320\n-1.0\n" + b"\x00" * 16, binary=True)
        all_ok &= _expect(td, "float-meta", td, check_float_meta, False, "PFM 头尺寸不符 → 红")

    # 5. 图表数据 + niceCeil
    good_nice = "function niceCeil(v) {\n  if (v <= 0) return 0;\n  const pow = Math.pow(10, Math.floor(Math.log10(v)));\n  const n = v / pow;\n  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;\n}\n"
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "a/data.json", json.dumps({"series": [{"name": "x", "values": [1, 2]}]}))
        _fixture(td, "b/data.json", json.dumps({"series": [{"name": "x", "values": [1, 2]}]}))
        _fixture(td, "chart.js", good_nice)
        all_ok &= _expect(td, "chart-data", td, check_chart_data, True, "data.json 同源 + niceCeil 正确 → 绿")
        _fixture(td, "b/data.json", json.dumps({"series": [{"name": "x", "values": [1, 3]}]}))
        all_ok &= _expect(td, "chart-data", td, check_chart_data, False, "两份 data.json 内容不同 → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "a/data.json", json.dumps({"series": []}))
        _fixture(td, "chart.js", good_nice.replace("n <= 5 ? 5 : 10", "n <= 5 ? 3 : 10"))
        all_ok &= _expect(td, "chart-data", td, check_chart_data, False, "niceCeil 返回 3 的倍数 → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "a/data.json", json.dumps({"series": []}))
        all_ok &= _expect(td, "chart-data", td, check_chart_data, False, "缺 niceCeil → 红")

    # 6. 回显消毒
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "term.html", "const sanitize = s => String(s).replace(/[\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F\\u007F]/g, '');\n")
        all_ok &= _expect(td, "sanitize", td, check_sanitize, True, "完整消毒正则 → 绿")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "term.html", "const sanitize = s => String(s).replace(/[\\u0000]/g, '');\n")
        all_ok &= _expect(td, "sanitize", td, check_sanitize, False, "只剥 NUL 不剥 ESC → 红")
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "echo.txt", "hi\x1b[31mthere\x07", binary=True)
        all_ok &= _expect(td, "sanitize", td, check_sanitize, False, "回显样本含 ESC/BEL → 红",
                          sample=str(Path(td) / "echo.txt"))

    # 7. Remotion
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "src/A.tsx", "import {random} from 'remotion';\nconst a = random('x');\n")
        mp4 = Path(td) / "out" / "a.mp4"
        mp4.parent.mkdir(parents=True, exist_ok=True)
        made = False
        if have("ffmpeg"):
            r = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                     "-i", "color=c=black:s=64x64:d=1:r=10", "-pix_fmt", "yuv420p", "-y", str(mp4)])
            made = r.returncode == 0 and mp4.exists()
        if made:
            all_ok &= _expect(td, "remotion", td, check_remotion, True, "mp4 存在 + src 无 Math.random → 绿")
        else:
            print("  [跳过] Remotion 绿例（缺 ffmpeg，无法生成合法 mp4）")
        _fixture(td, "src/B.tsx", "const v = Math.random();\n")
        all_ok &= _expect(td, "remotion", td, check_remotion, False, "src 出现 Math.random → 红")
        (Path(td) / "src/B.tsx").unlink()
        mp4.unlink()
        all_ok &= _expect(td, "remotion", td, check_remotion, False, "缺 out/*.mp4 → 红")

    # 8. 网络加载卫生
    with tempfile.TemporaryDirectory() as td:
        _fixture(td, "a.js", "async function loadWithRetry(u) { return await fetch(u); }\n")
        all_ok &= _expect(td, "network", td, check_network, True, "fetch 在 loadWithRetry 内 → 绿")
        _fixture(td, "b.js", "async function init() { const r = await fetch('x.json'); }\n")
        all_ok &= _expect(td, "network", td, check_network, False, "业务函数里裸 await fetch → 红")

    print()
    if all_ok:
        print("[self-test] 结论：全部门禁的必红用例均按预期失败，绿例均通过")
        return 0
    print("[self-test] 结论：存在未按预期行为的门禁（见上方 [自测失败]）")
    return 1


def main():
    ap = argparse.ArgumentParser(description="ascii-web-design 交付物验收器（SKILL.md §7【自动】项）")
    ap.add_argument("check", choices=sorted(CHECKS) + ["all", "self-test"])
    ap.add_argument("target", nargs="?", help="待验收的目录或文件")
    ap.add_argument("--slug", help="三端基名（不给则自动找同名的 html/py/c）")
    ap.add_argument("--frame", type=int, default=7, help="三端比对用的帧号（默认 7）")
    ap.add_argument("--mode", choices=["ascii-safe", "unicode"], default="ascii-safe")
    ap.add_argument("--ramp", help="显式指定要校验的 ramp（默认取契约 ramp 并从源码抽取）")
    ap.add_argument("--data-name", default="data.json", help="图表数据文件名（默认 data.json）")
    ap.add_argument("--echo-file", help="回显样本文件（校验其中不含控制字符）")
    ap.add_argument("--expected-duration", type=float, help="期望视频时长（秒）")
    a = ap.parse_args()

    if a.check == "self-test":
        sys.exit(self_test())
    if not a.target:
        ap.error("缺少目标路径")
    root = Path(a.target)
    if not root.exists():
        print(f"[失败] 目标不存在：{root}")
        sys.exit(2)

    if a.check == "all":
        sys.exit(run_all(root, a))
    rep = Report(a.check)
    CHECKS[a.check](root, a, rep)
    sys.exit(rep.verdict())


if __name__ == "__main__":
    main()
