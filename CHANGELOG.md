# 更新日志（skill-creator-cn）

格式参照 Keep a Changelog；版本号遵循 semver（仅修复→patch，功能新增→minor，破坏性→major）。与 frontmatter `metadata.version`、`_meta.json` 三处同步（validate_skill.py 自动比对）。

## [1.5.0] - 2026-10-25

用本技能自身的「已有技能优化入口」流程对元技能做的最后一轮优化。依据：七轮实战优化报告 + 会话日志考古 + 包本体深读 + 客观校验。修复 20 项、功能 4 项。

### 新增

- validate_skill.py `--self-test` 必红自测：每条检查规则配一个应失败的迷你坏包（29 例）＋全绿样本防自测自身永真；已做哨兵验证（临时禁用一条规则 → 自测变红）。
- 裸文本 .md 提及存在性检查：「见 xxx.md」这类无链接记号也是契约，断链必报。
- references 递归扫描：嵌套子目录的细则文档不再逃过代码块语法与引用检查（scripts/、evals/ 同步递归）。
- 版本源不足两处时显式警告「未交叉比对」；源文件存在但提取不到版本号时同样显式警告且不计入有效版本源——条件不满足不再静默当通过。
- 未闭合代码围栏显式警告（此前围栏状态机会把未闭合围栏内的内容静默放过语法检查）。
- 触发评测空桶防护：0 条用例的「全过」按失败处理（评测空转不等于通过）。
- references/session-archaeology.md：会话日志考古操作手册（jq 提取配方、压缩摘要两种形态、大文件纪律）。
- references/first-research.md：三源检索命令、借鉴规则与记录表模板（自第二步正文下沉）。
- references/writing-guide.md：写作细则与反模式（自第三步正文下沉）。
- _meta.json 与本 CHANGELOG：版本三处同步首次对本包自身完整生效；_meta.json 的 name 与 frontmatter 交叉核对。

### 修复

- 三个校验器盲区：版本一致性静默跳过、references 只扫顶层、裸文本引用不检查。
- 二轮只读深审发现的空转通过两处（H1/M1）：触发用例三桶全空仍报「评测通过」；版本源存在但无版本号时计入「交叉比对」——恰为本轮新代码引入，深审抓回。
- 异常路径三连崩溃改显式报错：name 非字符串、frontmatter metadata 非字典（校验器与打包器）、trigger_cases.json 顶层非对象。
- 规则 7 引用检查未剥 URL 导致外链路径误报断链。
- SKILL.md 行数统计 off-by-one（以换行结尾的文件多算 1 行）；skill_dir 以 `.` 传入时目录名比对误报（改用 resolve）。
- --trigger 在结构失败时静默跳过 → 显式说明跳过原因；评测器崩溃时 stderr 末行并入失败原因；bash 缺失时内嵌代码块检查改为显式跳过（与 node 一致）。
- package_skill.py 时间戳钳制 localtime→gmtime：UTC 负偏移时区会把 1980-01-01 UTC 折回 1979 仍触发 zip 崩溃（必红用例实测）；--out 指向文件时显式报错；清单漂移检查前移到写盘之前（防残留残缺压缩包）。
- 「Claude Code 17 个字段」口径三处不一致：实为 14 个（allowed-tools 归核心字段组）；compatibility 字段补文档；tags 分组口径统一。
- SKILL.md「走上方优化入口」方向错误；optimizing-existing 章节枚举漏「信息盘点」「E 维证据适配」。
- 验证清单「无 TODO/FIXME」自指行改写为「无未完成标记与占位符」，消除校验器自匹配警告。
- 最小骨架双源（正文内联副本 vs init_skill.py 模板）统一为脚本单一事实源。
- 包外悬空指针标注、示例命令缺参、示例工具名笔误、docstring 漏参、退出码文档粒度（含评测器格式非法路径）。
- 触发用例两个元提及措辞（install_only/read_only）换同族无关键词冲突措辞，落实 lessons 泛化门。

### 精简

- SKILL.md 262 → 177 行：三源命令块、借鉴规则、写作规范/反模式、优化入口对照表、最小骨架内联副本全部下沉 references，正文只留流程契约与「何时读」指针。

### 已知豁免

- 词数估算约 2179 仍超 1500 软警告：剩余正文是五步流程契约，继续下沉会破坏第一级渐进式披露的自足性（每步的触发加载需要正文自足）；行数硬门 177 远低于 500。阈值维持 1500 不改判据，警告保留作已知豁免。

## [1.4.0] - 2026-10-24

二轮深审修复轮：trace-evaluation.md R 维与 SKILL.md 同步（F1）、behavioral-eval 与 optimizing-existing 互链（F2）、内嵌代码块语法检查扩展到 references/*.md（G1）、references 相对引用存在性检查（G2，首跑即抓到一条真实断链歧义）、打包排除 node_modules/.venv。

## [1.3.0] - 2026-10-24

会话考古升级轮：对四次优化会话日志（literature-collection / constructivist-ppt / ascii01 / deep-research）做日志考古后升级——新增「已有技能优化入口」与 optimizing-existing.md 六节细则（两栏提案制、必红用例规则、数据流盘点、增量主键续编、文档对账、降级预案、二轮深审分工）；validate_skill.py 新增版本一致性检查（v1.3.0 起）与内嵌代码块语法检查；反思回环明确「会话日志是更大的矿藏」。

## [1.2.0] - 2026-10-24

deep-research 优化会话教训写回：TODO 检查降为警告、中文词数估算降为软警告、run_trigger_eval 的 CJK-拉丁交界切分等首批 lessons 沉淀。

## [1.0.0] - 2026-10-24

创生：五步流程（需求澄清含 RED 基线 → 先行研究三源借鉴 → 生成技能 → TRACE 五维自检内置第四步 → 交付与反思回环），十一文件包，中文正文 + 英文 description。TRACE 出处为 SkillHub×腾讯×玄武实验室五维评测体系。
