# 09-cursor-field — Cursor Field

> dot + ring 光标、磁吸按钮、多层视差、30° 倾斜卡片。
> 家族：F7 光标 / 磁吸 / 角色 · verified: `true`

## 机制

dot + ring 光标、磁吸按钮、多层视差、30° 倾斜卡片。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-faq-grid-bc30c4bd` | faq-grid | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-faq-grid-d6d63751` | faq-grid | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-modal-dialog-9fe01012` | modal-dialog | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-pricing-cards-1ea0566b` | pricing-cards | page-section | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| CursorLayer | `reverse-302/_kits/06-cursor.js` | authored |
| ParallaxField | `reverse-pilots/batch-156-205/deepest/cases/168-magnet-lover/site/script.js` | observed |
| TiltCard | `reverse-pilots/batch-156-205/deepest/cases/186-janna-deloume/site/script.js` | observed |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| dot / ring | 6px / 34px；hover 58px | Authored（kit 06） |
| ring lerp | .16 | Observed |
| magnet | dx × .18，clamp ±14px | Observed |
| depth | 1.1–1.8 × 10px | Observed（168） |
| tilt | 30° / perspective 900px | Observed（186） |
| deadzone | .035 | Observed（186） |

## 交互

- 键盘：Tab, Enter。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 取消视差/倾斜，保留 hover 颜色；pointer: coarse 隐藏光标层
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- 磁吸是视觉位移，不是可拖拽磁铁
- 自定义光标不替代 focus ring
