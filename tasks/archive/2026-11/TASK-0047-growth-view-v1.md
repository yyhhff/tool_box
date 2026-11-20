# TASK-0047 「我的成长」视图 v1（真实数据聚合）

- **状态**：已完成
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户指令「继续开发」。按 `docs/UX_PROGRESS_PLAN.md` P0 分期，TASK-0040 已交付持久化底座，本轮交付 P0 剩余薄片中的「我的成长」视图 v1：聚合真实学习数据让用户"看见自己"。画像 v1 与 onboarding 留下一轮。

## 方案（已按持续迭代模式确认实施）

- 新增第五个视图「🌱 成长」：复用 `GET /api/profile` 现有真实 stats（total_cards / new_words_week / mastered_count / dialogue_count / due_cards_count / accuracy），后端仅补暴露 `review_count`（累计复习次数 = SUM(review_logs.total_reviews)，聚合已有）
- 五张卡：词汇（累计/本周/已掌握）、对话（累计轮数）、复习（今日待复习/累计次数/正确率）、阅读（温和空态——阅读完成未落库，记篇目留后续）、画像（下轮）
- 顺手修复 TASK-0040 遗留缺陷：`FALLBACK_PROFILE.stats` 仍是假值（8/46/1024/0.87），归零并补全新字段
- 文案口径：温和鼓励，无施压词；空态不制造"0 恐慌"

## 改动点

- `backend/db.py`：get_profile stats 增 `review_count`
- `frontend/index.html`：「🌱 成长」tab + viewGrowth 容器；js v24→v25
- `frontend/app.js`：switchView 支持 'growth' + renderGrowth()；FALLBACK_PROFILE.stats 归零补全
- `frontend/styles.css`：growth 卡片样式（最小新增）

## 子任务

- [x] 子任务 1：db.py stats 增 review_count；FALLBACK_PROFILE.stats 归零补全
- [x] 子任务 2：前端成长视图（tab + 容器 + switchView + renderGrowth）+ 样式 + 版本号
- [x] 子任务 3：验收（py_compile/node --check + 临时实例 curl + 浏览器真机数字一致性/空态/零回归）+ 留痕

## 验收标准

- [x] 成长页各数字与 `GET /api/profile` 返回一致（词汇/对话/复习三卡全部真实）
- [x] 阅读卡温和空态，无假数据、无施压文案
- [x] 离线兜底 FALLBACK_PROFILE.stats 全 0（不再拿假数字冒充）
- [x] 原有 4 视图切换与既有功能零回归；`py_compile`/`node --check` 通过；数据库 schema 零改动

## 变更记录

- 2026-11-19 创建并完成（持续迭代模式，多角色分工）
