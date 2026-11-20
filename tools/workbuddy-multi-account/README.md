# WorkBuddy 多账号管理工具

支持多账号同时登录、自动签到、聊天记录合并与迁移的 WorkBuddy 管理工具。

## 功能特性

### P0 核心功能
- ✅ **多账号管理**
  - 扫码登录多个账号
  - 账号状态监控（在线/离线/登录过期）
  - 账号切换（设为客户端登录，自动重启客户端）
  - 账号删除（清 DB 行 + 凭据快照 + 关联签到/聊天记录，二次确认）

- ✅ **自动签到**
  - 定时任务（每天固定时间）
  - 签到任务列表（每日签到 + 成长中心）
  - 签到结果记录

- ✅ **签到结果可视化**
  - 成功/失败统计
  - 每日积分变化
  - 签到历史记录

### P1 重要功能
- ✅ **聊天记录存储**
  - 每个账号独立存储
  - 历史记录查询

- ✅ **聊天记录合并**
  - 一键合并所有账号的聊天记录到当前账号
  - 按联系人筛选
  - 按时间范围筛选

### P2 增强功能
- ✅ **自动迁移**（v1.4.0，TASK-0037）
  - 切换账号时把源账号的**客户端任务列表**复制合并到目标账号（源保留）
  - 按任务 id 去重，同 id 以 `lastActivityAt`/`updatedAt` 较新的快照为准覆盖，避免副本堆积
  - 写前自动备份 + 原子替换 + 失败回滚，只动目标 uid，不污染其他账号
  - 可配置开关（每账号 `auto_merge`）

- ✅ **账号池可视化**
  - 当前活跃账号高亮
  - 积分统计
  - Token 统计

## 技术栈

- **后端**：FastAPI + Python 3.11+
- **前端**：Next.js 14 + React + TailwindCSS（待开发）
- **数据库**：SQLite
- **任务调度**：APScheduler
- **HTTP 客户端**：urllib（标准库，零额外依赖）

## 真实协议说明（v1.2.0 起）

服务层已接入 WorkBuddy 真实协议（接口路径与判定来自 [88lin/workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin) 实测代码）：

| 项目 | 值 |
|------|-----|
| 端点 | `https://copilot.tencent.com`（凭据文件 `auth.endpoint` 优先） |
| 认证 | `Authorization: Bearer <accessToken>` |
| 凭据来源 | `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info` |
| 签到接口 | `POST /v2/billing/meter/checkin-activity-status` + `POST /v2/billing/meter/daily-checkin` |
| 成长中心 | `/v2/activity/growth/`（tasks / claim / streak / redeem / lottery / buddy ...） |

**多账号机制（切号不用反复扫码的关键）**：
- WorkBuddy 桌面端同一时刻只保存一个账号的登录态
- "添加账号" = 客户端当前登录账号的凭据文件**原样复制为快照**（bind）
- 运行时各账号用各自快照请求，互不影响，也不打扰客户端当前登录
- 添加另一个账号：客户端切换登录后再调一次 `POST /api/accounts/login`
- 快照失效：客户端重新登录该账号后调 `POST /api/accounts/{id}/refresh`

**前置条件**：需本机安装并登录 WorkBuddy 桌面端（凭据文件存在）。未登录时：
- `POST /api/accounts/login` 返回 503 + 已探测路径列表
- `POST /api/checkin/start` 返回 422 + 缺凭据原因
- token 为客户端加密串时返回 422（AUTH_ENCRYPTED，需客户端重新登录落盘明文）

## 安装

### 1. 安装依赖

```bash
cd tools/workbuddy-multi-account
pip install -r requirements.txt
```

### 2. 初始化数据库

首次运行时会自动初始化数据库。

## 使用方法

### 一键启动（推荐）

双击 `start.bat`，它会先尽力清理仍在运行的旧服务，再检查依赖并启动。服务就绪后**会自动在默认浏览器打开管理面板**（不用手动输地址，效果和呀呀法语一样）。

面板地址：启动脚本会在窗口里打印实际端口，默认 **http://127.0.0.1:8000**。

