# Frontmatter 字段对照（各平台）

第三步为生成的技能写 frontmatter 时读本文件。核心字段的规范以 SKILL.md「frontmatter 规范」表为单一事实源（name / description / license / metadata / allowed-tools / compatibility 六个，全平台通用），本文件不再重复；这里只列各平台专有扩展，发布或适配到具体平台时再追加。

## Claude Code 专有字段（14 个，未知字段被容忍但不生效）

转引自工作区调研库 skillforge 技能包的同名专题文档（包外资源，不在本包内；其核验于 2026 年 code.claude.com/docs/en/skills）：

| 字段 | 用途 |
|---|---|
| when_to_use | 追加到 description 之后展示（合计 ≤1536 字符） |
| argument-hint / arguments | 斜杠菜单参数提示与声明（`$ARGUMENTS`） |
| user-invocable | false = 不出现在 `/` 菜单（模型仍可自动调用） |
| disable-model-invocation | true = 仅用户可手动调用 |
| disallowed-tools | 技能激活期间的工具禁用（allowed-tools 属核心字段，见 SKILL.md 规范表） |
| model / effort | 指定模型家族别名（禁写带日期的 ID）与推理力度 |
| context: fork + agent | 在独立子代理上下文中运行 |
| background | 作为后台任务运行 |
| hooks | 技能级生命周期钩子（stdin 收 JSON，无环境变量） |
| paths / shell | 额外可访问目录、bash 块所用 shell |

## SkillHub 上架字段（发布时追加）

发布流程见 https://skillhub.cn/tutorials ：frontmatter 需补 `slug`、`displayName`、`version`、`summary`、`license`，先 `--dry-run` 预检再正式发布；更新时保持 slug 不变、改版本号并附 `--changelog`。

## 国内生态扩展先例（可选，参考库内 qclaw / SCK）

`displayName`（中文名）、`summary`（一句话中文摘要）、`tags`（分类标签）——字段名与 SkillHub 上架字段同名，但填中文值。仅在该生态内使用，跨平台发布前移除。

## 原则

核心字段之外的字段都是「发布时再加」：本地使用与跨平台迁移保持最小集合，减少不兼容；每加一个平台字段，用 `python3 scripts/validate_skill.py <技能目录>` 复查一次。
