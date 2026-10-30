# 字体

## 本机（Linux / 预览渲染）

| 角色 | 字体 | 来源 |
|---|---|---|
| 中文展示 + 正文 | Noto Sans CJK SC（含 Black） | `fonts-noto-cjk` |
| 西文展示 | Liberation Sans Narrow | `fonts-liberation` |
| 等宽 | DejaVu Sans Mono | `fonts-dejavu` |

检查是否装了：

```bash
fc-list :lang=zh | grep -i "noto sans cjk"
fc-list | grep -i "liberation sans narrow"
```

---

## 目标机器（PowerPoint）

`--font-profile office` 写入的是**微软雅黑 + Arial Narrow + Consolas**——这三个随 Windows/Office 必装，不会掉字。

| 想要的效果 | 现实 | 怎么办 |
|---|---|---|
| 极重的黑体标题 | 微软雅黑 Bold 没有 Noto Black 那么重 | 装思源黑体后用 `--font-profile source`；或关键标题 `data-fidelity="raster"` |
| 极窄的西文 | Arial Narrow 与 Liberation Narrow 度量兼容 | 直接用，没问题 |
| 思源黑体 | 需要用户自己装 | 提示用户在"字体替换"里换 |

---

## 装思源黑体（可选，但效果更好）

```bash
# Debian / Ubuntu
sudo apt install fonts-noto-cjk fonts-noto-cjk-extra

# 或在 Adobe 官网下载 Source Han Sans SC
# https://github.com/adobe-fonts/source-han-sans/releases
# 装上后刷新缓存
fc-cache -fv
```

Windows：下载 `.otf` 后右键安装，字体名会显示为「思源黑体 CN」。

---

## 授权

| 字体 | 授权 | 可商用 | 可嵌入 PPTX |
|---|---|---|---|
| Noto Sans CJK / 思源黑体 | SIL OFL 1.1 | 是 | 是（但没必要） |
| Liberation Sans Narrow | SIL OFL 1.1 | 是 | 是 |
| DejaVu Sans Mono | 自由 | 是 | 是 |
| 微软雅黑 | 随 Windows | 系统内使用 | 否 |
| Arial Narrow | 随 Office | 系统内使用 | 否 |

**本 skill 不打包任何字体文件。** 一是授权，二是体积——一份 10 页 deck 嵌两套中文字体就 30MB 起。

---

## 颜色与字重的关系

深色底上的中文字重不要低于 500。CJK 笔画密度高，Light 字重在投影仪上会糊成一团灰。
本 skill 的展示字一律 800–900，正文 400，元数据 400（但字距拉宽以补偿视觉重量）。
