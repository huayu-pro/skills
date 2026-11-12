# 11-audio-visualizer — Audio Visualizer

> 五个 oscillator 的 pad + analyser 64 bars；手势解锁、状态机、mute。
> 家族：F8 音频 / 波形 / 可视化 · verified: `true`

## 机制

五个 oscillator 的 pad + analyser 64 bars；手势解锁、状态机、mute。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-menu-mega-f90fa91b` | menu-mega | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-form-contact-818faee1` | form-contact | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-toggle-04df5cc0` | toggle | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-footer-mega-05ef457b` | footer-mega | page-section | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| AudioState | `reverse-302/_kits/09-audio.js` | authored |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| frequencies | 110 / 164.81 / 220 / 277.18 / 329.63 Hz | Authored（kit 09） |
| master | 0.035 | Authored |
| fft | 256 / 64 bars | Authored |
| unlock | 用户手势后 new AudioContext | Authored |
| mute | GainNode setTargetAtTime | Authored |
| visibility | hidden 时 suspend | Authored |

## 交互

- 键盘：Tab, Enter, Space。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：无 WebAudio/失败: 静态频谱 + error；reduced-motion: 静态频谱
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- pad 是合成音，不是原站音频
- 没有做 LUFS 测量；master 0.035 是保守值
