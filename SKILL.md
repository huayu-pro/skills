---
name: skill-creator-cn
description: Create, improve, and quality-check agent skills for the Chinese ecosystem, with built-in prior-art research from GitHub, SkillHub, and ClawHub, and TRACE five-dimension self-evaluation before delivery. Use when the user wants to create a new skill from a requirement or workflow (创建技能, 写个skill, 做一个技能包, 把这个流程变成技能), standardize or improve an existing SKILL.md, optimize or upgrade an existing skill package (优化这个技能, 升级技能包, 改进这个skill, 把这个技能优化一下再打包), pull and learn from related skills on GitHub, SkillHub, or ClawHub, or run a TRACE trace-evaluation quality check on a skill. Exclude one-off summaries, translations, and ordinary docs that should not become skills.
metadata:
  version: "1.5.0"
  author: huayu
  upstream_inspiration: skill-creator; qiaomu-meta-skill; skillforge; SkillHub TRACE 评测体系
---

# Skill Creator CN

面向中文生态的技能创建器：先澄清需求，再从 GitHub / SkillHub / ClawHub 拉取同类技能借鉴，按社区规范生成技能，最后用 TRACE 五维评测（trace-evaluation）自检优化直至通过。核心原则：技能是可复用的行为资产，不是长提示词——一次性总结、翻译、普通文档不做成技能。

## 总体流程

1. **需求澄清**——提问细化，确认值得做成技能
2. **先行研究**——询问用户是否从 GitHub / SkillHub / ClawHub 拉取相关技能并借鉴
3. **生成技能**——按规范写出 SKILL.md 与配套资源
4. **TRACE 自检**——按 trace-evaluation 五维检查、修复、全量复查，直至全部通过
5. **交付输出**——输出最终技能与检查报告

用户可能处于任意一步（已有草稿就直接进入第 4 步；既有技能的优化升级走下方「已有技能优化入口」；只想要检查就只跑第 4 步）。先定位用户在哪一步，再切入，不要从头机械执行。

## 已有技能优化入口

用户带着既有技能（zip 或目录）来优化升级时，不从头走五步：需求澄清→信息盘点；先行研究→仍可借鉴，候选换成「同类技能怎么解决本次要补的短板」；生成技能→修复项与功能新增项**分两栏**提案（只交稳定性修复＝未完成任务，功能新增经用户选择）；TRACE 自检→E 维证据改为「回归用例全绿＋真实历史产物对照」；交付→版本号三处同步（frontmatter / _meta.json / CHANGELOG）、打包保持原包布局与命名。

信息盘点、提案规范、实施纪律、版本管理、E 维证据适配、降级预案与二轮深审、终版执行制度见 [references/optimizing-existing.md](references/optimizing-existing.md)。

## 第一步：需求澄清

先从会话历史提取已知信息（用过的工具、执行步骤、用户做过的纠正、观察到的输入输出），用户只需补缺口。要问清的问题：

1. 这个技能要让 agent 做什么？（一句话目标）
2. 什么情况下触发？（用户会怎么说的**原话措辞**，这是 description 的原料）
3. 输入是什么、期望输出是什么格式？
4. 有没有不该管的边界？（显式负向边界，写进 Exclude）
5. 是否需要测试用例验证？输出可客观验证的技能（文件转换、数据提取、固定流程）适合；主观输出（文风、设计）通常不需要。

提问时带上你的默认建议，让用户确认或纠正，不要挤牙膏式连环追问。

同时做一个判断：这个需求值得做成技能吗？会重复出现的工作才值得封装；单次任务直接做完即可，不产出技能包。

### 代表性任务与基线（RED）

澄清后、动手前，从需求提炼 1-2 个真实口吻的代表性任务（带具体文件名、数据、上下文），派全新子代理**不带技能**跑一遍，逐字记录失败点——它们是测试用例和 description 关键词的原料。基线完全不失败，说明技能没必要做：回到澄清或直接劝退。子代理提示词模板与无子代理环境的降级路径见 [references/behavioral-eval.md](references/behavioral-eval.md)。