> **端口占用自动回退**：默认从 8000 启动；若 8000 被占（例如上次服务是"已死但端口没释放"的僵尸进程，`taskkill` 都杀不掉），脚本会自动从 8001–8019 挑一个空闲端口启动，并用该端口打开浏览器——所以请以窗口打印的地址为准。若想固定端口，启动前设 `set WORKBUDDY_MA_PORT=8000`（固定时被占用会报错而不自动换）。前端用相对路径请求 API，换端口不影响功能。

> 不想自动弹浏览器：启动前设环境变量 `MULTIACCT_NO_BROWSER=1`（当前 cmd 窗口执行 `set MULTIACCT_NO_BROWSER=1` 后再双击，或用 `set MULTIACCT_NO_BROWSER=1 && start.bat`）。自动打开最多等 30 秒，超时跳过、不影响服务运行。

> 服务以单进程运行（`reload=False`），避免热重载 spawn 子进程、kill 父进程时残留占住端口形成僵尸。

### 管理面板功能（v1.3.0）

- **账号池**：账号卡片（状态徽章：在线/需重登/离线/无凭据，显示 uid）、添加账号（bind）、刷新凭据、探测状态、设为客户端登录、删除账号、每号「每日自动签到」与「切号自动迁移任务列表」开关；切号/删除均防重复点击
- **签到中心**：30 天统计卡（成功/失败/总积分/账号数）、一键全部签到、签到记录明细表
- **聊天记录**：一键合并（目标账号 + 来源多选，按 会话ID+消息ID 去重）、消息查询

### 命令行启动

```bash
python server.py        # http://127.0.0.1:8000
```

### API 文档

访问 `http://127.0.0.1:8000/docs` 查看 API 文档。

### 主要 API 端点

#### 账号管理

- `POST /api/accounts/login` - 扫码登录账号
- `POST /api/accounts/switch` - 切换账号
- `POST /api/accounts/{account_id}/activate` - 设为客户端登录（重启客户端 + 可选任务迁移）
- `DELETE /api/accounts/{account_id}` - 删除账号（含凭据快照与关联记录，不可恢复）
- `GET /api/accounts/list` - 获取账号列表
- `GET /api/accounts/{account_id}/status` - 获取账号状态

#### 签到管理

- `POST /api/checkin/start` - 开始签到
- `GET /api/checkin/records` - 获取签到记录
- `GET /api/checkin/stats` - 获取签到统计
- `GET /api/checkin/tasks` - 获取签到任务列表

#### 聊天记录管理

- `GET /api/chat/messages` - 获取聊天记录
- `POST /api/chat/merge` - 合并聊天记录
- `GET /api/chat/history/{account_id}` - 获取聊天历史统计

## 切号任务列表迁移（v1.4.0）

WorkBuddy 客户端的「任务列表」（侧边栏会话）并不在本工具的数据库里，而在客户端私有目录：

- 任务列表快照：`~/.workbuddy/<uid>/sidebar-list-snapshot.json`（客户端 UI 直接渲染其 `items`）
- 会话记录：`~/.workbuddy/workbuddy.db` 的 `sessions` 表（按 `user_id` 隔离）
- 工具账号 ↔ uid 映射：凭据快照 `credentials/<account_id>.info` 的 `account.uid`（bind 时已解析写入，白名单读取，**从不解析 token**）

`POST /api/accounts/{id}/activate` 在目标账号开启 `auto_merge` 时，会在写回凭据、重启客户端前完成迁移：

1. 读客户端当前登录 uid → 找到对应工具账号的凭据快照（源）
2. 读源/目标两份快照，按任务 `id` 去重合并；同 id 取 `lastActivityAt`/`updatedAt` 更新者覆盖
3. 备份两份快照与 `workbuddy.db`（含 `-wal`/`-shm`）到 `data/cache/workbuddy-multi-account/snapshots/<时间戳>/`
4. 原子替换目标快照（`os.replace`），并 `UPDATE sessions SET user_id=目标` （限定 `user_id=源 AND id IN 任务集`，防串号）
5. 重启客户端；响应带 `task_migration` 摘要（attempted/ok/stats/error）

