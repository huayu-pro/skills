# ATTRIBUTION

> **混合许可**：本包的原创代码与文档是 MIT；第三方与 OPL 派生材料**不重新授权**。
> 完整边界见 `NOTICE` 与 `LICENSE`。对外发布前必须逐项核对。

## 1. 规则层

`references/02`–`08`、`12`–`14` 的规则与编号源自 *Refactoring UI*
（Adam Wathan & Steve Schoger）。本包只保留**规则、编号与中文解释**，不复制书页、插图或整段原文。
`§2.9`、`§5.9` 与 `§9.x`–`§11.x` 是本工作区的扩展。

## 2. 品牌语料

`assets/brands/` 的 84 份 `DESIGN.md` 来自
[awesome-design-md](https://github.com/VoltAgent/awesome-design-md)（MIT）。
Copyright (c) VoltAgent. 上游 MIT 全文以该仓库为准。
每份是第三方对品牌设计语言的观察，不是品牌官方规范；不包含品牌 logo、图片或字体文件。
商用前请自行核对原始仓库的 license 与品牌商标政策。

## 3. 原型语料

`assets/patterns/` 的 14 张原型卡由 One Page Love 公开目录蒸馏：
目录 550 条 → designlang/dembrandt 抽取成功 412 条 → 有 ≥3 个颜色 token 可聚类 379 条 → 14 个原型。
卡片只保留**区间、分布与 section 顺序**；代表站 URL 与 slug 已移除，不随包分发原始语料。
One Page Love 数据无明确再分发许可；**本包仅供内部设计参考，不构成商业再分发授权**。
商用派生语料前需联系 hello@onepagelove.com。

## 4. 动效代码

- `assets/motion/code/kits/`：reverse-302 复刻期自写的 12 个机制 kit。
- `assets/motion/code/components/`：reverse-final 自写的 12 个复合组件（HTML/CSS/JS 全部自写，
  视觉素材为渐变/SVG/canvas 自绘，无原站图片/字体/视频/shader 源码）。
- merged 示例（5 个）已因 200 源文件上限移出，历史版本可查；当前只保留 12 复合组件与 12 kit。
- `assets/motion/code/css/keyframes.css`：从 1,537 个观察块归并/重写的 24 条 canonical 配方。
- `assets/motion/code/snippets/`：本包自写的 8 个原语。
- `assets/motion/prompts/`：reverse-pilots 的 10 份自写强提示词。

**不打包**：`reverse-final/appendix/engines/`（19 份原站脚本，含真实项目文案）、
`reverse-final/appendix/sources/`（57 套无许可证结构来源）、302 复刻的原站资产/截图/证据。
这些只作为 provenance 记录，见 `SOURCE-LEDGER.md`。

## 5. 站点研究 / 手法 demo

`assets/site-studies/` 与 `assets/site-techniques/` 使用虚构品牌、自造图形与系统字体；
不包含原站图片、字体、视频。文本中的来源 URL 已统一移除。

## 6. Golden 页

`assets/golden/aperture.html`、`atelier-north.html` 来自本工作区 build-v3 的自设计演示；
`studio.html` 来自 reverse-final 的自写机制集成页。三者均不含第三方资产。

## 7. 审计金标准

`evals/cases/` 的 8 个用例继承自 `refactoring-ui-skill`（MIT）。
`evals/score.py` 的评分契约同源；本包只做路径与说明适配。

## 8. 第三方工具

构建/验证只读使用 Playwright、Microsoft Edge、ImageMagick；这些工具不进入组件运行时。
组件零依赖，不需要它们即可打开。

## 9. 再分发建议

| 对象 | 建议 |
|---|---|
| 规则/动效代码/组件 | 可内部复用；对外发布前替换示例文案/品牌 |
| 84 品牌文档 | 保留 MIT 署名；核对品牌商标政策 |
| 14 原型卡 | 只引用区间；不要声称为原始站点数据 |
| 30 案索引 | 可引用机制/参数；截图不随包 |
| 原始语料/302 证据 | 不对外分发 |
## 9. v5.0 packs

| Pack | 来源 | 许可 | 改写方式 |
|---|---|---|---|
| apple-motion | emilkowalski/skills | MIT | 独立提炼词汇/评审规则，不复制原文 |
| apple-liquid-glass | naplesblue/apple-design-skill | MIT + Lucide ISC + emilkowalski MIT | 独立散文 + 原创 CSS；不含截图/图标路径 |
| html-deliverables | alchaincyf/huashu-design | MIT | 提炼工作流与评审维度；不打包 232MB 资产 |
| design-md | VoltAgent/awesome-design-md | MIT | 工作流说明；复用已有 brands.json，不重复打包 |
| refactoring-ui | edisonmbli/refactoring-ui-skill | MIT 原创部分 | 规则 ID 映射；不复制书正文，非官方 |
| code-animation-prompts | XiaoyeCodes | 自定义免费/保留来源/禁付费打包 | 原创分类；不含 341 prompts/196 静帧 |
| remotion | remotion-dev/remotion | Remotion License | 外部依赖适配；不 vendor 代码；先过许可门槛 |

**排除**：guizang-ppt-skill（AGPL-3.0）不纳入，不复制代码或版式实现；ppt-master 与
open-design 保持外部。完整许可声明与商业交付清单见 `NOTICE`。

## 10. 语料偏差

302 个逆向站点与 84 份品牌 DESIGN 文档偏向拉丁语、桌面鼠标、作品集/代理站，不足以代表
CJK、utility、移动端或财务/后台界面。v5.0 用 `references/29-cjk-mobile.md`、
surface profiles 与 `assets/golden/ledger.html` 补边界；这些补充标 `inferred` 或
`authored`，不冒充 302 站点的 observed 结论。
