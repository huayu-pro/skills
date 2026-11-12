# 登录实现八式（auth 钩子实战模式）

**用途：实现 provider 登录时读本文——八种经过真实插件验证的登录方式、问答交互（prompts / ask）、token 写回与 refresh 纪律、头部与风控应对。** auth 钩子的字段级契约（methods/loader/usage/refresh 完整形状与字段表）见 `references/hooks.md`，本文件只讲「怎么实现登录」；usage 与模型声明见 `references/models-usage.md`。所有模式与代码形状摘自真实插件源码，出处随文标注（简称对照：agnes=`@magpie-community/opencode-agnes-code-auth`、cline=`…-cline-auth`、raccoon/catpaw/zcode/workbuddy/trae/qoder/loomy/orcaterm/autoclaw/codearts 同为 `@magpie-community/opencode-<名>-auth`；today=`magpie-plugin-today-auth`、tabbit=`magpie-tabbit-provider`、marvis=`magpie-marvis`、wps-lingxi=`@kevinfx/magpie-wps-lingxi`、vibex=作者自写插件）；标「整理」的代码块为缩略示意，字段名以 hooks.md 为准。

## 0. 选型决策树

按目标服务**能提供什么**选，实现成本从低到高：

```
服务有 OAuth / 设备码端点？
├─ 有 device code（RFC 8628）────────────────→ ① 设备码（无本地端口，最省事）
└─ 有 authorize/callback
    ├─ 允许 127.0.0.1 回调 ──────────────────→ ② loopback 回调服务器
    └─ 只许网页回调、无 loopback ────────────→ ③ 轮询 sid 或 ④ CDP 拦截
只有网页扫码/登录页 ─────────────────────────→ ④ CDP 拦截 或 ⑧ 扫码
有桌面客户端（凭证落在本机）──────────────────→ ⑤ 读客户端文件（零交互）
只有网页登录态、什么都拿不到 ────────────────→ ⑥ 粘贴凭证（万能兜底）
手机号 + 短信验证码体系 ─────────────────────→ ⑦ 短信验证码
```

| 方式 | 一句话 | 出处 |
|---|---|---|
| ① 设备码 | 轮询 RFC 8628 token 端点 | cline `deviceSignIn` |
| ② loopback | 本地 HTTP 服务器接 OAuth 回调 | raccoon / autoclaw / workbuddy / trae |
| ③ 轮询 sid | 无本地服务器，按 sid 查登录态 | catpaw |
| ④ CDP 拦截 | 浏览器请求阶段截回调 | marvis / wps-lingxi |
| ⑤ 读客户端文件 | 继承桌面客户端登录态 | agnes / raccoon / catpaw / tabbit |
| ⑥ 粘贴凭证 | 用户交 cookie/token，正则提取 | vibex / raccoon / catpaw / loomy / today / wps-lingxi |
| ⑦ 短信验证码 | `method:"code"` 两阶段 | loomy / today / autoclaw CN |
| ⑧ 扫码 | 网页扫码 + postMessage 回 code | orcaterm |

- 一个插件可以同时声明多个 methods：catpaw 同时提供网页轮询与粘贴凭证，raccoon 同时提供 loopback OAuth 与粘贴。挑对用户最无感的做主路径，其余兜底。
- `type:"api"`（用户直接填 API key）最简单，形状见 `references/hooks.md`；本文讲的都是有流程的登录。

## ① 设备码（WorkOS 系）

**适用场景**：服务实现了 RFC 8628 设备码授权（`/device/authorize` + `/device/token`）。
**出处**：`@magpie-community/opencode-cline-auth` 的 `deviceSignIn`。

实现要点：

- `authorize` 返回 `{ url, instructions, method: "auto", callback }`，宿主向用户展示 `url` 与说明，然后调用 `callback` 等结果。
- `callback` 里轮询 token 端点，**严格按 RFC 8628**：`authorization_pending` 继续等；`slow_down` 把轮询间隔按规范递增；5xx 与非 JSON 响应区别对待——5xx 重试，非 JSON 说明端点行为变了，报错。
- cline 拿到 WorkOS 的 JWT 后并不直接使用，再调 Cline 自己的 `/auth/register` 换成自家 token 对。

