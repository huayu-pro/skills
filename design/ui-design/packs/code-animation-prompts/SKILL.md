---
name: ui-code-animation-prompts
description: 代码动画风格分类与提示词选择程序。仅在用户点名代码动画/动画风格库时加载。
metadata: { version: "5.0.0", source: "XiaoyeCodes/code-animation-prompts", license: "custom-free-with-attribution", parent: "ui-design" }
---

# Code Animation Prompts Pack

来源：XiaoyeCodes/code-animation-prompts。许可为仓库自定义
「来源、许可与免责分配约定」：可免费使用与转发；保留来源与本说明；
**禁止把这些内容包装成课程、付费 skills 或任何收费产品售卖**；第三方文件仍按各自许可。
本 pack 不打包 196 张参考静帧、不复制大体积 prompts 合集、不收费分发。

## 使用方式
1. 先读 `subskills/motion/SKILL.md`；本 pack 只提供风格候选与选择程序。
2. 从本文件 Reference 的 taxonomy 选 3 个候选，做 motion casting；不是「挑最炫的」。
3. 用核心 token/register/budget 改写；提示词里的裸数值不能直接进代码。
4. 记录来源；若未来发布付费版，把本 pack 从发行物里排除。

## 边界
- 不把模型名当验证或背书；`observed/inferred/authored` 仍按核心证据分级。
- 不加载 125MB 仓库；不复制参考图；不把提示词当运行时资产。
- quality fail 时，不靠换一条更花哨的 prompt 绕过。

读本文件 Reference 的 taxonomy。许可全文链接与声明见 `NOTICE`。


---

## Reference: taxonomy

# Code animation taxonomy（原创分类，保留来源说明）

> 提炼自 XiaoyeCodes/code-animation-prompts 的分类思想；不复制其 341 条提示词、
> 196 张静帧或离线挑选器。来源、许可与免责分配约定见本文件末尾。

| 类 | 设计问题 | 优先 register |
|---|---|---|
| 入场/揭示 | 哪个对象是唯一 attention？ | expressive/editorial |
| 状态/反馈 | 输入是否 120ms 内被确认？ | all |
| 连续/惯性 | 释放后是否有物理续接？ | expressive/product |
| 转场/连续性 | enter/exit 是否共享物体与方向？ | product |
| 数据/生成 | 动画是否解释数据变化，而非装饰？ | product/utility |
| 环境/纹理 | 是否可停、是否压文字？ | expressive only |
| 文字/排版 | 字角色是否仍可读？ | editorial |
| 结束/删除 | 删掉后是否更清楚？ | all |

## 选择程序
1. 写 MOTION MAP，确定 role 与 profile。
2. 从对应类选 3 个候选：轻/中/重三种重量。
3. 每个候选写「为什么属于题材」「删掉会怎样」。
4. 用 token 改写；跑 compliance；再做五帧 quality review。
5. 失败优先减少动效，而不是换更炫的提示词。

---
来源：XiaoyeCodes/code-animation-prompts（自定义许可）。本文件是独立提炼；
保留来源与本说明；不得将本合集包装成课程、付费 skills 或收费产品售卖。
