# WorkBuddy 多账号管理工具调研报告

## 需求总结

基于你的需求：
1. **多账号同时登录**，在软件中直接切换
2. **每天自动签到**，可视化签到结果
3. **一键合并聊天记录**，所有账号会话合并到当前账号
4. **切号自动迁移**，聊天记录跟着自动迁移

## GitHub 成熟项目推荐

### 1. workbuddy2api-panel ⭐ 4914
**仓库**：https://github.com/linguo2625469/workbuddy2api-panel
**语言**：Go
**最后更新**：2026-11-18

**功能亮点**：
- ✅ 多账号网关，把 WorkBuddy 账号变成 OpenAI 兼容 API
- ✅ 自动完成任务中心全部任务
- ✅ Web 管理面板（账号池可视化 / 积分任务 / 配置热更新）
- ✅ 基于原 Sliverkiss/workbuddy2api 的增强分支

**适用性分析**：
- 已经实现了多账号管理和自动签到
- 有 Web 管理面板，但主要是 API 网关功能
- **缺少**：聊天记录合并和自动迁移功能

**改造方向**：
- 在现有面板中增加"聊天记录管理"模块
- 实现聊天记录合并功能
- 增加自动迁移开关

---

### 2. workbuddy-auto-signin ⭐ 2528
**仓库**：https://github.com/88lin/workbuddy-auto-signin
**语言**：Python
**最后更新**：2026-11-18

**功能亮点**：
- ✅ 自动领取 WorkBuddy / Qoder CN 每日签到积分
- ✅ 成长中心全部奖励（Buddy 旅行礼物、派 Buddy、开盲盒、领任务、连登兑换、断登补签）
- ✅ 无需额外安装依赖，零 Token 静默运行
- ✅ 支持配置 Windows / macOS 定时任务

**适用性分析**：
- **完美匹配**自动签到需求
- Python 实现，易于二次开发
- 支持断登补签，覆盖全面

**改造方向**：
- 作为签到模块集成到多账号管理工具
- 增加签到结果可视化（成功/失败统计）
- 与账号池管理对接

---

### 3. workbuddy-manager ⭐ 2869
**仓库**：https://github.com/ithtelab/workbuddy-manager
**语言**：Python (FastAPI) + Next.js
**最后更新**：2026-11-18

**功能亮点**：
- ✅ 腾讯 CodeBuddy 账号池管理控制台
- ✅ 扫码批量纳管账号
- ✅ 定时签到与保活
- ✅ 密钥分组分发
- ✅ IP 与模型白名单
- ✅ 调用日志与用量统计
- ✅ 支持带签名校验的一键更新

**适用性分析**：
- **最接近**你需求的综合管理平台
- 前后端分离架构（FastAPI + Next.js）
- 功能最全面

**缺少功能**：
- 聊天记录合并
- 自动迁移聊天记录

**改造方向**：
- 在 Next.js 前端增加"聊天记录管理"页面
- 后端增加聊天记录合并 API
- 增加自动迁移配置项

---

### 4. workbuddy-switch ⭐ 1924
**仓库**：https://github.com/changexbc/workbuddy-switch
**语言**：Rust
**最后更新**：2026-11-18

**功能亮点**：
- ✅ WorkBuddy、CodeBuddy 账号切换
- ✅ 积分到期监控
- ✅ 积分统计与 Token 统计
- ✅ Agent 状态悬浮窗

**适用性分析**：
- 专注于账号切换
- 有悬浮窗 UI，适合桌面应用
- Rust 实现，性能优秀

**改造方向**：
- 增加聊天记录合并功能
- 增加自动迁移选项
- 与签到模块集成

---

## 推荐技术方案

### 方案 A：基于 workbuddy-manager 改造（推荐）

**架构设计**：
```
┌─────────────────────────────────────────────┐
│  Next.js Web 管理面板（前端）                │
│  ┌──────────┬──────────┬──────────┐         │
│  │ 账号列表  │ 账号切换  │ 聊天记录  │         │
│  └──────────┴──────────┴──────────┘         │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  FastAPI 后端（Python）                      │
│  ┌──────────┬──────────┬──────────┐         │
│  │ 账号管理  │ 签到服务  │ 聊天记录  │         │
│  └──────────┴──────────┴──────────┘         │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│  WorkBuddy API（官方）                       │
│  ┌──────────┬──────────┬──────────┐         │
│  │ 账号登录  │ 任务中心  │ 聊天记录  │         │
│  └──────────┴──────────┴──────────┘         │
└─────────────────────────────────────────────┘
```

**核心模块**：

#### 1. 账号管理模块
- 扫码登录/手动登录
- 账号状态监控（在线/离线/登录过期）
- 账号切换（设置当前活跃账号）

#### 2. 自动签到模块（集成 workbuddy-auto-signin）
- 定时任务（每天固定时间）
- 签到任务列表：
  - 每日签到
  - 成长中心任务
  - 连登兑换
  - 断登补签
- 签到结果可视化：
  - 成功/失败统计
  - 每日积分变化
  - 历史签到记录