```js
// cline deviceSignIn（整理）：authorize 返回的形状
const authorizeReturn = {
  url: verification_uri,
  instructions: "在浏览器打开链接并确认设备码",
  method: "auto",
  callback: async ({ signal }) => {
    // RFC 8628 轮询：pending → 等待；slow_down → 递增间隔；5xx 重试
    // 拿到 provider JWT → POST /auth/register 换自家 token 对
    return { type: "success", access, refresh, expires, accountId, uid }
  },
}
```

⚠️ **坑**：`slow_down` 不递增间隔会越轮越快直至被拒。症状：用户已在浏览器确认，CLI 仍一直 pending 或报错。判据：轮询循环没有处理 `slow_down` 响应。修法：按 RFC 递增间隔，5xx 重试、非 JSON 报错。

## ② Loopback OAuth 回调服务器

**适用场景**：OAuth provider 允许 `http://127.0.0.1:<port>` 作为 redirect_uri。
**出处**：raccoon（`node:http` + 127.0.0.1 随机端口 + 64 位 hex 随机 state + authorize URL 带 `desktop_callback=loopback`）；autoclaw（**固定端口池** `[18432, 19654, 19723, 53699]`——官方客户端只在这几个端口被白名单）；workbuddy / trae 同类。

实现要点：

- 本地起 HTTP 服务器接住浏览器回调：`authorize` 返回 `{ url, method: "auto", callback }`，`callback` 里等回调请求、校验 state、拿 code 换 token。
- raccoon：随机端口 + 每次登录重新生成的 64hex state。
- autoclaw：端口不能随便选（上游按端口识别官方客户端），维护固定端口池逐个尝试绑定。

```js
// raccoon 式 loopback（整理）
let pending            // callback 请求到达时 resolve(code) 的 Promise
const server = createServer((req, res) => { /* 校验 state → 取 code → 唤醒 pending */ })
await listen(server, 0, "127.0.0.1")    // 随机端口
const redirectUri = `http://127.0.0.1:${server.address().port}/callback`
// authorize URL 拼上 redirect_uri、state(64hex)、desktop_callback=loopback
// authorize 返回 { url, method: "auto", callback }；callback 里 await pending → 换 token
```

⚠️ **端口选择不是实现细节**。autoclaw 用随机端口会被上游拒绝（官方 client 只白名单那 4 个端口）；反过来，服务没有白名单时固定端口容易撞占用。判据：浏览器回调页报错、或上游报 redirect_uri 无效。修法：有白名单就用白名单端口池逐个试，没有就随机端口。
⚠️ **state 必须每次登录重新随机**（raccoon 64hex）——复用 state 会把上一个登录会话的回调错配到当前账号。

## ③ 轮询 sid（无 loopback）

**适用场景**：服务只有网页登录页，redirect 不可控，但提供「凭 sid 查登录态」的端点。
**出处**：catpaw。

实现要点：

- 先调 `login-config` 拿网页登录入口 URL；
- 拼 URL 带上自己生成的 `sid` 和 `redirect: http://127.0.0.1:9/catpaw-callback`——9 端口是 discard，**不会有任何东西在监听**，浏览器跳过去报错也无所谓；
- `callback` 里每秒调 `poll-token?sid=...` 直到拿到 token（3 分钟超时）。
- catpaw 注释：这个做法免疫浏览器的 private-network 检查——因为根本没有本地服务器，浏览器不需要访问 localhost。

```js
// catpaw（整理）
const authorizeReturn = {
  url: loginUrl, instructions, method: "auto",
  callback: async ({ signal }) => {
    const deadline = Date.now() + 3 * 60_000
    for (;;) {
      const r = await fetch(`${base}/poll-token?sid=${sid}`, { signal })
      if (ok(r)) return finish(await r.json())
      if (Date.now() > deadline) return { type: "failed", error: "登录超时" }
      await sleep(1000)
    }
  },
}
```

⚠️ **redirect 别指向真实监听的端口**——那会把流程搅成方式 ②，还要处理 private-network 预检；catpaw 特意用不可达端口让重定向死在浏览器里，插件只认 sid。

