# 宿主钩子全契约

本文逐项给出 magpie 插件可实现的全部宿主钩子的契约：插件工厂形状、`config`、`auth`（methods/loader/refresh/checkin）、`provider.models`、`chat.headers`、`input.magpie.load`、失败与登录状态语义、PluginInput 映射与宿主调试协议。写插件前先读 `SKILL.md`，起步代码直接用 `template/`。OAuth 流程与 prompts 问答细节见 `references/auth-patterns.md`；模型清单与用量窗口纪律见 `references/models-usage.md`；静默失败全集见 `references/pitfalls.md`；发布见 `references/publishing.md`。

## 1. 插件形状与导出规则

插件是一个跑在 magpie 共享 Bun 宿主里的 Node 包。模块导出的**每个函数**都被宿主当作插件工厂调用：

```js
async (input, options) => hooks
// input:   { client, project, directory, worktree, serverUrl, $, experimental_workspace }
// options: plugins.json 中该项的 "options"，没有则 undefined
// hooks:   { config?, auth?, provider?, "chat.headers"? }
```

导出规则：

- 辅助函数**不能**放模块顶层导出——任何导出的函数都会被宿主当工厂调用。只给测试用的内部函数放 `export const _internal = {...}`。
- 宿主优先识别 `export default { id, server }`（OpenCode v1 形状）；存在时按 OpenCode 插件处理，其余具名导出再逐个尝试。
- 四个钩子全部可选，按需返回。

⚠️ 多账号作用域：宿主对每个账号各调用一次工厂函数，每次调用都在**该账号的作用域内**。不要用「以供应商 id 为键的模块级变量」保存账号状态（token、配额缓存等）——多账号时会互相串号。账号状态一律经 `getAuth()` / `client.auth.set` 读取与保存，或挂在本次调用的闭包里。

`input` 各字段在 magpie 里的实际语义见第 10 节的 PluginInput 映射表。

## 2. config 钩子：注册供应商与模型

`config` 钩子在宿主 `init` 阶段运行；magpie 会把**所有插件的 config 依次跑完**再定稿（`client.config.get` 拿到的就是这份定稿）。

```js
config: async (cfg) => {
  cfg.provider ??= {}
  cfg.provider["acme"] ??= {        // ??= 防止覆盖用户/其他插件已写的配置
    name: "Acme",
    npm: "@ai-sdk/openai-compatible",  // 决定 API 协议
    api: "https://api.acme.example/v1",
    models: {
      "acme-coder": {
        name: "Acme Coder",
        limit: { context: 200000, output: 32000 },
        tool_call: true,
      },
    },
  }
}
```

模型键名是插件内部使用的 id；模型字段一览：

| 字段 | 说明 |
|---|---|
| `id` | 上游 API 接受的模型 id，与键名不同时填 |
| `limit` | `{ context, output }` |
| `reasoning` | 是否推理模型 |
| `tool_call` | 是否支持工具调用 |
| `modalities` | `{ input: ["text", "image"] }` |
| `cost` | `{ input, output, cache_read }`，$/百万 token；套餐制可不填 |
| `variants` | 推理档位 |
| `provider` | `{ npm, api }`——该模型走与供应商不同的 API 协议/地址 |
| `headers` | 该模型的额外请求头 |
| `options` | 透传给 AI SDK 的选项 |
| `disabled: true` | 禁用 |
| `status: "deprecated"` | 不显示 |

### npm 包 → API 方言映射

`npm` 字段决定 loader 的 `fetch` 收到的请求格式（magpie 网关已把 AI SDK 调用转换成对应方言）：

| npm | API | 路径 |
|---|---|---|
| `@ai-sdk/anthropic`、`@ai-sdk/google-vertex/anthropic` | Anthropic Messages | `/messages` |
| `@ai-sdk/openai`、`@ai-sdk/azure` | OpenAI Responses | `/responses` |
| `@ai-sdk/google` | Gemini | `/models/<id>:streamGenerateContent?alt=sse` |
| `@ai-sdk/github-copilot` | GPT-5+ 用 Responses，其余 chat completions | |
| 其他（openai-compatible/xai/groq/deepseek…） | Chat completions | `/chat/completions` |

