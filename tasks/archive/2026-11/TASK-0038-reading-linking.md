# TASK-0038 分级阅读接入连读教学

- **状态**：已完成
- **优先级**：中
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户 2026-11-19："分级阅读也要连读功能"。即把已在对话气泡落地的 🔗 连读能力（TASK-0034/0035）扩展到分级阅读页的逐句对话与整篇原文。同批另有两个咨询项（真麦克风端到端验收内容、UX_PROGRESS_PLAN 4 个开放项）在对话中直接答复，不属本任务改动。

## 需求分析与方案

- **目标**：阅读页法语文本（逐句 `l.fr` + 整篇 `body_fr`）旁挂 🔗 连读按钮，检测到连读对才显示；点击原地展开连读块（整句示范 + 联诵/连音位置 + 独立试听 + 规则小卡），复用 `chatLinkBtnHTML` 与 `toggleLinkingInline`，零新增逻辑。
- **改动点**：`frontend/app.js`（renderReadLines 两处加 `chatLinkBtnHTML`；toggleLinkingInline 容器定位扩展兼容 `.rbubble`/`.whole-fr`）；`frontend/index.html`（js v21→v22）；styles.css 视需要微调。
- **涉及数据**：无（连读检测纯前端、规则数据已缓存）。
- **关键设计**：
  - 逐句连读按钮放在 `.rbubble` 内、🔊 `rplay` 之后；整篇原文按钮放在 `.whole-fr` 的 `<p>` 之后。
  - `toggleLinkingInline` 容器定位由 `btn.closest('.v') || .bubble || .say` 扩展为再加 `.rbubble`/`.whole-fr`；插入用现有 `row.parentNode===v ? afterend : appendChild` 逻辑即可落在正确位置。
  - 中文译文 `<p class="cn">` 不加连读按钮、不受影响。

## 子任务

- [x] 子任务 1：renderReadLines 逐句 + 整篇原文加连读按钮；toggleLinkingInline 容器兼容
- [x] 子任务 2：版本号 js v22（复用现有样式，未改 css）
- [x] 子任务 3：浏览器真机验收 + 留痕

## 验收标准

- [x] 阅读页逐句对话与整篇法语原文的连读句旁出现 🔗 按钮（有连读对才显示），中文译文旁无按钮
  - 实测（:8001，《在面包店》）：逐句 `.rbubble .chat-lk-btn` = 3、整篇 `.whole-fr .chat-lk-btn` = 1、中文 `.cn .chat-lk-btn` = 0；按钮 data-text 为整句，🔊 rplay = 6 保留
- [x] 点击连读按钮，连读块内嵌到对应 `.rbubble` / `.whole-fr` 内，再点收起
  - 实测：逐句块 inBubble:true（整句示范 + 1 条位置提示 + 独立🔊 + 规则小卡），整篇块 inWholeFr:true（5 条位置）；按钮「🔗 连读」↔「🔗 收起连读」，收起后块消失
- [x] 独立试听只请求对应片段 TTS，不触发整句播放
  - 实测（fetch 拦截）：点位置提示试听只请求 `voudrais une`，整句 `Bonjour ! Je voudrais une baguette...` 未被触发
- [x] 对话气泡、生词卡既有功能零回归；`node --check` 通过；数据库零改动
  - 实测：对话逐词 20、生词卡「怎么读」34 / 逐词 47 / 连读按钮 0、中文 0 词位、阅读逐词 41 均与历史一致；node --check PASS

## 变更记录

- 2026-11-19 创建并完成（持续迭代模式，多角色分工 + 真机验收留痕；同批咨询项已在对话答复）
