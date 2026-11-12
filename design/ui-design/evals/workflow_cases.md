# 行为用例

> `evals/cases/` 的 8 个视觉金标准测的是 **Workflow D（审计）**，而且是从上游项目原样继承的。
> 本文件补上它测不到的部分：**A（Tokens）、B（Build）、E（Reference）、F（Stack）**，
> 以及 Workflow B 的强制机制本身。

## 为什么需要这个文件

一个技能最容易出现的假绿是「审计很准，但没人验证过它能不能建东西」。上游的 8 个用例只覆盖诊断，
所以如果 Workflow B 的原型检索、约束简报、强制步骤全都不工作，那 8 个用例仍然会全绿。

本文件的每个用例都写清：**输入**、**必须出现的可检查产物**、**什么算失败**。

---

## A · Tokens

### A-1 生成色阶

**输入**：`python3 scripts/generate_palette.py --base "#0f766e" --name brand --json`

**必须**：
- 输出 9–11 个档位（100–900 或 50–950）
- 同色阶内明度单调
- 色相相对基准的偏移 ≤ 30°
- 明度远离 50% 时饱和度上升

**失败**：任何一档饱和度低于相邻档而明度更极端（说明没做补偿）；色相漂移 > 30°。

### A-2 对比度门槛

**输入**：`python3 scripts/check_contrast.py --pair "#9ca3af" "#ffffff"`

**必须**：报 FAIL，数值 2.54:1（±0.05），并说明需要 4.5:1。

**失败**：报 PASS；或只输出数字不判断。

### A-3 半透明复合

**输入**：一个 `opacity: 0.45` 的 `#111827` 元素在白底上。

**必须**：`audit.py` 算出复合后的有效色，报告对比度 < 4.5:1。

**失败**：按 `#111827` 的 17.7:1 判 PASS。这是 RED 基线里最容易漏的一类。

---

## B · Build（含强制机制）

### B-1 原型检索必须先跑

**输入**：要求"做一个 SaaS 定价页"。

**必须**：
- 输出里出现 `query_corpus.py` 的调用（或 `--list`）
- 出现一个真实的原型 ID（`arch-` 开头的 6 位哈希，可在 `archetypes.json` 里查到）
- 或明确声明「无匹配原型，走自由方向」并给出理由

**失败**：直接开始写 HTML，没有任何检索记录。

### B-2 约束简报在首行

**输入**：同上。

**必须**：产出文件第一行是 `DESIGN BRIEF` 注释块，含：
- `Archetype:` + 真实 ID（或"无匹配"）
- 内容分级（primary / secondary / tertiary）
- 主行动（唯一实心按钮的名称）
- token 来源（现有项目 token 或生成值）
- 禁用项

**失败**：简报缺失；或 ID 在 `archetypes.json` 里不存在；或写了 ID 但 token 与该原型契约矛盾且无说明。

**已验证**：`build/green/01-pricing.html` 第 1–9 行实际产出过这个块。

### B-3 偏离要说明

**输入**：同上。

**必须**：若成品 token 偏离所选原型的区间（如字阶比从 1.16 提到 1.25），简报里有一行 `Deviation:` 说明原因。

**失败**：偏离但不说明。这是「强制引用」退化成「引用过就算」的分界线。

### B-4 构建顺序留痕

**输入**：同上。

**必须**：约束简报里能看出先灰度后上色（token 分 pass 1 / pass 2，或说明"先灰度定层级"）。

**失败**：一次性给出最终配色，无过程痕迹。

---

## E · Reference

### E-1 检索有理由

**输入**：`python3 scripts/query_corpus.py --mood dark --style minimal`

**必须**：返回带 `score=` 和「匹配理由」的排序列表；若无匹配，输出「无匹配原型」并给出指示。

**失败**：返回空列表且不解释；或返回结果但无理由。

### E-2 品牌查询

**输入**：`--brand linear.app --section colors`

**必须**：只输出 colors 块，不是整份文件。

**失败**：输出全文；或对散文格式品牌（spotify/tesla/theverge/lamborghini/starbucks）静默失败——应说明该品牌是散文格式。

---

## G · Stack

### G-1 选型有依据

**输入**："用 shadcn 还是 Mantine 做后台？"

**必须**：引用 `18-stack-selection.md` 的决策树，且结论与决策树一致（后台/数据密集 → Mantine）。

**失败**：给出结论但不引用决策依据；或结论与决策树矛盾。

### G-2 版本警告

**输入**："在 HeroUI 项目里加个 Modal"（项目是 v2）。

**必须**：指出 v2/v3 API 不同（Provider、onPress、扁平 props），不要套 v3 规则。

**失败**：直接给 v3 代码。

---

## 如何跑这些用例

人工或子代理逐条走查。每条记录：

```json
{
  "case": "B-2",
  "passed": true,
  "evidence": "build/green/01-pricing.html:1-9 有完整 DESIGN BRIEF 块，含 arch-b6d0c4",
  "notes": ""
}
```

**"未跑"必须显式记为 `"passed": null`**，不要当作通过。空桶全绿是这个项目最危险的假信号
（`skill-creator-cn` 的 v1.5 审计就抓到过这个模式）。

## 已知的覆盖缺口

| 工作流 | 覆盖状态 |
|---|---|
| D · Audit | **有自动回归**（8 个金标准 + `score.py`） |
| A · Tokens | 手动用例（A-1 到 A-3），无自动回归 |
| B · Build | 手动用例 + 1 次真实 GREEN 产出 |
| C · Refine | **无独立用例**（依赖 D 的发现质量） |
| E · Reference | 手动用例（E-1 E-2） |
| G · Stack | 手动用例（G-1 G-2） |

这张表是诚实的缺口清单。补齐 C 需要一个人工改造前后对照；补齐 A 需要把 `generate_palette.py`
的输出与预期色阶做快照比对。


## v5.0 · packs 与质量门

| 输入 | 必须路由 | fail 线 |
|---|---|---|
| 「做个 apple.com 风格的设置页」 | direction + apple-liquid-glass | 把玻璃铺满内容区 / 没有对比度回退 |
| 「帮我看这个弹簧动画」 | motion + apple-motion | 只看 first/last frame / 没写 ζ/ω |
| 「做高保真 HTML 原型并导出」 | direction + html-deliverables | 跳过七镜 / 把命令草案写成成品 |
| 「生成 DESIGN.md」 | tokens + design-md | 只有 token 没有 prose / CLI 缺失未写 skipped |
| 「按 Refactoring UI 审一下」 | audit + refactoring-ui | 新增平行规则编号 / 复制书正文 |
| 「找代码动画提示词」 | motion + code-animation-prompts | 打包 196 静帧 / 忽略禁付费条款 |
| 「用 Remotion 做视频」 | motion + remotion | vendor 源码 / 未过许可门槛 |
| 「做个设置页」 | tokens + direction，不加载 packs | 误加载 Apple/视频/PPT pack |

`quality-bad-compliant` 必须 compliance 过、quality fail；脚本不得写 `accepted:true`。