## ④ CDP 浏览器拦截

**适用场景**：只有网页登录/扫码页，没有 sid 轮询端点，需要直接从浏览器截获回调。
**出处**：magpie-marvis 的 `openIsolatedLogin`；wps-lingxi 的 `chromiumLogin` / `safariLogin`。

实现要点（marvis）：

- 用**一次性 profile** 启动浏览器（不碰用户日常 profile 的 cookie），伪装 UA，抹掉 `navigator.webdriver`；
- 用 CDP 的 `Fetch.requestPaused` 在**请求阶段**拦下回调——code 在到达服务器前被插件收走，浏览器不会把它消费掉（否则网站会把这次 code 当网页端登录用掉）；
- `authorize` 返回 `{ url, opened: true, method: "auto", callback }`：`opened: true` 告诉宿主「页面我自己已经开了」，抑制宿主事后重复开页。

实现要点（wps-lingxi）：本地起一个引导页，内嵌微信 `qrconnect` iframe，扫码完成后从 iframe 跳转里取 code；chromium 与 safari 两套驱动分开实现。

```js
// marvis openIsolatedLogin（整理）
const method = {
  async authorize(inputs, { signal }) {
    const page = await openIsolatedLogin()  // 一次性 profile + 伪装 UA + 抹 navigator.webdriver
    // CDP: Fetch.requestPaused → 命中回调 URL 时取 code 并拦截（请求阶段）
    return { url: authorizeUrl, opened: true, method: "auto", callback }
  },
}
```

⚠️ **不抹自动化痕迹会被风控或污染用户会话**：不用一次性 profile 会把插件登录和用户日常 cookie 混在一起；不抹 `navigator.webdriver` 会被识别为自动化登录。
⚠️ **拦截必须在请求阶段**。症状：浏览器页面显示登录成功、插件却报 code 无效。判据：在响应阶段才拦截，code 已被浏览器消费过一次。修法：改用 `Fetch.requestPaused` 在请求到达服务器前截获。

## ⑤ 本机客户端文件读取

**适用场景**：服务有桌面客户端且登录态落在本机文件，用户已用桌面端登录过——插件零交互「继承」登录。
**出处**：agnes（Windows DPAPI）、raccoon（多候选路径）、catpaw（mtime 重读）、tabbit（macOS Cookie 解密）。

实现要点：

- 返回形状 `{ url: "", instructions, method: "auto", callback }`：`url` 留空（不需要开网页），`instructions` 说明「将复用桌面客户端登录态」。
- agnes：桌面端是 Electron，token 经 safeStorage 加密（Windows DPAPI + AES-256-GCM）；插件起 PowerShell 子进程解 DPAPI（15s 超时），主密钥缓存复用。
- raccoon：读 `~/.office-raccoon` 或 `~/.box-agent/.../auth.json` 等多候选路径；`sameAccount()` 校验文件身份，防止读到别人的账号。
- catpaw：读 `~/.meituan-catpaw/auth.json`，记录 mtime，文件变化时实时重读（桌面端可能中途刷新 token）。
- tabbit：`desktopSignIn` 走 macOS Cookie 库解密。

```js
// agnes 式（整理）
const authorizeReturn = {
  url: "", instructions: "将复用已登录的桌面客户端", method: "auto",
  callback: async () => {
    const raw = JSON.parse(await readFile(authPath, "utf8"))
    const plain = await dpapiDecrypt(raw.encrypted)   // PowerShell 子进程 + 15s 超时
    return { type: "success", ...toAccount(plain) }
  },
}
```

⚠️ **文件里的账号未必是你该用的账号**——本机文件可能装着别人的登录态，直接采信会串号（raccoon `sameAccount()` 的存在就是防这个）。
⚠️ **文件内容会变**：桌面客户端自己刷新 token 后，内存里的副本就成了旧 token——catpaw 用 mtime 触发重读。
⚠️ **子进程必须设超时**（agnes 15s）：卡死的 PowerShell 会把登录流程挂死。

## ⑥ 粘贴凭证