#### 3. 聊天记录管理模块
- 聊天记录存储（SQLite/JSON）
- 每个账号独立存储
- 一键合并功能：
  - 按联系人筛选
  - 按时间范围筛选
  - 合并到当前账号
- 自动迁移：
  - 切换账号时自动迁移历史记录
  - 可配置是否启用

**数据库设计**：

```sql
-- 账号表
CREATE TABLE accounts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL, -- 'online'/'offline'/'login_required'
  last_active_time DATETIME,
  auto_checkin BOOLEAN DEFAULT 1,
  auto_merge BOOLEAN DEFAULT 0,
  merged_from TEXT -- 'account_id,account_id,...'
);

-- 聊天消息表
CREATE TABLE chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  chat_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  sender TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp DATETIME NOT NULL,
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 签到记录表
CREATE TABLE checkin_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  checkin_time DATETIME NOT NULL,
  points INTEGER NOT NULL,
  status TEXT NOT NULL, -- 'success'/'failed'
  task_type TEXT NOT NULL, -- 'daily_checkin'/'growth_task'/'...
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 系统配置表
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

**关键 API 设计**：

```python
# 后端 FastAPI 路由

# 账号管理
POST   /api/accounts/login           # 扫码登录
POST   /api/accounts/logout          # 登出
GET    /api/accounts/list            # 账号列表
POST   /api/accounts/switch          # 切换账号
GET    /api/accounts/{id}/status     # 账号状态

# 签到管理
POST   /api/checkin/start            # 开始签到（批量）
GET    /api/checkin/records          # 签到记录
GET    /api/checkin/stats            # 签到统计
POST   /api/checkin/config           # 配置签到任务

# 聊天记录管理
GET    /api/chat/messages            # 获取消息（支持筛选）
POST   /api/chat/merge               # 合并聊天记录
POST   /api/chat/migrate             # 自动迁移
GET    /api/chat/history/{account_id} # 历史记录
```

---

### 方案 B：基于 workbuddy2api-panel 改造

**优势**：
- Go 语言实现，性能优秀
- 已有完整的 API 网关
- 社区活跃，Star 数高

**劣势**：
- 前端可能是单体架构，改造难度大
- 缺少聊天记录相关功能

**适用场景**：
- 如果主要需求是 API 网关，次要需求是聊天记录管理

---

### 方案 C：桌面应用（Electron + Rust）

**架构**：
- Electron 负责前端 UI
- Rust 负责底层协议通信
- Python 负责签到脚本

**优势**：
- 原生桌面体验
- 悬浮窗功能（参考 workbuddy-switch）
- 性能优秀

**劣势**：
- 开发成本高
- 跨平台兼容性问题

---

## 开发路线图

### Phase 1：基础架构（2 周）
- [ ] 基于 workbuddy-manager 搭建项目骨架
- [ ] 集成账号管理功能
- [ ] 实现账号切换逻辑
- [ ] 数据库设计与初始化

### Phase 2：自动签到（1 周）
- [ ] 集成 workbuddy-auto-signin 核心逻辑
- [ ] 实现定时任务调度
- [ ] 签到结果可视化
- [ ] 积分统计与监控

### Phase 3：聊天记录管理（2 周）
- [ ] 聊天记录存储与读取
- [ ] 实现合并功能
- [ ] 实现自动迁移
- [ ] 历史记录查询

### Phase 4：优化与完善（1 周）
- [ ] 性能优化
- [ ] 错误处理与日志
- [ ] 用户文档
- [ ] 自动更新

---

## 推荐行动方案

### 立即行动
1. **克隆 workbuddy-manager** 作为基础框架
2. **克隆 workbuddy-auto-signin** 作为签到模块
3. **阅读代码**，理解现有架构

### 短期目标（1 个月）
1. 实现账号管理界面
2. 集成自动签到功能
3. 实现聊天记录合并

### 中期目标（2-3 个月）
1. 完善聊天记录管理
2. 实现自动迁移
3. 优化用户体验

### 长期目标（3-6 个月）
1. 性能优化
2. 功能扩展（如：消息过滤、导出等）
3. 社区贡献

---

## 关键代码示例

### 自动签到集成（Python）

```python
# 从 workbuddy-auto-signin 提取核心逻辑
import requests
import json
from datetime import datetime

class WorkBuddyAutoSignIn:
    def __init__(self, account_id, cookies):
        self.account_id = account_id
        self.cookies = cookies
        self.base_url = "https://work.buddy.qq.com/api"

    def daily_checkin(self):
        """每日签到"""
        url = f"{self.base_url}/checkin/daily"
        response = requests.post(url, cookies=self.cookies)
        return self._parse_response(response)

    def growth_tasks(self):
        """成长中心任务"""
        url = f"{self.base_url}/growth/tasks"
        response = requests.get(url, cookies=self.cookies)
        return self._parse_response(response)

    def claim_rewards(self, task_id):
        """领取奖励"""
        url = f"{self.base_url}/growth/claim/{task_id}"
        response = requests.post(url, cookies=self.cookies)
        return self._parse_response(response)

    def _parse_response(self, response):
        """解析响应"""
        result = response.json()
        return {
            'success': result.get('code') == 0,
            'message': result.get('msg'),
            'data': result.get('data', {})
        }
