# SVG 片段库

按需复制。所有片段已验证可被 cairosvg 正确渲染，色值与 [style-spec.md](style-spec.md) 一致。

## 1. 文件骨架

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800"
     font-family="Noto Sans CJK SC, sans-serif">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
            orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#5A6B7E"/>
    </marker>
    <marker id="arrowBlue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
            orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#2F6BB0"/>
    </marker>
  </defs>
  <rect width="1200" height="800" fill="#FFFFFF"/>
  <!-- 图元 -->
</svg>
```

## 2. 标准模块框 + 居中文字

```xml
<rect x="160" y="104" width="240" height="72" rx="6"
      fill="#EEF4FB" stroke="#2F6BB0" stroke-width="1.5"/>
<text x="280" y="144" font-size="13" text-anchor="middle" fill="#1A1A1A">模块名称</text>
```
基线 = `y + h/2 + 0.35×13 ≈ y + 40.5`（示例 y=104，取 144）。

## 3. 强调框（左侧色条）

```xml
<rect x="160" y="104" width="240" height="72" rx="6"
      fill="#EEF4FB" stroke="#2F6BB0" stroke-width="2"/>
<rect x="160" y="104" width="6" height="72" fill="#2F6BB0"/>
<text x="286" y="148" font-size="14" font-weight="700" text-anchor="middle" fill="#1A1A1A">核心模块</text>
```

## 4. 深底反白标题条

```xml
<rect x="168" y="40" width="680" height="32" rx="6" fill="#2F6BB0" stroke="#2F6BB0" stroke-width="1.5"/>
<text x="508" y="62" font-size="16" font-weight="700" text-anchor="middle" fill="#FFFFFF">第一阶段　识别与划定</text>
```

## 5. 背景分组带

```xml
<rect x="120" y="48" width="960" height="160" rx="10"
      fill="#2F6BB0" fill-opacity="0.06"/>
<text x="144" y="80" font-size="13" font-weight="700" fill="#2F6BB0">应用层</text>
```
组名放带内左上角（`x+24`、基线 `y+32`）；成员框顶边 = `y+56`，左右内缩 ≥24。

## 6. 虚线边界框 / 阶段容器

```xml
<rect x="152" y="40" width="712" height="208" rx="10"
      fill="#F3F5F8" fill-opacity="0.6"
      stroke="#8A94A6" stroke-width="1.5" stroke-dasharray="6 3"/>
```

## 7. 胶囊流程条

```xml
<rect x="64" y="312" width="1072" height="152" rx="76"
      fill="#2F6BB0" fill-opacity="0.06" stroke="#2F6BB0" stroke-width="1.5"/>
<text x="600" y="344" font-size="15" font-weight="700" text-anchor="middle" fill="#2F6BB0">协同过程</text>
```

## 8. 竖排文字

逐字 tspan（标签宽 1 字，间距 = 字号 + 2）：

```xml
<text x="88" y="96" font-size="13" text-anchor="middle" fill="#1A1A1A"><tspan x="88" y="96">三</tspan><tspan x="88" y="111">网</tspan><tspan x="88" y="126">融</tspan><tspan x="88" y="141">合</tspan></text>
```

整段旋转（更省事，但 lint 不做包围盒检查）：

```xml
<text x="44" y="408" transform="rotate(-90 44 408)" font-size="16" font-weight="700"
      text-anchor="middle" fill="#1A1A1A">转型升级阶段</text>
```

## 9. 多行文字（tspan 换行）

```xml
<text x="280" y="136" font-size="13" text-anchor="middle" fill="#1A1A1A">第一行文字
  <tspan x="280" y="160">第二行文字</tspan>
</text>
```
行距 24px（13px 字的 1.85×）。切分点取词边界，单行估算宽 ≤ 框宽 × 0.9。

## 10. 中英双语模块

```xml
<text x="280" y="136" font-size="14" font-weight="700" text-anchor="middle" fill="#1A1A1A">数字技术</text>
<text x="280" y="160" font-size="11" text-anchor="middle" fill="#666666">(Digital Technology)</text>
```

## 11. 正交折线箭头

```xml
<path d="M 208 140 H 252 V 200 H 288" fill="none" stroke="#5A6B7E"
      stroke-width="1.5" marker-end="url(#arrow)"/>
```
只用 `M/H/V`，拐点落在中线；不要用 `C` 画随手曲线。

## 12. 虚线反馈箭头

```xml
<path d="M 920 520 V 560 H 280 V 486" fill="none" stroke="#5A6B7E"
      stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#arrow)"/>
