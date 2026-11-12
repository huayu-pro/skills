# 其他插件类型速查

provider/auth 插件之外，一个包还可以（或只能）是：网关中间件、异步请求钩子、路由策略、Agent 接入、窗口页面、工具、pi 扩展。**一个包可兼具多种**——官方示例插件就同时是 provider + 中间件。package.json 里的声明方式见 [publishing.md](publishing.md)。

## 网关中间件（*.middleware.js）

agent 发给网关的每个请求在路由前经过它，回复在返回路上也经过；对所有供应商生效。

⚠️ **不在 Bun 里跑**，而在 magpie 网关进程的 Go JS 引擎 moejs：只能相对导入插件目录内文件、**无 node_modules、无定时器/fetch/Node API**；每秒检查文件变化热重载。

```js
// alias.middleware.js —— 放包根或 package.json "magpie": { "middleware": "./mw.js" }
export const events = ["message_start"]          // 可选：只收这些事件
export function onRequest(body, ctx) {
  ctx.state.asked = body.model                   // ctx.state 每请求独立，钩子间共享
  if (body.model === "fast") body.model = "deepseek/deepseek-chat"
  if ((ctx.options.blocked ?? []).includes(body.model)) return ctx.reject(403, "not this model")
  return body                                    // 返回对象=替换，undefined=保留
}
export function onEvent(ev, ctx) { ev.message.model = ctx.state.asked; return ev }  // 返回 null 丢事件
```

钩子表：`onRequest(body,ctx)`（可 `ctx.reject(status,msg)` 改路由）、`onAccount(account,ctx)`（返回 `{skip:true}` 跳过账号；`account.ref` 是匿名化标识，每中间件不同）、`onProvider(body,ctx)`（已路由定，不能再拒）、`onEvent(event,ctx)`、`onResponse(body,ctx)`。

- 选项经 `ctx.options`（`magpie plugin options <名> '<json>'`）。
- 超时：请求/回复 250ms、事件 50ms、加载 1s；出错按不存在处理。
- 社区现成范例：`@magpie-community/middleware-think-tags`（去 `<think>` 标签）、`@magpie-community/middleware-model-map`（正则换模型）、`@magpie-community/middleware-param-override`。

## 异步网关请求钩子（*.hooks.js）

`"magpie": { "hooks": "./hooks.js" }` 或添加 `*.hooks.js/.mjs/.ts` 文件（纯网关插件不需要 main/exports）。跑在 **Bun**（不是 moejs），位于中间件之前：

```js
export async function onRequest(body, ctx) {
  const recalled = await recallProjectContext(ctx.query)   // 可等外部 I/O
  return { ...body, system: [...(body.system ?? []), recalled] } ?? undefined
}
export function onResponse(reply, ctx) { /* 尽力通知，不改回复 */ }
```

- ctx 含 `protocol/model/stream/path/agent/session/cwd/query/options/signal`（query 是最后一条用户文本，无 Authorization）。
- ⚠️ 改模型/流式/工具的改动会被回滚算失败。每钩子默认 1 秒（`gatewayTimeoutMs` 100–10000），链预算 2–10 秒。
- `ctx.report(code, bytes)` 只接受 `ready/empty/unbound/unauthorized/unavailable/invalid/skipped`。

## 路由策略与用量钩子（*.gateway.js / "magpie": {"gateway": "./gw.js"}）

```js
// 策略成为路由选项：magpie group set fast routing=<插件名>/<策略名>
export const strategies = {
  spread: (pool, seats, options) => [座位下标顺序],   // 20ms 超时
}
export function onUsage(row, options) { /* 每请求结束的用量记录，独立运行不阻塞，250ms */ }
```

座位字段：`key/account/known/learns/used/soon/pace/weight/resting/tokens`。社区范例 `@magpie-community/middleware-reserve`（额度用尽换号 / 订阅优先）。

## Agent 插件（*.agent.js）

给 magpie 没有内置接入的 Agent 做接入——声明模型写在哪个文件，magpie 把网关地址 + key + 选定模型写进它的配置，关掉即还原：

```js
export const agent = {
  id: "aider", name: "Aider", bin: "aider",
  config: "~/.aider.conf.yml", model: "model", prefix: "openai/",
  ua: ["aider", "litellm"],                        // 识别该 agent 的 UA
  notice: "Aider reads its settings when it starts: restart it.",
  format: "yaml",                                  // json/yaml/env
  library: { instructions, mcp, mcpFormat, skills },  // 接资源库
}
export function connect({ gateway, model }) {
  return { "openai-api-base": gateway.v1, "openai-api-key": gateway.key, "show-model-warnings": false }
}
```

