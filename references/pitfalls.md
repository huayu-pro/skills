# 静默失败清单（pitfalls）

**用途：本清单收录的每一个坑都不产生任何报错、只是悄悄错——设计时对照预防、发布前逐条自查、「插件不报错但行为不对」时来这里找病根。** magpie-marvis quota.mjs 的注释是最好的概括：「写错字段不会让插件崩，只会让用户看到『剩余额度未知』、让这个号在路由里被当成不存在——而插件作者从日志里什么都看不到。」每条坑按「症状 → 判据 → 修法」组织并标注出处（编号 P1–P25 与源码剖析清单一致，可直接引用）；钩子契约见 `references/hooks.md`，登录实现见 `references/auth-patterns.md`。

## 0. 怎么用这份清单

- **设计时**：过一遍「usage/路由类」「登录类」，把「字段必须显式给」的纪律写进实现。
- **发布前**：按第 8 节排查表跑沙箱，对照自查清单。
- **排障时**：按症状检索本文件；判据告诉你去哪里验证；修法给出真实插件的做法与出处。

速查索引（编号 P1–P25，与源码剖析清单一致，可直接引用）：

| 编号 | 一句话 | 详见 |
|---|---|---|
| P1 | usage 缺 `used` → 耗尽账号排到队首 | §1 |
| P2 | `resetsAt` 原样字符串 → 窗口整条被丢 | §1 |
| P3 | `aside` 标在主额度上 → 假占比 100% | §1 |
| P4 | authorize 里 await 用户 → 双向死锁 | §2 |
| P5 | oauth 型 authorize 直接返回账号 → 宿主挂死 | §2 |
| P6 | 成功结果缺 `refresh` → 宿主不落盘 | §2 |
| P7 | refresh 漏 `accountId` → 卡片名错乱 | §2 |
| P8 | 模型级错误回 401 → failover 全账号标失效 | §4 |
| P9 | `config.models` 空 → "0 models" | §3 |
| P10 | `input.image` 省略 ≠ false → 截图直发被拒 | §3 |
| P11 | `toolcall`/`tool_call` 拼写错位 → 静默为假 | §3 |
| P12 | `free` 从 rate 0 反推 → 套餐模型被派发 | §1 |
| P13 | 一次性 refresh token 并发双花 | §5 |
| P14 | 包名不是 slug → 依赖解析失败 | §6 |
| P15 | 改代码不 bump version → bun 缓存无更新 | §6 |
| P16 | 入口导出辅助函数 → 被当插件工厂调用 | §5 |
| P17 | 无 prompts 时 authorize 收到 undefined | §2 |
| P18 | 多账号状态按 provider 存 → 串号 | §5 |
| P19 | usage 认证头弄错 → 活账号标 lapsed | §4 |
| P20 | checkin 谎报 done → 「今日已签到」 | §2 |
| P21 | 整卡全 aside/文本 → 路由里账号不存在 | §8 |
| P22 | breakdown 拆分不加 aside → 同额度双计 | §8 |
| P23 | models 钩子失败返回 {} → 模型清单清空 | §8 |
| P24 | 成功结果 expires 缺失/0 → 宿主永不续期 | §8 |
| P25 | 流式改写不去 content-length → 流错位挂起 | §8 |

## 1. usage / 路由类

usage 钩子的返回值直接驱动 magpie 的账号路由。四个静默坑：

⚠️ **P1：`used` 缺省 = 0%，耗尽账号排到队首**
- 症状：余额已耗尽的账号被反复选中，请求接连失败。
- 判据：usage 返回对象里没写 `used`（或等价占比字段）——缺省按 0% 处理。
- 出处：today 真实事故——一个 0 余额账号 256 次路由被选中 255 次。
- 修法：始终显式回填 `used`，0 和满额都要写。

