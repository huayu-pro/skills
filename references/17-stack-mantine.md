# Mantine 适配器

> 版本校准点：`@mantine/core` 9.8.0、`@mantine/mcp-server` 9.8.0。
> **使用前以项目 `package.json` 为准。** MIT，可商用、无需署名。
>
> 已安装 `mantine-form` / `mantine-combobox` / `mantine-custom-components` 技能时，
> 表单、下拉、自定义组件优先按那三个技能写；本章只给整体路由与主题规则。

## MCP 配置

```json
{
  "mcpServers": {
    "mantine": {
      "command": "npx",
      "args": ["-y", "@mantine/mcp-server"]
    }
  }
}
```

5 个工具：

| 工具 | 参数 | 返回 |
|---|---|---|
| `search_docs` | `query` | 排序后的文档匹配（通常定位到小节） |
| `get_item_doc` | `section`, `full: true` | 大纲 / 单节 / 整页 |
| `get_item_props` | `item` | 组件 props / hook 的 TS 签名 |
| `list_items` | `kind`, `group`, `category`, `package`, `query` | 条目列表 |
| `get_api` | `symbol`（如 `useForm`） | 签名解析 |

环境变量：`MANTINE_MCP_DATA_URL`（默认 `https://mantine.dev/mcp`）、`MANTINE_MCP_TIMEOUT_MS`（默认 10000）。

## 离线降级（三个库里最好）

```bash
# 全量文档，约 4.6 MB，含所有 props 表 —— 一次抓取，完全离线可用
curl -s https://mantine.dev/llms-full.txt -o mantine-docs.txt

# 索引（以 `list_items` 为准；9.8.0 校准）
curl -s https://mantine.dev/llms.txt

# 单页 Markdown
curl -s https://mantine.dev/llms/core-button.md

# 结构化索引（406 条记录，含 kind/group/category/propsCount/llmUrl）
curl -s https://mantine.dev/mcp
```

## 包结构（以 `list_items` 为准；9.8.0 校准）

| 包 | 用途 |
|---|---|
| `@mantine/core` | 输入、按钮、浮层、布局（组件数以 `list_items` 为准） |
| `@mantine/hooks` | 状态/UI hooks（hooks 数以 `list_items` 为准） |
| `@mantine/form` | 表单状态 + 校验 |
| `@mantine/dates` | 日期选择器、日历 |
| `@mantine/charts` | 基于 Recharts 的图表 |
| `@mantine/notifications` | Toast |
| `@mantine/spotlight` | 命令面板 |
| `@mantine/modals` | 集中式模态管理 |
| `@mantine/tiptap` | 富文本编辑器 |
| `@mantine/dropzone` | 拖拽上传 |
| `@mantine/carousel` | 基于 Embla 的轮播 |
| `@mantine/lightbox` | 全屏媒体查看 |
| `@mantine/code-highlight` | 代码高亮 |
| `@mantine/nprogress` | 导航进度条 |
| `@mantine/schedule` | 排程 |
| `@mantine/colors-generator` | 调色板生成 |
| `@mantine/emotion` | Emotion 样式方案 |

`@mantine/core` 的 peer 依赖：React ^19.2、`@mantine/hooks` 同版本。

## 关键约定

### Provider 必需

```tsx
import { MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';

<MantineProvider theme={theme} defaultColorScheme="auto">
  <App />
</MantineProvider>
```

`defaultColorScheme="auto"` 会跟随系统深浅色。

### 主题用 `createTheme`

```tsx
const theme = createTheme({
  primaryColor: 'brand',
  colors: { brand: [...10 个色阶字符串] },
  fontFamily: 'Inter, sans-serif',
  defaultRadius: 'md',
  headings: { fontFamily: 'Inter, sans-serif', sizes: { h1: { fontSize: '2.5rem' } } },
});
```

Mantine 的色阶是**固定 10 档**（index 0 最浅，9 最深）。用 `@mantine/colors-generator` 从一个主色生成，不要手填。

### 样式 API 优先于全局 CSS

Mantine 组件的样式通过 props 控制，不是 class：

```tsx
<Button
  variant="filled"        // filled | light | outline | subtle | default | white | transparent
  color="brand"
  size="md"
  radius="md"
  classNames={{ root: 'my-root', label: 'my-label' }}   // 需要时用 Styles API
/>
```

`classNames` / `styles` 的键名见每个组件的 Styles API 文档（`get_item_doc` 能查）。

### `factory` 构建自定义组件

要做一个和 Mantine 一致的组件，用 `factory`：

```tsx
import { factory, Factory, useProps, useStyles } from '@mantine/core';

const MyCard = factory<MyCardFactory>((_props, ref) => {
  const { classNames, className, style, styles, unstyled, ...others } = useProps('MyCard', defaultProps, _props);
  const getStyles = useStyles({ name: 'MyCard', classes, classNames, style, styles, unstyled });
  return <div ref={ref} {...getStyles('root')} {...others} />;
});
```

详见 `mantine-custom-components` skill（`~/.zcode/skills/mantine-custom-components`）。

### 表单：非受控模式优先

```tsx
const form = useForm({
  mode: 'uncontrolled',            // 性能更好，推荐
  initialValues: { email: '' },
  validate: { email: (v) => (/^\S+@\S+$/.test(v) ? null : '邮箱格式不正确') },
});

<TextInput {...form.getInputProps('email')} />
```

`getInputProps` 会同时绑定 `value`/`onChange`/`error`/`onBlur`，不要手写。

### 组合框：用 `useCombobox`

要做搜索选择、标签输入、自定义下拉，用 `@mantine/core` 的 `Combobox` 原语，不要用原生 `<select>` 或自己写 `div` 下拉。

详见 `mantine-combobox` skill（`~/.zcode/skills/mantine-combobox`，20+ 模式）。

## 常见坑

1. **忘了 `@mantine/core/styles.css`**：所有组件无样式。
2. **色阶不是 10 档**：Mantine 要求正好 10 个字符串，少了会报错。
3. **用 `className` 改组件颜色**：应该用 `color` prop 或 Styles API 的 `classNames`。
4. **在 `MantineProvider` 外使用组件**：会丢主题。
5. **手写表单状态**：`@mantine/form` 的 `getInputProps` 已经处理了大部分情况。
6. **`useForm` 用了受控模式却以为是非受控**：`mode` 默认是受控，显式写 `mode: 'uncontrolled'`。
7. **`@mantine/charts` 忘记装 `recharts`**：它是 peer 依赖。

## 与设计系统的关系

Mantine 的设计系统能力集中在主题对象：

- `colors` — 自定义色阶
- `fontFamily` / `fontFamilyMonospace` / `headings`
- `defaultRadius` / `radius`
- `spacing` / `fontSizes` / `lineHeights` / `shadows` — 覆盖刻度
- `components` — 全局默认 props 和 classNames

改主题比改组件样式更持久。优先改主题。

## 与其他章节的接口

- 选型：`18-stack-selection.md`
- 表单规则：`11-copy.md` §11.3（错误文案）
- 无障碍：`10-accessibility.md`（Mantine 组件已内置大部分 ARIA）
