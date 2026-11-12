# 打包、测试与发布上架

写完插件后：把包做对（package.json 惯例与双入口）、测够（测试金字塔）、发出去（三条发现渠道）。快速上手与钩子契约见 [SKILL.md](../SKILL.md) 与 [hooks.md](hooks.md)。

## package.json 惯例

### 命名两流派

| 流派 | 包名 | 适用 |
|---|---|---|
| 社区 monorepo | `@magpie-community/opencode-<vendor>-auth` | PR 进 magpie-community/plugins 的包 |
| 独立包 | `magpie-<vendor>` / `magpie-plugin-<vendor>` / `@user/magpie-<vendor>` | 自己仓库发布 |

⚠️ `package.json.name` 必须是 slug（不能有空格/中文）——它同时是 bun 依赖键与 node_modules 目录名；中文显示名写 `magpie.name`。改包名要 package.json + bun.lock + 目录三处同步。

### 双入口（社区包必须，独立包可选）

社区包全部采用双入口，兼容 OpenCode 1.x / 2.x：

```json
"main": "./opencode.mjs",                    // OpenCode 1.x + magpie 宿主
"exports": { ".": "./opencode2.mjs" },       // OpenCode 2.x
"files": ["index.mjs", "opencode.mjs", "opencode2.mjs", "README.md"]
```

- `opencode.mjs` 只做 re-export：`export { TraeCNAuthPlugin } from "./index.mjs"`。⚠️ 1.x **拒绝**导出里出现任何非插件函数的包——`_internal` 不能进这个入口。
- `opencode2.mjs` 是把 1.x 函数翻译成 2.x `{id, setup(ctx)}` 的共享适配器；社区 monorepo 里所有包持有**字节相同**的副本，`scripts/check.mjs` 在副本不同时失败。
- 独立包可以简单：`"main": "./index.mjs", "exports": "./index.mjs"`，无 2.x 适配层（marvis/today/tabbit/lingxi 都这样）。

### keywords 决定能不能被搜到

插件市场搜索向 npm 查 `<关键词> opencode`，要求包名或 keywords 同时含 `opencode` 且含 `auth`/`plugin`/`provider` 之一（也查 `keywords:pi-package`）：

```json
"keywords": ["opencode", "opencode-plugin", "magpie", "<vendor>"]
```

⚠️ 少写 `opencode` 或三个动作词之一 = 应用内搜不到，但功能完全正常（坑 15 级别：静默）。

### magpie 专有字段（OpenCode 忽略，加了安全）

| 字段 | 含义 | 限制 |
|---|---|---|
| `magpie.icon` | 图标 URL / data URI / 内置图标名（如 `"sparkles"`） | ≤1 MB |
| `magpie.name` | 「已安装」行显示名（可中文） | ≤80 字节 |
| `magpie.summary` | 发现卡片简介 `{en, zh}` | ≤300 字节/语言 |
| `magpie.maxConcurrency` | 每账号并发上限 | 1–1000 整数，用户设置优先 |

auth 钩子上的 `icon`/`maxConcurrency` 优先于 package.json（多供应商插件每家一个图标）。

### 依赖习惯

16 个真实插件 `dependencies` 全部为空——裸 `fetch` + `node:*` 内置模块。npm 依赖可用但**不执行 install 脚本**（依赖 postinstall 的包不可用）。license 全 MIT；归属说明放 NOTICE 文件，LICENSE 写逐字 MIT 正文。

## 测试金字塔

1. **纯函数单测**：依赖注入到极致（`fetchImpl/env/readFileImpl/nowMsImpl` 全部可注入），纯函数挂 `_internal`，`node --test` / `bun test` 直接测。参考 agnes-code（535 行全可注入）。
2. **契约/合规检查**：`node ../magpie-community/plugins/scripts/check.mjs .`——模仿宿主加载包并检查钩子形状，退出码非 0 不合规。
3. **沙箱 e2e**：SKILL.md 的沙箱 HOME 命令；`m plugin --json` 看**加载错误**；`m provider test <id>` 打真上游。
4. **真探（probe）**：today-auth 的 `npm run probe` 对真 API 探端点、无需账号。
5. **Docker e2e**（面向网关类插件）：magpie-sub2api 用 Docker 临时起一套 sub2api（含假 Anthropic 上游），模拟 magpie 调用 auth.loader / auth.usage / provider.models 并断言；CI 对固定版本 + latest 各跑一遍。

