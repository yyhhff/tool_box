# TASK-0036 生词卡：删除连读按钮

- **状态**：已完成
- **优先级**：低
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户 2026-11-19："生词卡：删除连读按钮"。即删除 TASK-0035 加在生词卡"怎么读"右侧的 `.pron-link-entry` 连读按钮；对话气泡里的连读功能与独立试听保留不动。

## 需求分析与方案

- **目标**：仅移除生词卡连读入口，不影响对话气泡连读体系
- **改动点**：`frontend/app.js`（renderVocab 移除 linkText/linkEntry/linkRow，恢复只输出 pronEntry）；`frontend/styles.css`（移除 .pron-entries/.pron-link-entry，保留 .lk-pair-say）；`frontend/index.html`（js v20→v21、css v17→v18）
- **涉及数据**：无
- **确认方式**：持续迭代模式，用户指令明确（单一删除操作）

## 验收标准

- [x] 生词卡无连读按钮、怎么读保留
  - 实测（:8001）：`.v .pron-link-entry` = 0、`.v .pron-entries` = 0；`.v .pron-word-entry` = 34 保留
- [x] 对话气泡连读与独立试听零回归
  - 实测：`.chat-lk-btn` = 2；点开连读块存在，独立试听（提示行 5 + 示例 4）、整句播放均在；中文 `.cn .v-tok` = 0
- [x] `node --check` 通过；数据库零改动
  - PASS；版本号 js v21/css v18；无 pron-link-entry/pron-entries 残留

## 变更记录

- 2026-11-19 创建并完成（持续迭代模式，单一删除操作；多角色分工 + 真机验收留痕）
