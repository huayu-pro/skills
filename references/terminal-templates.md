# 三端交付模板（HTML + Python + C，统一命名）

**分级交付规则**：HTML 版必有；Python / C 版由深度档"技术栈偏好"选项决定——用户未表态时默认只交付 HTML；选择三端时按本文件执行。静态装饰件（无动画、无采样）可不交付终端版。

```
<slug>/
├── <slug>.html    # Web 版（主交付物）
├── <slug>.py      # 终端版，Python 3 标准库，零依赖
└── <slug>.c       # 终端版，C99 + POSIX，gcc 直编
```

slug 取用户场景语义（如 `matrix-rain`、`ghost-logo`），用户没给就自己起一个并告知。

**三端一致性契约**：同一 ramp 字符串、同一列数逻辑、同一强调色、同一帧间隔。用户在三端看到同一作品，只是载体不同。这四项与 SKILL.md §1.2 视觉契约表的「RAMP / COLS 甜点 / 强调色（24-bit ANSI） / 帧率·帧间隔」四行**同源**——本文是它们在终端侧的展开，改一处必须改两边。可直接复制运行的三端骨架见 `assets/templates/ascii.{html,py,c}`（同一 ramp / 同一行数公式 / 同一强调色 / 同一帧间隔，`scripts/verify_deliverable.py three-ends` 断言三端同帧输出逐字节一致）。

**控制字符即协议**：终端版的全部魔法来自 ASCII 控制区——`ESC(27)` 即 `\033`，后接 `[` 开头 ANSI 序列（`\033[H` 光标回顶、`\033[?25l` 隐藏光标、`\033[38;2;r;g;bm` 真彩色前景、`\033[m` 复位）；`LF(10)` 分行。不要把其他控制字符（BEL/BS/CR 等）混进帧数据。

**24-bit ANSI 色表（三端一致契约）**：网页 `color: #00FF41` 与终端 `\033[38;2;0;255;65m` 是同一强调色的两种写法，分量顺序固定为 `38;2;R;G;B`（前景）/ `48;2;R;G;B`（背景），复位统一 `\033[m`：

| 风格预设（SKILL.md §0.1） | 十六进制 | ANSI 前景序列 |
|---|---|---|
| Matrix 黑客 | `#00FF41` | `\033[38;2;0;255;65m` |
| 琥珀终端 | `#FFB000` | `\033[38;2;255;176;0m` |
| Cyberpunk 品红 | `#FF00FF` | `\033[38;2;255;0;255m` |
| Cyberpunk 青 | `#00FFFF` | `\033[38;2;0;255;255m` |
| 极简禅（白） | `#E0E0E0` | `\033[38;2;224;224;224m` |

不支持 truecolor 的终端（仅 256 色）按最近色降级：`#00FF41` → `\033[38;5;46m`；判断方式 `echo $COLORTERM` 含 `truecolor`/`24bit` 才用 `38;2`。

## Python 终端版模板（stdlib only，最通行）

```python
#!/usr/bin/env python3
"""<slug> — 终端 ASCII 版。依赖：Python 3.6+，零第三方库。"""
import itertools, os, shutil, signal, sys, time

RAMP = ' .:-=+*#%@'          # 与 SKILL.md §1.2 视觉契约一致
FPS_DELAY = 1 / 12           # 与 HTML 的 STEP、C 的 FRAME_TS 同源（契约帧间隔）
COLOR = '\033[38;2;0;255;65m'  # 强调色 #00FF41（24-bit ANSI，色表见上文；按风格预设替换）
RESET = '\033[m'

_resized = [False]
def _on_winch(sig, frame):
    _resized[0] = True

def sample_frame(rgba, width, height, cols, ramp=RAMP):
    """RGBA 字节串 → ASCII 行列表。与 scripts/ascii_pipeline.py 的 sample_frame() 同源
    （同一 Rec.601 亮度 / 同一 0.55 纵横比 / 同一索引公式 floor(lum×(n−1))），此处复制以保持模板零依赖。"""
    ASPECT = 0.55
    rows = max(1, round(height / width * cols * ASPECT)) if width else 1
    n = len(ramp)
    lines = []
    for y in range(rows):
        sy = min(height - 1, y * height // rows)          # 最近邻采样
        line = []
        for x in range(cols):
            sx = min(width - 1, x * width // cols)
            i = (sy * width + sx) * 4
            r, g, b, a = rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 * (a / 255.0)  # alpha 合成黑底
            line.append(ramp[min(n - 1, int(lum * (n - 1)))])   # 契约索引公式
        lines.append(''.join(line))
    return lines

def _tri(u):
    """三角波：整数相位折回 0..1000（与 assets/templates/ascii.py 同源）。"""
    m = ((u % 2000) + 2000) % 2000
    return m if m <= 1000 else 2000 - m

def _demo_frame(t, cols, ramp):
    """内置演示帧：两路正交三角波取差 → 斜向移动的呼吸波纹（开箱即跑，无需素材）。"""
    rows = (cols * 495 + 800) // 1600          # 16:9 幅面：round(cols × 9/16 × 0.55)，整数式与骨架一致
    return '\n'.join(
        ''.join(ramp[abs(_tri(x * 200 + t * 160) - _tri(y * 350 - t * 110)) * (len(ramp) - 1) // 1000]
                for x in range(cols))
        for y in range(rows))

def frames(source=None, cols=120, ramp=RAMP):
    """生成或加载 ASCII 帧（静态作品只产一帧）。
    - source 为 None：返回内置演示帧（默认路由，保证模板开箱即跑）。
    - source 为 .ppm（P6）：纯标准库解码后采样——零依赖路线的正确落点。
    - 其他格式（PNG/JPG/GIF）：用 scripts/ascii_pipeline.py 预转成 PPM 或 frames.json 再来。"""
    if source is None:
        for t in itertools.count():                        # 无限演示
            yield _demo_frame(t, cols, ramp)
    data = open(source, 'rb').read()                       # 极简 P6 读取（P5 灰度需另扩展）
    parts = data.split(maxsplit=4)                         # 魔数 / 宽 / 高 / 最大值 / 数据体
    w, h = int(parts[1]), int(parts[2])
    body = parts[4]
    rgba = bytearray(w * h * 4)
    for k in range(w * h):
        rgba[k * 4:k * 4 + 3] = body[k * 3:k * 3 + 3]
        rgba[k * 4 + 3] = 255
    yield '\n'.join(sample_frame(bytes(rgba), w, h, cols, ramp))

def main():
    signal.signal(signal.SIGWINCH, _on_winch)     # 注册窗口变化
    os.system('cls' if os.name == 'nt' else 'clear')
    sys.stdout.write('\033[?25l')             # 隐藏光标
    try:
        while True:
            if _resized[0]:                   # 尺寸已变：下一帧按新尺寸重算网格
                _resized[0] = False
            cols, rows = shutil.get_terminal_size()
            for f in frames():
                sys.stdout.write('\033[H' + COLOR + f + RESET)  # 光标回顶，免清屏闪动
                sys.stdout.flush()
                time.sleep(FPS_DELAY)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\033[?25h' + RESET)  # 恢复光标与颜色

if __name__ == '__main__':
    main()
```

