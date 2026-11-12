# reverse-302 mechanism kits

12 个原生 CSS/JS 机制 kit，零依赖，供 `replica/site` 组合复用。每个 kit 导出一个 `css` 字符串和一个 `mount(root, options)` 函数；`mount` 返回清理函数。坐标/尺寸都基于传入的 root，不假设全局布局。

| # | 文件 | 机制 | 典型站点 |
|---:|---|---|---|
| 1 | `01-scroll-narrative.js` | 滚动叙事、分段 reveal、进度条 | scroll/editorial |
| 2 | `02-horizontal.js` | 横向轨道、wheel/drag、snap | horizontal |
| 3 | `03-webgl-shader.js` | 全屏 WebGL fragment shader | canvas-webgl |
| 4 | `04-canvas-2d.js` | Canvas 2D 粒子隧道 | canvas-2d |
| 5 | `05-orbit-3d.js` | CSS 3D 轨道/卡片 | 3D portfolio |
| 6 | `06-cursor.js` | 自定义光标、磁吸、拖尾 | cursor |
| 7 | `07-typography.js` | 动态字体、marquee、行 reveal | typographic |
| 8 | `08-collage.js` | 可拖拽拼贴卡片、吸附 | collage |
| 9 | `09-audio.js` | WebAudio 解锁、频谱条 | audio |
| 10 | `10-map.js` | 地图 pan/zoom、pin | map/spatial |
| 11 | `11-game.js` | Canvas 小游戏循环、输入 | game |
| 12 | `12-editorial-landing.js` | 编辑落地页、sticky/nav/accordion | editorial-static |

用法：

```js
import { css, mount } from "../_kits/02-horizontal.js";
const style = document.createElement("style");
style.textContent = css;
document.head.appendChild(style);
const dispose = mount(document.querySelector("main"), { sections: ".panel" });
// dispose() 移除监听与 rAF
```

所有 kit 只做机制，不含原站资产/文案；复刻时把原站 DOM/class 映射到 `options`。
