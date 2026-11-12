# 常见问题与踩坑集（FAQ）

> 全部 references 里的坑在这里集中索引；每条答案末尾给出详出处（`文件.md §节`）。
> 排错顺序建议：先查「加载类」→ 再查「效果类」→ 最后「工程/端侧」。

## 加载类（页面空白 / 素材不出来）

**Q1：页面一片黑/空白，控制台报 `TypeError: Failed to fetch`？**
网络不通或服务器拒绝跨域。页面已内置自动重试（3 次指数退避）；彻底失败会显示静态兜底帧。排查：素材改本地相对路径；远程素材需服务器开 CORS。→ web-implementation.md §3.0（含「控制台原话→人话」对照表）

**Q2：GIF 转出来只有零星几个字符在动，背景全丢？**
GIF 增量帧压缩：相邻帧只存差异，直接解帧缺背景。判定式与帧合成方案已内置在模板里；素材侧根治：AE/GifGun 勾选"保留每帧完整像素"。→ web-implementation.md §3.1

**Q3：图片在 canvas 里画得好好的，一采样就报 `SecurityError`（画布污染）？**
跨域图没加 `crossOrigin='anonymous'`，或对方服务器没回 CORS 头。素材本地化最稳。→ SKILL.md §0.2 安全组、web-implementation.md §3.0

**Q4：素材超过 2MB，页面加载很慢？**
大 GIF 换构建期预生成（产物小一个量级且秒开）；或降 cols。红线参考与决策表。→ web-implementation.md §3.9、SKILL.md §0.2 性能组

## 效果类（画面不对劲）

**Q5：字符画"被压扁/拉长"，脸都是扁的？**
纵横比没修正：字符格是高瘦的（约 0.55 宽高比），按正方形采样必变形。修正系数 0.55（区间 0.5–0.66，随字体微调）。→ SKILL.md §1.2 视觉契约、image-to-ascii.md §2.1

**Q6：画面里汉字/全角字符一出，整个网格就错位？**
CJK 全角字符占两格宽，与半角 ramp 混排必撕裂网格。字符画层只用等宽半角/白名单 Unicode；中文文案放正常 HTML 层。→ SKILL.md §1.1、§4 第 7 条

**Q7：从 Windows 工具拷来的字符画多出空行/每行末尾错位？**
`\r\n` 陷阱：入库前统一 `.replace(/\r\n?/g, '\n')`。→ SKILL.md §1.1

**Q8：字符画看起来"毛边、不精细"？**
精度档位不够：标准 10 级 → 高清 24 级 → 超高清 70 级+抖动 → 盲文亚像素，按需升级。→ image-to-ascii.md §2.2

**Q9：彩色 ASCII 用 `<span>` 包每个字符后卡成幻灯片？**
DOM 节点爆炸。彩色改 canvas `fillText`（或逐行 span），`<span>` 逐字符只允许 ≤几百格的小件。→ image-to-ascii.md §2.1、SKILL.md §6

**Q10：CRT 效果加上后文字发虚/看着晕？**
剂量超了：扫描线透明度、暗角强度都减半；flicker 必须 `steps(1)` 且占比 <3%。CRT 只能耳语。→ web-implementation.md §3.7、SKILL.md §4 第 3 条

**Q11：morph（字形渐变）在大网格上掉帧？**
每帧全量重算超预算（160×60 以内才安全）。降 cols、或预计算种子表、或改脏区只算变化行。→ animation-patterns.md §P.8、§P.10

## 音频类

**Q12：频谱可视化一片死平，一点不动？**
Autoplay 策略：`AudioContext` 初始 suspended，没有用户手势 `resume()` 前拿到的全是 0。加"点击开启"按钮（或任意首次交互解锁）。→ audio-visual.md §M.4

**Q13：接了 AnalyserNode 之后音乐没声音了？**
`createMediaElementSource` 之后没把 analyser `connect(audioContext.destination)`——信号进了分析器但没进扬声器。另一坑：对同一元素调用两次 createMediaElementSource 会静音。→ audio-visual.md §M.1

## Remotion 类（导出视频）