要点：用 `\033[H` 光标回顶代替逐帧清屏（不闪）；`shutil.get_terminal_size()` 自适应；Ctrl+C 必须干净退出并恢复终端状态。图片采样用纯 Python 读 PPM（P6）——零依赖路线下让构建脚本先把 PNG 转成 PPM（或直接 `python3 scripts/ascii_pipeline.py x.png` 预转 frames.json 再读）；或直接内嵌预生成的帧字符串。`sample_frame()` 与 `scripts/ascii_pipeline.py` 的 `sample_frame()` 是同源副本（Rec.601 / 0.55 / `floor(lum×(n−1))`），任一处改公式必须同步另一处——`scripts/selfcheck.sh` 会比对两处的索引公式写法。

## C 终端版模板（C99 + POSIX，gcc 直编）

```c
/* <slug> — 终端 ASCII 版。
 * 编译：gcc -O2 -std=c99 <slug>.c -o <slug>
 * 平台：Linux / macOS / WSL（原生 Windows 需启用 VT 序列，见下）
 * 注意：-std=c99 会定义 __STRICT_ANSI__，glibc 随即隐藏 POSIX 声明，
 *      故必须在此处（所有 #include 之前）声明特性测试宏。 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <signal.h>
#include <time.h>

static const char RAMP[] = " .:-=+*#%@";   /* 与 SKILL.md §1.2 视觉契约一致 */
static const struct timespec FRAME_TS = { 0, 83333333L };  /* 1/12s，替代已废弃的 usleep */

static void cleanup(int sig) {
    (void)sig;
    fputs("\033[?25h\033[m", stdout);      /* 恢复光标与颜色 */
    fflush(stdout);
    exit(0);
}

static volatile sig_atomic_t g_resized = 0;
static void on_winch(int sig) { (void)sig; g_resized = 1; }

int main(void) {
    struct winsize ws;
    ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws); /* ws.ws_col / ws.ws_row 自适应 */
    signal(SIGINT, cleanup);
    signal(SIGWINCH, on_winch);            /* 注册窗口变化 */
    fputs("\033[?25l\033[2J", stdout);     /* 隐藏光标 + 清屏 */
    for (;;) {
        if (g_resized) {                   /* 尺寸变化后重新读取 */
            g_resized = 0;
            ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws);
        }
        /* 生成当前帧到 buf（采样或预生成），然后： */
        fputs("\033[H\033[38;2;0;255;65m", stdout);  /* 回顶 + 强调色 */
        /* fwrite(buf, 1, len, stdout); */
        fflush(stdout);
        nanosleep(&FRAME_TS, NULL);        /* 替代 usleep；被信号中断后可接受（退出路径已覆盖） */
    }
}
```

要点：帧缓冲用 `fwrite` 一次写出，不要逐字符 `putchar`；`signal(SIGINT, cleanup)` 保证退出恢复终端；原生 Windows 的 cmd/PowerShell 需先 `SetConsoleMode(ENABLE_VIRTUAL_TERMINAL_PROCESSING)`，可在模板里加 `#ifdef _WIN32` 分支。废弃 `usleep`/`useconds_t`（POSIX.1-2008 已移除，`-std=c99` 下不可见）；帧延时统一用 `nanosleep` + `struct timespec`。

## 三端分工建议

- **HTML 版**是主交付物：完整功能（交互、彩色、WebGL）。
- **Python / C 版**做"精华切片"：同一视觉的终端演绎——静态作品直接输出最终帧；动画作品带完整循环；交互可简化为终端键盘响应（如空格暂停）。
- 不要让三端功能强行对齐；对齐的是**视觉语言**（ramp、配色、节奏）。
