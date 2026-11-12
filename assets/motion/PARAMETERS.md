# Motion parameters — 实测值速查

> 每个值都带 provenance。`Observed` = 运行时/源码采样；`Inferred` = 从代码推断；
> `Authored` = 本包自写。不要把 `Inferred` 写成 `Observed`。

| 类别 | 项 | 值 | 证据 | 出处 |
|---|---|---|---|---|
| duration | 微交互 | `120–300ms` | Observed（65 站 + pilots） | 09 §7 |
| duration | 段落转场 | `400–900ms` | Observed（65 站 + pilots） | 09 §7 |
| duration | 长循环 | `1.4–24s` | Observed（pilots） | 09 §7 |
| duration | 超长 marquee | `42–148s` | Observed（65 站） | 09 §7 |
| duration | 手调进入值 | `450ms` | Observed（343 站 76 次） | 09 §7 |
| duration | Angelo 统一入场 | `700ms × 21` | Observed（case 155-001） | 23 F1 |
| duration | mono turn | `16s` | Observed（case 155-001） | 23 F1 |
| easing | 进入 | `cubic-bezier(0,0,.2,1)` | Observed（主流） | 09 §8 |
| easing | 退出 | `cubic-bezier(.4,0,1,1)` | Inferred | 09 §8 |
| easing | 强调/大转场 | `cubic-bezier(.22,.8,.2,1)` | Observed | 09 §8 |
| easing | GSAP 高频 | `expo / power4 / power2.out` | Observed（343 站） | 09 §8 |
| reveal | rootMargin | `200px` | Observed（87 站） | 09 §7 |
| reveal | threshold | `0` | Observed（97 站） | 09 §7 |
| reveal | 位移 | `16px` | Observed | 09 §7 |
| stagger | CSS 同组 | `20–50ms` | Observed/Authored | 09 §6 |
| stagger | GSAP | `0.05–0.1s` | Observed（27 站） | 09 §6 |
| stagger | 总时长 | `≤300ms` | Authored | 09 §6 |
| horizontal | follow | `lerp .15` | Observed（Tegra） | 22 F2 |
| horizontal | decay | `.95 / .92` | Observed（Tegra） | 22 F2 |
| horizontal | velocity | `touch 12 / mouse 8` | Observed（Tegra） | 22 F2 |
| horizontal | boundary | `*.15` | Observed（Tegra） | 22 F2 |
| belt | BASE | `62px/s` | Observed（pilots case 04） | 22 F11 |
| belt | MAX | `900` | Observed（pilots case 04） | 22 F11 |
| belt | friction | `1.1` | Observed（pilots case 04） | 22 F11 |
| belt | SPACING | `300` | Observed（pilots case 04） | 22 F11 |
| depth | scale | `0.72–1.06` | Observed（pilots case 01） | 09 §4 |
| depth | blur | `(1-depth)*1.1` | Observed（pilots case 01） | 09 §4 |
| depth | z-index | `60 ± depth*40` | Observed（pilots case 01） | 09 §4 |
| depth | opacity | `0.62–1.0` | Observed（pilots case 01） | 09 §4 |
| pin | budget | `320vh` | Authored | 22 F1 |
| pin | end | `innerHeight * duration * .78` | Observed（mappy） | 22 F1 |
| audio | fftSize | `256（128 bins；64 bars）` | Authored | 22 F8 |
| audio | bar mapping | `scaleY(0.06 + v * 0.94)` | Authored | 22 F8 |
| cursor | dot follow | `direct set (no lerp)` | Authored | 22 F7 |
| cursor | ring follow | `lerp .16` | Authored | 22 F7 |
| perf | rAF dt cap | `1/30s` | Authored | 22 §2.1 |
| perf | DPR cap | `2` | Authored | 22 §4 |
| perf | frame budget | `<8ms` | Authored | 22 §4 |
| a11y | flash | `≤3 次/秒` | WCAG | 09 §10 |

## 使用规则

1. 先取 3–5 个常量，不要把所有值都塞进一个页面。
2. 同一页面里，同一族的参数只允许一套；混两套会像两个人在做。
3. `Observed` 值是区间/中位，不是目标；按题材与内容长度调 ±20%。
4. 改参数后重跑 `check_motion.py` + `verify_motion.mjs`，不要只改数字。
