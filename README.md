# magpie-plugin-dev

创建、调试与发布 Magpie（usemagpie.ai）插件的技能。面向 AI agent 使用，入口是 [SKILL.md](SKILL.md)。

## 结构

```
magpie-plugin-dev/
├── SKILL.md                  # 主入口：插件模型、5 分钟起步、调试循环、红线、验证清单
├── template/                 # 可跑的 provider 插件骨架（acme 示例，改名即用）
├── scripts/
│   ├── sandbox.sh            # 一键离线沙箱（隔离 HOME + Bun 复用 + 秒失败代理）
│   └── new-plugin.sh         # 从 template 生成新插件骨架（acme→vendor 改名）
├── references/
│   ├── hooks.md              # 全钩子契约（config/auth/loader/models/refresh/checkin）
│   ├── auth-patterns.md      # 登录实现八式
│   ├── models-usage.md       # 模型清单与 usage 额度窗口纪律
│   ├── pitfalls.md           # P1–P20 静默失败清单（真实事故出处）
│   ├── publishing.md         # 打包、测试、发布三渠道
│   └── other-types.md        # 中间件/hooks/agent/页面/工具/pi 兼容
└── evals/trigger_cases.json  # 触发回归用例
```

## 快速开始

```bash
~/.agents/skills/magpie-plugin-dev/scripts/new-plugin.sh fooai "FooAI"
source ~/.agents/skills/magpie-plugin-dev/scripts/sandbox.sh
m plugin add ./opencode-fooai-auth </dev/null
m plugin
```

素材来自官方文档全文 + 16 个真实插件源码剖析（含实测踩坑注释）。版本历史见 [CHANGELOG.md](CHANGELOG.md)。