基地址优先级：loader 返回的 `baseURL` → 模型的 `provider.api` → 供应商的 `api` → AI SDK 默认。

请求体的 `model` 字段 = 模型的 API id：模型写了 `id` 用 `id`，否则用键名。

## 3. auth 钩子：登录方式与账号管理

完整形状：

```js
const auth = {
  provider: "acme",     // 登录信息存放在此供应商 id 下
  methods: [],          // 登录方式，见 references/auth-patterns.md
  loader,               // 见第 4 节
  usage,                // 见 references/models-usage.md
  refresh, refreshLead, // 见第 7 节
  checkin,              // 见 references/models-usage.md
  icon: "",
  maxConcurrency: 4,    // 账号并发上限
}
```

要点（OAuth 全流程见 `references/auth-patterns.md`）：

- `methods` 可混合两种方式：`[{ type: "api", label, placeholder }]` 或 `{ type: "oauth", label, authorize }`。
- `api` 方式没有 `authorize` 时，key 原样存为 `{ type: "api", key, metadata? }`；prompts 的回答进 `metadata`。
- `oauth` 的 `authorize(inputs)` 返回 `{ url, instructions, method: "auto"|"code", callback }`；`callback` 成功返回 `{ type: "success", refresh, access, expires: Date.now() + expires_in * 1000, accountId }`，失败返回 `{ type: "failed", error? }`（error ≤ 500 字符）。
- `prompts`（authorize 前向用户提问）：`[{ type: "select"|"text"|"password", key, message, placeholder?, options?, when?/condition?, validate? }]`。`password` 是 magpie 专有（OpenCode 没有）。
- 全程支持 AbortSignal：`callback(code, { signal })`、`authorize(inputs, { signal })`。
- 多账号存储：第一账号存供应商 id 本身，其余存 `id#xxxxxx`；重新登录时 accountId 相同则整体替换；显示名依次取 accountId → `metadata.email` → email。

## 4. loader：每账号的请求配置

```js
const loaderHook = {
  async loader(getAuth, provider) { /* 每账号调用一次；登录信息变化后重跑 */ },
}
```

每账号调用一次，登录信息变化后重跑。返回对象的四个字段全部可选：

| 字段 | 用法 |
|---|---|
| `baseURL` | 优先于模型/供应商的 `api` |
| `apiKey` | 按 AI SDK 方式发送：Anthropic 用 `x-api-key`，Google 用 `x-goog-api-key`，其余 `Authorization: Bearer`。api 登录时默认就是保存的 key |
| `headers` | 加到每个请求 |
| `fetch` | 自定义发请求函数；不提供则用标准 fetch |

### fetch 契约

自定义 `fetch(input, init)` 收到：

- `input`：完整 URL；
- `init.headers`，按序覆盖：① `apiKey` 对应的头 → ② loader `headers` → ③ 网关请求头 → ④ `chat.headers` 钩子的头；
- `init.body`：该 API 方言的 JSON（见第 2 节映射表）；
- `init.signal`：agent 放弃时中止。

返回的 `Response` 原样流式传回给 agent。

⚠️ 要在 fetch 里改写流式响应正文时，必须去掉 `content-length` / `content-encoding` 头，否则流解析会错位或挂起。

### 最小直连型 loader

`@magpie-community/opencode-agnes-code-auth`（535 行的包）的核心 loader 精要——API 型登录时把保存的 key 直接交给 AI SDK：

```js
const agnesLoader = {
  async loader(getAuth) {
    const auth = await getAuth()
    if (auth?.type !== "api" || !auth.key) return {}
    return { baseURL: CHAT_GATEWAY_BASE, apiKey: auth.key }
  },
}
```

需要 OAuth 刷新、网关转发、多账号轮换的 loader 写法见 `references/auth-patterns.md`。

## 5. 失败语义与登录状态

- 非 2xx 一律按厂商的回答处理：限流/5xx → magpie 转下一账号或模型；401 → 标记该账号登录失效。
- 账号没有某个模型的权限时，用 403/404 并带上厂商原话，**别用 401**——401 会把整个账号标记为登录过期，而不是把该模型按「被拒」处理。

响应头 `X-Magpie-Sign-In` 精确控制登录状态（magpie 转发给 agent 前会去掉它）：