**适用场景**：以上都不可行时的万能兜底——用户从 devtools / 已知位置复制 cookie / token 粘贴进来。
**出处**：vibex（整段 Cookie）、raccoon（三态解析）、catpaw / loomy / today / wps-lingxi（token / session / cookie）。

实现要点（vibex）：

- prompt 让用户粘贴**整段 Cookie**，兼容三种粘贴物：整个 `document.cookie`、devtools 里的请求行、裸 token 值；
- 正则提取 `Rh-Accesstoken` / `Rh-Refreshtoken`；对 JWT 做 exp 校验，当场判「已过期」而不是等第一次请求失败。

实现要点（raccoon）：`parseCallbackInput` 三态解析——回调链接（含 code）/ 裸 JWT / JSON 文本，一个 prompt 兜住多种用户习惯。

```js
// vibex 式（整理）
const pasteMethod = {
  type: "oauth", label: "粘贴凭证登录",
  prompts: [{ type: "password", key: "cookie", message: "粘贴整段 Cookie" }],
  authorize: async (inputs) => {
    const pair = extractTokens(inputs.cookie)     // 正则 Rh-Accesstoken / Rh-Refreshtoken
    assertFresh(pair)                             // JWT exp 校验
    // oauth 型必须包 callback，凭证已到手也一样（见下方坑）
    return { url: "", instructions: "", method: "auto",
             callback: async () => ({ type: "success", ...toAccount(pair) }) }
  },
}
```

⚠️ **oauth 型方法必须 `{ url: "", method: "auto", callback }` 并在 callback 里交结果**——在 authorize 里直接 return 账号，宿主会挂在一个永远不会到来的 callback 上（catpaw:1100 与 loomy:373 有相同注释）。症状：登录 UI 永久转圈、无任何输出。修法：凭证已到手也包一层 callback。
⚠️ **先做结构校验再提交**（vibex 的 exp 校验、raccoon 的三态解析）——用户粘错内容的报错要落在「请检查粘贴内容」，而不是上游 401 被当成登录过期。

## ⑦ 短信验证码

**适用场景**：手机号 + 短信验证码体系。
**出处**：loomy（两阶段）、today（`requestPhoneCode`）、autoclaw CN。

实现要点（loomy 两阶段）：

- `authorize` 里先调上游 `sendMsgCode` 发短信、拿到 `msgid`；
- 方法标 `method: "code"`，宿主据此弹验证码输入框，用户输入后以 `callback(code)` 回来；
- `callback(code)` 里用 `msgid + code` 调 `checkCode` 完成登录。

实现要点（today）：`requestPhoneCode` → `method: "code"`；**校验码字段名是 `code` 不是 `otp`**。

```js
// loomy（整理）
const smsMethod = {
  type: "oauth", label: "手机号登录",
  prompts: [{
    type: "text", key: "phone", message: "手机号",
    validate: (v) => (normalizePhone(v) ? undefined : "请填写 11 位中国大陆手机号"),
  }],
  authorize: async (inputs) => {
    const msgid = await sendMsgCode(inputs.phone)          // authorize 只发起，不等用户
    return {
      url: "", instructions: "输入短信验证码", method: "code",
      callback: async (code) => {
        const r = await checkCode(inputs.phone, msgid, code)
        return { type: "success", ...toAccount(r) }
      },
    }
  },
}
```

⚠️ **authorize 里只能「发起」，不能「等待」**：发短信可以放 authorize，等用户输入必须走 callback——在 authorize 里 await 用户会与宿主双向死锁（marvis 连 `findBrowser()` 查注册表的 1.4 秒都挪进了 callback；详见 `references/pitfalls.md` 登录类）。
⚠️ `password` 类型 prompt 是 magpie 专有（终端不回显、应用内掩码）；验证码用 `text`，密钥粘贴用 `password`。

## ⑧ 扫码

**适用场景**：服务登录页是「微信 / APP 扫码」。
**出处**：orcaterm（WeChat OAuth QR）。

实现要点：

- orcaterm 用微信 OAuth 二维码 + `self_redirect: true`（扫码后页面在 iframe 内自跳转），页面 `postMessage` 把 code 送回插件；
- 其余同 ②/④：`{ url, method: "auto", callback }`，callback 里等 code 换 token。

