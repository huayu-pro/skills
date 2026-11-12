# SELF-CHECK — ui-design 5.0.0

> 生成时间：2026-11-12。本文件只记录本次本机实跑；未跑的检查写 `skipped`，
> 不沿用 4.5.1 的历史读数冒充 5.0.0 验证。

## 0. 包体（实测）

| 项 | 值 |
|---|---|
| 源文件数 | 197（core 187 / packs 10；dist 不计数） |
| 预算 | core 190 / packs 12 / total 200（≤200；无二进制） |
| SKILL.md | 88 行（路由版） |
| sub-skills | 4：direction / tokens / motion / audit |
| references | 30 章（00–29） |
| scripts | 11 个（原 8 + detect_stack.mjs + build_skills.py + score_rubric.py） |
| evals | 8 审计 + 10 动效 + 触发/评分/工作流 |
| golden | 4 HTML + 0 二进制（截图只在评审会话中渲染） |
| packs | 7 个，10 文件；一次最多加载 2 个 |

## 1. 本机回归

| 检查 | 命令 | 结果 |
|---|---|---|
| 资产/版本/结构/许可 | `python3 -I scripts/check_assets.py` | **0 errors / 0 warnings** |
| 构建 manifest | `python3 -I scripts/build_skills.py --check` | **ok: true**；core 186 / packs 10 |
| 构建 dist | `python3 -I scripts/build_skills.py --out dist` | 5 个发行目录 |
| 动效扫描自测 | `python3 -I scripts/check_motion.py --self-test` | **17/17** |
| 动效夹具 | `python3 -I scripts/check_motion.py evals/motion --expect` | **10/10** |
| 审计器自测 | `python3 -I scripts/audit.py --self-test` | **35/35** |
| utility golden 动效 | `python3 -I scripts/check_motion.py assets/golden/ledger.html --json` | `[]` |
| 全部 shipped assets | `check_motion.py assets --json` | 0 P1；3 个已知 P2（2 无限循环 + 1 cursor） |
| motion profile 生成 | `python3 -I scripts/emit_tokens.py --motion-profile utility` | 通过 |
| visual ledger | Edge headless 1200×800 + 375×844 | 会话内渲染并人工核对；截图不随包（no binaries） |
| 运行时组件 | `verify_motion.mjs --dir assets/motion/code/components` | **12/12**（merged 已移出） |
| ledger 1280/375 | `verify_motion.mjs --url <ledger> --viewports 1280,375 --profile utility --trace --throttle` | `verified:true / accepted:false`；overflow `{}`；63 条 trace；0 console errors |
| ledger audit | `audit.py assets/golden/ledger.html --json` | **0 P0 / 0 P1 / 0 P2** |
| ledger utility rubric | `score_rubric.py --profile utility` | **4.25 / pass**（克制 5、完成度 4、动效 4） |
| golden 1280/375 | `verify_motion.mjs --url <3 pages> --viewports 1280,375` | 3/3 `verified:true`；overflow 全空 |
| golden audit | `audit.py <3 pages> --json` | aperture 0 P0 / 1 P1；atelier 0/0；studio 0 P0 / 9 P1（设计例外已记录） |
| golden rubric | `score_rubric.py --profile expressive/catalog` | aperture **4.85**；atelier **4.95**；studio **4.25**（均 pass） |
| Apple pack 1280/375 | `verify_motion.mjs --url <reference.html> --viewports 1280,375` | `verified:true`；overflow `{}`；0 errors |
| Apple pack audit | `audit.py packs/apple-liquid-glass/reference.html --json` | **0 P0 / 0 P1 / 0 P2** |
| Apple pack rubric | `score_rubric.py --profile product` | **4.05 / pass** |
| HTML sample audit | `audit.py packs/html-deliverables/sample.html --json` | **0 P0 / 0 P1 / 0 P2** |
| HTML sample 1280/375 | `verify_motion.mjs --url <sample.html> --viewports 1280,375` | `verified:true`；overflow `{}`；0 errors |
| HTML export dry-run | ffmpeg 静态 smoke | MP4 2s + GIF 1s 成功；PPTX 明确 `skipped`（无 HTML→PPTX 转换器） |
| Refactoring UI 覆盖 | `packs/refactoring-ui/coverage-report.md` | 151 条：138 covered / 7 partial / 6 gap，逐条明细 |
| 汇总证据 | `evals/reports/v5-evidence.json` | ledger/golden/Apple/HTML 的 audit+verify+rubric 全量记录 |

## 2. v5.0 质量门

- `accepted = compliance + quality + appropriateness`；脚本不单独写 `accepted:true`。
- `quality-bad-compliant` 静态扫描 `[]`，其 `quality: human-review-required / accepted:false`
  记录在 `evals/reports/v5-evidence.json`；证明两层分离。
- 旧 12 组件与 m01–m06 夹具走 legacy allowlist；新文件必须过 M-013..M-016。
- 五类 surface profile 与加权 rubric 写入 `12`；utility 对照 `ledger`。
- 七维等权、纸感单一品味、`0.45s + expo` 默认、frame-based lerp、欠阻尼冒充临界
  已在 `01` / `09` / `22` / `28` 中修正。

## 3. packs 许可与边界

- 已登记：emilkowalski/skills (MIT)、naplesblue (MIT + Lucide ISC + emilkowalski MIT)、
  huashu-design (MIT)、awesome-design-md (MIT)、refactoring-ui-skill (MIT 原创部分)、
  code-animation-prompts (自定义免费/保留来源/禁付费打包)、remotion (Remotion License)。
- 排除：guizang-ppt-skill (AGPL-3.0)；不 vendor ppt-master / open-design 大仓库。
- `NOTICE` / `ATTRIBUTION.md` / 根 `SKILL.md` 的 pack 表包含来源、许可门槛、商业交付清单。
- Pack 只在用户点名时加载；普通页面 0 packs；Stack 只在 `references/18` 可选分支。

## 4. 未验证 / skipped

- 运行时探针在本机静态服务与 `ledger`/三页 golden/Apple reference 上跑过；不代表
  用户的 React/Vue/SSR 项目、路由转场、代码分割或 hydration/FOUC 已被验证。
- `--throttle` 是 CDP 4x CPU + Fast-3G-like 网络，不是真机低端安卓/120Hz 测量。
- 五帧 quality 录屏、用户真实项目的 appropriateness 复核仍未执行；
  `verify_motion`/rubric 的 `accepted:false` 是有意保留的边界。golden 的 P1 是
  已记录的艺术方向例外（编辑型微字阶 / catalog 大阴影），不是静默通过。
- `validate_skill.py` / `run_trigger_eval.py` 不在本包；触发用例已更新但外部 CLI 未跑。
- 三库（shadcn/HeroUI/Mantine）仍为 docs-verified，未建真实 React 项目。
- CJK / 移动端 / 真机 120Hz / Safari / Firefox / 低端安卓：规则已补，实测仍 `skipped`。
- 196 张代码动画静帧、341 条提示词、232MB 原型资产、4.47GB Remotion 仓库未打包。
- 人工/LLM quality 与 appropriateness 复核是交付前必做；脚本只提供证据。

## 5. 结论

5.0.0 在**本机已声明的检查面**内通过：结构、资产、许可声明、静态动效、夹具、
审计器、token 生成、utility golden 渲染。运行时真页验收、触发 CLI、真机性能与
人工质量复核未执行，已逐条标 `skipped`；不声称「零缺陷」，也不声称脚本证明好看。