**Q14：为什么 Remotion 里禁用 `Math.random()`？**
渲染是多线程逐帧截图，各线程的随机序列不一致，同一帧两次渲染结果不同 → 成片必出鬼影/闪烁。用 `random(seed)`（同种子恒同值），结构性参数用稳定种子、闪烁细节用含帧号的种子。→ remotion-video.md §R.2、§R.4、§R.10

**Q15：视频里 CSS 动画/过渡完全不动？**
逐帧渲染捕捉不到 CSS 时间推进。`transition`/`animation`/Tailwind 动画类全部重构成 `interpolate(frame, …)` 内联 style。→ remotion-video.md §R.2、§R.10

**Q16：渲染出来的字符画字体不对/变宋体了？**
渲染机器没有你的等宽字体。字体文件放 `public/` 用 `loadFont` 本地加载；不要依赖 Google Fonts（国内还不稳）。→ remotion-video.md §R.3

**Q17：Remotion 可以免费商用吗？**
特殊许可证：个人 / 非营利 / **≤3 人的营利公司**免费；更大的公司需购买 Company License（remotion.pro）。**交付前向用户确认使用主体性质**。→ remotion-video.md §R.10

**Q18：`npx remotion render` 卡在下载 Chrome / 装包超慢？**
国内网络问题：npm 走镜像源；Chrome Headless Shell 下载失败按官方文档配镜像环境变量。→ remotion-video.md §R.10

## 工程与端侧

**Q19：导出的 PFM 浮点数据颜色全反了？**
PFM 是**底向上**行序，写入前必须翻转行序（模板含 `flipRows()`），并随数据落盘 `rowOrder` 元数据。→ image-to-ascii.md §2.3

**Q20：C 模板编译警告 `implicit declaration of 'usleep'` / signal 处理不生效？**
两个经典坑：`usleep` 已废弃（POSIX.1-2008 删除），换 `nanosleep`；`-std=c99` 触发 `__STRICT_ANSI__` 隐藏 POSIX 声明，需 `#define _POSIX_C_SOURCE 200809L`。→ terminal-templates.md

**Q21：三端（HTML/Python/C）同屏对比帧率不一致？**
帧间隔没对齐：三端必须共用同一 `fps` 与同一份帧数据（`data.json` / `frames.json` 单一事实源）。→ terminal-templates.md 三端一致性契约、web-implementation.md §3.9

**Q22：动画在后台标签页还狂转 CPU？**
没挂 `visibilitychange` 暂停。所有 rAF/rVFC 循环都要：页面不可见即停、可见再续。→ SKILL.md §6、web-implementation.md §3.5

**Q23：管线脚本报 `[依赖缺失]`？**
按脚本给的中文指引装：Pillow（图片/GIF）`pip install Pillow`，ffmpeg（视频）系统包管理器；纯 PPM 路径零依赖可直接用。→ scripts/ascii_pipeline.py 文件头、web-implementation.md §3.9

**Q24：滚动渐变在 Safari 上抖动 / 触屏上交互全无反应？**
滚动监听缺 `{passive:true}` + rAF 节流；触屏没有 hover——按回退表改点击开关。→ scroll-and-pointer.md §I.1、§I.6

**Q25：SVG logo 转成字符画后细线整根消失？**
位图式直接降采样把 1–2 单位的笔画抹成 10% 灰，乘 ramp 只剩空格。走超采样：每字符格栅格成 4×4 像素再取均值（覆盖率采样），或构建期用 resvg 先转 4× 宽 PNG 再进管线。→ image-to-ascii.md §2.5

**Q26：字符画里一放中文，整行就向右错位、网格逐行撕裂？**
全角占 2 格：中文字符若按 1 格排版，其后所有字符右移一格。三条方案——全角补位（终端优先）、CJK 感知列宽 + CSS Grid（网页优先）、混排行宽对齐（默认推荐，中文标题走正常 HTML 层）。另注意 `'中文'.length` 是 2 但视觉宽度是 4，不能用 `length` 算宽度。→ image-to-ascii.md §2.6

**Q27：换了字体/字号后字符画被拉长或压扁？**
纵横比 0.55 只对特定字体字号成立。用 `measureCell()` 量出实际字符格 `w/h` 作为 aspect，落在 0.5–0.66 之外就换字体而不是硬调系数；Web Font 未就绪时要 `await document.fonts.ready` 再量。→ web-implementation.md §3.8