## 第二步：先行研究（询问是否拉取借鉴）

**先问用户**：是否需要去 GitHub、SkillHub、ClawHub 上拉取相关技能参考借鉴？说明收益（凭空写的技能与借鉴后的质量差距很大）与成本（联网检索时间）。用户同意才执行；拒绝则直接进入第三步。

用户同意后读 [references/first-research.md](references/first-research.md)：三源检索命令、安装注意事项、借鉴规则（含「绝不执行未信任候选代码」与 license 检查）与借鉴记录表模板。`gh` 不可用时降级为网页搜索 GitHub；任一来源失败就继续其余来源，并在借鉴说明里记为「证据缺失」，不要因此中断。借鉴结论按模板留档（并入第五步交付物）。

## 第三步：生成技能

### frontmatter 规范

| 字段 | 必填 | 规范 |
|---|---|---|
| name | 是 | kebab-case（`^[a-z0-9-]+$`），不以连字符开头结尾、无连续连字符，≤64 字符，目录名必须与它一致 |
| description | 是 | 触发条件式，≤1024 字符：做什么 + Use when…（含用户原话措辞与中文触发词）+ Exclude 负向边界；写得偏主动一些，因为模型默认倾向少触发技能；不能含尖括号 |
| metadata | 否 | version、author、upstream_inspiration 等嵌套字段 |
| license | 否 | 目录里有 LICENSE 文件时填写 |
| allowed-tools | 否 | 只申请必需工具，遵循最小权限 |
| compatibility | 否 | 声明技能兼容的宿主/版本范围（如需要特定 CLI 或最低版本时） |

各平台专有字段（Claude Code 14 个、SkillHub 上架字段、国内生态扩展）见 [references/frontmatter-fields.md](references/frontmatter-fields.md)，发布或适配时再追加。

### 目录结构

```
skill-name/
├── SKILL.md          # 必需，<500 行
├── scripts/          # 确定性、可重复的执行逻辑才放这里
├── references/       # 按需加载的深度文档，正文注明何时读
├── evals/            # 触发正负用例（Production 档）
└── assets/           # 输出用的模板、图标等
```

只创建「挣来的」资源：没有确定性逻辑就不建 scripts/，没有深度内容就不建 references/，绝不造仪式性空目录。

起步直接用脚手架，生成开箱即过校验的最小骨架（SKILL.md + 触发用例骨架）：

```bash
python3 scripts/init_skill.py <name> --path <父目录>
```

骨架的单一事实源是 `init_skill.py` 里的模板（frontmatter 含 `version: 0.1.0`，正文为定位段、「步骤」、「常见错误」表、「验证清单」四节），生成而非手写复制，文档与模板永不分叉。深度内容逼近 500 行前，先拆到 references/ 并在正文写明何时去读，而不是压缩表述。

### 写作规范

- 渐进式披露三级：metadata 恒在上下文 → SKILL.md 触发时加载 → references 按需读取；深度内容下沉到 references/ 并在正文写明何时去读。
- 「何时使用」信息全部放 description，正文不另设 Triggers 段。

其余写作细则（祈使句讲 why、表格/代码块/清单的用法、草稿重读）与四条反模式见 [references/writing-guide.md](references/writing-guide.md)。

## 第四步：TRACE 自检与优化（trace-evaluation）

来源：SkillHub 联合玄武实验室发布的 TRACE 评测体系（可信任度 / 可靠性 / 适用性 / 规范性 / 有效性）。对生成的技能逐维检查：