**安全边界**：源账号数据只读不改；只用白名单字段（uid/id/title/state/时间/space），任一异常回滚且不破坏目标文件；云同步若随后回写覆盖，属客户端行为，工具只保证本地快照落盘正确。

## 切号凭据写回（v1.5.0）

迁移完成后才写回凭据并重启客户端。客户端自身原子写 `.info` 时也用固定名 `workbuddy-desktop.info.tmp`，两边撞名会报 `[Errno 13] Permission denied`（表现为"任务迁移成功但切换失败"）。实现要点：

- 临时名用 `<auth>.<pid>.<random>.tmp`，不与客户端 `.tmp` 或历史残留锁撞名；
- 写回失败退避重试 5 次，每次清理临时文件；仍失败返回明确错误；
- `taskkill` 结果记录日志，kill 后轮询最多 5 秒等客户端退出，不再静默失败；
- 写回后读回比对字节，确认无误才重启客户端。

删除账号只动工具自身数据（DB 行 / `credentials/<id>.info` / 关联 `chat_messages`、`checkin_records`），不改客户端当前登录态与客户端私有任务/会话；不可恢复，前端有二次确认。

### 验证步骤

```bash
# 1. 单元与逻辑测试
python -m unittest discover -s tools/workbuddy-multi-account/tests -v

# 2. dry-run 只读预演（不改客户端任何文件，总指挥已实现）
#    在 Python shell 中：
#    from services.task_snapshot_service import dry_run
#    print(dry_run("credentials/<源账号>.info", "<目标uid>"))
#    期望：will_add / will_update / final_count 合理，且两次快照文件字节不变

# 3. 真机（需客户端可重启）
#    面板把目标账号 auto_merge 打开 → 点「设为客户端登录」
#    检查响应 task_migration.ok=true，新增/更新条数 > 0
#    核对 ~/.workbuddy/<目标uid>/sidebar-list-snapshot.json 的 items 含源任务且无重复 id
#    客户端侧边栏目视确认；源 uid 快照未变化
#    失败时从 data/cache/workbuddy-multi-account/snapshots/<时间戳>/ 回滚
```

## 项目结构

```
workbuddy-multi-account/
├── api/                    # API 路由
│   ├── accounts.py         # 账号管理路由
│   ├── checkin.py          # 签到管理路由
│   └── chat.py             # 聊天记录管理路由
├── services/               # 服务层
│   ├── account_service.py        # 账号服务（扫码登录/状态检查/切号）
│   ├── checkin_service.py        # 签到服务（自动签到）
│   ├── task_snapshot_service.py  # 切号任务快照迁移（TASK-0037）
│   └── scheduler.py              # 定时任务调度器
├── tests/                  # unittest 单测（TASK-0037 / TASK-0045）
│   ├── test_task_snapshot.py
│   └── test_account_service.py
├── models.py               # 数据库模型
├── config.py               # 配置文件
├── server.py               # FastAPI 主文件
├── requirements.txt        # Python 依赖
└── README.md               # 本文件
```

## 数据库结构

### accounts（账号表）
- `id` - 账号 ID
- `name` - 账号名称
- `status` - 状态（online/offline/login_required）
- `last_active_time` - 最后活跃时间
- `auto_checkin` - 是否自动签到
- `auto_merge` - 是否自动迁移任务列表
- `uid` - 客户端用户 uid（bind 时从凭据快照 account.uid 解析）
- `merged_from` - 合并来源账号

### chat_messages（聊天消息表）
- `id` - 消息 ID
- `account_id` - 所属账号
- `chat_id` - 会话 ID
- `message_id` - 消息 ID
- `sender` - 发送者
- `content` - 消息内容
- `timestamp` - 发送时间

### checkin_records（签到记录表）
- `id` - 记录 ID
- `account_id` - 账号 ID
- `checkin_time` - 签到时间
- `points` - 获得积分
- `status` - 状态（success/failed）
- `task_type` - 任务类型
- `task_id` - 任务 ID

### settings（系统配置表）
- `key` - 配置键
- `value` - 配置值

## 开发计划