| 值 | 含义 |
|---|---|
| `expired` | 登录已被上游拒绝，标记账号过期 |
| `kept` | 这个 401 是别的问题（如配额），不清登录态 |
| `renewed` | 插件已续期，清除过期标记 |

在 `fetch` 或 `provider.models` 里抛出带标记的错误，效果相同：

```js
throw Object.assign(new Error("Acme 拒绝了登录"), { signIn: "expired" })
```

由此引发的静默失败案例（如把模型级 403 错标成登录过期）见 `references/pitfalls.md`。

## 6. provider.models：动态模型清单

`provider` 钩子返回 `{ id, models }`；`models(provider, { auth } = {})` 按账号拉实时清单：

```js
const providerHook = {
  id: PROVIDER,
  async models(provider, { auth } = {}) {
    if (auth?.type !== "api") return provider.models
    try {
      const res = await fetch(`${BASE}/models`, { headers: { authorization: `Bearer ${auth.key}` } })
      if (!res.ok) return provider.models        // 失败时 magpie 保留原列表
      const { data } = await res.json()
      const base = provider.models["acme-coder"] // 入参条目是 config 写入的形状
      // ⚠️ 返回值必须是 OpenCode Model 形状：工具调用写 capabilities.toolcall
      //（不是 config 静态模型的 tool_call——写错位置静默为假，见 pitfalls P11）
      return Object.fromEntries(data.map((m) => [m.id, {
        id: m.id,
        name: m.name ?? m.id,
        limit: base.limit,
        cost: base.cost,
        capabilities: { reasoning: Boolean(base.reasoning), toolcall: true, attachment: false, input: ["text"] },
      }]))
    } catch { return provider.models }
  },
}
```

返回 OpenCode `Model` 对象：`id`/`name`、`api: { id, url, npm }`、`limit: { context, input?, output }`、`capabilities: { reasoning, toolcall, attachment, input }`、`cost: { input, output, cache: { read, write } }`、`variants`、`release_date`、`status`。

**magpie 额外读取**的字段（OpenCode 忽略）：

| 字段 | 含义 |
|---|---|
| `free: true` | 唯一被认可的免费判定字段 |
| `rate` | 倍率，数字或 `"x0.5"`；0 视为未给出 |
| `rateWas` | 优惠前倍率（划线价） |
| `serviceTiers` | 如 `["priority", "ultrafast"]`；选中的 tier 以 `service_tier` 到达 fetch |

**magpie 专有供应商能力**：

- `searches: true`——上游托管联网搜索；
- `decide: true` + 模型 `decides: true`——System One 路由分类器，`POST {baseURL}/systemone`；标记 `decides` 的模型对智能体隐藏。

失败回退（三者等价，都保留上次列表）：

1. 返回 `provider.models`；
2. 抛异常；
3. `list[Symbol.for("magpie.fellBack")] = true`。

清单常量的组织方式、free/rate 判定纪律、canonical id 映射见 `references/models-usage.md`。

## 7. auth.refresh：自动续期（magpie 专有，v0.1.684+）

```js
const refreshHook = {
  refreshLead: 5 * 60 * 1000,   // expires 前多久续期，默认 5 分钟
  async refresh(auth, provider) {
    const t = await exchange(auth.refresh)
    if (t.error === "invalid_grant")
      throw Object.assign(new Error("Acme 拒绝了登录"), { signIn: "expired" })
    return {
      access: t.access_token,
      refresh: t.refresh_token ?? auth.refresh,
      expires: Date.now() + t.expires_in * 1000,
    }
  },
}
```

行为规则：

- OAuth 账号的 `expires` 距 `refreshLead` 以内时，在 loader / models / usage / 请求前运行；`expires` 为 0 或缺失则不续期。
- **单飞**：并发请求触发续期时只执行一次（保护一次性 refresh token），最多等 15 秒。
- **合并语义**：返回字段与账号原有登录信息**合并**（同名覆盖），保留其余字段——与 `client.auth.set` 的整体替换不同。
- 续期失败保持旧 token 继续用；其他错误 30 秒后重试。

⚠️ OpenCode 与旧版 magpie 忽略此钩子。插件要跨宿主运行时，`fetch` 内部的「token 快过期先刷新」检查必须保留，不能只依赖 refresh。