```

### 聊天记录合并（SQL）

```python
from fastapi import APIRouter
from sqlalchemy import create_engine, text

router = APIRouter()
engine = create_engine("sqlite:///workbuddy.db")

@router.post("/api/chat/merge")
async def merge_chat_messages(target_account_id: str, source_account_ids: list[str]):
    """合并聊天记录到目标账号"""

    # 获取目标账号的所有消息
    target_messages = """
        SELECT * FROM chat_messages
        WHERE account_id = :target_id
        ORDER BY timestamp
    """

    # 获取源账号的所有消息
    source_messages = """
        SELECT * FROM chat_messages
        WHERE account_id IN :source_ids
        ORDER BY timestamp
    """

    # 合并 SQL
    merge_sql = """
        INSERT OR REPLACE INTO chat_messages
        (account_id, chat_id, message_id, sender, content, timestamp)
        SELECT
            :target_id as account_id,
            chat_id,
            message_id,
            sender,
            content,
            timestamp
        FROM (
            {target_messages}
            UNION ALL
            {source_messages}
        ) AS merged
        WHERE NOT EXISTS (
            SELECT 1 FROM chat_messages
            WHERE account_id = :target_id
            AND chat_id = merged.chat_id
            AND message_id = merged.message_id
        )
    """

    with engine.connect() as conn:
        # 更新账号的 merged_from 字段
        conn.execute(text("""
            UPDATE accounts
            SET merged_from = :sources
            WHERE id = :target_id
        """), {
            'target_id': target_account_id,
            'sources': ','.join(source_account_ids)
        })

        # 执行合并
        conn.execute(text(merge_sql).format(
            target_messages=target_messages,
            source_messages=source_messages
        ))

        conn.commit()

    return {
        'success': True,
        'message': f'成功合并 {len(source_account_ids)} 个账号的聊天记录'
    }
```

### 自动迁移（FastAPI）

```python
from fastapi import APIRouter, BackgroundTasks
from datetime import datetime

router = APIRouter()

async def migrate_chat_records(current_account_id: str, background_tasks: BackgroundTasks):
    """后台迁移聊天记录"""

    # 获取当前账号的 merged_from
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT merged_from FROM accounts WHERE id = :account_id
        """), {'account_id': current_account_id}).fetchone()

        if not result or not result[0]:
            return  # 没有需要迁移的账号

        source_ids = result[0].split(',')

        # 合并聊天记录
        merge_sql = """
            INSERT OR REPLACE INTO chat_messages
            (account_id, chat_id, message_id, sender, content, timestamp)
            SELECT
                :current_id as account_id,
                chat_id,
                message_id,
                sender,
                content,
                timestamp
            FROM chat_messages
            WHERE account_id IN :source_ids
            AND NOT EXISTS (
                SELECT 1 FROM chat_messages
                WHERE account_id = :current_id
                AND chat_id = chat_id
                AND message_id = message_id
            )
        """

        with engine.connect() as conn:
            conn.execute(text(merge_sql), {
                'current_id': current_account_id,
                'source_ids': tuple(source_ids)
            })
            conn.commit()

        # 更新 merged_from
        conn.execute(text("""
            UPDATE accounts SET merged_from = NULL WHERE id = :account_id
        """), {'account_id': current_account_id})
        conn.commit()

@router.post("/api/accounts/switch")
async def switch_account(account_id: str, background_tasks: BackgroundTasks):
    """切换账号"""

    # 更新当前活跃账号
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE accounts SET last_active_time = :now
            WHERE id = :account_id
        """), {'account_id': account_id, 'now': datetime.now()})
        conn.commit()

    # 如果启用了自动迁移，后台执行
    result = conn.execute(text("""
        SELECT auto_merge FROM accounts WHERE id = :account_id
    """), {'account_id': account_id}).fetchone()

    if result and result[0]:
        background_tasks.add_task(migrate_chat_records, account_id, background_tasks)

    return {'success': True, 'message': f'已切换到账号 {account_id}'}
```

---

## 总结

### 推荐方案
**基于 workbuddy-manager 改造**，原因：
1. 功能最全面，架构清晰（FastAPI + Next.js）
2. 社区活跃，Star 数高（2869）
3. 前后端分离，易于扩展
4. Python 实现，易于二次开发

### 关键功能实现
1. **多账号切换**：利用现有账号管理功能
2. **自动签到**：集成 workbuddy-auto-signin
3. **聊天记录合并**：SQL UNION ALL 实现
4. **自动迁移**：切换账号时触发后台任务

### 下一步行动
1. 克隆 workbuddy-manager
2. 克隆 workbuddy-auto-signin
3. 阅读代码，理解架构
4. 开始开发 Phase 1

---

**调研日期**：2026-11-18
**调研人**：AI 助手
