#!/usr/bin/env python3
"""ascii.py —— ascii-web-design 三端骨架之 Python 终端版（Python 3.8+，零第三方依赖）。

视觉契约（SKILL.md §1.2）：RAMP 10 级 / Rec.601 亮度 / 纵横比 0.55 / COLS 120 / fps 12 / 强调色 #00FF41。
与同目录 ascii.html、ascii.c 同源：同一 ramp、同一列数与行数逻辑、同一强调色、同一帧间隔 1/12s。
三端一致性由 scripts/verify_deliverable.py 断言（逐字节比对 renderFrame 输出）。

用法：
    python3 ascii.py                 # 无限循环动画（Ctrl+C 干净退出并恢复终端）
    python3 ascii.py --frames 3      # 播 3 帧后退出（适合录屏/管道测试）
    python3 ascii.py --dump 5        # 只打印第 5 帧的裸网格（无 ANSI，供三端比对）
    python3 ascii.py --no-color      # 关闭 24-bit 真彩色（仅纯 ASCII 输出）
    python3 ascii.py --cols 100      # 改列数（行数按 16:9 × 0.55 联动；契约甜点 80–160）
"""

import argparse
import os
import shutil
import signal
import sys
import time

# ==== ASCII KERNEL BEGIN ====  （与 ascii.html / ascii.c 同源，改动必须三端同步）
RAMP = " .:-=+*#%@"
COLS = 120
ASPECT = 0.55
FPS = 12
ACCENT_RGB = (0, 255, 65)          # #00FF41


def rows_for(cols):
    """16:9 演示幅面的行数：round(cols × 9/16 × 0.55)，整数式保证三端逐位一致。"""
    return (cols * 495 + 800) // 1600


def tri(u):
    """三角波：整数相位折回 0..1000。"""
    m = ((u % 2000) + 2000) % 2000
    return m if m <= 1000 else 2000 - m


def lum1000(x, y, t):
    """演示亮度场（毫单位 0..1000）：两路正交三角波取差 → 斜向移动的呼吸波纹。"""
    return abs(tri(x * 200 + t * 160) - tri(y * 350 - t * 110))


def char_at_1000(v):
    """亮度 → 字符：契约公式 floor(lum × (n−1)) 的整数等价式（v 为 0..1000 毫单位）。"""
    return RAMP[v * (len(RAMP) - 1) // 1000]


def render_frame(t, cols=COLS):
    """第 t 帧 → 整幅网格字符串（行尾无空格，行间 \\n）。"""
    rows = rows_for(cols)
    return "\n".join(
        "".join(char_at_1000(lum1000(x, y, t)) for x in range(cols))
        for y in range(rows)
    )
# ==== ASCII KERNEL END ====

FRAME_DELAY = 1.0 / FPS            # 帧间隔 1/12s（契约：与 HTML 的 STEP、C 的 FRAME_TS 一致）
RESET = "\033[m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
HOME = "\033[H"

_resized = [False]


def _on_winch(sig, frame):
    _resized[0] = True


def _cleanup(sig, frame):
    """Ctrl+C / SIGTERM：恢复光标与颜色，干净退出（终端不被搞坏）。"""
    sys.stdout.write(SHOW_CURSOR + RESET)
    sys.stdout.flush()
    sys.exit(0)


def play(frames, cols, color):
    signal.signal(signal.SIGINT, _cleanup)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _cleanup)
    if hasattr(signal, "SIGWINCH"):
        signal.signal(signal.SIGWINCH, _on_winch)
    prefix = "\033[38;2;%d;%d;%dm" % ACCENT_RGB if color else ""
    sys.stdout.write(HIDE_CURSOR + "\033[2J")
    count = 0
    try:
        while True:
            if _resized[0]:                     # 窗口变化：清屏重画，避免残影
                _resized[0] = False
                sys.stdout.write("\033[2J")
            term_cols = shutil.get_terminal_size().columns
            use_cols = min(cols, term_cols) if term_cols >= 16 else cols
            for t in range(frames if frames else 1 << 30):
                sys.stdout.write(HOME + prefix + render_frame(t, use_cols) + RESET)
                sys.stdout.flush()
                count += 1
                if frames and count >= frames:
                    return
                time.sleep(FRAME_DELAY)
    finally:
        sys.stdout.write(SHOW_CURSOR + RESET)
        sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="ASCII 骨架 · Python 终端版（零依赖）")
    ap.add_argument("--frames", type=int, default=0, help="播放帧数后退出（0 = 无限循环）")
    ap.add_argument("--dump", type=int, default=None, help="只打印第 N 帧裸网格（无 ANSI）")
    ap.add_argument("--cols", type=int, default=COLS, help=f"列数（默认 {COLS}，甜点 80–160）")
    ap.add_argument("--no-color", action="store_true", help="关闭 24-bit 真彩色")
    args = ap.parse_args()

    if args.dump is not None:
        sys.stdout.write(render_frame(args.dump, args.cols) + "\n")
        return
    if os.name == "nt":
        os.system("")                        # 原生 Windows 启用 VT 序列
    play(args.frames, args.cols, not args.no_color)


if __name__ == "__main__":
    main()
