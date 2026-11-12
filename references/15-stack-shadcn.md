# shadcn/ui 适配器

> 版本校准点：CLI `shadcn@4.23.0`（MIT）。**使用前以项目 `package.json` / `npx shadcn@latest --version` 为准。**
> 组件是**复制进项目**的源码，不是 npm 依赖。
>
> 先跑项目探测，不要凭记忆写：
>
> ```bash
> npx shadcn@latest info --json          # 项目配置 + 已装组件
> npx shadcn@latest docs button          # 组件文档 + 示例 URL
> npx shadcn@latest add button           # 加组件
> npx shadcn@latest init --preset <code> # 新项目整套预设
> npx shadcn@latest apply <code>        # 已有项目套预设
> npx shadcn@latest view <item>         # 浏览未安装的 registry 项
> npx shadcn@latest add --diff          # 预览已装组件的差异
> ```
>
> 安装/初始化前确认 `components.json`；没有就先 `init`。

## MCP 配置（推荐）

shadcn 的 MCP server 内置在 CLI 里，没有独立包。

```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["shadcn@latest", "mcp"]
    }
  }
}
```

自动配置：`pnpm dlx shadcn@latest mcp init --client claude`（也支持 `cursor` / `vscode` / `codex` / `opencode`）。

**前提**：项目里有 `components.json`。没有就先 `npx shadcn@latest init`。

### 7 个工具

| 工具 | 参数 | 用途 |
|---|---|---|
| `get_project_registries` | — | 读 `components.json` 里的注册表名 |
| `list_items_in_registries` | `registries[]`, `types[]`, `limit`, `offset` | 分页列出 |
| `search_items_in_registries` | `query`(必填), `registries[]`, `types[]` | 模糊搜索 |
| `view_items_in_registries` | `items[]`(必填, `@ns/name`) | **含完整文件内容** |
| `get_item_examples_from_registries` | `query`(必填) | 示例 + 完整代码 |
| `get_add_command_for_items` | `items[]` | 返回 `shadcn add` 命令 |
| `get_audit_checklist` | — | 生成后自查清单 |

## 离线降级（MCP 不可用时）

```bash
# 组件清单
curl -s https://ui.shadcn.com/r/index.json          # 65 个 registry:ui 项

# 单个组件源码（含 content 字段）
curl -s https://ui.shadcn.com/r/styles/new-york-v4/button.json

# 文档（Markdown）
curl -s https://ui.shadcn.com/docs/components/button.md
```

## 关键规则（违反即 bug）

### 样式与 Tailwind

| 规则 | 正确 | 错误 |
|---|---|---|
| `className` 只做布局 | `<Card className="p-6">` | `<Card className="bg-blue-500">` |
| 用 `gap-*` 不用 `space-*` | `flex flex-col gap-4` | `space-y-4` |
| 相等尺寸用 `size-*` | `size-10` | `w-10 h-10` |
| 截断用 `truncate` | `truncate` | `overflow-hidden text-ellipsis whitespace-nowrap` |
| 深色模式用语义 token | `bg-background text-muted-foreground` | `dark:bg-gray-900` |
| 条件类用 `cn()` | `cn("p-4", active && "bg-accent")` | 模板字符串三元 |
| 不手写 overlay 的 `z-index` | 交给 Dialog/Sheet/Popover | `z-50` |

### 表单

- 布局用 `FieldGroup` + `Field`，**不要** `div` + `space-y-*`。
- `InputGroup` 内必须用 `InputGroupInput` / `InputGroupTextarea`，不能用裸 `Input`。
- 输入框里的按钮用 `InputGroup` + `InputGroupAddon`。
- 2–7 个选项用 `ToggleGroup`，不要循环 `Button` 手写选中态。
- 校验态：`Field` 上加 `data-invalid`，控件上加 `aria-invalid`。
- 禁用态：`Field` 上加 `data-disabled`，控件上加 `disabled`。

```tsx
<FieldGroup>
  <Field data-invalid>
    <FieldLabel htmlFor="email">邮箱</FieldLabel>
    <Input id="email" aria-invalid />
    <FieldDescription>邮箱格式不正确。</FieldDescription>
  </Field>
</FieldGroup>
```

### 组合结构

