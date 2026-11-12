# Changelog

## [1.1.0] - 2026-11-08

### 修复（第二轮：对抗审查 + GREEN 走查整改）

- **sandbox.sh 秒失败代理失效（HIGH，实测证实）**：proxy_args 是 init 函数 local 变量，m() 在函数返回后才调用、动态作用域取空值——提为全局 SANDBOX_PROXY_ARGS 并以假二进制端到端验证代理真实到达；就绪提示打印当前代理模式
- **SKILL.md 验证清单新旧指令打架（HIGH）**：登录一行仍写"换 text 型"，与本轮新结论矛盾——统一为"非 TTY 一律 EOF，按 plugin-auth.json 形状直写登录态"
- source 模式找不到 magpie 时 `exit 1` 杀掉调用方 shell → 改为 return；无 Bun 缓存可复制时输出 stderr 警告
- new-plugin.sh：显示名标识符安全校验（含空格/竖线的名字会生成非法 JS）；node --check 失败改为 exit 1；esc() 补转义 sed 分隔符
- template 三处"注释与代码打架"：oauth 才要求 refresh 字段（api 型按 {type:"api"} 存储）、resetsAt 的 ISO 警告与原样透传、models 钩子返回 OpenCode Model 形状（capabilities.toolcall 而非 tool_call，P11）——hooks.md §6 示例同步修正
- 实测修正登录管道结论：text 型 prompt 同样报 no key on stdin: EOF（此前文档建议换 text 型是错的）；补充"未登录时 provider test 报 no provider"
- pitfalls 增补 P21–P25（整卡全 aside、breakdown 双计、models 返回 {}、expires 缺失、流式 content-length——散落其他文件的静默失败入册编号）
- description 补安装失败类触发（装不上/加载报错/改了不生效）；MCP server 措辞收窄为"不经 magpie tool 插件暴露的独立开发"

### 修复（第一轮）

### 修复

- description 改为触发条件式：补 Use when（用户原话措辞）与 Exclude 负向边界（非 magpie 宿主插件、应用本体改动、通用教程、文档翻译总结）；frontmatter 增 metadata（version/author/updated）
- 新增「验证清单」节：交付插件前的逐项自查（沙箱加载、provider test、quota、红线对照、登录实测、导出规则）
- 文档对账：外部文件 .md 裸提及改写（NOTICE/AGENTS/HOOKS 契约）；26 处 js 示例代码块修正为可过 node --check 的合法语法（const 包装/函数包装，无语义变化）
- 开发-调试循环收敛为 scripts/sandbox.sh 一键封装（市场开关、秒失败代理、Bun 运行时复制三坑）

### 新增

- `scripts/sandbox.sh`：一键离线沙箱（隔离 HOME + 复用本机 Bun 缓存 + 秒失败代理），支持 --online 真联网与 MAGPIE_SANDBOX 复用
- `scripts/new-plugin.sh`：从 template/ 生成新插件骨架（vendor-id kebab-case 校验、Acme→vendor 全局改名、node --check 自检）
- `evals/trigger_cases.json`：触发回归用例（正例 6 / 负例 5 / 近邻 3，词法概念四组）

## [1.0.0] - 2026-11-08

### 新增

- 首版：SKILL.md 主入口 + template/（完整可跑 provider 插件骨架，沙箱实测加载）+ references/ 六份（hooks 钩子契约、auth-patterns 登录八式、models-usage 模型与额度窗口、pitfalls P1–P20 静默失败清单、publishing 打包发布、other-types 中间件/agent/页面等）
- 素材基础：官方文档 23 章节全转述、16 个本地插件源码剖析、GitHub magpie-plugin topic 与 registry.json 市场调研