⚠️ **P2：`resetsAt` 塞厂商原样字符串**
- 症状：额度卡片「剩余额度未知」，重置窗口整条丢失；`usage()` 本身无任何报错。
- 判据：`resetsAt` 是 `"2026-10-28 23:59:59"` 这类厂商原样格式——宿主解析失败就丢掉整条窗口。
- 修法：转成宿主可解析的时间格式再返回。

⚠️ **P3：`aside: true` 标在 amount / limit 上**
- 症状：占比永远 100%（假占比）。
- 判据：aside 窗口带 `amount/limit`——aside 是给钱包/展示行用的，分母变成余额本身 → 永远显示剩余 100%（marvis 校验器规则）。
- 修法：只有真正的旁支/展示行才 aside，且 aside 窗口禁止带 amount/limit。

⚠️ **P12：`free` 从 `rate === 0` 反推**
- 症状：开了 Free first 后，付费套餐模型被源源不断派发。
- 判据：把 `rate === 0` 的模型标成了 `free`——qoder 38 个模型 rate 0 但实际吃套餐额度。
- 修法：只有厂商明确声明的免费档才标 free；rate 0 ≠ 免费。

对照示例（整理；字段契约见 `references/hooks.md`）：

```js
function usageExample(toIso, resetTime, bad) {
  if (bad) // ❌ 缺 used、resetsAt 塞厂商原样格式：耗尽账号排队首 + 窗口整条被丢，usage() 无任何报错
    return { limit: 100, resetsAt: "2026-10-28 23:59:59" }
  // ✅ 数值显式回填（0 和满额都要写）、时间转成宿主可解析格式
  return { used: 100, limit: 100, resetsAt: toIso(resetTime) }
}
```

## 2. 登录类

⚠️ **P4：在 `authorize` 里 await 用户 → 与宿主双向死锁**
- 症状：登录 UI 卡死无响应。
- 判据：authorize 里有等待用户/外部事件的 await——宿主在等 authorize 返回，你在等用户，互相等死。marvis：连 `findBrowser()` 查注册表的 1.4 秒都必须挪进 callback。
- 修法：authorize 只「发起」（发短信、生成 URL、起服务器、开浏览器），一切等待进 `callback`。

```js
// ❌ authorize 里等用户：宿主等 authorize 返回、你等用户操作，双向死锁
authorize: async () => { await waitUserConfirm(); return account }
// ✅ authorize 发起即返回；等待放进 callback
authorize: async () => ({ url, instructions, method: "auto", callback: waitConfirmThenReturn })
```

⚠️ **P5：oauth 型方法 authorize 直接返回账号 → 宿主挂死**
- 症状：登录 UI 永久转圈。
- 判据：`type:"oauth"` 的 authorize 没有返回 `{url:"", method:"auto", callback}` 形状，而是直接返回账号——宿主会挂在一个不存在的 callback 上（catpaw:1100、loomy:373 相同注释）。
- 修法：oauth 型一律包 callback，凭证已到手也一样。

⚠️ **P6：成功结果缺 `refresh` 字段 → 宿主不落盘**
- 症状：「登录成功但列不出账号」。
- 判据：success 返回对象没有 `refresh` 字段（orcaterm #675；marvis 注释）。
- 修法：`refresh: r.refreshToken || r.accessToken` 兜底，字段宁可有占位也不要缺。

⚠️ **P7：refresh 返回漏 `accountId`（合并语义）**
- 症状：刷新一轮后卡片显示名错乱、改不回。
- 判据：refresh 返回值是**合并**进旧记录的——返回什么就覆盖什么，漏掉的沿用旧值。真实事故：CodeArts 0.2.4 把 `principal_urn` 写进 accountId。
- 修法：refresh 返回里显式重申 accountId 等全部 UI 字段；accountId 放显示名，别塞 urn。

