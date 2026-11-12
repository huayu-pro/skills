#!/usr/bin/env python3
"""批量把 SVG 渲染成 PNG，供目检使用。

用法:
    python3 scripts/render_svg.py <svg文件或目录> [--out 输出目录] [--scale 2]
    python3 scripts/render_svg.py assets/templates --sheet /tmp/sheet.png

--sheet 会把所有渲染结果拼成一张缩略图总览（批量验收时不用逐张打开）。
依赖: cairosvg（必需）、Pillow（仅 --sheet 需要）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import cairosvg
except ImportError:
    print("缺少 cairosvg，先执行: pip install cairosvg")
    sys.exit(4)


def render_one(svg: Path, out_dir: Path, scale: float) -> Path | None:
    out = out_dir / (svg.stem + ".png")
    try:
        cairosvg.svg2png(url=str(svg), write_to=str(out), scale=scale)
        print(f"OK   {svg.name} -> {out.name}")
        return out
    except Exception as e:  # 单个失败不影响整批
        print(f"FAIL {svg.name}: {e}")
        return None


def build_sheet(pngs: list[Path], sheet: Path, cols: int, thumb_w: int) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("--sheet 需要 Pillow，先执行: pip install pillow")
        return
    if not pngs:
        return
    font = None
    for cand in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"):
        if Path(cand).exists():
            font = ImageFont.truetype(cand, 16)
            break
    if font is None:
        font = ImageFont.load_default()

    thumbs = []
    for p in pngs:
        im = Image.open(p).convert("RGB")
        h = max(1, round(im.height * thumb_w / im.width))
        thumbs.append((p, im.resize((thumb_w, h))))
    cell_h = max(t.height for _, t in thumbs) + 34
    rows = (len(thumbs) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * (thumb_w + 16) + 16, rows * cell_h + 16), "#E9EDF2")
    draw = ImageDraw.Draw(canvas)
    for i, (p, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = 16 + c * (thumb_w + 16)
        y = 16 + r * cell_h
        canvas.paste(t, (x, y))
        draw.rectangle([x, y, x + t.width, y + t.height], outline="#B7C0CC")
        label = p.stem if len(p.stem) <= 28 else p.stem[:27] + "…"
        draw.text((x, y + t.height + 6), label, fill="#33404F", font=font)
    canvas.save(sheet)
    print(f"拼版 -> {sheet}（{len(thumbs)} 张，{cols} 列）")


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG 批量渲染质检")
    ap.add_argument("target", help="SVG 文件或目录（不递归）")
    ap.add_argument("--out", default=None, help="PNG 输出目录，默认与 SVG 同目录")
    ap.add_argument("--scale", type=float, default=2.0, help="缩放倍数，默认 2")
    ap.add_argument("--sheet", default=None, help="额外输出一张缩略图总览")
    ap.add_argument("--cols", type=int, default=6, help="总览列数，默认 6")
    ap.add_argument("--thumb-width", type=int, default=420, help="总览单图宽，默认 420")
    args = ap.parse_args()

    if args.scale <= 0 or args.scale != args.scale:
        print("--scale 必须为正数")
        return 1
    if args.cols < 1:
        print("--cols 必须 ≥1")
        return 1

    target = Path(args.target)
    if not target.exists():
        print(f"目标不存在: {target}")
        return 1
    svgs = (sorted(p for p in target.iterdir() if p.is_file() and p.suffix.lower() == ".svg")
            if target.is_dir() else [target])
    if not svgs:
        print("未找到 SVG 文件")
        return 1
    out_dir = Path(args.out) if args.out else (target if target.is_dir() else target.parent)
    if out_dir.exists() and not out_dir.is_dir():
        print(f"--out 指向的不是目录: {out_dir}")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    ok, done = 0, []
    for svg in svgs:
        png = render_one(svg, out_dir, args.scale)
        if png:
            ok += 1
            done.append(png)
    print(f"\n完成: 成功 {ok}, 失败 {len(svgs) - ok}")
    if args.sheet:
        if not done:
            print("没有渲染成功的文件，--sheet 跳过")
        else:
            build_sheet(done, Path(args.sheet), args.cols, args.thumb_width)
    return 0 if ok == len(svgs) else 1


if __name__ == "__main__":
    sys.exit(main())
