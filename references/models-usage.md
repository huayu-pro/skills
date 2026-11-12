# 模型清单与用量窗口纪律

本文汇总 16 个真实插件中模型清单的四种组织形状、live 拉取与回退模式、free/rate 判定纪律、canonical id 映射，以及 usage 窗口的四种形态与路由纪律、checkin 的诚实语义。钩子本身的调用契约（何时被调、回退语义、字段表）见 `references/hooks.md`；OAuth 与多账号见 `references/auth-patterns.md`；静默失败全集见 `references/pitfalls.md`。

## 1. 模型常量的四种形状

（16 个真实插件源码剖析归纳，按写死程度递减）

### 形状 1：带 capabilities 的全文常量表（bootstrap 表 + live 覆盖）

`@magpie-community/opencode-agnes-code-auth` 用 `BOOTSTRAP` 表做离线兜底，live 拉取成功后覆盖。表行是 `{ id, context, output, thinking }`，`bootstrapRows()` 展开成完整模型对象：

```js
const model = {
  id, name,
  limit: { context, output },
  reasoning: thinking,
  tool_call: true,
  modalities: { input: ["text", "image"] },
  capabilities: { reasoning: thinking, toolcall: true, attachment: true, input: ["text"] },
}
```

### 形状 2：紧凑对象表（vendor 原生 id）

- `@magpie-community/opencode-catpaw-auth` 的 `MODELS`：`{ "longcat-2.0": { name, type: 77, image: true } }`——`type` 是上游数字模型 id；
- `@magpie-community/opencode-zcode-auth` 的 `MODELS`：`{ id, context, output, efforts: ["low", "high", "max"] }`；
- `@magpie-community/opencode-workbuddy-auth` 的 `CN_MODELS`：`[id, name, context, efforts]` 四元组数组，运行时展开。

### 形状 3：FALLBACK 数组 + 运行时构造

`@magpie-community/opencode-raccoon-auth` 维护一份 `FALLBACK_MODELS`（`{ id, name, context, output, images, reasoning, rate, free, rateWas }`），两个构造函数分别服务两个钩子：

- `configModels()`——config 钩子用的 magpie 简写形状；
- `runtimeModel()`——provider.models 钩子用的 OpenCode 内部 `Model` 形状。

⚠️ config 钩子与 models 钩子要求的模型对象形状不同（magpie 简写字段 vs OpenCode `Model`），同一份常量要各写一个构造器，不要混用。

### 形状 4：live-only

`magpie-plugin-today-auth` 完全不写死模型表——「一律从 /v1/pricing/status 现拉，不猜」，只留一条兜底：

```js
const fallbackModel = { id: "today", name: "Today AI（账号当前档位）" }
```

适用于模型集合完全随账号档位变化的供应商；代价是离线/上游失败时只剩兜底模型。

## 2. live 拉取与回退模式

各插件的模式高度一致：

```js
const modelsHook = {
  async models(provider, { auth } = {}) {
    try {
      const rows = await fetchLiveModels(token)        // 带账号凭证
      return Object.fromEntries(rows.map((r) => [r.id, modelOf(r)]))  // 或 { ...静态表, ...live }
    } catch {
      return provider.models                           // 回退到上次列表
    }
  },
}
```

实测变体：

- raccoon：`catalogCache`，TTL 10 分钟；
- catpaw：按 token 缓存 5 分钟；负命中（拉取失败）时返回旧缓存而不是空表；
- `@magpie-community/opencode-codearts-auth`：live 端点 401/403 时 `throw { signIn: "expired" }`——把「登录失效」与「网络失败」区分开（401/403 纪律见 `references/hooks.md` 第 5 节）；
- catpaw 的 models 是**合并**而非替换：静态表的 rate/free 让位给 live，用户自定义配置永远保留；
- `@magpie-community/opencode-trae-auth`：读列表里各模型的 max 窗口，给 `id + "MAX"` 单列一个模型。

## 3. free / rate 判定纪律

⚠️ 重灾区。只认厂商自己的声明，不猜：

- **`free` 不能从 `rate === 0` 反推**。qoder 有 38 个模型 rate 为 0 但实际吃套餐额度（marvis 文档实锤）；只认厂商声明免费的方式——展示名含「免费」、`x0.0` 倍率、计费端点明说。
- qoder `freeOf`：`price_factor === 0` **且不在活跃促销中**才算免费；`rateOf` 同时产出 `rate`（现价）与 `rateWas`（划线原价，取 `before_promotion_price_factor` 或 `original_price_factor`）。
- ⚠️ qoder 上游字段有拼写错误：读 `raw.promotion ?? raw.prommotion`；`is_free` 在打折模型上恒为 true，不可信。
- loomy `splitRateSuffix`：从显示名的 `(x3.0)` 后缀解析倍率，需兼容全角括号。
- `magpie-tabbit-provider` 的 `isFree`：`model_access_type.startsWith("free")`。

`rate` 为 0 视为未给出（magpie 语义，见 `references/hooks.md` 第 6 节）。

