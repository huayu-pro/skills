#!/usr/bin/env python3
"""ascii_pipeline.py —— 构建期 ASCII 资产管线（构建期预生成字符帧，运行时零解码）。

把图片 / GIF / 视频在**构建期**离线转成 ASCII 帧文件（frames.json + 可选首帧 txt），
网页端直接 fetch 本地 JSON 即刻播放；失败兜底用首帧 txt 内联；亦可直接喂给
Remotion 帧序列模式（remotion-video.md §R.6）。采样算法与 image-to-ascii.md §2.1
同一内核：Rec.601 亮度 + 纵横比修正 0.55 + alpha 合成黑底。

用法：
    python3 scripts/ascii_pipeline.py <输入文件> [--cols 120] [--ramp ' .:-=+*#%@']
                                     [--fps 12] [--out frames.json] [--inline-first]
    python3 scripts/ascii_pipeline.py serve [--out frames.json] [--port 8765]
                                            # 本地实时预览：文件变更自动重载
    python3 scripts/ascii_pipeline.py self-test        # 零依赖自检（生成渐变图并转换验证）

依赖（均为可选，缺失时按输入类型给出中文指引）：
    Pillow  —— 图片(PNG/JPG/WebP)与 GIF 帧解码：pip install Pillow（国内镜像可用）
    ffmpeg  —— 视频抽帧（系统命令）；抽帧产物为 PPM，后续走纯标准库路径

退出码：0 成功；2 用法错误（argparse 原生）；3 依赖缺失；4 输入文件问题。
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ASPECT = 0.55          # 纵横比修正（视觉契约，SKILL.md §1.2；字符格高瘦）
DEFAULT_RAMP = " .:-=+*#%@"
DEFAULT_FPS = 12        # 非 GIF 输入的默认帧率（GIF 按每帧 delay 自动推算）
DEFAULT_COLS = 120

EXIT_DEPENDENCY = 3    # 依赖缺失
EXIT_FILE = 4          # 输入文件问题


# ── 采样内核（与 image-to-ascii.md §2.1 同一算法，Python 版单一事实源） ──────────

def sample_frame(rgba, width, height, cols, ramp):
    """RGBA 像素字节串 → ASCII 行列表。亮度映射：深底亮字符（亮部→密字符）。"""
    rows = max(1, round(height / width * cols * ASPECT)) if width else 1
    n = len(ramp)
    lines = []
    for y in range(rows):
        sy = min(height - 1, y * height // rows)          # 最近邻采样
        chars = []
        for x in range(cols):
            sx = min(width - 1, x * width // cols)
            i = (sy * width + sx) * 4
            r, g, b, a = rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 * (a / 255.0)  # alpha 合成黑底
            chars.append(ramp[min(n - 1, int(lum * (n - 1)))])  # 契约索引公式 floor(lum×(n−1))
        lines.append("".join(chars))
    return lines


# ── PPM/PGM 纯标准库解码（无 Pillow 时的兜底路径；也是视频抽帧的产物格式） ────────

def read_pnm(path):
    """读 P5/P6 二进制位图，返回 (rgba 字节串, width, height)。"""
    data = Path(path).read_bytes()
    tokens, pos = [], 0
    while len(tokens) < 4:                                 # 魔数/宽/高/最大值，# 为注释行
        while pos < len(data) and data[pos : pos + 1].isspace():
            pos += 1
        if data[pos : pos + 1] == b"#":
            pos = data.index(b"\n", pos) + 1
            continue
        start = pos
        while pos < len(data) and not data[pos : pos + 1].isspace():
            pos += 1
        tokens.append(data[start:pos])
    magic, w, h, _maxval = tokens[0], int(tokens[1]), int(tokens[2]), int(tokens[3])
    pos += 1                                               # 跳过头部长度分隔符（单个空白）
    w, h = int(w), int(h)
    if magic == b"P6":                                     # RGB 三通道
        rgb, px = data[pos : pos + w * h * 3], 3
    elif magic == b"P5":                                   # 灰度单通道
        rgb, px = data[pos : pos + w * h], 1
    else:
        raise ValueError(f"不支持的 PNM 类型：{magic.decode(errors='replace')}（仅 P5/P6）")
    if len(rgb) < w * h * px:
        raise ValueError("PNM 数据体不完整，文件可能被截断")
    rgba = bytearray(w * h * 4)
    for i in range(w * h):
        if px == 3:
            rgba[i * 4 : i * 4 + 3] = rgb[i * 3 : i * 3 + 3]
        else:
            rgba[i * 4 : i * 4 + 3] = rgb[i : i + 1] * 3   # 灰度复制到三通道
        rgba[i * 4 + 3] = 255
    return bytes(rgba), w, h


# ── 各输入类型的帧获取 ────────────────────────────────────────────────────────

def frames_from_image(path):
    """静态图片 → 单帧。优先 Pillow（格式全），缺失时走 PNM 标准库路径。"""
    try:
        from PIL import Image                              # Pillow 可选依赖
    except ImportError:
        if path.suffix.lower() in (".ppm", ".pgm"):
            rgba, w, h = read_pnm(path)
            return [(rgba, w, h, None)]
        sys.exit(
            f"[依赖缺失] 解码 {path.suffix} 需要 Pillow：请先执行  pip install Pillow\n"
            f"（国内镜像：pip install Pillow -i https://pypi.tuna.tsinghua.edu.cn/simple）"
        )
    try:
        img = Image.open(path).convert("RGBA")
    except Exception as e:                                 # 文件损坏 / 非图片
        sys.exit(f"[文件问题] 无法解码图片 {path}：{e}")
    return [(img.tobytes(), img.width, img.height, None)]


def frames_from_gif(path):
    """GIF → 多帧（逐帧 delay 毫秒）。需要 Pillow（标准库不解 GIF）。"""
    try:
        from PIL import Image, ImageSequence
    except ImportError:
        sys.exit(
            "[依赖缺失] GIF 逐帧解码需要 Pillow：请先执行  pip install Pillow\n"
            "（国内镜像：pip install Pillow -i https://pypi.tuna.tsinghua.edu.cn/simple）"
        )
    try:
        gif = Image.open(path)
    except Exception as e:
        sys.exit(f"[文件问题] 无法解码 GIF {path}：{e}")
    out = []
    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert("RGBA")
        delay = frame.info.get("duration", 100) or 100     # 单帧 delay（毫），缺省 100
        out.append((rgba.tobytes(), rgba.width, rgba.height, delay))
    if not out:
        sys.exit(f"[文件问题] GIF {path} 没有可用帧")
    return out


def frames_from_video(path, fps):
    """视频 → ffmpeg 抽帧（PPM）→ 纯标准库解码。ffmpeg 缺失时给安装指引。"""
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "[依赖缺失] 视频抽帧需要 ffmpeg：\n"
            "  Debian/Ubuntu: sudo apt install ffmpeg    Fedora: sudo dnf install ffmpeg\n"
            "  macOS(brew): brew install ffmpeg          Windows: winget install Gyan.FFmpeg"
        )
    with tempfile.TemporaryDirectory(prefix="ascii_pipe_") as tmp:
        pattern = str(Path(tmp) / "frame%06d.ppm")
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
               "-vf", f"fps={fps}", pattern]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(f"[文件问题] ffmpeg 抽帧失败（{path}）：{proc.stderr.strip()[:300]}")
        frames = sorted(Path(tmp).glob("frame*.ppm"))
        if not frames:
            sys.exit(f"[文件问题] {path} 未抽出任何帧（文件损坏或非视频？）")
        return [(*read_pnm(f), None) for f in frames]


# ── 主流程 ───────────────────────────────────────────────────────────────────

def convert(args):
    src = Path(args.input)
    if not src.is_file():
        sys.exit(f"[文件问题] 找不到输入文件：{src}（请核对路径与文件名大小写）")

    suffix = src.suffix.lower()
    if suffix == ".gif":
        raw = frames_from_gif(src)
    elif suffix in (".mp4", ".mkv", ".mov", ".webm", ".avi"):
        raw = frames_from_video(src, args.fps or DEFAULT_FPS)
    else:
        raw = frames_from_image(src)

    # 帧率：GIF 按各帧 delay 中位数推算（保持原节奏）；其余用 --fps（默认 12）
    delays = sorted(d for *_, d in raw if d)
    if suffix == ".gif" and delays and args.fps is None:
        fps = max(1, min(50, round(1000 / delays[len(delays) // 2])))
    else:
        fps = args.fps or DEFAULT_FPS

    grids = [sample_frame(rgba, w, h, args.cols, args.ramp) for rgba, w, h, _ in raw]
    _, w0, h0, _ = raw[0]
    doc = {
        "meta": {
            "cols": args.cols, "rows": len(grids[0]), "fps": fps,
            "ramp": args.ramp, "aspect": ASPECT,
            "source": src.name, "width": w0, "height": h0, "frameCount": len(grids),
        },
        "frames": ["\n".join(g) for g in grids],
    }

    out = Path(args.out)
    out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if args.inline_first:
        Path(out.with_suffix(".first-frame.txt")).write_text(doc["frames"][0], encoding="utf-8")

    size_kb = out.stat().st_size / 1024
    print(f"[完成] {len(grids)} 帧 × {args.cols}列 → {out}（{size_kb:.0f} KB，fps={fps}）")
    if args.inline_first:
        print(f"[兜底] 首帧已内联导出：{out.with_suffix('.first-frame.txt')}")
    if size_kb > 800:
        print("[提醒] 产物超过 800KB：建议 --cols 降到 100 以下，或对视频降低 --fps 再跑一次")


def self_test():
    """零依赖自检：内存生成 64×32 渐变 PPM → 转换 → 断言尺寸、字符域与索引公式。"""
    w, h = 64, 32
    header = f"P6\n{w} {h}\n255\n".encode()
    body = bytes(b for y in range(h) for x in range(w) for b in (x * 255 // w,) * 3)  # 行主序横向渐变
    with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
        f.write(header + body)
        tmp = Path(f.name)
    try:
        rgba, rw, rh = read_pnm(tmp)
        assert (rw, rh) == (w, h), "PNM 解码尺寸不符"
        lines = sample_frame(rgba, rw, rh, cols=32, ramp=DEFAULT_RAMP)
        assert len(lines) == max(1, round(h / w * 32 * ASPECT)), "行数与纵横比公式不符"
        left, right = lines[0][0], lines[0][-1]
        assert left == DEFAULT_RAMP[0], f"最暗端应为空格，得到 {left!r}"
        assert DEFAULT_RAMP.index(right) > DEFAULT_RAMP.index(left), "渐变方向错误：亮端应映射到密字符"
        print(f"[自检通过] 32 列渐变图转换正常（首行：{lines[0][:16]}…），纵横比 {ASPECT} 生效")
    finally:
        tmp.unlink(missing_ok=True)

    # 索引公式契约（SKILL.md §1.2）：index = min(n-1, floor(lum × (n−1)))
    # 探针取「旧 ×n 写法与契约 ×(n−1) 必然分歧」的灰阶：v = ceil(255×i/n)，i=1..n−1。
    # 这类亮度落在 [i/n, i/(n−1)) 区间内——×n 会错判成第 i 档，×(n−1) 必须仍是第 i−1 档。
    n = len(DEFAULT_RAMP)
    probes = []
    for i in range(1, n):
        v = -(-255 * i // n)                              # ceil(255×i/n)
        idx = (v * (n - 1)) // 255                        # 契约的整数等价式
        probes.append((v, DEFAULT_RAMP[idx]))
        got = sample_frame(bytes((v, v, v, 255)), 1, 1, 1, DEFAULT_RAMP)[0][0]
        assert got == probes[-1][1], (
            f"索引公式偏离契约 floor(lum×(n−1))：灰阶 {v}/255 应得 {probes[-1][1]!r}，实得 {got!r}"
            f"（实得为更密一档说明仍用旧的 ×n 写法）"
        )
    px = bytes((255, 255, 255, 255))
    assert sample_frame(px, 1, 1, 1, DEFAULT_RAMP)[0][0] == DEFAULT_RAMP[-1], "纯白必须映射到 ramp 末字符"
    print(f"[自检通过] 亮度→字符索引公式 floor(lum×(n−1)) 逐档吻合（{n - 1} 个分歧探针 + 纯白端点）")


PREVIEW_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>ASCII 预览</title>
<style>body{background:#111;color:#ccc;font-family:ui-monospace,Consolas,monospace}
pre{font-size:14px;line-height:1.05;white-space:pre}
#tip{color:#888;font-size:12px;font-family:sans-serif;margin-bottom:8px}</style></head>
<body><div id="tip">监视 frames.json，文件变更后自动重载</div><pre id="a"></pre>
<script>
let frames=[],fps=12,i=0,last=null;
async function load(){const d=await(await fetch('frames.json',{cache:'no-store'})).json();
 frames=d.frames||[];fps=(d.meta&&d.meta.fps)||12;i=0;}
function tick(){if(frames.length){document.getElementById('a').textContent=frames[i%frames.length];i++;}}
load();setInterval(tick,1000/fps);
setInterval(async()=>{try{const r=await fetch('frames.json',{method:'HEAD',cache:'no-store'});
 const lm=r.headers.get('Last-Modified');
 if(last===null)last=lm;else if(lm&&lm!==last){last=lm;await load();}}catch(e){}},1500);
</script></body></html>"""


