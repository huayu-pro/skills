# 组件库选型

## 一句话结论

| 你的情况 | 选 |
|---|---|
| 要完全掌控组件源码，做独特视觉 | **shadcn/ui** |
| 要开箱即用、内置无障碍和动效，接受组件是依赖 | **HeroUI v3** |
| 要组件数量最多、表单和日期最强、可商用零负担 | **Mantine** |
| 已有设计系统，只缺行为层 | **Base UI / Radix 原语** |
| 不确定 | 先看下表，再选；不要因为"流行"而选 |

## 对比矩阵

> 下表的版本与组件数是**校准点**，不是永久事实。使用前查项目的 `package.json` 与
> 各库 `llms.txt` / `list_components`；不要用旧表的数字做迁移决策。

| 维度 | shadcn/ui 4.23 | HeroUI 3.2 | Mantine 9.8 |
|---|---|---|---|
| **形态** | 源码复制进项目 | npm 包 | npm 包 |
| **改样式** | 直接改源码（彻底） | props + CSS 变量 + 主题 | props + 主题 + Styles API |
| **升级组件** | 手动 `--diff` 合并 | `npm update` | `npm update` |
| **组件数** | 以 registry 为准 | 73（v3.2.7） | 以 `list_items` 为准 |
| **无障碍** | 靠 Base UI/Radix，需自己补语义 | **内置最好**（React Aria） | 内置良好 |
| **动画** | 需自己加（`tw-animate-css`） | 内置（React Aria + CSS） | 内置（Transition） |
| **表单** | 无（配 react-hook-form） | 有 Form/Field | **最强**（`@mantine/form`） |
| **日期** | 需装 | 有完整套件 | 完整套件 |
| **图表** | `Chart`（包 Recharts） | 无 | `@mantine/charts`（Recharts） |
| **包体积** | 只装用到的 | 中等 | 大（但有 tree-shaking） |
| **Tailwind** | 强绑定（v3/v4） | v4 必需 | **不需要**（CSS Modules） |
| **许可** | MIT | Apache-2.0 | MIT（最宽松） |
| **MCP** | 内置 CLI（7 工具，需 `components.json`） | 独立包（6 工具） | 独立包（5 工具） |
| **离线文档** | 按组件 `.md` + registry JSON | `llms-full.txt`（部分） | **`llms-full.txt` 4.6MB 全量** |
| **适合** | 定制化产品、营销站、设计系统 | 快速交付、无障碍优先 | 后台/管理界面、数据密集 |

## 决策树

```
1. 项目已经有组件库？
   → 是：用它。本 skill 只做适配，不主张迁移。
   → 否：继续

2. 需要改组件内部结构（不只是外观）？
   → 是：shadcn/ui（源码在你手里）
   → 否：继续

3. 无障碍是硬要求，团队没有专人？
   → 是：HeroUI v3（React Aria 兜底）
   → 否：继续

4. 表单/日期/图表/排程需求重？
   → 是：Mantine
   → 否：继续

5. 用 Tailwind 且要精细控制视觉？
   → 是：shadcn/ui
   → 否：Mantine 或 HeroUI，按第 3 条
```

## 混用是可行的，但有代价

三者可以共存（比如 Mantine 的表单 + shadcn 的展示组件），但：

- **主题系统会打架**：Mantine 的 10 档色阶和 Tailwind 的 CSS 变量不互通。
- **无障碍基线不一致**：一个库处理焦点的方式和另一个不同，模态嵌套时会出问题。
- **包体积叠加**。

如果必须混用，选**一个作为主题权威**（通常是有主题对象的那一个），另一个只提供无样式原语。

## 迁移成本参考

| 从 → 到 | 成本 | 主要工作 |
|---|---|---|
| shadcn (Radix) → shadcn (Base UI) | 中 | `asChild` → `render`，见 `migrate-radix-to-base` skill |
| MUI → Mantine | 高 | 完全不同的 API 和主题模型 |
| HeroUI v2 → v3 | 高 | 无 Provider、复合组件、`onPress`、去 framer-motion |
| 任意 → shadcn | 中高 | 组件要一个个加，样式要从头做 |
| 任意 → HeroUI | 中 | 主要是替换导入和主题变量 |

**迁移不是设计改进**。如果视觉本身有问题，迁移只会把问题搬到新库。

## 三库的 MCP 配置汇总

```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["shadcn@latest", "mcp"]
    },
    "heroui-react": {
      "command": "npx",
      "args": ["-y", "@heroui/react-mcp@latest"]
    },
    "mantine": {
      "command": "npx",
      "args": ["-y", "@mantine/mcp-server"]
    }
  }
}
```

三个都装不冲突，共 18 个工具。shadcn 的工具是项目感知的（需要 `components.json`），另两个是无状态的。

## 离线降级

MCP 不可用时：

| 库 | 命令 |
|---|---|
| shadcn | `curl https://ui.shadcn.com/r/index.json`，再按需 `curl https://ui.shadcn.com/r/styles/new-york-v4/<name>.json` |
| HeroUI | `npx heroui-cli@latest agents-md --react`（下载到 `.heroui-docs/`） |
| Mantine | `curl https://mantine.dev/llms-full.txt`（一次 4.6MB，全量） |

在输出中标注「MCP 不可用，使用离线文档快照」。

## 与其他章节的接口

- shadcn 细节：`15-stack-shadcn.md`
- HeroUI 细节：`16-stack-heroui.md`
- Mantine 细节：`17-stack-mantine.md`
- 品牌语料：`19-brand-index.md`
