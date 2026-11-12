# 05-shader-plane — Shader Plane

> 覆盖三角形 + 单 fragment shader：时间/分辨率/指针/进度四个 uniform。
> 家族：F3 WebGL 全屏 shader / lens · verified: `true`

## 机制

覆盖三角形 + 单 fragment shader：时间/分辨率/指针/进度四个 uniform。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-faq-grid-c5f520fd` | faq-grid | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-section-split-94d7508d` | section-split | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-timeline-steps-fe980e8c` | timeline-steps | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-stats-74b69dcb57` | stats | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-footer-mega-1fbe5026` | footer-mega | block | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| ShaderPlane | `reverse-302/_kits/03-webgl-shader.js` | authored |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| geometry | 覆盖三角形 3 顶点 | Authored |
| uniforms | u_res / u_time / u_mouse / u_progress | Authored |
| DPR | min(devicePixelRatio, 2) | Observed（kit 03）+ 修正 |
| rings | sin(r×13 - t×3.2 + n×3) | Authored |
| glow | 0.18 × exp(-dist×3.2) | Authored |
| pause | visibilitychange + button | Authored |

## 交互

- 键盘：Tab, Enter, Space。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：WebGL2 不可用/编译失败: CSS 渐变；reduced-motion: 只画一帧
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- shader 是自写近似，不是原站 shader
- kit 03 的 DPR 鼠标坐标 bug 已修