def serve(args):
    """本地实时预览：起 http 服务渲染 --out 的 frames.json，文件变更自动重载。"""
    import http.server
    frames_path = Path(args.out).resolve()
    if not frames_path.exists():
        print(f"[失败] 预览目标不存在：{frames_path}（先跑 convert 生成，或用 --out 指向已有产物）")
        sys.exit(4)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body, ctype = PREVIEW_HTML.encode("utf-8"), "text/html; charset=utf-8"
            elif self.path == "/frames.json":
                body, ctype = frames_path.read_bytes(), "application/json; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self):
            if self.path != "/frames.json":
                self.send_error(404)
                return
            st = frames_path.stat()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Last-Modified", time.strftime(
                "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(st.st_mtime)))
            self.send_header("Content-Length", str(st.st_size))
            self.end_headers()

        def log_message(self, fmt, *a):
            pass  # 静默访问日志，避免刷屏

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[预览] http://127.0.0.1:{args.port}/ （监视 {frames_path.name}，变更自动重载，Ctrl+C 停止）")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[停止] 预览服务已关闭")


def main():
    parser = argparse.ArgumentParser(
        description="构建期 ASCII 资产管线：图片/GIF/视频 → frames.json（详见 web-implementation.md §3.9）")
    parser.add_argument("input", nargs="?", help="输入文件（图片 / .gif / 视频）；或 self-test")
    parser.add_argument("--cols", type=int, default=DEFAULT_COLS, help=f"输出列数（默认 {DEFAULT_COLS}）")
    parser.add_argument("--ramp", default=DEFAULT_RAMP, help="亮度→字符映射串（默认 10 级经典 ramp）")
    parser.add_argument("--fps", type=int, default=None,
                        help=f"帧率（默认 {DEFAULT_FPS}；GIF 自动按原 delay 推算）")
    parser.add_argument("--out", default="frames.json", help="输出 JSON 路径（默认 frames.json）")
    parser.add_argument("--inline-first", action="store_true",
                        help="额外导出首帧 txt（网页加载失败的静态兜底素材）")
    parser.add_argument("--port", type=int, default=8765,
                        help="serve 预览端口（默认 8765，仅监听 127.0.0.1）")
    args = parser.parse_args()

    if args.input == "self-test":
        self_test()
        return
    if args.input == "serve":
        serve(args)
        return
    if not args.input:
        parser.error("缺少输入文件（用法：ascii_pipeline.py <文件> [选项]，或 self-test 自检，或 serve 预览）")
    if args.cols < 16 or args.cols > 400:
        parser.error("--cols 取值 16–400（视觉契约甜点 80–160，见 SKILL.md §1.2）")
    convert(args)


if __name__ == "__main__":
    main()
