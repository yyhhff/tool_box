# TASK-0050 重置对话：UI 与持久化同步清空

- **状态**：已完成
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户：点击重置对话，本场景的对话记录就初始化，持久化存储里也清掉。

## 背景

TASK-0040 让「重置对话」只具备"重开"语义（前端不带历史渲染），但数据库里该场景的真实对话轮仍保留，下次进场景会被读回。本任务把重置做成真正的"清空"。

## 方案

- 后端新增 `DELETE /api/chat/history?scene_id=xxx`：删除该场景 `created_at IS NOT NULL` 的对话轮（种子开场白 `created_at IS NULL` 保留），返回删除条数；scene_id 缺省清全部场景；未知场景 404
- `db.clear_dialogue_history(user_id, scene_id)`：与 `list_dialogue_history` 同样的过滤口径，DELETE 后返回 rowcount
- 前端 `resetChat` 改 async：在线模式先 `confirm` 提示（明确告知持久化会清空），确认后调 DELETE，成功才 `selectScene(id, {withHistory:false})` 重开；DELETE 失败不重开（避免 UI 与存储不一致）；离线模式维持原 fallback 语义
- js 版本 v27→v28

## 改动点

- `backend/db.py`：新增 `clear_dialogue_history`
- `backend/app.py`：新增 `DELETE /api/chat/history`
- `frontend/app.js`：`resetChat` 在线模式加确认 + 先清持久化再重开
- `frontend/index.html`：js v28

## 子任务

- [x] 子任务 1：后端清空接口 + db 函数
- [x] 子任务 2：前端确认 + 调用 + 版本号
- [x] 子任务 3：真机验收 + :8001 重启

## 验收标准（全部通过）

- [x] API 层：cafe 场景 DELETE 返回 `deleted:100`，GET 复查 0 条；重发一轮对话后 DELETE 返回 `deleted:2`、复查 0 条；种子开场白 3 条保留；未知场景返回 40401
- [x] UI 层（agent-browser 真机）：重置点击后气泡回到 3 条种子开场白，`/api/chat/history` 复查 0 条
- [x] `node --check` + `py_compile` 通过；:8001 常驻服务已重启加载新代码
