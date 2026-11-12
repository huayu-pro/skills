# Skills · 我的 AI Agent 技能库

一组按用途分类的可复用 Agent 技能包（`SKILL.md` 体系）。`main` 分支按分类收录全部技能；每个技能另有一条独立分支，分支根目录就是该技能本身，可直接安装。

## 技能一览

| 分类 | 技能 | 版本 | 一句话用途 | 独立分支 |
|---|---|---|---|---|
| 设计 | [ui-design](design/ui-design/) | 4.5.1 | 审美优先的网站 UI 设计、改造与评审；含动效、品牌语言、组件库适配 | `ui-design` |
| 科研 | [research-architecture-figure](research/research-architecture-figure/) | 1.5.1 | 把论文的研究框架/理论模型/技术架构/机制图画成可投稿的 SVG 架构图 | `research-architecture-figure` |
| 科研 | [literature-collection](research/literature-collection/) | 1.4.0 | 批量文献检索（知网/WOS）、筛选、下载全文、转 Markdown 并建立索引 | `literature-collection` |
| 科研 | [deep-research](research/deep-research/) | 1.3.0 | 可溯源、可引用的深度研究流程：研究设计 → 并行取证 → 对抗审查 → 成稿 | `deep-research` |
| 效率 | [auto-resume-tasks](productivity/auto-resume-tasks/) | 1.2.1 | 后台任务失败后的自动恢复决策：重试/续跑/放弃/转人工 | `auto-resume-tasks` |
| 元工具 | [skill-creator-cn](meta/skill-creator-cn/) | 1.5.0 | 中文生态的技能创建、优化与 TRACE 五维评测 | `skill-creator-cn` |
| 创意 | [ascii-web-design](creative/ascii-web-design/) | 1.4.0 | ASCII/字符化网页视觉与动画：图片/视频转字符、CRT、字符雨、Remotion 导出 | `ascii-web-design` |

## 目录结构

```
skills/
├── design/
│   └── ui-design/
├── research/
│   ├── research-architecture-figure/
│   ├── literature-collection/
│   └── deep-research/
├── productivity/
│   └── auto-resume-tasks/
├── meta/
│   └── skill-creator-cn/
├── creative/
│   └── ascii-web-design/
├── scripts/
│   └── sync-branches.sh      # 从 main 重新生成单技能分支
├── skills.json               # 机器可读清单
└── README.md
```

每个技能目录都自带 `SKILL.md`、`_meta.json`、`CHANGELOG.md`，以及各自的 `references/`、`scripts/`、`assets/`、`evals/`。许可与来源声明见各目录内的 `LICENSE` / `ATTRIBUTION.md` / `NOTICE`。

## 安装

### 方式一：整库克隆

```bash
git clone https://github.com/huayu-pro/skills.git
```

### 方式二：只装一个技能（推荐）

每条技能分支的根目录就是技能内容，克隆后可直接使用：

```bash
# 例：安装 ui-design
git clone -b ui-design --depth 1 https://github.com/huayu-pro/skills.git ui-design
```

把得到的目录放进客户端的技能加载路径，例如：

- ZCode：`~/.zcode/skills/<name>/`
- 通用 Agent Skills：`~/.agents/skills/<name>/`

以你的客户端实际加载路径为准。目录名需与 `SKILL.md` 的 `name` 保持一致。

### 方式三：从 main 复制指定目录

```bash
git clone --depth 1 https://github.com/huayu-pro/skills.git
cp -r skills/design/ui-design ~/.zcode/skills/
```

## 分支说明

| 分支 | 内容 |
|---|---|
| `main` | 全部分类技能 + 索引 + 同步脚本 |
| `ui-design` | 仅 `design/ui-design/` 的内容（根目录） |
| `research-architecture-figure` | 仅该技能内容 |
| `literature-collection` | 仅该技能内容 |
| `deep-research` | 仅该技能内容 |
| `auto-resume-tasks` | 仅该技能内容 |
| `skill-creator-cn` | 仅该技能内容 |
| `ascii-web-design` | 仅该技能内容 |

**单技能分支由脚本生成，请勿直接在分支上修改**——改动只提交到 `main`，再同步下来。

## 更新流程

```bash
# 1. 在 main 上修改技能
vim design/ui-design/SKILL.md

# 2. 更新技能自身的版本号与 CHANGELOG 后提交
git add -A && git commit -m "ui-design: 4.5.2"

# 3. 重新生成单技能分支
./scripts/sync-branches.sh

# 4. 推送 main 与所有分支
git push origin main
git push origin --all
```

`sync-branches.sh` 只重建内容有变化的分支；也支持只同步指定技能：

```bash
./scripts/sync-branches.sh ui-design
```

## 迁移记录

本仓库由以下单技能仓库合并而来，原仓库在内容核验后已删除：

| 原仓库 | 现路径 | 独立分支 |
|---|---|---|
| `huayu-pro/skill-creator-cn` | `meta/skill-creator-cn/` | `skill-creator-cn` |
| `huayu-pro/literature-collection` | `research/literature-collection/` | `literature-collection` |
| `huayu-pro/deepreaserch` | `research/deep-research/` | `deep-research` |
| `huayu-pro/auto-resume-tasks` | `productivity/auto-resume-tasks/` | `auto-resume-tasks` |
| `huayu-pro/ascii01` | `creative/ascii-web-design/` | `ascii-web-design` |

各原仓库的提交历史已通过 `git subtree` 保留在 `main` 中。`deepreaserch`、`ascii01` 是原仓库 slug；技能本体声明的 `name` 分别为 `deep-research`、`ascii-web-design`，目录与分支均以技能名为准。

## 许可

各技能保留自身许可：`ui-design`、`deep-research` 为 MIT；其余技能请见各自目录内的声明文件。