```js
// orcaterm（整理）
const qrMethod = {
  url: qrPageUrl, instructions: "用微信扫码", method: "auto",
  callback: async ({ signal }) => { /* 等 postMessage 的 code → 换 token */ },
}
```

⚠️ **成功结果缺 `refresh` 字段时，宿主只把它存成 `type:"api"`、永不续期**（orcaterm #675）——症状：「登录成功但列不出账号」「用几天就失效」。修法：`refresh: r.refreshToken || r.accessToken` 兜底，字段宁可有占位也不要缺。同类问题见 `references/pitfalls.md` 登录类。

## prompts 与 ask(inputs)：多步问答

**静态 prompts**（authorize 前依次提问；项的形状）：

```js
// prompts 项的形状：type ∈ select | text | password（password 是 magpie 专有）；
// when / condition 二选一做条件出现；validate 返回 undefined=通过、字符串=错误提示
const promptItem = {
  type: "select", key: "region", message: "Region",
  placeholder: "", options: [], when: null, condition: null, validate: (v) => undefined,
}
```

- `password` 是 magpie 专有类型：终端不回显、应用内掩码显示。
- `validate` 返回 `undefined` = 通过，返回字符串 = 错误提示。loomy 例：

```js
validate: (v) => (normalizePhone(v) ? undefined : "请填写 11 位中国大陆手机号")
```

- `select` 例（zcode）：

```js
const endpointPrompt = { type: "select", key: "endpoint", message: "选择接入点",
  options: [{ label: "Z.ai", value: "zai", hint: "z.ai" }] }
```

**动态 ask(inputs)**（出处：vibex）：auth 方法可提供 `ask(inputs)`，宿主决定下一个问题时**优先调它**（没有才回落到静态 `prompts`）；每次调用返回下一个 prompt，返回 `null` 表示问完了。vibex 用它实现「首次没有答案时自动打开官网」：

```js
// vibex（整理）：挂到 auth 方法上的 ask(inputs)
const askHook = {
  async ask(inputs) {
    if (!inputs?.token) {
      spawn("xdg-open", [officialUrl], { stdio: "ignore", detached: true }).unref()
      return { type: "password", key: "token", message: "已打开官网，登录后粘贴 token" }
    }
    return null
  },
}
```

⚠️ **即使用了 `ask`，`prompts` 声明也必须保留**——宿主只在 `m.prompts?.length` 为真时才给 `authorize` 传 `inputs`；删掉 prompts，authorize 拿到的 inputs 永远是 undefined，多步逻辑形同虚设。判据：authorize 里 inputs 为 undefined，用户明明答过问题。
⚠️ **没有 prompts 的方法，authorize 收到 `undefined` 而不是 `{}`**（marvis 包内 HOOKS 契约文档陷阱 2）——authorize 开头做 `inputs ??= {}`。

**AbortSignal**：`authorize(inputs, { signal })` 与 `callback(code, { signal })` 都接收 signal（用户取消登录时宿主 abort）——长轮询/长等待必须把 signal 透传给 fetch，否则取消后轮询还在跑。

**成功 / 失败返回**：

```js
function settle(ok) {   // authorize / callback 的两种返回
  if (ok) return { type: "success", access, refresh, expires, accountId, uid,
                   /* 自由字段一并保存：phone、cardName、mainConversationId、deviceId、source … */ }
  return { type: "failed", error: "…" }   // error ≤ 500 字符
}
```

- `accountId` 是**显示名**（列表里给人看的），`uid` 是**去重身份**（判断是不是同一账号）。宿主 whoOf 回退链：`accountId → metadata.email → email`；API key 登录没有 accountId 时，宿主显示 key 末 4 位。
- 多账号存储：第一个账号存 provider id，后续账号 `id#xxxxxx`；重登时 accountId 相同则**替换**旧账号（两边都有 uid 时还要求 uid 一致）。

## token 存储与写回

**写回宿主**（raccoon `saveAuth` / vibex / workbuddy 同款）：

