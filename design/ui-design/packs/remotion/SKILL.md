---
name: ui-remotion
description: 程序化视频/React 时间轴适配层；外部依赖，不 vendor 代码。仅在用户明确要 Remotion/程序化视频时加载。
metadata: { version: "5.0.0", source: "remotion-dev/remotion", license: "Remotion-License-external", parent: "ui-design" }
---

# Remotion Pack

来源：remotion-dev/remotion。许可是 **Remotion License**（source-available 双轨）：
个人、≤3 人营利组织、非营利、评估场景可免费用于创建视频/图片；
超过门槛的营利组织需要 Company License。禁止复制/修改 Remotion 代码用于
销售、租赁、再许可或分发自己的衍生版本。本 pack **不 vendor 4.47GB 代码/资产**。

## 加载门槛
先问清/确认使用主体规模。无法确定时按「需要 Company License」处理，并给出
不用 Remotion 的 HTML/CSS/WebM 替代路径。不要把本 pack 打进付费衍生发行物。

## 用法
1. 明确这是视频交付，不是普通网页；普通 UI 不加载。
2. 用 `ui-direction` / `ui-tokens` 定视觉；时间轴用帧，不把网页 token 当帧率。
3. 组件/序列/合成按本文件 Reference 的原创示例；依赖由用户在自己项目安装。
4. 动效仍写证据：关键帧、时长、fps、渲染命令、`skipped`。
5. 商业/大团队使用前核对 <https://www.remotion.dev/license>。

## 边界
- 不复制 Remotion 源码、模板或品牌资产进本仓库。
- 不替用户判断法律资格；只把门槛写进交付说明。
- headless 渲染读数不等于真机播放体验。


---

## Reference: setup

# Remotion external setup

> 这是原创最小示例，不含 Remotion 源码。用户自行安装并遵守 Remotion License。

```bash
# 在用户自己的项目里，不在本 skill 仓库里
npm i remotion @remotion/cli react react-dom
npx remotion render src/index.ts MyComp out/demo.mp4
```

```tsx
// 原创结构示意：帧是时间源，UI token 只负责视觉
const MyComp: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: 'clamp',
  });
  return <main style={{ opacity, fontFamily: 'var(--font-body, system-ui)' }}>Title</main>;
};
```

交付说明必须含：`entity eligibility / fps / duration / resolution / render command /
binary source / skipped`。没有合法资格或没有渲染器就写 `skipped`，不产出「假成品」。
许可全文见 <https://github.com/remotion-dev/remotion/blob/main/LICENSE.md>。
