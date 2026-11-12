---
name: magpie-plugin-dev
description: 创建、调试与发布 Magpie（usemagpie.ai）插件——provider/auth 插件、网关中间件、请求钩子、agent、页面、tool 插件。Use when 用户要写个 magpie 插件、把某服务接入 magpie、创建 provider 或登录 auth 插件、改 magpie 插件代码、排查插件问题（模型不显示、额度未知、登录失败、账号被误标过期、插件装不上、加载报错、改了代码不生效）、把插件发布上架 magpie 插件市场。Exclude 非 magpie 宿主的插件开发（VSCode、Claude Code 等）与不经 magpie tool 插件暴露的独立 MCP server 开发、magpie 应用本体（网关与路由源码、agent 适配器）的改动、纯 OpenCode 生态通用插件教程、翻译或总结插件文档。
metadata:
  version: "1.1.0"
  author: huayu
  updated: "2026-11-08"
---

# Magpie 插件开发

给 Magpie（AI 编程应用的 provider 聚合器，yetone/magpie）写插件：登录某个服务、替它发请求，magpie 把它包装成所有 agent 可用的 provider（多账号、故障切换、用量统计由 magpie 承担）。本 skill 的内容来自官方文档全文 + 16 个真实插件源码剖析（含多个插件的实测踩坑注释），按"动手时需要什么"组织。

## 30 秒理解插件模型

- 插件 = **npm 包 / git 仓库 / 本地文件夹**（或单个 `*.middleware.js` / `*.agent.js` / `*.hooks.js` / `*.gateway.js` 文件），完全兼容 OpenCode v1 provider 插件与 pi 扩展包。
- 所有插件跑在**一个共享 Bun 宿主进程**里；宿主与 magpie 经 stdin/stdout 每行一条 JSON 通信。
- 插件工厂：`async (input, options) => hooks`；`options` 来自 `plugins.json` 该项的 `"options"`。
- 宿主只调用这些钩子：`config`（声明供应商/模型）、`auth`（`methods`/`loader`/`usage`/`refresh`/`checkin`）、`provider.models`（每账号拉模型）、`chat.headers`（会话头）。
- **模块导出的每个函数都被当插件工厂调用**——辅助函数只能挂 `export const _internal = {...}`。
- 配置目录 `~/.config/magpie/`：`plugins.json`（安装与 options）、`plugin-auth.json`（登录态，600）、`plugin-providers.json`（模型缓存）。

## 5 分钟最小插件

用 `scripts/new-plugin.sh` 从 `template/`（完整可跑的 provider 插件骨架，含逐行注释）生成并改名：

```bash
~/.agents/skills/magpie-plugin-dev/scripts/new-plugin.sh fooai "FooAI"   # 生成 ./opencode-fooai-auth，acme→fooai 全局替换
magpie plugin add ./opencode-fooai-auth             # 本地文件夹就地加载，不安装任何东西
magpie plugin login fooai                           # 触发登录方式
magpie provider test fooai                          # ✓ chat  7 ms · fooai-coder
magpie quota                                        # 账号额度窗口
```

也可以手动复制 `template/` 后把 `acme` 全局替换成厂商 id。四种安装来源都支持：`./文件夹`、`npm包名[@版本]`、`github:owner/repo`、`owner/repo` 简写。

## 开发-调试循环

**沙箱**（独立 HOME，不碰日常 magpie）。用本 skill 自带脚本一键初始化（封装了三个实测坑：市场开关、秒失败代理、Bun 运行时复制）：

```bash
source ~/.agents/skills/magpie-plugin-dev/scripts/sandbox.sh   # 定义 sb（沙箱路径）与 m()（包装函数）
m plugin add ./opencode-fooai-auth </dev/null    # ← 5 分钟流程生成的目录；手动复制的 template 则是 opencode-acme-auth
m plugin              # 账号/模型/加载错误都在 plugin 列表输出（--json 为机器可读格式）
m provider test fooai [model]   # ⚠️ 未登录时这里报 "no provider"——先 m plugin login fooai
m quota
```

⚠️ `source` 定义的 `m()` 只在同一 shell 会话存活——每条命令独立 shell 的环境（agent/CI）用单发模式：`~/.agents/skills/magpie-plugin-dev/scripts/sandbox.sh -- plugin --json`（配 `MAGPIE_SANDBOX=/路径` 复用同一沙箱）。

脚本细节：默认开启秒失败代理（`HTTPS_PROXY=http://127.0.0.1:1` 等，让 CLI 启动探测立刻回退而不是挂数分钟——magpie CLI 会联网拉 GitHub 插件市场，无代理时必挂）；自动从 `~/.cache/magpie/bun` 复制 Bun 运行时（全新沙箱没有它，`plugin` 命令会去 GitHub 下载并挂死）；加 `--online` 参数跳过代理、真联网测上游（接受启动可能挂几分钟）。就绪提示会打印当前代理模式，可用假二进制自检代理是否真的传到（`MAGPIE_BIN=/tmp/fake ./sandbox.sh -- env`）。

⚠️ 实测：非 TTY（管道）下登录 prompt 一律读不到输入——`password` 与 `text` 型都直接报 `no key on stdin: EOF`。脚本化验证登录不要走管道：按 `plugin-auth.json` 的存储形状直写登录态（api 型为 `{"<provider id>": {"type": "api", "key": "…"}}`，形状见 references/hooks.md；oauth 型含 access/refresh/expires），再跑 `provider test` 验全链路。

