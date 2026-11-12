# 24 · 动效验收

> 动效不能靠「看起来在动」验收。三层证据：**静态扫描**（可脚本化）、
> **运行时探针**（真实浏览器读数）、**人工视觉复核**（截图/录屏）。
> 任何一层缺失都要在交付里写明 `verified: false` 或 `skipped: <原因>`。

## 1. 三层验收

| 层 | 工具 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| 静态扫描 | `scripts/check_motion.py` | 布局属性动画、缺 reduced-motion、`transition: all`、autoplay 等模式 | 动效是否真的发生、手感、性能 |
| 运行时探针 | `scripts/verify_motion.mjs` | rAF 帧数、`document.getAnimations()` 条数/时长、reduced-motion 终态、375 溢出、console 错误 | 设计好坏、真机 GPU 性能 |
| 人工复核 | 1280/375 截图 + 录屏 | 构图、节奏、终态、边缘 | 帧级性能 |

**结论写法**：

- `verified: true` 只在运行时探针通过后写。
- 只跑静态 → `verified: false, evidence: "static-only"`。
- 无 Playwright/浏览器 → `skipped: "no browser"`，不算通过。
- `inferred` 的读数不能升级成 `observed`。

## 2. 静态扫描（check_motion.py）

### 检查项

| ID | 严重度 | 检查 | 为什么 |
|---|---|---|---|
| M-001 | P1 | `@keyframes`/`transition` 动 `width/height/top/left/right/margin/padding`；WAAPI `.animate([{width…}])` | 每帧布局，移动端掉帧 |
| — | 人工 | JS `style.width/height/top/left` 的写：区分「创建时静态定位」与「每帧动画」 | 静态定位合法；rAF/pointermove 里每帧写布局要改 transform |
| M-002 | P1 | 有 animation/transition 但没有 `prefers-reduced-motion` 块 | 前庭/晕动用户无法关闭 |
| M-003 | P1 | `autoplay` 的 `<video>`/`<audio>`（无 muted） | 扰民/被浏览器拦截 |
| M-004 | P1 | 同一页 ≥3 个 section 使用 `fade-in-up`/`reveal`/`animate-in` 入场 | 每个区块都表演＝没有注意焦点 |
| M-005 | P2 | `transition: all` | 意外属性参与过渡，卡顿/不可控 |
| M-006 | P2 | 全局 `html{scroll-behavior:smooth}` | 劫持滚动，长页晕动 |
| M-007 | P2 | `animation-iteration-count: infinite` 且无 hover 暂停/visibility 处理 | 无法阅读，持续耗电 |
| M-008 | P2 | keyframes 动 `box-shadow`/`filter: blur` | 每帧绘制，长循环很贵 |
| M-009 | P2 | 自定义光标（`cursor: none`）无 `pointer: fine` 回退 | 触屏用户失去光标 |
| M-010 | P2 | `will-change` 常驻且无清理 | 吃显存 |
| M-011 | P2 | `scroll-jacking` 迹象（wheel preventDefault + 无键盘出口） | 可访问性/导航失效 |
| M-012 | P2 | 同一元素同时有 `transition` 与 `animation` 争抢同一属性 | 状态互相覆盖 |

> 静态扫描是**提示**，不是审美判决。它只报可构造反例的模式；不判断「这个动效该不该存在」。

### 必红用例

`evals/motion/` 里每组好/坏夹具必须：

- 好夹具：0 个 P1；坏夹具：至少命中预期 ID。
- 新增一条检查，必须构造一个**只命中它**的夹具；永不失败的门禁等于没有门禁。
- `check_motion.py --self-test` 对检查函数跑合成输入；`--expect` 对夹具跑端到端。

## 3. 运行时探针（verify_motion.mjs）

### 测什么（当前实现）

1. **加载**：正常页与 reduced 页的 console error / pageerror = 0。
2. **可见性**：`body` 的 `visibility` 不是 `hidden`，`opacity` 不是 `0`。
3. **交互探针**：1280 下 wheel + 水平拖拽 + 深滚动 + 首按钮点击 + Tab/ArrowRight；
   比较 before/after 的 `frames`、`animations`、`stats`。必须至少有一项变化：
   `frameDelta > 0 || animationDelta > 0 || statsChanged`。加载时运行的动画也算。
4. **reduced-motion**：`emulateMedia({ reducedMotion: "reduce" })` 后两次采样：
   - 不得有 running 的动画（不限 infinite，有限时长的过渡也算）；
   - stats frames 不得继续增长；
   - 关键元素终态需人工/截图确认（脚本不猜）。
