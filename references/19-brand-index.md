# 19 · 品牌语料索引（84）

## 这是什么

`assets/brands.json` 里有 **84 份真实品牌的设计语言分析**，来自
[awesome-design-md](https://github.com/VoltAgent/awesome-design-md)（MIT）。
每份是 Google Stitch 的 DESIGN 文档格式：frontmatter 是 token，正文是规则与理由。

这不是「好看的设计 gallery」，而是**被真实产品验证过的 token 系统**。
它们回答教材不回答的问题：一个暗色技术产品的主色饱和度是多少？一个奢侈品站的圆角是几？
一个新闻媒体的字阶比值是多少？

## 怎么用

**当语言样本，不当模板。** 抄 token 会得到一个像 Linear 的界面，而不是适合你的界面。

1. 选 **3 个** 与题材气质相邻、但彼此不同的品牌（不要选 3 个同类的）。
2. 每个只记三件事：
   - **色彩关系**：谁是底、谁是面、谁只出现一次；强调色占多少面积。
   - **字体角色**：标题/正文/数据各自承担什么；字阶比值与字重。
   - **一个签名动作**：圆角策略、分隔线、留白比例、材质、阴影层级。
3. 写成一段「语言假设」，再决定自己的 token。
4. 不复制布局、文案、图形资产；品牌名只出现在参考说明里。

```bash
# 列出全部 84 个品牌及 token 数
python3 -I scripts/query_corpus.py --brands

# 读某个品牌的某一节
python3 -I scripts/query_corpus.py --brand linear.app --section colors
python3 -I scripts/query_corpus.py --brand apple --section typography
python3 -I scripts/query_corpus.py --brand stripe --section depth

# 按特征找（实现见 query_corpus.py）
python3 -I scripts/query_corpus.py --brands --filter dark,low-saturation
```

**格式**：74 份是 YAML frontmatter（可程序解析），10 份是散文格式（视觉语言在正文里，
没有结构化 token 块）。散文格式的不要指望 `--section` 命中，直接读正文。

## 全部 84 个品牌

| # | 品牌 | 文档名 | Hex 数 | 格式 | 一句描述 |
|---:|---|---|---:|---|---|
| 1 | `1win` | 1win Analysis | 10 | YAML | An analysis of 1win's design language — a near-black crypto casino and sportsbook built on Inter at heavy w... |
| 2 | `airbnb` | Airbnb-design-analysis | 19 | YAML | A warm, generous consumer marketplace anchored on a clean white canvas and Airbnb Rausch (#ff385c), the sin... |
| 3 | `airtable` | Airtable-design-analysis | 23 | YAML | A sober, editorial workflow-software interface anchored on white canvas and dark-ink type, where brand volt... |
| 4 | `aljazeera` | Al Jazeera Analysis | 19 | YAML | An analysis of Al Jazeera's design language — a hard-news editorial system built on flat white paper and de... |
| 5 | `apple` | Apple-design-analysis | 17 | YAML | A photography-first interface that turns marketing into a museum gallery. Edge-to-edge product tiles altern... |
| 6 | `binance` | Binance-design-analysis | 18 | YAML | A confident financial-platform interface anchored on a deep near-black canvas, where Binance's iconic yello... |
| 7 | `bmw` | BMW-design-analysis | 22 | YAML | BMW's corporate site — distinct from BMW M's motorsport-bombastic variant, this is a measured and settled c... |
| 8 | `bmw-m` | BMW-M-design-analysis | 17 | YAML | A motorsport-engineering interface anchored on a near-black canvas with white BMW Type Next Latin display h... |
| 9 | `bugatti` | Bugatti-design-analysis | 14 | YAML | An austere luxury-automotive interface that uses near-pure black canvas, white uppercase letterspaced displ... |
| 10 | `cal` | Cal.com-design-analysis | 21 | YAML | A clean, calendar-software-first interface anchored on white canvas with black primary CTAs and custom Cal ... |
| 11 | `claude` | Claude-design-analysis | 23 | YAML | A warm-canvas editorial interface for Anthropic's Claude product. The system anchors on a tinted cream canv... |
| 12 | `clay` | Clay-design-analysis | 26 | YAML | A vibrant claymation-meets-data interface for Clay.com (GTM data-orchestration platform). Anchors on white ... |
| 13 | `clickhouse` | ClickHouse-design-analysis | 18 | YAML | A high-performance database interface anchored on near-pure black canvas with electric yellow as the brand ... |
| 14 | `cohere` | Cohere-design-analysis | 21 | YAML | Cohere's 2026 web system is a controlled enterprise AI interface built from stark white editorial space, de... |
| 15 | `coinbase` | Coinbase-design-analysis | 15 | YAML | An institutional-grade crypto exchange whose marketing surfaces read like a quietly-confident financial-ser... |
| 16 | `composio` | Composio-design-analysis | 18 | YAML | A developer-tools brand for AI-agent tool integration whose marketing surfaces lean into a dark, technical ... |
| 17 | `cursor` | Cursor-design-analysis | 19 | YAML | An AI-first code editor whose marketing site reads like a quietly-confident developer-tools brand with a wa... |
| 18 | `dell-1996` | Dell 1996 Inspired | 15 | YAML | An inspired interpretation of Dell.com's 1996 design language — a catalog-era enterprise web design built a... |
| 19 | `dji` | DJI Analysis | 31 | YAML | An analysis of DJI's design language — a product-photography showroom for drones and cameras, where full-bl... |
| 20 | `elevenlabs` | ElevenLabs-design-analysis | 19 | YAML | A voice-AI brand whose marketing surfaces read like a quietly editorial print magazine. The base canvas is ... |
| 21 | `expo` | Expo-design-analysis | 21 | YAML | A React Native developer-platform whose marketing site reads like a quietly-confident infrastructure brand.... |
| 22 | `ferrari` | Ferrari-design-analysis | 20 | YAML | A luxury-automotive brand whose marketing surfaces read as cinematic editorial. The base canvas is **near-b... |
| 23 | `figma` | Figma-design-analysis | 14 | YAML | A confident black-and-white editorial frame interrupted by oversized, hand-cut pastel color blocks. The mar... |
| 24 | `framer` | Framer-design-analysis | 14 | YAML | A confident dark-canvas builder marketing site that treats the page like a working artboard — pure black su... |
| 25 | `hashicorp` | HashiCorp-design-analysis | 22 | YAML | An enterprise-infrastructure marketing canvas built around a near-black ground (#000000) and a system of pe... |
| 26 | `hp` | HP-design-analysis | 20 | YAML | An inspired interpretation of HP's design language — a white-paper enterprise-consumer system anchored by H... |
| 27 | `ibm` | IBM-design-analysis | 15 | YAML | An enterprise-marketing canvas faithful to Carbon Design System: white surfaces, charcoal type, IBM Blue (#... |
| 28 | `intercom` | Intercom-design-analysis | 19 | YAML | An editorial customer-service marketing canvas built around a soft cream-white ground, charcoal type set in... |
| 29 | `jobright` | Jobright Analysis | 7 | YAML | An analysis of Jobright's design language — an AI job-hunting platform built on an energetic spring-mint gr... |
| 30 | `kraken` | kraken | 11 | 散文 |  |
| 31 | `lamborghini` | lamborghini | 20 | 散文 |  |
| 32 | `linear.app` | Linear-design-analysis | 21 | YAML | A near-black product-focused marketing canvas built around #010102 (the deepest dark surface of any tool in... |
| 33 | `lovable` | lovable | 7 | 散文 |  |
| 34 | `mastercard` | mastercard | 19 | 散文 |  |
| 35 | `mercury` | Mercury Analysis | 13 | YAML | An analysis of Mercury's design language — a fintech system that moves between a deep ink-violet night worl... |
| 36 | `meta` | Meta-design-analysis | 26 | YAML | Meta's design system spans hardware commerce (Quest VR, Ray-Ban Meta AI glasses) and brand surfaces with a ... |
| 37 | `minimax` | MiniMax-design-analysis | 25 | YAML | MiniMax presents itself as a premium AI infrastructure brand through a striking duality — bold black-pill C... |
| 38 | `mintlify` | Mintlify-design-analysis | 26 | YAML | Mintlify presents documentation infrastructure with a dual-mode aesthetic — atmospheric sky-gradient market... |
| 39 | `miro` | Miro-design-analysis | 34 | YAML | Miro presents itself as the AI-powered visual workspace through a confident, almost playful brand voice — a... |
| 40 | `mistral.ai` | Mistral-AI-design-analysis | 26 | YAML | Mistral AI brands itself with a singular signature — atmospheric sunset gradients (mustard, orange, deep re... |
| 41 | `mongodb` | MongoDB-design-analysis | 26 | YAML | MongoDB carries a strong dual-mode visual identity — dark deep-teal hero bands with bright MongoDB green ({... |
| 42 | `mydealz` | mydealz Analysis | 15 | YAML | An analysis of mydealz's design language — a high-density German deals-community system built on a confiden... |
| 43 | `nerdwallet` | NerdWallet Analysis | 22 | YAML | An analysis of NerdWallet's design language — a personal-finance comparison platform built almost entirely ... |
| 44 | `nike` | Nike-design-analysis | 21 | YAML | A photography-first commerce system built on extreme typographic contrast — towering uppercase Futura displ... |
| 45 | `nintendo-2001` | Nintendo.com (2001) Analysis | 17 | YAML | An analysis of Nintendo.com's 2001 design language — a brushed-periwinkle "console chrome" interface where ... |
| 46 | `notion` | Notion-design-analysis | 42 | YAML | Notion presents itself as the all-in-one workspace through a confident, illustration-rich brand voice — anc... |
| 47 | `nvidia` | NVIDIA-design-analysis | 22 | YAML | An engineering-grade marketing system organized around two surface modes — a deep black canvas for hero and... |
| 48 | `ollama` | Ollama-design-analysis | 13 | YAML | An almost defiantly minimal documentation-first system that treats the home page like a Markdown README — p... |
| 49 | `opencode.ai` | OpenCode-design-analysis | 20 | YAML | A terminal-native marketing system rendered entirely in Berkeley Mono — every word on the page, from the he... |
| 50 | `oracle` | Oracle Analysis | 20 | YAML | An analysis of Oracle's design language — an enterprise system built on a warm neutral ladder rather than a... |
| 51 | `oura` | Oura Analysis | 25 | YAML | An analysis of Oura's design language — a warm-paper wellness system that pairs a high-contrast Editorial s... |
| 52 | `pinterest` | Pinterest-design-analysis | 21 | YAML | A photography-first discovery system organized around the Pinterest Red CTA, the masonry pin grid, and a so... |
| 53 | `playstation` | PlayStation-design-analysis | 21 | YAML | A three-surface marketing system organized around alternating black, white, and PlayStation Blue chapters t... |
| 54 | `posthog` | PostHog-design-analysis | 25 | YAML | A playful developer-tools system rendered on a warm cream canvas with hand-drawn hedgehog mascots dotted ac... |
| 55 | `raycast` | Raycast-design-analysis | 21 | YAML | Raycast's marketing system reads like an extended product screenshot. The chrome IS the in-product chrome a... |
| 56 | `renault` | Renault-design-analysis | 17 | YAML | Renault's web presence pairs the freshly-modernised Renault diamond |
| 57 | `replicate` | Replicate-design-analysis | 17 | YAML | Replicate's marketing surfaces pair the warm-cream developer-tools aesthetic |
| 58 | `resend` | Resend-design-analysis | 16 | YAML | Resend's marketing surfaces sit on a near-pure black canvas with off-white |
| 59 | `revolut` | Revolut-design-analysis | 27 | YAML | Revolut's marketing surfaces pair a stark black canvas with the brand's |
| 60 | `runwayml` | runwayml | 17 | 散文 |  |
| 61 | `sanity` | sanity | 16 | 散文 |  |
| 62 | `sap` | SAP Analysis | 15 | YAML | An analysis of SAP's design language — an enterprise system that keeps almost everything on white and spend... |
| 63 | `sentry` | Sentri-Inspired-design-analysis | 17 | YAML | An inspired interpretation of Sentri's design language — a developer-tools brand built on a deep purple-vio... |
| 64 | `shopify` | Shopifi-Inspired-design-analysis | 17 | YAML | An inspired interpretation of Shopifi's design language — a cinematic commerce platform that runs two paral... |
| 65 | `slack` | Slacc-Inspired-design-analysis | 18 | YAML | An inspired interpretation of Slacc's design language — a workplace messaging brand built on a deep aubergi... |
| 66 | `spacex` | Spacex-Inspired-design-analysis | 8 | YAML | An inspired interpretation of Spasex's design language — a mission-oriented aerospace brand built on pure b... |
| 67 | `spotify` | spotify | 18 | 散文 |  |
| 68 | `starbucks` | starbucks | 18 | 散文 |  |
| 69 | `stripe` | Stripi-Inspired-design-analysis | 19 | YAML | An inspired interpretation of Stripi's design language — a financial-infrastructure brand built on a deep n... |
| 70 | `supabase` | Supabaze-Inspired-design-analysis | 25 | YAML | An inspired interpretation of Supabaze's design language — an open-source database platform built on a clea... |
| 71 | `superhuman` | Superhumon-Inspired-design-analysis | 14 | YAML | An inspired interpretation of Superhumon's design language — a fast-email productivity brand split between ... |
| 72 | `tesla` | tesla | 9 | 散文 |  |
| 73 | `theverge` | theverge | 16 | 散文 |  |
| 74 | `together.ai` | Together-AI-Inspired-design-analysis | 12 | YAML | An inspired interpretation of Together AI's design language — an AI infrastructure platform whose surface a... |
| 75 | `uber` | Uber-Inspired-design-analysis | 10 | YAML | An inspired interpretation of Uber's design language — a transportation-and-delivery super-app brand whose ... |
| 76 | `vercel` | Vercel-Inspired-design-analysis | 30 | YAML | An inspired interpretation of Vercel's design language — a developer-platform brand whose surface is a star... |
| 77 | `vodafone` | Vodafone-Inspired-design-analysis | 6 | YAML | An inspired interpretation of Vodafone's design language — a telecom super-brand whose web surface alternat... |
| 78 | `voltagent` | Voltagent-Inspired-design-analysis | 12 | YAML | An inspired interpretation of Voltagent's design language — a developer-focused AI agent engineering platfo... |
| 79 | `warp` | Warp-Inspired-design-analysis | 7 | YAML | An inspired interpretation of Warp's design language — an agentic terminal-and-development-environment bran... |
| 80 | `webflow` | Webflow-Inspired-design-analysis | 17 | YAML | An inspired interpretation of Webflow's design language — a visual web development platform whose surface c... |
| 81 | `wired` | Wired-Inspired-design-analysis | 7 | YAML | An inspired interpretation of Wired's design language — a flagship technology-magazine brand whose surface ... |
| 82 | `wise` | Wise-Inspired-design-analysis | 21 | YAML | An inspired interpretation of Wise's design language — a global money-transfer brand whose surface combines... |
| 83 | `x.ai` | xAI-Inspired-design-analysis | 15 | YAML | An inspired interpretation of xAI's design language — Elon Musk's frontier-AI company whose web surface is ... |
| 84 | `zapier` | Zapier-Inspired-design-analysis | 9 | YAML | An inspired interpretation of Zapier's design language — a workflow-automation platform whose surface combi... |

## 选择建议

- **暗色技术产品**：`linear.app`、`vercel`、`raycast`、`supabase`、`expo`。
  看它们的 surface 阶梯与强调色面积，不要看具体 hex。
- **消费/友好**：`airbnb`、`stripe`、`notion`、`figma`、`pinterest`。
  看圆角与留白如何降低压迫感。
- **编辑/文化**：`wired`、`theverge`、`claude`、`apple`。
  看衬线标题与无衬线正文的分工、栏宽。
- **奢华/工业**：`ferrari`、`bmw`、`bmw-m`、`bugatti`、`lamborghini`。
  看黑/金/红的关系与几何精度。

> 这是索引，不是规范。品牌文档是别人对别人产品的观察，
> 你的题材不同，落点必须不同。