- 终端每条命令起独立宿主，文件夹插件总是加载最新内容——改完代码直接重跑。
- 常驻 magpie 应用的宿主：插件关掉再开（或重启应用）才重载。
- 单元测试：把纯函数挂 `_internal`，用 `bun test` / `node --test` 直接测；社区合规检查脚本在 magpie-community/plugins 仓库（`node …/magpie-community/plugins/scripts/check.mjs .`，模仿宿主加载每个包并检查钩子）。

## 文档地图（按需读）

| 要做什么 | 读哪个 |
|---|---|
| 钩子的完整契约（config/auth/loader/models/refresh/usage/checkin/宿主协议） | [references/hooks.md](references/hooks.md) |
| 实现登录（8 种模式：device code、loopback OAuth、CDP 拦截、读客户端文件、粘贴 Cookie、短信、扫码…） | [references/auth-patterns.md](references/auth-patterns.md) |
| 写模型清单（静态表/live 拉取/free-rate 判定）与 usage 额度窗口 | [references/models-usage.md](references/models-usage.md) |
| 排查"不报错但悄悄错"的问题 | [references/pitfalls.md](references/pitfalls.md) |
| 打包、测试、发布上架（npm / registry.json PR / GitHub topic） | [references/publishing.md](references/publishing.md) |
| 中间件 / hooks.js / 路由策略 / agent / 页面 / 工具插件 | [references/other-types.md](references/other-types.md) |

## 红线：最常见的静默失败

这些错的共同特征：**不报错，只是悄悄错**（完整清单与出处见 [references/pitfalls.md](references/pitfalls.md)）：

1. **usage `used` 缺省 = 0%** → 耗尽的账号在路由里排到队首（真实事故：0 余额账号 256 次被选中 255 次）。蹬空就画 `{used: 100}`。
2. **成功登录结果缺 `refresh` 字段** → 宿主不落盘，"登录成功但列不出账号"。兜底 `refresh: r.refreshToken || r.accessToken`。
3. **模型级错误回 401** → magpie failover 打遍所有账号并全部标登录失效。模型不可用用 403/404 带厂商原话。
4. **`capabilities.input.image` 省略 ≠ false** → magpie 去 models.dev 投票，截图直发被上游拒。
5. **oauth 型 authorize 直接返回账号**（不走 callback）→ 宿主挂在回调上。
6. **`resetsAt` 塞厂商原样时间格式** → 整条窗口被静默丢弃，卡片显示"剩余额度未知"。
7. **一次性 refresh token 并发双花** → 必须 promise 锁 / single-flight。

## 抄哪个范本

写同类插件时"从最接近的真实包改名起步"是官方推荐的路径：

| 范本 | 本机源码 | 适合抄什么 |
|---|---|---|
| agnes-code（OpenAI 兼容直连 + DPAPI/粘贴双登录，535 行） | `~/.config/magpie/plugins/node_modules/@magpie-community/opencode-agnes-code-auth/index.mjs` | 最小完整结构、依赖注入可单测、checkin 诚实语义 |
| cline（WorkOS device code + 讲究的 refresh/错误语义） | `~/.config/magpie/plugins/node_modules/@magpie-community/opencode-cline-auth/index.mjs` | OAuth 生命周期、错误映射、chat.headers |
| magpie-marvis（工程化全家桶） | `~/.config/magpie/plugins/node_modules/magpie-marvis/` | 一钩子一文件、quota 校验器、HOOKS 契约文档（包内） |
| today（逆向官方客户端协议） | `~/.config/magpie/plugins/node_modules/magpie-plugin-today-auth/` | 协议逆向注释法、WS+SSE 翻译、测试金字塔 |
| sub2api 接入（面向 OpenAI 兼容网关） | https://github.com/broven/magpie-sub2api | 按模型路由 API 方言、usage 窗口换算、Docker e2e |

GitHub 上还有 348 个打 `magpie-plugin` topic 的社区仓库可检索。

## 背景与边界

- 供应商 id 即 agent 引用前缀（`<id>/<model>`）；被内置占用时用 `<id>-plugin`。
- `magpie` 专有的 package.json 字段（icon/name/summary/maxConcurrency）对 OpenCode 无害。
- 插件能看到请求里的一切（对话、工具与结果）——只发到用户要求的地方，别记日志。
- npm 依赖可用但**不执行 install 脚本**；尽量零运行时依赖（16 个真实插件全部裸 `fetch` + `node:*`）。

## 验证清单（交付插件前逐项过）

- [ ] 沙箱 `m plugin add ./` 后 `m plugin` 列出 provider 与模型数（加载错误随 plugin 列表输出，`--json` 为机器可读）
- [ ] `m provider test <id> [model]` 真实打通一条 chat
- [ ] `m quota` 能看到窗口（有 usage 钩子时）；数值字段全部显式、时间是宿主可解析格式；**至少一条窗口可路由**——全 aside 的卡片显示正常但在路由里等于不存在（P21）
- [ ] models 钩子失败回退 `provider.models` 而非 `{}`（P23）；改写流式响应时已去掉 content-length/content-encoding（P25）
- [ ] 红线 1–7 逐条对照（见上文红线节与 references/pitfalls.md 的 P1–P25 全集）
- [ ] 登录流程真走一遍（非 TTY 管道喂不进 prompt——password 与 text 都报 EOF；脚本化验证按 `plugin-auth.json` 存储形状直写登录态再跑 provider test）
- [ ] 入口除插件工厂与 `_internal` 外无其他导出；`node --check` / `bash -n` 全部文件通过
- [ ] 模型不可用返回 403/404 而非 401；`capabilities` 不支持的模态显式声明为 false
- [ ] package.json：name 是 slug、keywords 含 `opencode` + `auth|plugin|provider`；README 写清登录方式与凭据存放
- [ ] （要上架时）对照 references/publishing.md 的上架检查清单