## 8. chat.headers：会话透传头

把 magpie 侧的会话上下文透传出去（上游配额统计、会话亲和等）：

```js
const chatHeadersHook = {
  "chat.headers": async (input, output) => {
    const id = input?.model?.providerID ?? input?.provider?.info?.id
    if (id !== PROVIDER || !input?.sessionID) return
    output.headers["x-magpie-acme-session"] = String(input.sessionID).slice(0, 128)
  },
}
```

⚠️ 只用于插件内部传递、不应出网的私有头，在 loader 的 `fetch` 里取出后要 `headers.delete(...)` 删掉——私有头不出网。

## 9. input.magpie.load：上报模型负载

用于「繁忙的模型靠后」路由。插件自行定期拉上游负载并上报：

```js
const report = async () => {
  const r = await fetch(`${BASE}/load`).then((r) => r.json()).catch(() => null)
  if (r) input.magpie?.load?.("acme", { "acme-large": r.large, "acme-small": r.small })
}
report()
setInterval(report, 60_000)  // 5 分钟内须再报，否则负载变未知
```

规则：百分比从 0 起，100 = 满载，可超过 100（上限 10000）；模型 id 不分大小写；一次最多上报 1000 个模型。

## 10. PluginInput 映射与宿主实际调用的钩子

`input`（即 OpenCode 的 PluginInput）各字段在 magpie 里的语义：

| 字段 | 在 magpie 里 |
|---|---|
| `client.auth.set` / `.remove` | 保存/删除当前作用域账号的登录信息 |
| `client.app.log` | 写 magpie 日志 |
| `client.tui.showToast` | 写日志 |
| `client.config.get` | 所有插件 config 跑完后的配置 |
| 其他 `client.*` | 返回 `{ data: undefined }` |
| `directory`、`worktree` | magpie 配置目录（可存文件） |
| `project` | `{ id: "magpie", worktree }` |
| `$` | Bun shell |
| `magpie.option` / `.options` / `.load` | 用户设置的插件选项、模型负载上报 |

magpie **只调用**这些钩子：

- `config`
- `auth` 的 `methods` / `loader` / `usage` / `refresh` / `checkin`
- `provider.models`
- `chat.headers`

OpenCode 的 tool / event / chat.params 等钩子不会被调用。唯一例外是 tool——经 MCP 暴露，见 `references/other-types.md`。

## 11. 供应商 id 规则

- agent 以 `<id>/<model>` 引用模型，`<id>` 就是 `auth.provider`（即 config 里 `cfg.provider` 的键）。
- 目标 id 被内置订阅/预设或 google/openai/anthropic 等占用时，改用 `<id>-plugin`。
- **例外**：社区为已弃用内置订阅做的兼容插件用内置 id（cursor、zed 等）。
- 两个插件登录同一 id 时由用户选定的插件提供；`magpie plugin use <插件名> <id>` 切换。

## 12. 宿主协议摘要（调试用）

magpie 与共享 Bun 宿主通过 stdin/stdout 交换 JSON 消息：magpie 向宿主 stdin 写 `{id, method, params}`，宿主回 `{id, result}` 或 `{id, error: { message }}`。

方法（节选）：

| 方法 | 说明 |
|---|---|
| `init` | 运行所有 config 钩子；其他调用等它完成 |
| `providers` / `prompt` / `validate` | 配置查询与校验 |
| `authorize` / `callback` / `apiKey` | 登录流程 |
| `load` | 模型负载上报 |
| `fetch` | 代理一次上游请求（流式，见下） |
| `usage` / `check` | 用量与签到 |
| `import` / `take` / `signOut` / `reload` | 账号导入 / 取出 / 登出 / 重载 |

`fetch` 是流式的：宿主收到 `{id, event: "head", status, headers}` → 若干 `{id, event: "chunk", data}`（base64）→ 结束帧 `{id, result: null}`；取消用 `{method: "abort", params: {id}}`。

宿主主动事件：`log`、`toast`、`auth`、`signIn`。

官方实现在 magpie 源码 `internal/plugin/host.js`。调试插件时可直接观察这段协议，确认钩子是否被调用、参数是什么。
