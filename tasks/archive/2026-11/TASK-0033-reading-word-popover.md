# TASK-0033 P2 融入点：分级阅读页逐词点击学发音（复用贴词气泡）

- **状态**：已完成
- **优先级**：中
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

持续迭代模式（用户 2026-11-19 授权）。读音方案 P2 分期「阅读页融入」（PRONUNCIATION_PLAN §8）+ 用户反馈"单个词在对话框里面才会点"的同一使用习惯延伸到阅读页：阅读时遇到不会读的词，原地点击学习。

## 需求分析

- **目标**：分级阅读页三处法语文本逐词可点 → 复用 TASK-0032 贴词气泡（🔊 听发音 + 规则 + 完整讲解入口）：
  ①逐句对话/逐段阅读的每句 `l.fr`；②整篇法语原文 `body_fr`；③右侧生词卡词位 `.rw-word`
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `frontend/app.js`：renderReadLines 用 sentenceTokensHTML 替换 esc；renderReadWords 词位加 v-tok 行为
  - `frontend/index.html`：js v17→v18
- **涉及数据**：无

## 方案（持续迭代模式，复用既有组件直接实施）

- sentenceTokensHTML 已存在且 onclick 已指向 openWordPopover（TASK-0032 时统一替换）——阅读页只需替换渲染调用；中文译文与标题不处理；🔊 整句按钮保留。
- 风险：正文词多，全部包 span 的 DOM 开销可控（每篇 100-200 词）；点词后气泡 z-index 高于阅读容器 ✓。

## 子任务

- [x] 子任务 1：renderReadLines / renderReadWords 逐词化 + js v18
- [x] 子任务 2：浏览器真机验收（正文点词气泡/侧栏词卡点词/🔊 零回归）+ 留痕

## 验收标准

- [x] 阅读页逐句与整篇原文的法语词虚线可点，点击原地弹气泡（含🔊与规则）；中文不受影响
  - 实测（:8001，面包店篇）：逐句对话区 `.fr .v-tok` = 41 词、整篇法语原文 `.whole-fr p .v-tok` = 41 词；点 Bonjour 弹 `.pron-pop`（含 🔊听发音 + 规则「辅音 r 发小舌音 /ʁ/」+ 例词 IPA + 完整讲解入口），模态未弹、URL 不变；中文译文区 `.v-tok` = 0（逐句 + 整篇均 0），中文不受影响
- [x] 侧栏生词卡词位可点弹气泡；整句 🔊、收词、推荐等既有功能零回归
  - 实测：`.rw-word.v-tok` = 7 词，点 "s'il vous plaît" 弹气泡且 anchor 正确；整句 `.rplay` = 6 保留、data-text 正常；`.rw-collect`（收词）、推荐下一篇按钮均在；点空白关闭气泡通过
  - 说明：「再点同一词收起」在对话页（TASK-0032 原场景，未受本任务影响）与阅读页表现一致（均保持弹出），系既有 `openWordPopover`+capture 外点监听的固有行为，非本任务引入回归，不在本任务改动范围
- [x] `node --check` 通过；数据库零改动
  - `node --check frontend/app.js` PASS；无旧引用残留（openPronCardForWord/openLinkingCard）；本任务未触及任何后端/数据文件

## 变更记录

- 2026-11-19 创建（持续迭代模式，P2 既定分期）
- 2026-11-19 完成：子任务 1 代码已在工作中落地（renderReadLines 的 l.fr 与 body_fr 走 sentenceTokensHTML；renderReadWords 词位加 v-tok + openWordPopover；index.html js v13→v18）；多角色审查（前端代码审查 + 架构师风险边界）+ 浏览器真机验收全过，留痕如上。本任务代码改动仅 frontend/app.js（3 处）+ frontend/index.html（版本号）；数据库与数据文件零改动
