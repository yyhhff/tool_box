# TASK-0034 场景对话框逐词点击 + 连读迁移到对话气泡

- **状态**：已完成
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户 2026-11-19 纠正 TASK-0033 方向："我要的是在场景对话框中直接单个词点击，将 🔗 连读迁移到场景对话框中"。即对话陪练的聊天气泡里法语单词可直接点（贴词气泡学发音），并把目前只在生词卡的 🔗 连读能力迁到对话气泡里原地学习。

## 需求分析

- **目标**：①对话气泡（用户句 / 呀回复 / 重述卡）法语逐词可点弹贴词气泡；②🔗 连读入口进对话气泡、内嵌展开
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `frontend/app.js`：messageHTML 三处 `esc(m.fr)` → `sentenceTokensHTML(m.fr)`；新增对话气泡连读按钮 + toggleLinkingInline 容器适配
  - `frontend/styles.css`：气泡内 v-tok（白字场景）/ lk-inline 样式适配；生词卡连读按钮隐藏（代码保留）
  - `frontend/index.html`：js v18→v19、css v15→v16
- **涉及数据**：无（零后端/数据库改动）

## 方案（已确认 2026-11-19）

- **实现思路**：复用 TASK-0029/0032 现有组件（sentenceTokensHTML / openWordPopover / toggleLinkingInline），只改渲染入口与容器定位，不重写逻辑。
- **改动点清单**：
  - messageHTML：三处法语文本逐词化，🔊 整句按钮保留；用户句气泡白字需给 v-tok 适配样式
  - 对话连读：每条 assistant/重述句气泡的 🔊 旁加 🔗 按钮，data-text=整句；toggleLinkingInline 容器从硬依赖 `.v` 改为兼容 `.bubble`/`.say`
  - 生词卡连读按钮：CSS 隐藏（加 `.lk-legacy` class + display:none），代码保留待用户下次裁决
  - 版本号 js v19 / css v16
- **风险与限制**：
  - `.bubble` 内插入 lk-inline 需 change 定位逻辑（原 `row.parentNode===v` 判断依赖 .v-ex 结构）；对齐后复用同一展开块
  - user 气泡为深橙底白字，v-tok 虚线默认深色看不清 → 需给 `.row.user .bubble .v-tok` 白色描边
  - 连读块展开撑高气泡，renderChat 已自动滚到底
- **用户确认日期**：2026-11-19（裁决：阅读页逐词化保留；生词卡连读按钮先隐藏、代码留着）

## 子任务

- [x] 子任务 1：messageHTML 三处逐词化 + 对话连读按钮 + toggleLinkingInline 容器适配
- [x] 子任务 2：样式适配（用户气泡白字 v-tok + lk-inline 气泡内）+ 生词卡连读按钮隐藏 + 版本号
- [x] 子任务 3：浏览器真机验收（气泡点词/连读展开收起/中文与🔊零回归/生词卡连读隐藏）+ 留痕

## 验收标准

- [x] 对话气泡（我/呀/重述卡）法语词虚线可点弹贴词气泡（🔊+规则）；中文译文不受影响，🔊 整句保留
  - 实测（:8001）：用户句 7 词、助手句 13 词逐词化；点 "Je" 弹 pron-pop（含🔊、anchor 正确、模态未弹）；重述卡内存注入验证 7 词逐词化；三类消息中文 `.cn` 词位均 = 0；气泡内 🔊 3 个保留
- [x] 对话气泡内 🔗 连读可内嵌展开（整句示范 + 联诵/连音提示 + 收起），展开块落在气泡内
  - 实测：连读按钮 2 个（data-text 为整句）；点按钮展开 `.lk-inline` 落在 `.bubble` 内（existsInBubble:true），含整句示范 + 🔊 播放 + 1 条联诵/连音提示，按钮变「🔗 收起连读」；再点收起、块消失、按钮还原
- [x] 生词卡连读按钮隐藏（不显示但代码在）；既有生词卡逐词/发音零回归
  - 实测：生词卡 `.lk-legacy` 代码 14 处、`getComputedStyle.display = none`（隐藏）；既有逐词 47 / 发音入口 34 / 🔊 35 均保留
- [x] `node --check` 通过；数据库零改动
  - `node --check frontend/app.js` PASS；版本号 js v19 / css v16；零后端/数据库改动

## 变更记录

- 2026-11-19 创建（用户纠正方向，多角色分工，方案已确认）
- 2026-11-19 完成：新增 chatLinkBtnHTML（仅检测到连读对的句子才显按钮）；messageHTML 三处法语逐词化；toggleLinkingInline 容器兼容 .v/.bubble/.say；生词卡连读按钮加 .lk-legacy class 由 CSS 隐藏（代码保留待用户下次裁决删/覆盖）。样式：用户橙底气泡 v-tok 白色虚线适配、chat-lk-btn 间距。阅读页逐词化（TASK-0033）按用户裁决保留。浏览器真机验收全过、留痕如上
