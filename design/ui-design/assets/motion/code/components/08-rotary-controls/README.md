# 08-rotary-controls — Rotary Controls

> 三个 270° 旋钮 + 物理灯开关；中心 12px 退化，键盘 ±4。
> 家族：F14 状态机 / 产品演示 · verified: `true`

## 机制

三个 270° 旋钮 + 物理灯开关；中心 12px 退化，键盘 ±4。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-pricing-cards-7128ba01` | pricing-cards | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-pricing-cards-a1663abc` | pricing-cards | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-toggle-5e5664fb` | toggle | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-modal-dialog-5687378625` | modal-dialog | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-modal-dialog-5d88beb3` | modal-dialog | block | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| RotaryKnob | `reverse-pilots/batch-156-205/deepest/cases/163-app-flow/site/script.js` | observed |
| LightSwitch | `reverse-pilots/batch-156-205/deepest/cases/188-the-unholy-project/site/script.js` | observed |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| sweep | 270° (-135 → +135) | Observed（163-app-flow） |
| center fallback | 12px 内用 (dx-dy)/5 | Observed |
| wheel / keyboard | ±4 | Observed |
| switch travel | 20px / .28s | Observed（188） |
| theme transition | .5s | Observed |

## 交互

- 键盘：Tab, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Home, End, Enter, Escape。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 取消过渡；旋钮/开关仍可操作
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- 三个旋钮的 value 是演示值，不驱动真实音频
- 灯开关只切换本组件主题，不改系统主题