```js
await client?.auth?.set?.({ path: { id: PROVIDER_ID }, body: next })
```

⚠️ **`client.auth.set` 可能失败，必须 try/catch 包住**。cline 的对策是内存链：store 写失败后 `getAuth` 会一直交回旧 token，于是维护 `held: Map<spentRefreshToken, newestPair>`——每个花掉的 refresh token 对照它自己链上的最新一对，防止一个插件实例服务多账号时串号。
⚠️ **「宿主仍持有旧 auth 对象」竞态**：refresh 刚写回，宿主手里还攥着旧 auth 对象又发起新请求。vibex 用 `renewedHere` Map：按旧 token 查「是不是我这里刚续过」，是就直接复用新 token，不对上游发起第二次续期。

串号是 token 存储的头号事故源：一个插件实例可能同时服务多个账号（id 形如 `id#xxxxxx`），任何「按 provider 存单份」的模块级状态都会把 A 账号的新 token 发给 B 账号的请求。workbuddy 的对策是每账号独立落盘 `<plugin>-<site>__<account>.json`（详见 `references/pitfalls.md` 并发与状态类）。

## refresh 实现纪律

**1. 返回值是合并，不是替换。** refresh 钩子返回的字段合并进旧记录：漏给 `accountId` 等字段意味着沿用旧值——上游换发新显示名时卡片名改不回来。真实事故：CodeArts 0.2.4 把 `principal_urn` 写进 accountId。写 refresh 返回时显式重申全部 UI 字段。

**2. refreshLead 的真实取值**（量级参考）：cline 5 分钟（请求前自查）+10 分钟（宿主预续期）、vibex 1 小时、raccoon 5 分钟、marvis 1 天。太小则续期请求频繁打上游，太大则赶不上过期。

⚠️ **`expires` 为 0 或缺失的账号，宿主永不续期**——即使你提供了 refresh 钩子。症状：账号从不自动续、到期直接失效。修法：登录成功结果里给真实过期时间戳。

**3. 一次性 refresh token 必须串行化。** cline 注释：「refresh token 是一次性的，两请求同时续期会花掉一个丢一个」：

```js
// cline：promise 链锁
const locked = fn => { const run = lock.then(fn, fn); lock = run.catch(()=>{}); return run }
```

raccoon 用 `renewing` / `renewed` Map 做 single-flight（60 秒内同 key 复用）；qoder 的新 token 对立刻写回（「Qoder spends a refresh token once, so the new pair is saved straight away」）。marvis 的上游 refresh 成对轮换、旧 token 立即失效，同样一花即废——不加锁必然偶发全账号掉线。

**4. 过期要给出宿主认识的信号。** loomy / raccoon / catpaw 用同一个错误工厂，cline 用 `class Lapsed extends Error`：

```js
const expired = (msg) => Object.assign(new Error(msg), { signIn: "expired" })
```

宿主据此把账号标成「需重新登录」，而不是当成普通请求失败重试。

**5. 没有 refresh 端点就别硬凑。** catpaw / loomy / orcaterm-wechat / agnes-桌面 都不提供 refresh 钩子——上游不给续期端点，过期 = 重新登录，比假装有 refresh、实际静默失败好。tabbit 上游无刷新端点，7 天后重登；today 是 1 小时短 JWT + auth.refresh 自动续期（但设备不注册 WS 握手会报 4003）。

**6. 特例**：marvis 的 uskey 同一值从第 3 次请求起必 403（上游配额限制而非风控）——每次请求前在本地现签一个新 uskey（毫秒级、不联网）。

## 头部与风控应对速查

上游按「客户端指纹」放行/拒绝是常态。真实插件的做法一览：