⚠️ **P17：没有 prompts 的方法，authorize 收到 `undefined` 而不是 `{}`**
- 症状：authorize 里解构 inputs 抛错或字段全 undefined。
- 判据：方法没声明 `prompts`（marvis 包内 HOOKS 契约文档陷阱 2）；配合 `ask(inputs)` 时 prompts 也必须保留——宿主只在 `m.prompts?.length` 时才传 inputs。
- 修法：authorize 开头 `inputs ??= {}`；用 ask 也不删 prompts 声明（见 `references/auth-patterns.md`）。

⚠️ **P20：checkin 谎报 done → 宿主渲染成「今日已签到」**
- 症状：用户看到已签到、不再手动领，余额却一直没到账。
- 判据：checkin 在无法确认发放时返回了 done。agnes:471：「余额没涨 ≠ 已发放：无领取接口…不能报 done」；tabbit 上游有日界 bug，必须在签到后重读状态验证。
- 修法：done 只在验证发放后返回；验证不了就返回未完成状态。

## 3. 模型与能力声明类

⚠️ **P9：`config.models` 为空 → 卡片显示 "0 models"**
- 判据：静态配置没给 models 或给了空数组（源码注释称之为三条铁律之一）。
- 修法：loader 动态拉取失败时回落到非空静态清单。

⚠️ **P10：`capabilities.input.image` 省略 ≠ false → magpie 去 models.dev 投票**
- 症状：用户截图直发上游被拒。
- 判据：能力字段省略时宿主按 models.dev 的社区数据补齐——社区说该模型支持图片，你的纯文本上游就收到图。真实事故：CodeArts 8 个模型 4 天里 161 次截图直发上游全被拒。
- 修法：不支持就显式声明（TEXT_ONLY 模板显式写明），不要省略。

对照示例（整理）：

```js
// ❌ 省略 image：宿主去 models.dev 投票，纯文本模型被判为支持图片
capabilities: { /* input 里没写 image */ }
// ✅ 显式声明（TEXT_ONLY 模板的做法）
capabilities: { input: { image: false } }
```

⚠️ **P11：`toolcall` / `tool_call` 拼写错位 → 静默为假**
- 症状：模型明明支持工具调用，实际却收不到 tools。
- 判据：两种拼写各属一处——`toolcall` 是 provider.models 返回的 OpenCode 形状；`tool_call` 是 config 静态模型的写法。写错位置不报错。
- 修法：按数据来源对号入座，两处对照检查。

## 4. 错误语义类

⚠️ **P8：模型级错误回 401 → failover 打遍所有账号且全部标登录失效**
- 症状：一个模型不可用，整个 provider 的账号被集体标成需重登。
- 判据：模型不可用/不支持时返回了 401——401 的宿主语义是「登录态过期」。
- 修法：模型级问题回 403 或 404。额度耗尽同理是 403 而非封号（marvis）——按路由策略切账号，别标登录失效。

⚠️ **401/403 判定用宽松子串**
- 症状：偶发把活账号标成需重登。
- 判据：`msg.includes("token")` 这类判断。cline:618：「403 that happens to mention 'tokens' is not a lapsed sign-in」——**never a loose substring**。
- 修法：按精确短语/错误码白名单分类（见下方纪律）。

**错误码映射纪律**（cline `failure(status, text)` 为范本）：

```js
// cline failure 分类（整理）
// JSON envelope 抽 message，按精确短语/代码分类：
//   ENTITLEMENT_ERROR / 未订阅          → 403
//   insufficient_credits                → 429（可附充值链接）
//   401，或 403 且 /^(unauthorized|invalid[ _]token|…)$/ → 401（锚定正则）
//   429 / SPEND_LIMIT_EXCEEDED          → 429
```

- zcode `call()`：`{code,msg,data}` envelope，code 0/200 成功；错误带 `err.code`（限流 3002）与 `err.retryAfterMs`（读 Retry-After）。
- loomy 业务码白名单：`OK = "000000"`，`AUTH_CODES = Set(["020002", "100002"])`——白名单之外不要按认证错处理。
- vibex loader.fetch 错误分派：`Expired` → 401 + `X-Magpie-Sign-In: expired`；`/额度|quota|limit/i.test(msg)` → 429。
- 改写文案时**保持原 status**：loomy `retryableRefusal` 把「内容太长了」改写成 magpie 认识的「上下文超出长度限制」，status 原样带回。历史事故：曾按字数猜 502，导致 magpie 轮询全部账号后整轮 502。