`connect({gateway, model, models, agent})` 可 async；gateway 有 `url/v1/key`。⚠️ 与内置 Agent 同 id（codex、claude 等）会被拒；agent 也跑在 moejs（需要定时器等的包可另带 Bun main）。社区范例 `@magpie-community/agent-aider`。

## 窗口页面（page / panels / actions）

在 magpie 窗口加 HTML/CSS/JS 页面——**无需 Bun、无需构建**：

```js
// package.json: "magpie": { "page": { "title": "用量一览", "file": "./page.html",
//                                        "titles": {"zh": "用量一览", "en": "Usage"},
//                                        "replaces": "usage" } }
```

⚠️ 页面跑在 `sandbox="allow-scripts"` 沙盒 iframe（独立 origin，`connect-src 'none'`）——**没有 fetch/WebSocket，脚本必须独立文件不能内联**。只通过 `_magpie/bridge.js` 通信：

```html
<script src="_magpie/bridge.js"></script>
<script>
  const theme = await magpie.ready                       // {dark, lang, tokens} + --magpie-* CSS 变量
  const s = await magpie.read("usage:summary", { period: "today" })
  const opts = await magpie.options.get()                // 每秒最多一次
  await magpie.options.set({ ...opts, hideCost: true })
</script>
```

- `magpie.read` 只允许 `magpie.permissions` 声明的读取，目前有 `usage:summary`、`providers:list`；**任何读取都不给密钥/账号/登录信息/请求内容**。
- `magpie.panels`：slot `agents/usage/settings/provider`，最多 8 个，`magpie.context` 给 `{provider:{id,name}}`。
- `magpie.actions`：provider/agent 右键菜单项，最多 8 个，页面用 `magpie.onAction` 处理。
- `replaces` 可替代内置页面（`sessions/library/routing/usage` 之一）。只有页面的插件不启动宿主。
- 社区范例 `@magpie-community/page-usage`（Usage Glance）。

## 工具插件（tool 钩子 → MCP）

OpenCode `tool` 钩子提供的工具自动组成 magpie 的 MCP 服务器 `/mcp/magpie/tools`（Streamable HTTP），任何支持 MCP 的智能体可接入；工具名 `<插件>_<工具>`；每工具最长 55 秒：

```js
import { tool } from "@opencode-ai/plugin"
export const WeatherTools = async () => ({
  tool: {
    now: tool({
      description: "某个城市现在的天气。",
      args: { city: tool.schema.string().describe("城市") },   // tool.schema 就是 zod；也接受 JSON Schema
      async execute({ city }, ctx) {
        const r = await fetch(`https://wttr.in/${encodeURIComponent(city)}?format=3`, { signal: ctx.abort })
        return await r.text()                                  // 文本；对象按 JSON 发回
      },
    }),
  },
})
```

```bash
claude mcp add --transport http magpie-tools http://127.0.0.1:3425/mcp/magpie/tools
```

提供工具的插件在资源库 MCP 页成为独立服务器；可按插件「对智能体隐藏」。社区范例 `@magpie-community/tools-calc`（零依赖离线计算器，官方推荐的抄写起点）。

## pi 扩展包兼容

判定：package.json 有 `pi` 清单 / `pi-package` keyword / 依赖 `@earendil-works/pi-coding-agent`。magpie 自动装 pi 并用 pi 自己的加载器在同一宿主加载；`pi.registerProvider` 注册的供应商直接成为 magpie 供应商（模型接收 Anthropic Messages）。OAuth 按 pi 方式（onPrompt 变 magpie 提问、onAuth 开浏览器、refreshToken 续期）。pi 文件放 magpie 配置目录的 `pi/` 下。每次登录一个账号，支持多账号。

## 系统级能力字段（provider 插件的高级项）

- `searches: true`（供应商级）——上游自己执行托管联网搜索（Anthropic/OpenAI 官方 API），客户端的 WebSearch 原样转发。
- `decide: true` + 模型 `decides: true`——提供 System One 决策 API 作路由分类器：magpie `POST {baseURL}/systemone`，请求 `{"model","questions","state"}`，回答 `{"model","answers":{"<问题>":{"choice","score","confidence"}}}`。标了 decides 的模型对智能体隐藏。
- `input.magpie.load(provider, loads)`——上报模型负载（0-100+），用于「繁忙的模型靠后」路由，5 分钟内须再报。详见 [hooks.md](hooks.md)。
