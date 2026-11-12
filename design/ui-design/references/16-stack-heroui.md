# HeroUI 适配器

> 版本校准点：`@heroui/react` 3.2.7、`@heroui/react-mcp` 1.1.4、`heroui-cli` 3.2.0。
> **使用前以项目 `package.json` 与已安装的 `heroui-react` 技能为准。** Apache-2.0（v3 起从 MIT 变更）。
>
> 已安装 `heroui-react` 技能时，优先用它的脚本取真实文档/源码，而不是凭记忆：
>
> ```bash
> node scripts/list_components.mjs
> node scripts/get_component_docs.mjs Button Card TextField
> node scripts/get_source.mjs Button
> node scripts/get_styles.mjs Button
> node scripts/get_theme.mjs
> ```
>
> **版本警告**：本文件只适用 v3。v2 的 API 完全不同（有 Provider、依赖 framer-motion、用扁平 props）。
> 看到项目里 `@heroui/react` 是 2.x，**不要**套用这里的规则；走 `heroui-migration`（若未安装，按本文件 v2→v3 表手工迁移）。

## MCP 配置

```json
{
  "mcpServers": {
    "heroui-react": {
      "command": "npx",
      "args": ["-y", "@heroui/react-mcp@latest"]
    }
  }
}
```

需要 Node ≥ 22.22。6 个工具：

| 工具 | 参数 | 返回 |
|---|---|---|
| `list_components` | — | 全部组件名 |
| `get_component_docs` | `components[]` | 文档 |
| `get_component_source_code` | `components[]` | **源码** |
| `get_component_source_styles` | `components[]` | 样式 |
| `get_docs` | `path` | 指定文档页 |
| `get_theme_variables` | — | 默认主题 token |

## 离线降级

```bash
# 目录（索引）
curl -s https://heroui.com/react/llms.txt

# 全量文档（较大）
curl -s https://heroui.com/react/llms-full.txt

# 模式文档
curl -s https://heroui.com/react/llms-patterns.txt

# 最干净的离线包：下载文档到 .heroui-docs/ 并生成 AGENTS 文档 索引
npx heroui-cli@latest agents-md --react
```

**注意**：`heroui.com/docs/react/components/*.mdx` 返回 404；sitemap 只有 5 个 URL（文档不在里面）。不要试图按 sitemap 抓文档。

## 关键规则（v3）

### 没有 Provider

v3 不需要 `<HeroUIProvider>`。看到项目里包了 Provider，说明是 v2 代码。

### Tailwind v4 必需

```css
@import "tailwindcss";      /* 必须在 heroui 样式之前 */
@import "@heroui/styles";
```

顺序错了样式不生效。

### 复合组件优先于配置 props

```tsx
// v3 正确
<Card>
  <Card.Header>标题</Card.Header>
  <Card.Body>内容</Card.Body>
  <Card.Footer>操作</Card.Footer>
</Card>

// v2 写法，v3 不支持
<Card header="标题" footer="操作">内容</Card>
```

### 事件用 `onPress` 不用 `onClick`

```tsx
<Button onPress={handleSave}>保存</Button>
```

`onClick` 在 v3 的 Button 上不保证触发（它走 React Aria 的 press 抽象，需要处理键盘、触控、长按）。

### 语义变体优先于原始颜色

```tsx
<Button variant="primary">主要</Button>
<Button variant="secondary">次要</Button>
<Button variant="danger">删除</Button>

// 不要
<Button className="bg-blue-500 text-white">主要</Button>
```

### 主题用 oklch CSS 变量

```css
:root {
  --heroui-primary: oklch(0.62 0.19 260);
}
```

不要覆盖 Tailwind 的原始调色板变量。

### 深色模式

```html
<html class="dark" data-theme="dark">
```

两个属性都要。只加 `class="dark"` 不够（部分组件读 `data-theme`）。

## 组件清单（73 个顶层组件；下表含 compound 子组件，共 79 个名称；以 `list_components.mjs` 为准）

| 类别 | 组件 |
|---|---|
| Buttons | Button, ButtonGroup, ToggleButton, ToggleButtonGroup, CloseButton |
| Collections | ListBox, ListBoxItem, ListBoxSection |
| Colors | ColorPicker, ColorArea, ColorField, ColorSlider, ColorSwatch, ColorThumb |
| Controls | Checkbox, CheckboxGroup, Radio, RadioGroup, Switch |
| Data Display | Table, Card, Chip, Badge, Avatar, Accordion, Disclosure |
| Date & Time | Calendar, DatePicker, DateField, DateRangePicker, RangeCalendar, TimeField |
| Feedback | Alert, ProgressBar, ProgressCircle, Spinner, Skeleton, Toast |
| Forms | Form, Input, Textarea, NumberField, SearchField, Slider, FieldError, Label, Description |
| Layout | Divider, Spacer, Surface, Header, Footer, Sidebar |
| Media | Image, Video, Carousel |
| Navigation | Tabs, Breadcrumbs, Pagination, Link, Navbar |
| Overlays | Modal, Popover, Tooltip, Dropdown, Menu, Sheet, Drawer |
| Pickers | Autocomplete, ComboBox, Select |
| Typography | Heading, Text, Code, Kbd |
| Utilities | VisuallyHidden, FocusRing, ScrollShadow, ResizeObserver |

## CLI

```bash
npx heroui-cli@latest init my-app -t vite -p pnpm
npx heroui-cli@latest install          # 装 @heroui/react + @heroui/styles
npx heroui-cli@latest info button      # 组件 API 参考
npx heroui-cli@latest doc button       # 组件文档
npx heroui-cli@latest doctor           # 诊断
npx heroui-cli@latest upgrade
```

**没有 `add <component>` 命令**。HeroUI 是 npm 包，不是复制式注册表。要组件源码只能：MCP `get_component_source_code`、npm tarball、或 GitHub `packages/react/src/components/`。

## 常见坑

1. **v2 代码混入 v3 项目**：Provider、`onClick`、扁平 props、`framer-motion` 依赖，四个特征任一出现就是 v2。
2. **Tailwind 导入顺序错**：HeroUI 样式必须在 Tailwind 之后。
3. **只加 `class="dark"`**：需要同时加 `data-theme="dark"`。
4. **给组件加尺寸类**：HeroUI 组件自己有 size 属性，不要用 `w-4 h-4` 覆盖。
5. **忘了 `onPress`**：`onClick` 在键盘操作时不触发。
6. **在 Button 里塞 `<a>`**：用 `Button` 的 `as` 属性或 `Link` 组件。
7. **手写模态焦点管理**：HeroUI 的 Modal 已处理焦点困住，不要叠加自己的逻辑。

## 许可注意

v3 是 Apache-2.0，再分发需要：附许可全文、保留版权/专利/商标声明、标注修改过的文件、不得用 HeroUI 商标暗示背书。

HeroUI 的 **Design Taste** skill（78 条设计原则）需要 Pro 令牌，**不可再分发**。

## 与其他章节的接口

- 选型：`18-stack-selection.md`
- 无障碍基础：`10-accessibility.md`