通用原则：magpie 只认 status 与少数约定信号（如 vibex 的 `X-Magpie-Sign-In: expired` 头、loomy 系 `signIn: "expired"` 错误字段）。status 分类的输出直接是路由决策的输入——分类错一档，路由就错一轮；这正是不报错、只悄悄错的典型。

⚠️ **P19：usage 认证头弄错 → 活账号被标 lapsed**
- 症状：账号能正常对话，却被 magpie 标成登录过期。
- 判据：usage 请求用了错的认证头——catpaw 的 usage 认证头是 `X-Auth-Token` 而不是 `Cookie: X-Passport-Token`；usage 的 401 是 magpie 判账号过期的依据（「弄错不是表面 bug」）。
- 修法：usage 认证头与真实客户端逐字对齐，并与对话请求的头对照检查。

## 5. 并发与状态类

⚠️ **P13：一次性 refresh token 并发双花**
- 症状：偶发全账号掉线，无固定复现路径。
- 判据：两个请求同时触发续期，各花掉一个 refresh token（cline 注释：「refresh token 是一次性的，两请求同时续期会花掉一个丢一个」）。
- 修法：promise 链锁或 single-flight——cline `locked`（promise 链锁）、raccoon `renewing`/`renewed` Map（60 秒内同 key 复用）、qoder 新 token 对立刻写回；代码形状见 `references/auth-patterns.md` refresh 纪律。

⚠️ **P16：入口模块导出辅助函数 = 被当插件工厂调用**
- 症状：宿主加载入口时把辅助函数也执行一遍，报奇怪的加载错误或产生幽灵插件。
- 判据：宿主约定是「模块导出的每个函数都被当插件调用」，入口文件却 export 了非工厂函数。
- 修法：辅助函数挂 `_internal` 命名空间；非函数常量按 today 的惯例命名 `_pure`。

⚠️ **P18：多账号状态放「以供应商为键」的模块变量 → 串号**
- 症状：A 账号的请求拿到 B 账号的 token / 计数 / 设备 id。
- 判据：模块级变量按 provider 存单份，而一个插件实例可同时服务多个账号（workbuddy 教训）。
- 修法：状态键带上账号 id；workbuddy 的做法是每账号独立落盘 `<plugin>-<site>__<account>.json`。

串号有三个入口，排障时逐一排查：登录态继承错了本机文件（`references/auth-patterns.md` 方式 ⑤ 的 `sameAccount()`）、refresh 写回失败后旧 token 复发（`client.auth.set` try/catch 与 cline 的 held 链、vibex 的 renewedHere，见 auth-patterns 的 token 存储一节）、以及本条的模块级状态键。三处的共同修法一致：一切按账号 id 分桶，永不按 provider 存单份。

## 6. 包与工具链类

⚠️ **P14：`package.json.name` 不是 slug**
- 症状：安装或依赖解析失败。
- 判据：name 带空格或中文——它同时是 bun 依赖键与 node_modules 目录名。
- 修法：用纯 slug；改包名要三处同步：package.json + bun.lock + node_modules 目录。

⚠️ **P15：npm 源改代码不 bump version**
- 症状：改了代码、宿主行为没变。
- 判据：bun 按版本缓存，同版本号命中旧缓存。
- 修法：每次发布 bump version。另注意：`magpie plugin add xxx.tgz` 有 bug（把 tgz 当 JS import）——本地测试用文件夹直装（`magpie plugin add ./文件夹`）。

## 7. 上游对抗观察清单

上游会悄悄换身份要求与风控规则。已知案例（全部有出处）：

