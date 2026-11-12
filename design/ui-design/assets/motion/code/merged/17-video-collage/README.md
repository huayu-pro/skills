# 17-video-collage — Video Collage

> F13 视频拼贴 / 多图层 · `verified: true`

## 机制

六块版面零件（7/5、4/4/4、12 的 12 列网格），每块有 `data-depth`。
指针在网格内移动时，`--dx/--dy` 以 `lerp .12` 跟随；每块按
`depth × ±10px` 位移。离屏卡片由 IntersectionObserver 加 `is-offscreen`，
暂停其 CSS 漂移；Pause all 暂停整个组件。

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| depths | .6 / .7 / .85 / 1 / 1.1 / 1.25 | Authored |
| parallax | ±10px × depth | Authored |
| follow | `lerp .12` | Observed（cursor 组） |
| IO rootMargin | 120px | Observed（接近主流 200px） |

## 真实视频替换

```html
<div class="mr-collage__media art-a">
  <video muted playsinline preload="metadata" poster="poster.jpg">
    <source src="clip.mp4" type="video/mp4">
  </video>
</div>
```

`mount()` 会自动收集 `root.querySelectorAll("video")`，在 Pause all /
reduced-motion 时暂停。视频必须 `muted playsinline`，不要在加载时自动播放声音。

## 降级

- `prefers-reduced-motion`：取消视差与 CSS 漂移，视频暂停、保留 poster。
- 无 IntersectionObserver：所有卡片保持播放（不暂停离屏），功能不坏。
- 375px：所有卡片 `grid-column: span 12`，单列堆叠。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

期望：`__rfStats.videoCollage.cards === 6`；pointermove 后 frames 增长；
Pause all 后 playing=false；reduced 模式不增长；375 无溢出。

## 限制

- 演示用 CSS 渐变占位，不包含真实视频资产。
- 视差是 2D translate，不模拟 3D 透视；需要透视时给 grid 加 `perspective`。