端点用环境变量覆盖便于调试（如 today 的 `TODAY_API_BASE`）。

## 发布三渠道

### 1. npm（必做）

照常 `npm publish`。用户可按名/版本/git/文件夹添加。npm 上的 README 会显示在应用内插件详情页——写清登录什么、怎么登录、凭据存哪、有哪些模型。

### 2. 社区注册表 registry.json（推荐列表）

PR 到 [magpie-community/plugins](https://github.com/magpie-community/plugins) 的 `registry.json`（magpie 每 6 小时拉取 + 内置副本兜底）：

```json
{
  "package": "opencode-acme-auth",            // 独立包示例；社区 monorepo 包写 @magpie-community/opencode-<name>-auth
  "name": "Acme",
  "icon": "https://acme.example/icon.svg",   // URL / 内置图标名 / data URI
  "providers": ["acme"],                      // 仅认证类插件有
  "summary": { "en": "Your Acme Coding Plan.", "zh": "使用你的 Acme Coding Plan。" }
}
```

- 中间件加 `"kind": "middleware"`（不写 providers）、工具 `"kind": "tools"`、页面 `"kind": "page"`、Agent `"kind": "agent"`。
- 社区分组条目带 `"community": true`；自己仓库发布的包不写（卡片显示 npm 发布者）。
- **社区包**放 `packages/<name>/`，命名 `@magpie-community/opencode-<name>-auth` / `middleware-<name>` / `tools-<name>` / `page-<name>` / `agent-<name>`。
- ⚠️ **渠道去重规则**：按 vendor 服务判定重复，同渠道新包必须在 PR/README/registry 摘要中说明差异，否则拒收。

**社区包发布自动化**：版本号 bump 推到 main 即触发发布，两条路径——npm trusted publishing（OIDC，需在 npmjs 配 Trusted Publisher；首版需 owner 发）+ dist 分支兜底（tgz + sha512，magpie 0.1.1243+ 在 npm 缺版本时从此安装）。这些包在每个 magpie 里**自动更新**（启动后一次、之后每小时）。

### 3. GitHub 发现（零审核）

仓库打 topic **`magpie-plugin`** 即进「发现 → 非官方插件」（按 star 排序）。要求：`package.json` 在仓库根、加载文件已提交（构建产物才出现的仓库不显示）；fork/归档被排除；每 10 分钟查一次。

## 其他 npm 包：手动更新语义

`@magpie-community/*` 自动更新；其他 npm 包新版只显示圆点，用户手动 `magpie plugin update`；`name@1.2.3` 固定版本不升级；git 仓库比对提交（每 10 分钟）。

## 经验教训

- ⚠️ **npm tarball 可能被安全扫描扣住**（404）：wps-lingxi 读浏览器 Cookie 库 + 下载远端二进制，npm 0.3.x 三次发布 tarball 均 404。`github:` 方式安装是重要备选渠道——README 里写明。
- ⚠️ 改 npm 源代码必须 bump version，否则 bun 缓存命中无更新。
- ⚠️ `magpie plugin add xxx.tgz` 有 bug（把 tgz 当 JS import）——别用。
- 自定义市场：`MAGPIE_PLUGIN_MARKET=<url>` 换清单，`off` 只用内置副本。
- 仓库普遍带：`registry-entry.json`（registry 条目的仓库内副本）、AGENTS 与 CHANGELOG 惯例文件、MIT LICENSE、icon.png（1024×1024）。

## 上架检查清单

- [ ] `name` 是合法 slug；keywords 含 `opencode` + `auth|plugin|provider`
- [ ] `type: "module"`；入口指向正确（社区包双入口）
- [ ] 入口只导出插件工厂（+ `_internal`）
- [ ] `magpie.{name,summary,icon}` 填了中英文
- [ ] README 写清登录方式/凭据存放/模型列表
- [ ] `scripts/check.mjs` 通过；沙箱 `plugin --json` 无加载错误；`provider test` 打通
- [ ] repository 字段指向 GitHub 仓库（GitHub 发现渠道要求）
- [ ] （进社区列表）registry.json PR + 渠道去重说明