规律：值得持续监控的信号有三类——400 类「字段不存在/未启用」响应（身份字段被换）、特定路由突然 403/405（指纹与路由策略变化）、上游客户端发版（协议与身份字段的唯一权威来源）。每次上游客户端更新后，先 diff 官方请求样本再发版。

| 上游动作 | 症状 | 判据 | 修法 |
|---|---|---|---|
| 身份字段停用（catpaw：`source: "CatPawCLI"` 11-01 起停用） | 全部请求返回 `{code:400, msg:"source 不存在或未启用"}` | 上游客户端发版换了身份字段 | 换新身份（catpaw → 冻结对象 `{source:"CatX", mode:"CATX_APP"}`，round/turn 共享防漂移）；把 400 类响应纳入监控 |
| 提示词指纹风控（zcode：11-03 起 Start Plan 405 / 3012「unusual activity」） | 特定路由 405、错误码 3012 | 上游按系统提示词指纹放行 | 逐字节内嵌官方 CLI 提示词 + SHA-256 前 16 位自检 |
| charset 缺省按 GBK 解码（loomy） | CJK 字符全烂 | `Content-Type` 没带 `charset=utf-8` | 显式带 charset（load-bearing 头） |
| 签名值重复使用限制（marvis：uskey 同值第 3 次起 403） | 第 3 次请求起稳定 403 | 是配额限制而非风控 | 每请求本地现签新值（毫秒级不联网） |
| 上游字段拼写错误（qoder：`prommotion`） | 按正确拼写发的字段被上游忽略 | 对照上游真实请求样本 | 错拼写也要读/发 |
| UA 门禁（workbuddy：error 10085） | 请求被直接拒绝 | UA 与官方客户端不符 | 每个 SITES 带自己的 `app`/`cli`/`appName` 头集合 |
| 拒绝客户端路由（cline：2026-11-06 起拒 `providerOptions`，403） | 带路由选项的请求 403 | 上游不再接受客户端自带路由 | 报错提示用户关选项，不重试 |
| 额度超限只报 400 不说明原因（wps-lingxi） | 偶发 400，无字段说明 | 上游按请求体大小拒 | 客户端预算裁剪：掐长条（单条上限）→ 丢最老历史（system 保留）→ 保 tool_calls/result 配对 → 插压缩标记 |

## 8. 其他静默失败（细则在对应文件，此处入册编号）

这五条原本散落在 hooks / models-usage / auth-patterns 里，因同样"不报错、只是悄悄错"入册统一编号：

⚠️ **P21：usage 整卡全部 aside/文本 → 账号在路由里"不存在"**
- 症状：卡片显示正常，magpie 却从不把请求派给这个号。
- 判据：所有窗口 `aside: true` 或无 used 的文本窗——路由的 `allowanceOf` 全部跳过。
- 修法：至少一条可路由窗口（`aside !== true` 且有 used 或 balance）；细则见 `references/models-usage.md` 第 5 节。

⚠️ **P22：breakdown 拆分窗口不加 aside → 同一额度算两遍**
- 症状：额度一到整个号被提前摘除。
- 判据：同一份额度的拆分条目参与了路由。
- 修法：拆分条目一律 `aside: true`；细则见 `references/models-usage.md` 第 6 节。

⚠️ **P23：models 钩子失败返回 `{}` 而非 `provider.models`**
- 症状：上游 models 端点偶发失败后，模型清单被清空。
- 判据：catch/非 2xx 分支返回了空对象而不是入参 `provider.models`。
- 修法：失败一律回退 `provider.models`（magpie 保留上次列表）；细则见 `references/models-usage.md` 第 2 节。

⚠️ **P24：登录成功结果 `expires` 缺失或为 0 → 宿主永不续期**
- 症状：账号到点直接失效，refresh 钩子从不被触发。
- 判据：success 返回没给真实过期时间戳（oauth 型）。
- 修法：给 `expires: Date.now() + expires_in * 1000`；细则见 `references/auth-patterns.md` refresh 纪律 2。

