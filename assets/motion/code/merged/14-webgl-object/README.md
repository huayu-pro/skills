# 14-webgl-object — WebGL Object

> F4 WebGL 3D 物体 / 相机 · `verified: true`

## 机制

一个覆盖三角形 + 一个 fragment shader。`map()` 是旋转后的 box SDF；
80 步 raymarch 求交，有限差分求法线；主光 + rim + specular 三项着色。
指针偏移相机位置，时间旋转物体；暂停只停 rAF，不销毁 GL 资源。

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| raymarch steps | 80 | Authored |
| box half-size | 0.82 | Authored |
| object rotation | `time * 0.35` | Authored |
| mouse follow | `lerp .12` | Observed（cursor 组） |
| DPR cap | 2 | Authored |

## 交互

- 指针移动：相机水平 ±0.55、垂直 ±0.35。
- Pause/Play：停/启 rAF；按钮 `aria-pressed` 同步。
- 页面隐藏：停 rAF；恢复时继续。
- `prefers-reduced-motion`：只画一帧（time=0.6）。

## 降级

- 无 WebGL2：隐藏 canvas，显示 CSS 3D cube + 说明。
- shader 编译/链接失败：同上，readout 写 `shader failed`。
- context lost：`preventDefault()`，显示降级；**不自动重建**（见限制）。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

期望：`__rfStats.webgl.ok === true`；frames 增长；reduced 模式 frames 停在 1；
375 无溢出；console 0 error。

## 限制

- 单物体 raymarch，不是完整 3D 场景；复杂模型/材质用 `prompts/F4-tristan-rain-scene.prompt.md` 的 Three.js 路线。
- context restore 不重建 program；生产环境应 reload 或实现完整资源重建。
- 无 GPU 环境可能走 SwiftShader；只保证能画，不保证帧率。