## 4. canonical id 映射

上游 feed/catalog 的模型 id 与标准 catalog（models.dev）的 id 常不一致，映射要保守：

- cline：feed id `cline-pass/deepseek-v4.1-flash` 对应 catalog `deepseek/deepseek-v4.1-flash`。`inputsFor()` 先按完整 id 查，查不到再按 `bareOf`（去前缀、去 `:variant`）匹配，且**要求所有同名条目一致**才采用；否则返回 undefined，让 magpie 去问 models.dev。
- catpaw：用上游 `modelTypeId` 反查静态表，查不到再 slug 化。
- agnes：直接用上游 id，`member_only` 模型照列——免费账号会得到透明的 403，magpie 按模型被拒处理，不会误标登录态。

## 5. usage 窗口：四种形态与字段表

`usage(getAuth, provider)` 账号作用域调用；结果显示在账号卡片、`magpie quota`、`GET /v1/magpie/quotas`。顶层全字段可选：

```js
const usage = {
  plan: "Pro", user: "ada@example.com", until: "2026-11-01T00:00:00Z", renew: "auto",
  balance: "$12.40", error: "",
  windows: [{ /* 见下 */ }],
  resets: { count: 2, until: "…", byWindow: false, fiveHour: 1, weekly: 1 },
  signIn: "kept",
}
```

窗口四种形态（marvis `src/quota.mjs` 运行时校验器的归纳，引用官方 issue #468 / magpie v0.1.1934 机制）：

| 形态 | 必填字段 | 语义 |
|---|---|---|
| 占比型 | `used`（百分比） | 参与路由 |
| 数量型 | `amount` + `limit` 成对 | used 自动按 `amount/limit*100` 计算 |
| 钱包型 | `balance` + `unit` | 预付钱包，不写 used/limit |
| 文本型 | `textOnly: true` + `display` | 纯展示，路由跳过（没有 used 的窗口即文本） |

window 全字段：

| 字段 | 说明 |
|---|---|
| `name` | 窗口名 |
| `used` | 已用百分比；**不知道就别传，别用 0** |
| `resetsAt` | 重置时间；或 `resetSecs: 3600` |
| `span` | 窗口长度（秒），如 18000 |
| `display` | 展示文本，如 `"370 / 1000 credits"` |
| `amount` / `limit` / `unit` | 数量型三件套 |
| `model` / `models` / `notModels` | 统计范围：单个模型 / 精确列表 / 排除列表 |
| `aside` | `true`：只展示，路由不读 |
| `runsOutAt` / `runsOut` | 预计耗尽时间 / 秒数 |
| `balance` | 预付钱包余额（按 `unit`），不与 used/limit 同用 |

时间字段是 ISO 字符串或秒/毫秒时间戳。marvis 的 `toIso()` 能解 ISO、秒（<1e12 ×1000）、毫秒与厂商原样格式；解不了直接抛 `QuotaShapeError`——宁可构建期报错，不要让用户看到「剩余额度未知」。

### 两种实战范式

A. 可路由窗口：used 百分比 + amount/limit + display（`@magpie-community/opencode-qoder-auth` 的 parseUsage）：

```js
const win = {
  name: b.name,
  used: Math.min(100, (100 * used) / total),
  display: `${fmt(used)} / ${fmt(total)} ${unit}`,
  amount: used,
  limit: total,
  unit,
}
```

B. aside + display 文本（钱包/展示行，只展示不参与路由）：

```js
// agnes:   windows: [{ name: "积分", balance: balance.total_balance }]
// catpaw:  { name: "可用积分", used: 0, display: `${credit} credit`, aside: true }
// loomy:   { name: "每日赠送积分", used: 0, display: `${daily} credits`, aside: true }
```

顶层字段在真实插件里的用法：

- `plan`：qoder 的 userType、tabbit 的 `"Tabbit " + member_level`；
- `user`：账号卡片名——raccoon 用 `a.cardName || a.accountId`；
- `until`：套餐到期；`balance`：字符串（`"$12.40"` / `"6,291 积分"`）；`error`：错误行；
- `renew: "auto"|"off"`：today 按 `subscriptionState` 是否匹配 `/cancel/` 判定；
- `resets: { count }`：重置计数；窗口上可挂 `models` 精确列表。

⚠️ `aside: true` 的窗口**禁止**带 `amount/limit`——分母是余额本身，会永远显示剩余 100%。

⚠️ 整卡至少要有一条可路由窗口：`aside !== true` 且有 `used` 或 `balance`。全部 aside/文本会让该账号在路由里被当成不存在。

## 6. used 是路由输入：三条实证

（today `usage.mjs` 注释 + marvis 校验器）

1. 号被蹬空时**必须**画 `{ name: "额度", used: 100, display: "已用尽" }`——不画 = 没有参与路由的窗口 = magpie 认为它还有余量、继续排前面。真实事故：一个 0 余额账号 256 次路由被选中 255 次。
2. `breakdown.items[]` 是同一份额度的拆分，**一律 `aside: true`**——参与路由会把同一个号算两遍，额度一到整个号被摘掉。
3. 剩余文本要换算：上游给 `"12%"` 剩余 → `used = 100 - remaining`。

