# WorkBuddy 多账号管理工具

支持多账号同时登录、自动签到、聊天记录合并与迁移的 WorkBuddy 管理工具。

## 功能特性

### P0 核心功能
- ✅ **多账号管理**
  - 扫码登录多个账号
  - 账号状态监控（在线/离线/登录过期）
  - 账号切换（设置当前活跃账号）

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
- ✅ **自动迁移**
  - 切换账号时自动迁移聊天记录
  - 可配置开关

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

### 启动服务器

```bash
python server.py
```

服务器将在 `http://localhost:8000` 启动。

### API 文档

访问 `http://localhost:8000/docs` 查看 API 文档。

### 主要 API 端点

#### 账号管理

- `POST /api/accounts/login` - 扫码登录账号
- `POST /api/accounts/switch` - 切换账号
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

## 项目结构

```
workbuddy-multi-account/
├── api/                    # API 路由
│   ├── accounts.py         # 账号管理路由
│   ├── checkin.py          # 签到管理路由
│   └── chat.py             # 聊天记录管理路由
├── services/               # 服务层
│   ├── account_service.py  # 账号服务（扫码登录/状态检查）
│   ├── checkin_service.py  # 签到服务（自动签到）
│   └── scheduler.py        # 定时任务调度器
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
- `auto_merge` - 是否自动迁移
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