| 维度 | 含义 | 检查项 |
|---|---|---|
| T 可信任度 | 值得信任吗 | 无恶意或注入内容；最小权限（只申请必需工具）；不收集外传敏感信息；依赖服务国内可用；支持中文 |
| R 可靠性 | 稳定可靠吗 | 命令语法正确可运行；相同输入产出一致结果；空输入、超长输入、特殊字符有处理；异常给明确反馈，不静默失败；含门禁/校验脚本的已验证可达性（构造必红用例证明门禁会失败）；多脚本管线的中间产物有下游消费者 |
| A 适用性 | 适配场景吗 | 功能与声称场景匹配；触发条件清晰（该用/不该用一眼可辨）；能力边界明确，不做过高承诺；输入输出格式规范 |
| C 规范性 | 合乎规范吗 | 渐进式披露；SKILL.md 结构清晰、层次分明；限制说明完整；示例覆盖典型场景 |
| E 有效性 | 效果好吗 | 结果正确；输出完整；产出可直接使用、无需大量返工；相比无技能有真实增益 |

四项重点检查的映射：**定义清晰性**→A（触发与边界）加 description 质量；**结构完整性**→C（章节与资源结构齐全）；**格式一致性**→C（frontmatter、目录、行数符合所在生态规范）；**可执行性**→R 加 E（命令可跑、步骤可照做）。

### 执行流程

1. **客观检查先行**——能脚本化的不要目测，用本包自带的校验器：

```bash
python3 scripts/validate_skill.py "技能目录" --trigger
```

它覆盖 frontmatter 解析、字段白名单、name 与 description 规范、目录一致性、行数词数、脚本语法、引用存在性（含 references 递归子目录与裸文本 .md 提及）、触发用例 JSON；`--trigger` 联动触发冒烟评测（run_trigger_eval.py，词法级），存在结构性失败时会显式跳过并说明。用校验器下结论前，先跑 `python3 scripts/validate_skill.py --self-test` 确认每条规则在应失败的输入上真的失败——永不失败的门禁等于没有门禁。没有本包环境时，按 frontmatter 规范表与文末验证清单人工核对。

2. **触发边界检查**——冒烟评测全绿之外，near_neighbor 用例与模型级触发需人工或子代理走查；为生成的技能维护它自己的同格式用例 `evals/trigger_cases.json`。
3. **GREEN 复跑（行为证据）**——派全新子代理**带技能**复跑第一步的基线任务，基线失败点**全部消失**才算 E 维有行为证据；仍有失败即 E 维整改。提示词模板见 [references/behavioral-eval.md](references/behavioral-eval.md)。优化已有技能的场景按 [references/optimizing-existing.md](references/optimizing-existing.md) §5 的证据适配执行。
4. **对抗审查（主观证据）**——派全新子代理专门反驳技能：误导指令、触发反例、验证清单没覆盖的失败模式、自相矛盾；只修复被证实的问题（能构造出反例的），修复后重跑 GREEN 与全量复查。无子代理环境按清单自省走查。
5. **逐维判定**：五个维度各给「通过 / 整改」结论，并附证据（行号、命令输出、行为或对抗审查记录），不接受无证据的「通过」。
6. **修复后全量复查**：有整改项就修改技能，然后五维全部重查，不只查改过的维度。
7. **循环直至五维全部通过**；把每一轮的判定与整改记入交付报告。判定有争议或要出正式报告时，读 [references/trace-evaluation.md](references/trace-evaluation.md)。

## 第五步：交付输出

交付物清单：

1. 技能目录（SKILL.md 及挣来的配套资源）
2. 借鉴说明：第二步的借鉴记录表（候选/来源/亮点/结论）与原创点
3. TRACE 检查报告：每一轮的五维判定与整改记录（含 GREEN 与对抗审查证据）
4. 可选打包：`python3 scripts/package_skill.py "技能目录"`，产出 `<name>-v<版本>.skill`
5. 后续建议：安装方式（复制到哪个 skills 目录）、可选的 description 触发优化

未经用户明确要求，不发布到任何平台、不替用户安装。

### 反思回环