| 插件 | 做法 | 细节 |
|---|---|---|
| cline | 完整复刻官方 CLI 头 | `CLIENT = {type:"cline-cli", version:"3.0.68", platform:"cli", core:"0.0.90"}` → `X-CLIENT-TYPE` / `X-CLIENT-VERSION` / `X-PLATFORM` / `X-CORE-VERSION` / `HTTP-Referer` / `X-Title` / `User-Agent`；每任务加 `X-Task-ID`（sessionID 的 sha256 造 UUIDv4）。免费模型门禁读这些头，版本号要与官方当前发布对齐 |
| catpaw | 网关头 + 不伪造不可得头 | `gatewayHeaders`：`User-Agent: axios/1.19.0`、`m-appkey: com.sankuai.mcopilot.cli`、双 trace id；capture 里的 `m-host` 是 LAN IP，「不是能从别处真实发送的值，所以整个头省掉而不伪造」 |
| workbuddy | 每站点一套头 | UA 不对直接被拒（error 10085）；每个 SITES 带自己的 `app` / `cli` / `appName` 头集合 |
| zcode | 设备指纹 + 提示词指纹 | `X-Device-Mid`：确定性 UUID（`uuidOf(sha256(seed))`，同 key 同 id）；`prompt.mjs` 逐字节内嵌 ZCode CLI 3.17.2 系统提示词（SHA-256 前 16 位自检）——上游按提示词指纹放行 Start Plan 请求（11-03 起 405/3012「unusual activity」） |
| loomy | 签名头 | 九段 `\n` 拼接的 HMAC-SHA1 签名 + `Content-MD5`（注释自认「这是客户端指纹复刻，不是安全边界」）；`Content-Type: application/json;charset=utf-8` 是 load-bearing——没 charset 上游按 GBK 解码，CJK 全烂 |
| qoder | 私有信封 | COSY envelope + RSA 公钥加密 + 专有 body codec（从 CLIProxyAPI 移植） |
| marvis | 签名有路由边界 | `Ual-Access-MarvisExt`（uskey + qimei36 本地生成，无需官方 SDK/DLL）。签名只用于 `/v3/*` 业务接口，`/v1/chat/completions` 不需要——加错地方会把「403 风控」变成「401 登录态过期」 |
| catpaw | 身份字段轮换 | `source: "CatPawCLI"` 被上游 11-01 停用（`{code:400, msg:"source 不存在或未启用"}`）→ 换桌面端身份 `BODY_IDENTITY = Object.freeze({source:"CatX", mode:"CATX_APP"})`，round/turn 共享同一冻结对象防漂移 |

三条通用纪律：

1. **能真实计算的头就算出来；不能真实复现的头整个省掉，不要伪造**（catpaw 对 `m-host` 的处理）。
2. **签名头加在正确的路由上**（marvis 的 /v1 与 /v3 边界）——加错地方，风控 403 会被误判成登录过期，触发全账号 re-auth。
3. **身份字段（source / appkey / UA）上游随时会换**——监控 400 类「source 不存在」响应，出现就查上游客户端更新（见 `references/pitfalls.md` 上游对抗观察清单）。

## 登录态调试速记

```bash
# 沙箱：独立 HOME/缓存 + 关市场（不关会联网拉 GitHub 插件市场，无代理挂几分钟）
sb=$(mktemp -d)
m() { env HOME=$sb XDG_CONFIG_HOME=$sb/.config XDG_CACHE_HOME=$sb/.cache \
      MAGPIE_ADDR=127.0.0.1:3499 MAGPIE_PLUGIN_MARKET=off magpie "$@"; }

m plugin --json                            # 方式/账号/模型/加载错误（机器可读格式）
m plugin add ./你的插件文件夹 </dev/null    # 沙盒里装本地文件夹插件
```

- 终端里每条命令起独立宿主（文件夹插件总是最新内容）；应用内测试则关掉再开插件即重载；`magpie plugin on/off` 对本地插件认路径。
- ⚠️ 无代理环境的离线沙箱技巧（秒失败代理 + 复制 Bun 缓存）与 `password` prompt 非 TTY 的 EOF 坑，见 `SKILL.md` 开发-调试循环与 `references/pitfalls.md` §8 排查表。
- ⚠️ `pkill -f magpie` 会误杀用户正在运行的 magpie 应用（进程名 `~/.local/bin/magpie`）——调试别用全局 pkill。

---

插件骨架与目录结构见 `SKILL.md` 与 `template/`；静默失败清单（缺字段不落盘、死锁、串号）见 `references/pitfalls.md`；非 auth 型插件见 `references/other-types.md`。