marvis 校验器规则清单（写 usage 前逐条过）：

- 四形态字段互斥：占比用 `used`；数量 `amount+limit` 成对；钱包 `balance+unit`；文本 `textOnly+display`；
- `aside: true` 禁带 `amount/limit`；
- 时间字段解不了就抛错，不静默吞掉；
- `usage()` 保证至少一条窗口可路由（`aside !== true && (used !== undefined || balance !== undefined)`）；
- 路由的 `allowanceOf` 跳过 `aside` 与文本窗口。

作者原话：「写错字段不会让插件崩，只会让用户看到『剩余额度未知』、让这个号在路由里被当成不存在——而插件作者从日志里什么都看不到。」

## 7. 真实案例精选

### qoder：SPENT_IN_TURN 多池子合成

plan credits、add-on、team shared 在一回合内依次消耗。`turn[]` 汇总「Total credits」合成一个窗口置顶（可路由），各池子分别 `aside: true` 展示。免费账号全 0 时补一条：

```js
const emptyWin = { name: "Credits", used: 100, display: "0 credits left" }
```

否则 magpie 显示「没额度」反而不知道账号是空的。

### zcode：plansOf 过滤到期套餐

区分 active/expired/pending；entitlement 的 bucket（`total_units` / `remaining_units` / `used_units` + `expires_at`）映射成窗口；过期剔除；`span` 从 entitlement `period` 或 `period_start`/`period_end` 推。

### raccoon：主备双端点 + grant 汇总

`/points/v1/balance` 403 时退 `/office/v3/setting_info`；`used = grantedFromBills - avail`（从 grant bills 汇总）；最早过期的批次算 `runsOutAt`/`runsOut`。⚠️ 分页 100 行上限会让 grant 汇总溢出视野——拉全量或接受误差要明确选择。

### cline：creditsOf 递归取数

余额形状未定型（`total/used`、`remaining` 或裸 count），递归收集两层内的数字字段再按别名列表 pick。教训原话：「window made of a count alone read as 0% used — its bar full」——只有裸数字的窗口会被读成已用 0%，进度条全满。

### lingxi：临时积分单独成窗

`remaining` 字段塞进窗口（非官方扩展）；`summarizeExpiring` 把 15 天内到期的批次单独汇总成一条「临时积分」窗口。

## 8. checkin：六态与诚实语义

每个北京日对每账号调用一次：

```js
const checkinHook = {
  async checkin(getAuth, provider) {
    const auth = await getAuth()
    const r = await claim(auth.access)
    if (r.already) return { outcome: "done" }
    return { outcome: "claimed", credit: r.points, streak: r.days, message: r.text }
  },
}
```

| outcome | 含义 |
|---|---|
| `claimed` | 签到成功，拿到了奖励 |
| `done` | 今天已签过。2xx 但无可领也算 done，不是 failed |
| `ineligible` | 账号不符合签到条件 |
| `inactive` | 无活动 |
| `captcha` | 不要试图解——用户去厂商应用签 |
| `failed` | 当天稍后再试 |

抛异常或返回表外 outcome 都按 failed 处理。

诚实语义：

- agnes 用**余额差**观测签到：「涨了记 claimed，没涨不谎称已签——宿主把 done 渲染成今日已签到，是没发生的断言」。
- tabbit 教训：上游在午夜日界答 `"success"` 但记到错的日期。「声称成功」必须用**重读状态**验证（`signed_today === true` 且日期等于本机今天），否则报 failed 让 magpie 当天重试。

## 9. ⚠️ 静默失败速查

本文件相关、最容易写错且不报错的点（完整清单见 `references/pitfalls.md`）：

- ⚠️ `free` 从 `rate === 0` 反推 → 免费标签落在一堆吃套餐额度的模型上（qoder 38 个反例）。
- ⚠️ 蹬空的号不画 `used: 100` → 路由继续优先选它（today 事故：0 余额账号 256 次被选 255 次）。
- ⚠️ `aside: true` 的窗口带 `amount/limit` → 永远显示剩余 100%。
- ⚠️ usage 全部窗口 aside/text → 账号在路由中「不存在」，用户却看得到卡片。
- ⚠️ breakdown 拆分窗口不加 aside → 同一额度算两遍，整个号被提前摘除。
- ⚠️ models 钩子失败返回 `{}` 而非 `provider.models` → 模型清单被清空。
- ⚠️ `used` 不知道时传 0 → 显示「没用过」且路由放行。
- ⚠️ checkin 上游答 success 不验证落账 → 显示已签但奖励没发，当天也不会重试。

---

相关文件：`SKILL.md`（总览与起步）、`template/`（可跑模板）、`references/hooks.md`（钩子契约）、`references/auth-patterns.md`（OAuth 与多账号）、`references/pitfalls.md`（静默失败全集）、`references/publishing.md`（发布）、`references/other-types.md`（tool 等非钩子导出）。