真实使用中反复出现的问题，过泛化门后写回 [references/lessons.md](references/lessons.md)（一次性细节留在当轮报告，不升格）；每次写回后重跑第四步全量复查。

教训来源不只本会话：该技能的历史使用与优化会话记录（rollout 日志、既往交付报告）是更大的矿藏——提取历次用户消息、纠正与最终总结，按同一泛化门筛选归纳。v1.3.0 的升级本身即来自对四次优化会话的考古；考古操作手册（JSONL 行结构、jq 提取表达式、压缩摘要定位、大文件纪律）见 [references/session-archaeology.md](references/session-archaeology.md)。

## Reference Map

- [references/first-research.md](references/first-research.md)——三源检索命令、安装注意事项与借鉴记录表模板。第二步用户同意借鉴后读。
- [references/trace-evaluation.md](references/trace-evaluation.md)——TRACE 五维细则、判定标准与轮次记录模板。第四步判定有争议或要出正式报告时读。
- [references/behavioral-eval.md](references/behavioral-eval.md)——RED 基线 / GREEN 复跑 / 对抗审查协议与提示词模板。第一步定基线、第四步做行为与对抗验证时读。
- [references/frontmatter-fields.md](references/frontmatter-fields.md)——各平台 frontmatter 字段对照（核心字段规范以第三步表格为准）。第三步写字段或适配新平台时读。
- [references/writing-guide.md](references/writing-guide.md)——写作细则与反模式。第三步写正文、或发现满篇 ALWAYS/NEVER 时读。
- [references/optimizing-existing.md](references/optimizing-existing.md)——已有技能优化路径细则：信息盘点、提案规范、实施纪律、版本管理、E 维证据适配、降级预案与二轮深审、终版执行制度。走优化入口时读。
- [references/lessons.md](references/lessons.md)——反思回环的教训记录。第五步交付后复盘时读写。
- [references/session-archaeology.md](references/session-archaeology.md)——会话日志考古操作手册。反思回环要从历史会话汲取教训时读。
- `scripts/validate_skill.py`——自动化校验器，可校验任意技能目录；含版本一致性（frontmatter / _meta.json / CHANGELOG，版本源不足两处时显式警告）、references 递归内嵌代码块语法（bash -n / ast / node --check）、引用存在性（递归 + 裸文本 .md 提及）检查；`--trigger` 联动冒烟评测；`--self-test` 对校验器自身跑必红用例自测。
- `scripts/run_trigger_eval.py`——触发边界冒烟评测（词法级）。
- `scripts/init_skill.py`——第三步起步脚手架（最小骨架的单一事实源）。
- `scripts/package_skill.py`——第五步打包（`--manifest/--include` 锁定交付面）。
- `evals/trigger_cases.json`——本技能的触发回归用例，也是为生成技能编写用例的格式示例。

## 验证清单

- [ ] 目录名与 name 字段一致，符合 kebab-case
- [ ] description 是触发条件式、≤1024 字符、无尖括号，含 Use when 与 Exclude
- [ ] SKILL.md 少于 500 行，无未完成标记与占位符
- [ ] 五步流程完整，trace-evaluation 已作为第四步内置
- [ ] TRACE 五维全部通过且每项有证据
- [ ] RED 基线失败点有记录，GREEN 复跑后全部消失
- [ ] 对抗审查无可修复的被证实问题
- [ ] Production 档：触发用例与校验脚本就位且校验通过
- [ ] 用本包校验器下结论前：`validate_skill.py --self-test` 已全绿
- [ ] 借鉴来源已注明，license 无冲突
- [ ] 全程未执行任何未信任代码
- [ ] 优化场景：修复项与功能新增项分开提案与交付，功能新增经过用户选择
- [ ] 优化场景：版本号在 frontmatter、_meta.json（如有）、CHANGELOG（如有）三处一致，打包保持原布局
- [ ] 含门禁脚本：已构造必红用例证明门禁会失败