⚠️ **P25：改写流式响应正文不去掉 `content-length` / `content-encoding`**
- 症状：流解析错位或挂起。
- 判据：TransformStream/改写 SSE 后原样透传了长度与编码头。
- 修法：改写正文时 `headers.delete("content-length")` 等一并处理；细则见 `references/hooks.md` 第 4 节。

## 9. 排查表

发布前与排障时按此跑一遍：

```bash
# 隔离沙箱（独立 HOME/缓存 + 关市场——magpie CLI 会联网拉 GitHub 插件市场，无代理挂几分钟）
sb=$(mktemp -d)
m() { env HOME=$sb XDG_CONFIG_HOME=$sb/.config XDG_CACHE_HOME=$sb/.cache \
      MAGPIE_ADDR=127.0.0.1:3499 MAGPIE_PLUGIN_MARKET=off magpie "$@"; }

m plugin --json                            # 方式/账号/模型/加载错误（机器可读格式）
m plugin add ./你的插件文件夹 </dev/null    # 沙盒里装本地文件夹插件
```

⚠️ 全新沙箱的两个实测坑（完整命令与原理见 `SKILL.md` 开发-调试循环）：① 即使 `MAGPIE_PLUGIN_MARKET=off`，CLI 启动仍会联网探测，无代理挂数分钟——加 `HTTPS_PROXY=http://127.0.0.1:1 HTTP_PROXY=http://127.0.0.1:1 NO_PROXY=127.0.0.1,localhost` 让它秒失败回退；② 沙箱缺 Bun 运行时，`plugin` 命令会去 GitHub 下载并挂死——先 `cp -r ~/.cache/magpie/bun "$sb/.cache/magpie/"`。
⚠️ 非 TTY（管道）下登录 prompt 一律读不到输入：`password` 与 `text` 型都直接报 `no key on stdin: EOF`——没有"换 text 型"的绕法。脚本化验证登录按 `plugin-auth.json` 存储形状直写登录态（api 型 `{"<id>": {"type":"api","key":"…"}}`）再跑 `provider test`。
⚠️ 未登录账号时 `m provider test <id>` 报的是 `no provider "<id>"`——先 login 再 test，别把这条当成"插件没装上"。

- 终端每条命令起独立宿主（文件夹插件总是最新内容）；应用内关掉再开即重载。
- `magpie plugin on/off` 对本地插件认路径。
- ⚠️ `pkill -f magpie` 会误杀用户正在运行的 magpie 应用（进程名 `~/.local/bin/magpie`）——调试别用全局 pkill。

自查清单（对照本清单逐条过）：

1. usage 的每个数值字段都显式给了吗？时间戳是宿主可解析格式吗？（P1/P2/P3/P12）
2. 每个 success/refresh 返回里，`refresh` 和 `accountId` 都在吗？（P6/P7）
3. 所有非 401 语义的错误，是不是都按精确短语/错误码分类、而不是子串匹配？（P8/P19）
4. authorize 里还有没有「等用户/等外部事件」的 await？oauth 型方法都包了 callback 吗？（P4/P5）
5. 模块级状态的状态键带账号 id 吗？入口还导出了非工厂的函数吗？（P16/P18）
6. 包名是纯 slug 吗？这次改动 bump version 了吗？（P14/P15）

模型与 usage 字段的完整契约见 `references/models-usage.md`；发布流程见 `references/publishing.md`；非 auth 型插件（协议转换、流式翻译）见 `references/other-types.md`。

最后，三句值得贴在显示器旁的原话（实测注释原文）：

1. magpie-marvis quota.mjs：「写错字段不会让插件崩，只会让用户看到『剩余额度未知』、让这个号在路由里被当成不存在——而插件作者从日志里什么都看不到。」
2. cline:618：「403 that happens to mention 'tokens' is not a lapsed sign-in」
3. agnes:471：「余额没涨 ≠ 已发放：无领取接口…不能报 done（宿主渲染成『今日已签到』）」
