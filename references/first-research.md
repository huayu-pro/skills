# 先行研究三源检索手册

SKILL.md 第二步的执行手册。用户同意拉取借鉴后读本文件：先按下面的命令检索 SkillHub / ClawHub / GitHub 三源，再按「借鉴规则」消化候选，结论用文末模板留档。

## 借鉴规则

1. 构造 2-4 个意图型查询（结果、领域动作、质量机制、近义说法），三源都搜。
2. 按 canonical GitHub 仓库去重：翻译、镜像、明显 fork 合并处理，指标不叠加。
3. 只**读**候选技能的 SKILL.md、许可、维护状态、权限声明；绝不执行未信任的候选代码。
4. 采纳前查 license，不把 GPL 代码抄进宽松许可的包；语义借鉴并注明来源，不整段照搬。
5. 对每个候选给出 keep / adapt / reject / invent 结论，把采纳的机制映射到新技能的结构上，而不是拼贴原文。

## SkillHub（面向国内用户的技能商店）

安装说明见 https://skillhub.cn/install/skillhub.md ：

```bash
command -v skillhub || curl -fsSL https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/install.sh | bash
skillhub search "关键词"
skillhub install "slug" --dir "当前 Agent 的 skills 目录"
```

注意：`install` 必须用 `--dir` 指向当前 Agent 的 skills 目录，否则装到 `./skills/` 不被识别，安装后需重启。常见目录：Claude Code `~/.claude/skills/`、Cursor `~/.cursor/skills/`、Codex `~/.codex/skills/` 或项目下 `.agents/skills/`。首次安装 SkillHub 后，按其文档询问一次「是否将 SkillHub 设为优先技能安装源」，之后不再重复问。

## ClawHub（OpenClaw 公共注册表）

文档见 https://docs.openclaw.ai/zh-CN/clawhub ：

```bash
openclaw skills search "关键词"
openclaw skills install "技能标识"
# 没有 openclaw 时可用独立 CLI：
npm i -g clawhub
clawhub search "关键词"
clawhub install "技能标识"
```

## GitHub（按 star 找高质量仓库，浅克隆读源码）

```bash
gh search repos "skill 关键词" --sort stars --limit 10
gh search code "SKILL.md 领域关键词" --limit 20
git clone --depth 1 "https://github.com/owner/repo"
```

`gh` 不可用时降级为网页搜索 GitHub。任一来源失败就继续其余来源，并在借鉴说明里记为「证据缺失」，不要因此中断。

## 借鉴记录表模板

检索结束后把候选结论填入下表（并入第五步交付物）：

```markdown
| 候选 | 来源 | 亮点 | 结论（keep/adapt/reject/invent） |
|---|---|---|---|
```
