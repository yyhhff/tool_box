# TASK-0040 学习进度持久化 P0：对话历史读回 + 假值清零 + 真实统计

- **状态**：已完成
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户 2026-11-19："继续后续开发，持久化"。即启动 UX_PROGRESS_PLAN 的 P0 薄片（持久化底座）。4 个开放项按用户"按推荐方案来"惯例拍板：①P0 薄片优先；②seed 假值清零重来；③七维采集前端先展示五维（本轮仅底座，不涉及画像表）；④XP 保留为激励分但只记真实行为。

## 需求分析与方案

- **目标**：解决"写了读不回、展示假值、无回路"三断点——对话历史读回、xp/streak 假值清零（迁移幂等）、profile 统计全真实化、顶部"词汇"错位修复。
- **裁决**：seed 场景开场对话与场景词卡是**内容**不是假进度，不删（与方案 §5.5"演示行删除"区分开）；只清零 xp/streak/last_active_date。
- **改动点**：
  - `backend/db.py`：`ensure_profile_initialized()`（PRAGMA 查列 → ALTER 加 profile_initialized → 未初始化行 xp/streak/last_active_date 清零并置 1，幂等）；`list_dialogue_history()`（created_at IS NOT NULL 排除种子预置行，id 倒序取再反转）；`get_profile()` stats 加 `total_cards`/`dialogue_count`，due 查询补 user_id 过滤（方案 §5.2 既定修正）
  - `backend/app.py`：启动段调迁移；新增 `GET /api/chat/history?scene_id=&limit=`（默认 50 上限 200，输出 `{items, has_more}`）
  - `backend/seed.py`：SEED_USER xp 1280→0、streak 12→0（新库从真实 0 起）
  - `frontend/app.js`：FALLBACK_PROFILE xp/streak 假值改 0；`selectScene` 在线模式拉历史 append 到 start_dialogue 后（`withHistory` 参数，`resetChat` 保持"重开"语义不带历史）；`renderTop` 顶部"词汇"改显示真实词卡数（原填 XP 属错位）；`renderLedger` 加「累计对话」
  - `frontend/index.html`：台账区加一格「累计对话」；js v23→v24
- **涉及数据**：users 表加列 + 现有行清零（迁移，用户已批准）；其余零 schema 变更。

## 子任务

- [x] 子任务 1：db.py 迁移函数 + history 查询 + profile stats 增强
- [x] 子任务 2：app.py history 端点 + 启动迁移；seed.py 假基数归零
- [x] 子任务 3：前端历史恢复 + FALLBACK/顶部/台账真实化 + 版本号
- [x] 子任务 4：验收（py_compile + node --check + 临时实例 curl 端到端 + 浏览器真机刷新恢复）+ 留痕

## 验收标准

- [x] 迁移幂等：模拟 xp=77 后重跑迁移保持 77、profile_initialized=1；清零后 chat 一次 xp=20、streak=1
- [x] `GET /api/chat/history`：种子预置行不出现（全部 created_at 有值）；chat 后返回 user+assistant 轮（id 117/118，assistant 带 recast_of）；limit 分页 has_more 正确；limit=0→40001、场景不存在→40401
- [x] 前端：进入场景恢复历史（真机 :8021 全新加载 chatLog=53 = 开场 3 + 历史 50，末条为最近对话）；重置按钮仍为"重开"（3 条全预置）；FALLBACK_PROFILE 0/0
- [x] 顶部"词汇"显示真实词卡数 46（原填 XP 属错位，已修）；台账「累计对话」106；`GET /api/profile` stats 含 total_cards=46/dialogue_count=106，due 查询已带 user_id 过滤
- [x] `py_compile`/`node --check` 通过；:8021 实例日志全端点 200（其余端点零回归）；js v24

## 变更记录

- 2026-11-19 创建并完成（持续迭代模式；4 开放项按推荐口径拍板：P0 优先/清零重来/七维采集展示五维/XP 保留只记真实行为。本轮交付持久化底座；「我的成长」完整 5 卡视图、onboarding、画像 v1 留 P0 后续轮次）
