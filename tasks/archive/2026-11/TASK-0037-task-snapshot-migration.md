# TASK-0037 切号任务列表迁移：接管客户端任务快照

- **状态**：进行中
- **优先级**：高
- **项目**：tools/workbuddy-multi-account
- **创建日期**：2026-11-19
- **完成日期**：

## 原始需求

排查并修复多账号挂机与聊天合并工具中的任务列表迁移问题：当前账号切换已能成功执行，但切换后原账号的任务列表没有迁移或加载到目标账号。请确保任务列表与账号正确绑定，切换后按对应账号恢复任务数据，避免任务丢失、重复或串号，并给出必要的验证步骤。

用户在确认环节补充裁决：
- 任务列表 = **WorkBuddy 客户端真实任务列表**（不是工具自带的签到任务模板，也不是工具库里的 chat_messages）
- 机制 = **复制**（源账号保留），相同任务以**最新快照为准覆盖**，避免大量副本
- 写入时机 = `activate`（设为客户端登录）成功后自动迁移
- 允许工具接管客户端任务快照（停机 + 备份 + 写回 + 重启）

## 需求分析

- **目标**：切号后把源账号的客户端任务列表合并进目标账号，按 id 去重、以最新快照覆盖，不丢失、不重复、不串号。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `tools/workbuddy-multi-account/`（工具索引行状态更新）
- **涉及数据**（引用数据地图 `docs/data_content.md`）：
  - 客户端侧：`~/.workbuddy/<uid>/sidebar-list-snapshot.json`（侧边栏任务列表，UI 直接渲染）+ `~/.workbuddy/workbuddy.db` 的 `sessions` 表（按 user_id 隔离）——新增登记
  - 工具侧：`tools/workbuddy-multi-account/credentials/<account_id>.info` 的 `account.uid`（已解析的 uid 映射，白名单读取，不碰 token）

### 实测根因（只读调研，2026-11-19）

| 事实 | 证据 |
|------|------|
| 工具账号 ↔ uid 映射已存在于凭据快照 | `credentials/acc_…1a45a6.info` → `account.uid=849f279b-…`；`acc_…a6fc80.info` → `uid=3773931e-…` |
| 客户端任务列表 = sidebar 快照 | `~/.workbuddy/<uid>/sidebar-list-snapshot.json`，849f 有 9 个任务，3773 为 `items:[]` |
| 会话记录在 sessions 表按 user_id 隔离 | `workbuddy.db` sessions 表 16 条全部 `user_id=849f…` |
| 本工具 activate 从不动任务数据 | `services/account_service.py::activate_account` 只写凭据 + 重启 |
| 现有迁移钩子是空壳且前端未调用 | `api/accounts.py::migrate_chat_records` SQL 全注释；`/switch` 前端从未调用 |

## 方案（已确认）

- **实现思路**：新增 `services/task_snapshot_service.py`，用白名单从 `credentials/<id>.info` 读 `account.uid` 建立账号↔uid 映射；读源/目标 `sidebar-list-snapshot.json`，按任务 id 去重合并（同 id 取 `updatedAt`/`lastActivityAt` 更新者覆盖），备份后原子写回目标；配套复制 `sessions` 表对应记录并改 `user_id`。`activate` 成功后若目标账号 `auto_merge` 则调用。`Account` 加 `uid` 列（轻量迁移）便于展示。
- **改动点清单**：
  - `config.py`：新增 `CLIENT_DATA_ROOT`（默认 `~/.workbuddy`，环境变量覆盖）+ 备份目录
  - `models.py`：`Account` 加 `uid` 列 + `_ensure_columns` 迁移
  - `services/task_snapshot_service.py`（新）：uid 解析、快照读写、去重合并、备份回滚、sessions 复制、编排
  - `api/accounts.py`：`activate` 成功后触发迁移；处理空的 `migrate_chat_records`
  - `static/index.html`：账号卡片显示 uid；切号提示迁移结果
  - `tests/test_task_snapshot.py`（新）：unittest 覆盖解析/去重/备份/幂等/串号隔离
  - 文档：README、两张地图、任务文件
- **风险与限制**：
  - `~/.workbuddy/workbuddy.db` 客户端占用中（有 wal/shm），写入必须**关闭客户端 + 备份三件套**，写完重启；
  - 客户端快照格式随版本变化，用白名单字段容错（缺字段回退）、整对象搬迁 token/envelope 原样保留；
  - 云同步可能回写覆盖本地合并结果，属客户端行为，工具只保证本地快照正确。
- **用户确认日期**：2026-11-19

## 子任务

- [x] 1. 登记任务 + 多角色分工（总指挥）
- [x] 2. 后端：config/models/task_snapshot_service/api 实现（backend-dev）
- [x] 3. 前端：index.html 显示 uid + 切号提示（总指挥）
- [x] 4. 测试：13 用例 unittest 覆盖核心逻辑（test-dev）
- [x] 5. 总指挥：单测 13/13 + py_compile 5 文件 + 真实数据只读 dry-run + 回传链静态核验，逐条验收通过
- [x] 文档：README + 两张地图同步（总指挥）

## 验收标准

- [x] 单测全绿：`python -m unittest discover -s tools/workbuddy-multi-account/tests` → Ran 13, OK
- [x] uid 解析：从两份凭据快照白名单读出正确 uid（849f/3773），不读 token 值；test 1-3
- [x] 去重合并：同 id 取更新快照；源保留；重复执行不累积（幂等）；test 5-8 + 后端自测
- [x] 备份回滚：写前生成带时间戳备份，失败可回滚；test 9 + write_snapshot_atomic 实现
- [x] 串号隔离：只合并源→目标，不污染第三个 uid；test 11 逐字节比对
- [x] dry-run：真实数据只读预演 → will_add=9/will_update=0/final=9，两份快照字节前后一致
- [x] 回传链：`task_migration` 从回调→result→API→前端静态核验闭合
- [ ] 真机（需用户在场）：切号后目标快照含源任务、客户端 UI 可见、原号不受损——**待用户真机验收，本轮未执行（不 kill 客户端）**

## 变更记录

- 2026-11-19 创建（方案经用户三轮确认）
