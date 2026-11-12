/* ascii.c —— ascii-web-design 三端骨架之 C 终端版。
 *
 * 视觉契约（SKILL.md §1.2）：RAMP 10 级 / Rec.601 亮度 / 纵横比 0.55 / COLS 120 / fps 12 / 强调色 #00FF41。
 * 与同目录 ascii.html、ascii.py 同源：同一 ramp、同一列数与行数逻辑、同一强调色、同一帧间隔 1/12s。
 * 三端一致性由 scripts/verify_deliverable.py 断言（逐字节比对 renderFrame 输出）。
 *
 * 编译：gcc -O2 -std=c99 ascii.c -o ascii
 * 平台：Linux / macOS / WSL。原生 Windows 的 cmd/PowerShell 需先启用 VT 序列
 *       （SetConsoleMode(ENABLE_VIRTUAL_TERMINAL_PROCESSING)，本文件末尾有 #ifdef _WIN32 提示）。
 * 注意：-std=c99 会定义 __STRICT_ANSI__，glibc 随即隐藏 POSIX 声明，
 *       故必须在此处（所有 #include 之前）声明特性测试宏。
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <signal.h>
#include <sys/ioctl.h>
#include <unistd.h>
#endif

/* ==== ASCII KERNEL BEGIN ====  （与 ascii.html / ascii.py 同源，改动必须三端同步） */
#define RAMP " .:-=+*#%@"
#define COLS 120
#define FPS 12
#define ACCENT_R 0
#define ACCENT_G 255
#define ACCENT_B 65
#define ASPECT_NUM 55              /* 0.55 = 55/100，契约区间 50–66 */
#define ASPECT_DEN 100

/* 16:9 演示幅面的行数：round(cols × 9/16 × 0.55)，整数式保证三端逐位一致。 */
static int rows_for(int cols) { return (cols * 495 + 800) / 1600; }

/* 三角波：整数相位折回 0..1000。 */
static int tri(int u) {
    int m = ((u % 2000) + 2000) % 2000;
    return m <= 1000 ? m : 2000 - m;
}

/* 演示亮度场（毫单位 0..1000）：两路正交三角波取差 → 斜向移动的呼吸波纹。 */
static int lum1000(int x, int y, int t) {
    int a = tri(x * 200 + t * 160);
    int b = tri(y * 350 - t * 110);
    return a > b ? a - b : b - a;
}

/* 亮度 → 字符：契约公式 floor(lum × (n−1)) 的整数等价式（v 为 0..1000 毫单位）。 */
static char char_at_1000(int v) {
    int idx = v * ((int)strlen(RAMP) - 1) / 1000;
    if (idx < 0) idx = 0;
    if (idx > (int)strlen(RAMP) - 1) idx = (int)strlen(RAMP) - 1;
    return RAMP[idx];
}

/* 第 t 帧 → 整幅网格，写入调用方提供的缓冲区（需 ≥ rows × (cols+1) + 1 字节）。
 * 返回写入的字节数（不含结尾 NUL）。 */
static size_t render_frame(int t, int cols, char *buf, size_t cap) {
    int rows = rows_for(cols), y, x;
    size_t n = 0;
    for (y = 0; y < rows; y++) {
        for (x = 0; x < cols; x++) {
            if (n + 2 >= cap) { buf[n] = '\0'; return n; }
            buf[n++] = char_at_1000(lum1000(x, y, t));
        }
        if (n + 1 >= cap) { buf[n] = '\0'; return n; }
        buf[n++] = (y == rows - 1) ? '\0' : '\n';
    }
    buf[n] = '\0';
    return n;
}
/* ==== ASCII KERNEL END ==== */

#define FRAME_TS_NS 83333333L      /* 1/12s，与 HTML 的 STEP、Python 的 FRAME_DELAY 一致 */

static volatile sig_atomic_t g_resized = 0;
static volatile sig_atomic_t g_quit = 0;

#ifndef _WIN32
static void on_winch(int sig) { (void)sig; g_resized = 1; }
static void on_int(int sig) { (void)sig; g_quit = 1; }
#endif

static int terminal_cols(int fallback) {
#ifdef _WIN32
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &info))
        return info.dwSize.X > 16 ? info.dwSize.X : fallback;
    return fallback;
#else
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == 0 && ws.ws_col >= 16) return ws.ws_col;
    return fallback;
#endif
}

int main(int argc, char **argv) {
    int frames = 0, cols = COLS, color = 1, i;
    char *buf;
    size_t cap;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--frames") == 0 && i + 1 < argc) frames = atoi(argv[++i]);
        else if (strcmp(argv[i], "--cols") == 0 && i + 1 < argc) cols = atoi(argv[++i]);
        else if (strcmp(argv[i], "--no-color") == 0) color = 0;
        else if (strcmp(argv[i], "--dump") == 0 && i + 1 < argc) {
            int t = atoi(argv[++i]);
            cap = (size_t)(rows_for(cols) + 1) * (size_t)(cols + 1) + 8;
            buf = malloc(cap);
            if (!buf) return 1;
            render_frame(t, cols, buf, cap);
            fputs(buf, stdout);
            fputc('\n', stdout);
            free(buf);
            return 0;
        }
    }
    if (cols < 16 || cols > 400) {
        fputs("[用法错误] --cols 取值 16-400（契约甜点 80-160）\n", stderr);
        return 2;
    }

#ifndef _WIN32
    signal(SIGINT, on_int);
    signal(SIGWINCH, on_winch);
#else
    {
        HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
        DWORD mode;
        if (GetConsoleMode(h, &mode))
            SetConsoleMode(h, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
    }
#endif

    cap = (size_t)(rows_for(cols) + 1) * (size_t)(cols + 1) + 8;
    buf = malloc(cap);
    if (!buf) { fputs("[失败] 内存不足\n", stderr); return 1; }

    fputs("\033[?25l\033[2J", stdout);              /* 隐藏光标 + 清屏 */
    {
        long played = 0;
        int t = 0;
        while (!g_quit) {
            int use_cols = cols;
            if (g_resized) { g_resized = 0; fputs("\033[2J", stdout); }
            {
                int tc = terminal_cols(cols);
                if (tc < cols) use_cols = tc;
            }
            if (use_cols != cols) {
                size_t need = (size_t)(rows_for(use_cols) + 1) * (size_t)(use_cols + 1) + 8;
                if (need > cap) {
                    char *grown = realloc(buf, need);
                    if (!grown) break;
                    buf = grown; cap = need;
                }
            }
            render_frame(t, use_cols, buf, cap);
            fputs("\033[H", stdout);                 /* 光标回顶，免逐帧清屏闪动 */
            if (color) printf("\033[38;2;%d;%d;%dm", ACCENT_R, ACCENT_G, ACCENT_B);
            fwrite(buf, 1, strlen(buf), stdout);     /* 整帧一次写出，不逐字符 putchar */
            fputs("\033[m", stdout);
            fflush(stdout);
            t++;
            played++;
            if (frames && played >= frames) break;
            {
                struct timespec ts = { 0, FRAME_TS_NS };   /* nanosleep：usleep 已废弃 */
                nanosleep(&ts, NULL);
            }
        }
    }
    free(buf);
    fputs("\033[?25h\033[m", stdout);                /* 恢复光标与颜色 */
    fflush(stdout);
    return 0;
}