5. **响应式**：默认 1280/768/375 三档，每档 `scrollWidth <= innerWidth + 1`。
6. **键盘**：Tab 至少让焦点离开 body；Esc/Space/Enter 的语义需人工验证。
7. **元数据**：`meta.json` 的 duration/easing 对账目前**不自动做**，由人工抽检；
   组件 README 需写清实测值。

### 未自动化的检查（人工必做）

- `meta.json` duration/easing 与实际 animation 的逐项对账。
- Esc 关闭 modal/menu、Space/Enter 触发、焦点陷阱。
- 8 方向手势、释放惯性、边界吸附的逐项状态变化。
- `gl.getError()`、context lost/restore、暂停按钮的语义。
- 终态 `opacity/transform` 的具体值（reduced 截图对照）。

### 报告 schema（实际输出）

```json
{
  "component": "10-scroll-narrative",
  "viewports": {
    "1280": {"animations": [], "stats": {}, "scrollWidth": 1280, "innerWidth": 1280},
    "768": {},
    "375": {}
  },
  "interaction": {
    "frameDelta": 0,
    "animationDelta": 0,
    "statsChanged": true,
    "hasMotion": true
  },
  "reduced": {"infinite": 0, "stats": {}, "animations": []},
  "overflow": {},
  "keyboard_tab": true,
  "console_errors": [],
  "verified": true,
  "notes": []
}
```

### 限制

- headless rAF 的 83ms/1016ms 是软件渲染读数，不是真机性能；只用于「有没有循环」。
- 跨域 iframe/canvas 读不到内部动画；标 `skipped: cross-origin`。
- WebGL 在无 GPU 环境可能走 SwiftShader；只验证「能画/无错误」，不验证帧率。
- `document.getAnimations()` 不包含 `requestAnimationFrame` 手写的变换；rAF 组件要看自定义 stats 或采样 `transform`。

## 4. 验收流程

```bash
# 1. 静态
python3 -I scripts/check_motion.py --self-test
python3 -I scripts/check_motion.py evals/motion --expect
python3 -I scripts/check_motion.py path/to/page.html --json

# 2. 运行时（需要 Playwright + Chromium/Edge）
node scripts/verify_motion.mjs --component assets/motion/code/components/10-scroll-narrative
node scripts/verify_motion.mjs --dir evals/motion --viewports 1280,375

# 3. 人工
# 1280/375 全页 + 视口截图；注意瞬间至少起点/终点两帧或 3s 录屏；
# reduced-motion 再截一次
```

**一个页面通过的条件**：

- 静态：0 个 P1（P2 可解释/可留）。
- 运行时：`verified: true`，reduced-motion 终态正确，375 无溢出，console 0 error。
- 人工：注意瞬间 ≤1，动效与物理关系一致，终态干净；有起点/终点两帧或 3s 录屏。
  只有静态首屏 → `skipped: no motion evidence`，不算通过。
- 交付说明里写：证据等级、跳过的项、未验证的项。

## 5. 假绿清单

| 假绿 | 为什么不可信 | 正确做法 |
|---|---|---|
| 截图通过 | 只证明一帧 | 加运行时读数 |
| 302 复刻有交互 | 共享 runtime 0 rAF/0 shader | 只把 12 组件当动效证据 |
| `advanced: true` | 可能是合成字段 | 读 `verified` + 探针报告 |
| 动画条数多 | 可能是同一条重复 | 看 `unique_anim_names` |
| headless 帧率好 | 软件渲染/无 vsync | 只证明循环存在，不证明流畅 |
| `check_motion --self-test` 全绿 | 只测函数，不测入口 | 再跑 `--expect` 夹具与 CLI |
| 结构 verifier 全绿 | 只查文件存在/数量 | 需求逐条断言 |
| 「已尊重 reduced-motion」 | 只写了 media query，元素仍 opacity:0 | 检查终态值 |

## 6. 与审计的关系

`audit.py` 管静态 UI 缺陷（对比度、层级、硬编码色、空状态等）；
`check_motion.py` 管动效模式；`verify_motion.mjs` 管运行时。
三者输出同一套 finding schema（P0/P1/P2 + 规则 ID + 位置 + 建议），
在 `12-audit-rubric.md` 里合并成一份报告。**不要用一个的全绿代替另一个。**