```

## 13. 双向关联

```xml
<line x1="320" y1="148" x2="440" y2="148" stroke="#5A6B7E" stroke-width="1.5"
      marker-start="url(#arrow)" marker-end="url(#arrow)"/>
```

## 14. 带标签的连线

```xml
<line x1="320" y1="148" x2="440" y2="148" stroke="#2F6BB0" stroke-width="1.5" marker-end="url(#arrowBlue)"/>
<text x="380" y="144" font-size="11" text-anchor="middle" fill="#666666">H1</text>
```
标签基线比线高 4px；压到其他元素时加 `<rect fill="#FFFFFF"/>` 白底再写字。

## 15. 块箭头（支撑/上升流）

```xml
<path d="M 600 260 L 622 288 L 610 288 L 610 312 L 590 312 L 590 288 L 578 288 Z"
      fill="#FFFFFF" stroke="#2F6BB0" stroke-width="1.5"/>
```
头部 44 宽、杆 20 宽、总高 52；只在"支撑、上升、汇聚"语义用，别拿它当普通箭头。

## 16. 梯形底座 / 金字塔层

```xml
<path d="M 136 512 H 1064 L 1160 640 H 40 Z" fill="#F3F5F8" stroke="#8A94A6" stroke-width="1.5"/>
```

## 17. 编号标签（垂直侧签）

```xml
<rect x="40" y="40" width="96" height="176" rx="6" fill="#2F6BB0" stroke="#2F6BB0" stroke-width="1.5"/>
<text x="88" y="96" font-size="13" font-weight="700" text-anchor="middle" fill="#FFFFFF">阶段一<tspan x="88" y="120">问题识别</tspan></text>
```
侧签与右侧容器同高；文字两行居中。

## 18. 直角树形连接线

```xml
<!-- 父节点底边中点 -> 横线 -> 子节点顶边中点 -->
<path d="M 600 120 V 160 H 220 V 200" fill="none" stroke="#5A6B7E" stroke-width="1.5"/>
<path d="M 600 160 H 980 V 200" fill="none" stroke="#5A6B7E" stroke-width="1.5"/>
```
横线取父节点下方 40px；子节点顶边各接一段竖线。

## 19. 中心圆 + 辐射

```xml
<circle cx="550" cy="400" r="80" fill="#2F6BB0" fill-opacity="0.08" stroke="#2F6BB0" stroke-width="2"/>
<text x="550" y="394" font-size="15" font-weight="700" text-anchor="middle" fill="#2F6BB0">核心主题</text>
<text x="550" y="418" font-size="11" text-anchor="middle" fill="#666666">Core Theme</text>
<line x1="550" y1="320" x2="550" y2="256" stroke="#5A6B7E" stroke-width="1.5" marker-end="url(#arrow)"/>
```
连线从圆周出发（`cy-r`），不要从圆心画进圆里。

## 20. 图例

```xml
<rect x="880" y="672" width="280" height="88" rx="6" fill="#FFFFFF" stroke="#DDDDDD" stroke-width="1"/>
<rect x="896" y="692" width="16" height="16" rx="3" fill="#2F6BB0" fill-opacity="0.08" stroke="#2F6BB0"/>
<text x="920" y="705" font-size="11" fill="#1A1A1A">核心模块</text>
<rect x="896" y="724" width="16" height="16" rx="3" fill="#EDF7F2" stroke="#3E9B6C"/>
<text x="920" y="737" font-size="11" fill="#1A1A1A">结果输出</text>
```
图例只解释颜色语义，不解释结构；一图最多 4 条。

## 21. 常见手滑

| 写法 | 问题 | 改 |
|---|---|---|
| `<path d="M336,96 V96" marker-end="..."/>` | 零长度，箭头不画 | 给终点留 ≥2px 位移，或删掉这条线 |
| `<text>` 只有 `tspan` 没有 `x/y` | 各渲染器行为不一致，位置漂移 | 每个 `tspan` 都写 `x` 与 `y` |
| 用 `fill-opacity` 的带子又设 `opacity` | 成员一起变透明 | 只在外层带用 `fill-opacity` |
| 复制模板后只改 `width` 不改 `x` | 右边缘越界 | 改宽度时同步重算 `x` 与相邻间距 |
| 替换多行文字后删了内容没删 tspan | 新文本行数少于旧 tspan 数，末尾残留半句 | 替换时同步删掉多余 `<tspan>` |
| 中文里混用全角/半角括号 | 视觉不齐 | 全图统一，中文用全角（） |