- **Item 必须在 Group 内**：`SelectItem` → `SelectGroup`，`DropdownMenuItem` → `DropdownMenuGroup`。
- **Dialog / Sheet / Drawer 必须有 Title**（无障碍要求），视觉隐藏用 `className="sr-only"`。
- **Card 用完整组合**：`CardHeader` / `CardTitle` / `CardDescription` / `CardContent` / `CardFooter`。
- **Button 没有 `isPending`**：用 `Spinner` + `data-icon` + `disabled` 组合。
- **`TabsTrigger` 必须在 `TabsList` 内**。
- **`Avatar` 必须有 `AvatarFallback`**。
- 用组件不要造轮子：提示用 `Alert`，空状态用 `Empty`，分隔用 `Separator`，加载占位用 `Skeleton`，徽章用 `Badge`。

### 图标

- 按钮内图标用 `data-icon`：`<SearchIcon data-icon="inline-start" />`。
- **不要**给组件内图标加尺寸类（`size-4` / `w-4 h-4`），组件自己管。
- 图标作为对象传入：`icon={CheckIcon}`，不要字符串查找。

### 聊天界面

- `MessageScroller` 管滚动（流式跟随、锚定、跳到底部），不要自己写 `useStickToBottom`。
- 行用 `Message`，气泡用 `Bubble`。
- 附件用 `Attachment`，系统提示用 `Marker`。
- 助手活动（推理、工具调用）用 `Trace` + `TraceLine`。

## 项目探测

```bash
npx shadcn@latest info --json
```

关键字段：

| 字段 | 用途 |
|---|---|
| `aliases` | import 前缀，不要硬编码 `@/` |
| `isRSC` | `true` 时用 `useState` 等需 `"use client"` |
| `tailwindVersion` | `v4` 用 `@theme inline`；`v3` 用 `tailwind.config.js` |
| `tailwindCssFile` | 自定义 CSS 变量写这里，不要新建文件 |
| `style` | 视觉风格（`nova` / `vega` / …） |
| `base` | `radix` 或 `base`，影响 API（`asChild` vs `render`） |
| `iconLibrary` | `lucide` → `lucide-react`；不要假设 |
| `resolvedPaths` | 组件/工具/hook 的确切落点 |
| `framework` | Next.js App Router vs Vite SPA |
| `packageManager` | 装其他依赖时用 |

## 工作流

1. `npx shadcn@latest info` 拿项目上下文。
2. 先查已装组件（`components` 字段或列 `resolvedPaths.ui` 目录）。
3. `npx shadcn@latest search` 找组件。
4. `npx shadcn@latest docs <component>` 拿文档 URL，**必须 fetch**。
5. `npx shadcn@latest add <component>` 安装。
6. **读一遍加进来的文件**，检查：缺子组件、导入错误、组合违规、图标库不匹配。第三方注册表的组件常有硬编码 `@/components/ui/...` 路径，要用项目的 alias 改写。
7. 更新已有组件时用 `--dry-run` 和 `--diff`，**不要**手动从 GitHub 抓文件。

## 常见坑

1. **注册表必须明确**。用户说「加个登录块」但没说哪个注册表，要问，不要默认 `@shadcn`。
2. **`--overwrite` 必须先获得明确同意**。
3. **预设切换前问清楚**：overwrite / partial / merge / skip。
4. **`--only` 只支持 `theme` 和 `font`**，不支持 `icon`（改图标要重装组件）。
5. **`base` 不会被预设码编码**，在临时目录做 `--dry-run` 时要显式传 `--base`。
6. **组件是源码**，升级不会自动跟随上游。用 `--diff` 手工合并。

## 与设计系统的关系

DESIGN 文档 → 主题的完整流程见项目内 项目内的设计系统文档 的模式：

1. `init --preset <code> --template vite --name <app> --no-monorepo -y` → `add --all -y`
2. 读 DESIGN 文档 的 frontmatter、Do's/Don'ts、Known Gaps
3. 把 token 映射到 `tailwindCssFile` 里的 CSS 变量，钉住 radius / shadow / font / `type-*`
4. 改组件的 `cva` variants 重新造型，**同一层级的控件高度一起改**
5. 建设计系统页：对比度校验过的颜色角色、字体样张、状态矩阵、边界情况、do/don't
6. 浏览器验证：typecheck、无 console 错误、无横向溢出、深色模式

## 与其他章节的接口

- 选型：`18-stack-selection.md`
- 设计系统语料：`19-brand-index.md`
- Tailwind 映射：`20-tailwind-mapping.md`
