# opencode-acme-auth

把你的 Acme Coding Plan 接入 magpie（以及 OpenCode）。

## 登录

`magpie plugin login acme`，粘贴 Acme API key。key 保存在
`~/.config/magpie/plugin-auth.json`（权限 600），本插件不另存副本。

## 模型

- `acme/acme-coder` — Acme Coder（200K 上下文 / 32K 输出，工具调用）

登录后还会自动拉取该账号实际可用的模型列表（失败时用上面的静态清单）。

## 额度

`magpie quota` 显示 5 小时窗口用量，来自 Acme 的 `/usage` 端点。