### Phase 1：基础架构搭建（已完成）
- ✅ 创建项目目录结构
- ✅ 初始化 FastAPI 后端
- ✅ 配置 SQLite 数据库
- ✅ 创建数据库模型
- ✅ 创建基础路由和 API

### Phase 2：账号管理模块（已完成）
- ✅ 实现扫码登录 API 调用
- ✅ 实现账号切换 API
- ✅ 实现账号状态监控（每 5 分钟）
- ✅ 实现账号服务层（account_service.py）
- ⏳ 前端账号列表页面（待开发）

### Phase 3：自动签到模块（后端已完成）
- ✅ 集成 workbuddy-auto-signin 核心逻辑（checkin_service.py）
- ✅ 实现定时任务调度（每天 9:00）
- ✅ 实现签到记录存储
- ⏳ 前端签到统计页面（待开发）

### Phase 4：聊天记录管理（API 已完成）
- ✅ 实现聊天记录存储 API
- ✅ 实现历史记录查询 API
- ✅ 实现聊天记录合并 API
- ⏳ 前端聊天记录页面（待开发）

## 参考资料

- [workbuddy-manager](https://github.com/ithtelab/workbuddy-manager) - 账号池管理控制台
- [workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin) - 自动签到工具
- [workbuddy2api-panel](https://github.com/linguo2625469/workbuddy2api-panel) - 多账号网关

## 许可证

MIT License

## 更新日志

### v1.5.0 (2026-11-19)
- ✅ 修切号凭据写回 `[Errno 13] Permission denied`（TASK-0045）：唯一临时名 + 5 次退避重试 + 写回字节校验 + taskkill 日志与退出轮询
- ✅ 新增账号删除：`DELETE /api/accounts/{id}` + 面板「删除」按钮（二次确认、防重复点击），清 DB 行/凭据快照/关联记录
- ✅ 单测 18/18 通过（新增写回重试/临时名清理/删除隔离 5 例）；清理 6 个无凭据测试账号，保留 my-work / my-second

### v1.4.0 (2026-11-19)
- ✅ 切号任务列表迁移（TASK-0037）：接管客户端 `sidebar-list-snapshot.json`，源→目标按 id 去重、最新快照覆盖
- ✅ uid 映射从凭据快照 `account.uid` 白名单解析（不碰 token）；Account 表新增 uid 列（轻量迁移）
- ✅ 写前备份 + 原子替换 + 失败回滚；sessions 表按 (user_id, id) 精确 UPDATE 防串号
- ✅ activate 响应带 task_migration 摘要；前端显示 uid 与迁移结果；unittest 覆盖解析/去重/备份/幂等/串号隔离

### v1.3.0 (2026-11-19)
- ✅ Web 管理面板（static/index.html 单文件，FastAPI 静态托管，零构建链）
- ✅ 三 Tab：账号池 / 签到中心 / 聊天记录
- ✅ 新增 PATCH /api/accounts/{id}（auto_checkin / auto_merge / name 设置）
- ✅ start.bat 一键启动（依赖自检 + 自动安装）

### v1.2.0 (2026-11-19)
- ✅ 接入真实 WorkBuddy 协议（copilot.tencent.com，Bearer 认证）
- ✅ 新增 workbuddy_client.py：凭据发现/读取重试/快照复制/HTTP 封装
- ✅ 多账号改为官方级凭据快照机制（bind / refresh）
- ✅ 真实签到链路：状态查询 + 每日签到（已签到幂等）+ 成长中心任务领取
- ✅ 定时签到与状态监控改走真实 API
- ✅ Account 表新增 credential_path（轻量迁移）
- ✅ 单测 21/21 + 服务器级冒烟通过

### v1.1.0 (2026-11-18)
- ✅ 完成账号服务层（扫码登录/状态检查/Token 刷新）
- ✅ 完成签到服务层（每日签到/成长任务/领取奖励）
- ✅ 完成定时任务调度器（每天 9:00 签到 + 每 5 分钟状态监控）
- ✅ API 路由接入服务层

### v1.0.0 (2026-11-18)
- 初始版本发布
- 实现基础 API 路由
- 实现数据库模型
