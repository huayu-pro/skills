// 最小完整 provider 插件骨架 —— 复制本目录后把 "acme" 全局替换成你的厂商 id 即可起步。
// 直接可跑：magpie plugin add ./本目录 → magpie plugin login acme → magpie provider test acme
//
// 两条铁律：
// 1. 模块导出的【每个函数】都会被宿主当插件工厂调用 —— 辅助函数只能挂到 _internal。
// 2. magpie 只调用 config / auth(methods,loader,usage,refresh,checkin) / provider.models / chat.headers。

const PROVIDER = "acme"
const BASE = "https://api.acme.example/v1"

// ── 错误类：抛出它 = 告诉宿主登录态失效（不要对"模型不可用"用 401，见 references/pitfalls.md）──
class Expired extends Error {
  constructor(msg = "Acme 登录已过期，请重新登录") {
    super(msg)
    this.name = "Expired"
    this.signIn = "expired"
  }
}

// ── 模型清单：静态兜底表；live models 拉取失败时宿主保留它 ──
// limit.context/output 必填；tool_call 写对位置：静态模型用 tool_call（下划线），
// provider.models 返回的 OpenCode 形状用 capabilities.toolcall —— 写错位置静默为假。
const MODELS = {
  "acme-coder": {
    name: "Acme Coder",
    limit: { context: 200_000, output: 32_000 },
    reasoning: false,
    tool_call: true,
    // modalities: { input: ["text"] },   // 纯文本模型要显式声明 image 不可用，
    //                                    // 省略 ≠ false：magpie 会去 models.dev 投票
    cost: { input: 0, output: 0 }, // 套餐内不按量计费
  },
}

// ── 登录提示：type:"password" 是 magpie 专有（终端不回显）──
// ⚠️ 宿主只在方法声明了 prompts 时才把用户输入交给 authorize —— 想收输入就必须保留这个声明。
const KEY_PROMPT = {
  key: "apiKey",
  message: "Acme API key",
  type: "password",
  placeholder: "acme-…",
}

// ── 工厂函数：export 出来的函数都会被调用，所以只导出这一个 ──
export const AcmeAuthPlugin = async (input, options) => ({
  // ── 1. 声明供应商与静态模型；??= 防止覆盖用户与其他插件的配置 ──
  config: async (cfg) => {
    cfg.provider ??= {}
    cfg.provider[PROVIDER] ??= {
      name: "Acme",
      npm: "@ai-sdk/openai-compatible", // 决定网关把 agent 请求转换成哪种 API 方言
      api: BASE, // 除非 loader 另给 baseURL，否则请求发到这里
      models: MODELS,
    }
  },

  auth: {
    provider: PROVIDER,

    methods: [
      {
        type: "api",
        label: "Acme API key",
        // prompts 与 authorize 二选一：有 authorize 就自己校验/换 key。
        prompts: [KEY_PROMPT],
        async authorize(inputs) {
          const key = inputs?.apiKey?.trim()
          if (!key) return { type: "failed", error: "缺少 API key" }
          // 建议在这里打一次轻量校验端点，提前暴露错误而不是等第一次对话失败。
          const res = await fetch(`${BASE}/me`, { headers: { authorization: `Bearer ${key}` } })
          if (!res.ok) return { type: "failed", error: `key 无效（HTTP ${res.status}）` }
          const me = await res.json().catch(() => ({}))
          // ⚠️ oauth 型登录的 refresh 字段不能省：缺失时宿主把账号存成 type:"api" 且永不续期
          // （pitfalls P6）。本示例是 api 型——宿主按 {type:"api", key} 存储，无此问题。
          return { type: "success", key, accountId: me.email ?? "acme" }
        },
      },
    ],

    // ── 2. loader：该账号的每个请求经它发出。返回空对象 = 用宿主默认行为 ──
    async loader(getAuth) {
      const auth = await getAuth()
      if (auth?.type !== "api" || !auth.key) return {}
      return {
        baseURL: BASE,
        // 只加头时不必自定义 fetch：apiKey 会按 AI SDK 方式自动发（OpenAI 系是 Bearer）。
        apiKey: auth.key,
        async fetch(req, init) {
          const res = await fetch(req, init)
          if (res.status === 401) throw new Expired()
          return res
        },
      }
    },

    // ── 3. usage（magpie 专有）：额度窗口。写错字段不报错、只是悄悄错，逐字段对照文档 ──
    async usage(getAuth) {
      const auth = await getAuth()
      if (auth?.type !== "api") return { windows: [] }
      const res = await fetch(`${BASE}/usage`, { headers: { authorization: `Bearer ${auth.key}` } })
      if (!res.ok) return { error: `Acme answered ${res.status}`, windows: [] }
      const u = await res.json()
      // used 是百分比（0-100）。不知道就别传 —— 传 0 会被当成"没用"，耗尽的号反而排到队首。
      return {
        plan: u.plan,
        windows: [
          {
            name: "5 hours",
            used: u.percent,
            resetsAt: u.resets_at, // ⚠️ 必须是宿主可解析的 ISO 时间。本示例假设上游已返回 ISO；
            // 若厂商给"2026-10-28 23:59:59"这类原样格式，整条窗口会被静默丢弃（P2）——先转 ISO
            span: 5 * 3600,
            display: `${u.used} / ${u.limit} credits`,
            amount: u.used,
            limit: u.limit,
            unit: "credits",
          },
        ],
      }
    },
  },

  // ── 4. live models：拉取失败回退 provider.models（宿主保留上次列表）──
  provider: {
    id: PROVIDER,
    async models(provider, { auth } = {}) {
      if (auth?.type !== "api") return provider.models
      try {
        const res = await fetch(`${BASE}/models`, { headers: { authorization: `Bearer ${auth.key}` } })
        if (!res.ok) return provider.models
        const { data } = await res.json()
        const base = provider.models["acme-coder"]
        // 这里返回 OpenCode Model 形状：工具调用写 capabilities.toolcall（不是 config 静态
        // 模型的 tool_call——写错位置静默为假，见 pitfalls P11）；limit/cost 沿用静态表
        return Object.fromEntries(data.map((m) => [m.id, {
          id: m.id,
          name: m.name ?? m.id,
          limit: base.limit,
          cost: base.cost,
          capabilities: { reasoning: Boolean(base.reasoning), toolcall: true, attachment: false, input: ["text"] },
        }]))
      } catch {
        return provider.models
      }
    },
  },

  // ── 5. 会话透传（可选）：此头会原样发给上游（上游按它做会话粘缓存）。
  // 若做的是插件内部专用头（不发出网），在 loader 的 fetch 里取出后
  // headers.delete(...)——私有头不出网，见 references/hooks.md 第 8 节 ──
  "chat.headers": async (req, out) => {
    const id = req?.model?.providerID ?? req?.provider?.info?.id
    if (id !== PROVIDER || !req?.sessionID) return
    out.headers["x-magpie-acme-session"] = String(req.sessionID).slice(0, 128)
  },
})

// 测试要用的纯函数挂这里 —— 名字必须叫 _internal，宿主不会调用它。
export const _internal = { PROVIDER, BASE, MODELS, Expired }
