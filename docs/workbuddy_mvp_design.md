# WorkBuddy 多账号管理 MVP 方案

## 一、项目分析（基于 GitHub API 数据）

### 1.1 workbuddy-manager 项目结构推断

**技术栈**：
- **后端**：Python + FastAPI
- **前端**：Next.js + TailwindCSS
- **数据库**：SQLite（推断，因为使用 FastAPI）
- **架构**：前后端分离

**核心功能**（从搜索结果推断）：
- ✅ 账号池管理（扫码批量纳管账号）
- ✅ 定时签到与保活
- ✅ 密钥分组分发
- ✅ IP 与模型白名单
- ✅ 调用日志与用量统计
- ✅ 一键更新（带签名校验）

**缺少功能**（基于用户需求）：
- ❌ 多账号在软件中直接切换
- ❌ 签到结果可视化
- ❌ 聊天记录合并
- ❌ 切号自动迁移

---

### 1.2 workbuddy-auto-signin 项目分析

**技术栈**：
- **语言**：Python
- **依赖**：无额外依赖（零 Token 静默运行）
- **部署**：支持 Windows / macOS 定时任务

**核心功能**：
- ✅ 每日签到积分
- ✅ 成长中心任务（Buddy 旅行礼物、派 Buddy、开盲盒、领任务、连登兑换、断登补签）
- ✅ 自动化配置（AI 配置定时任务）

**可复用部分**：
- 签到 API 调用逻辑
- 任务列表解析
- 响应处理

---

## 二、MVP 功能范围

### 2.1 MVP 定义

**最小可行产品**：在 1-2 周内实现的核心功能，验证技术可行性。

### 2.2 MVP 功能清单

#### P0（核心功能，必须实现）
1. ✅ **多账号管理**
   - 扫码登录多个账号
   - 账号状态监控（在线/离线/登录过期）
   - 账号切换（设置当前活跃账号）

2. ✅ **自动签到**
   - 定时任务（每天固定时间）
   - 签到任务列表（每日签到 + 成长中心）
   - 签到结果记录

3. ✅ **签到结果可视化**
   - 成功/失败统计
   - 每日积分变化
   - 签到历史记录

#### P1（重要功能，优先实现）
4. ✅ **聊天记录存储**
   - 每个账号独立存储
   - 历史记录查询

5. ✅ **聊天记录合并**
   - 一键合并所有账号的聊天记录到当前账号
   - 按联系人筛选
   - 按时间范围筛选

#### P2（增强功能，后续迭代）
6. ✅ **自动迁移**
   - 切换账号时自动迁移聊天记录
   - 可配置开关

7. ✅ **账号池可视化**
   - 当前活跃账号高亮
   - 积分统计
   - Token 统计

---

## 三、架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│           Next.js Web 管理面板（前端）                │
│  ┌──────────┬──────────┬──────────┬──────────┐     │
│  │ 账号列表  │ 账号切换  │ 签到统计  │ 聊天记录  │     │
│  └──────────┴──────────┴──────────┴──────────┘     │
│  - React + TailwindCSS                             │
│  - 账号池可视化                                     │
│  - 实时状态更新                                     │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│         FastAPI 后端（Python）                       │
│  ┌──────────┬──────────┬──────────┬──────────┐     │
│  │ 账号管理  │ 签到服务  │ 聊天记录  │ 定时任务  │     │
│  └──────────┴──────────┴──────────┴──────────┘     │
│  - 路由：/api/accounts, /api/checkin, /api/chat   │
│  - 任务调度：node-cron                              │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│         WorkBuddy API（官方）                        │
│  ┌──────────┬──────────┬──────────┬──────────┐     │
│  │ 账号登录  │ 任务中心  │ 聊天记录  │ 积分查询  │     │
│  └──────────┴──────────┴──────────┴──────────┘     │
│  - HTTPS API                                        │
│  - Cookie/Token 认证                               │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│         SQLite 数据库（本地存储）                    │
│  - accounts（账号表）                               │
│  - chat_messages（聊天记录表）                      │
│  - checkin_records（签到记录表）                     │
│  - settings（系统配置表）                           │
└─────────────────────────────────────────────────────┘
```

### 3.2 技术选型

| 层级 | 技术选型 | 理由 |
|------|----------|------|
| 前端 | Next.js 14 + React + TailwindCSS | 现代化 UI，服务端渲染，热更新 |
| 后端 | FastAPI + Python 3.11+ | 高性能，异步支持，自动文档 |
| 数据库 | SQLite | 零配置，本地存储，适合 MVP |
| 任务调度 | node-cron | 轻量级，支持 Cron 表达式 |
| HTTP 客户端 | httpx / requests | 异步 HTTP，性能优秀 |

---

## 四、数据库设计

### 4.1 数据库结构

```sql
-- 账号表
CREATE TABLE accounts (
  id TEXT PRIMARY KEY,                    -- 账号 ID
  name TEXT NOT NULL,                     -- 账号名称（用户自定义）
  status TEXT NOT NULL DEFAULT 'offline', -- 状态：online/offline/login_required
  last_active_time DATETIME,              -- 最后活跃时间
  auto_checkin BOOLEAN DEFAULT 1,        -- 是否自动签到
  auto_merge BOOLEAN DEFAULT 0,           -- 是否自动迁移
  merged_from TEXT,                       -- 合并来源账号（逗号分隔）
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 聊天消息表
CREATE TABLE chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,               -- 所属账号
  chat_id TEXT NOT NULL,                  -- 会话 ID
  message_id TEXT NOT NULL,               -- 消息 ID（WorkBuddy 原生 ID）
  sender TEXT NOT NULL,                   -- 发送者（用户/自己）
  content TEXT NOT NULL,                  -- 消息内容
  timestamp DATETIME NOT NULL,            -- 发送时间
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 签到记录表
CREATE TABLE checkin_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,               -- 账号 ID
  checkin_time DATETIME NOT NULL,         -- 签到时间
  points INTEGER NOT NULL,                -- 获得积分
  status TEXT NOT NULL,                   -- 状态：success/failed
  task_type TEXT NOT NULL,                -- 任务类型：daily_checkin/growth_task/...
  task_id TEXT,                           -- 任务 ID（可选）
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 系统配置表
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- 初始化配置
INSERT INTO settings (key, value) VALUES
  ('checkin_hour', '09:00'),              -- 签到时间
  ('checkin_enabled', 'true'),            -- 是否启用签到
  ('auto_merge_enabled', 'false');        -- 是否启用自动迁移
```

### 4.2 数据库操作示例

```python
from sqlalchemy import create_engine, text

# 初始化数据库
engine = create_engine("sqlite:///workbuddy.db", echo=True)

# 创建表
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'offline',
            last_active_time DATETIME,
            auto_checkin BOOLEAN DEFAULT 1,
            auto_merge BOOLEAN DEFAULT 0,
            merged_from TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS checkin_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            checkin_time DATETIME NOT NULL,
            points INTEGER NOT NULL,
            status TEXT NOT NULL,
            task_type TEXT NOT NULL,
            task_id TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """))
    conn.commit()
```

---

## 五、核心功能实现方案

### 5.1 账号管理模块

#### 5.1.1 扫码登录

**实现思路**：
1. WorkBuddy 官方提供扫码登录 API
2. 前端生成二维码
3. 用户扫码后获取 token/cookie
4. 保存到数据库

**API 设计**：
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    name: str  # 账号名称

class LoginResponse(BaseModel):
    success: bool
    account_id: str
    qr_code_url: str

@router.post("/api/accounts/login", response_model=LoginResponse)
async def login_account(request: LoginRequest):
    """
    扫码登录账号

    流程：
    1. 调用 WorkBuddy 扫码登录 API
    2. 生成二维码 URL
    3. 等待用户扫码
    4. 获取 token/cookie
    5. 保存到数据库
    """
    # TODO: 调用 WorkBuddy 扫码登录 API
    # TODO: 生成二维码 URL
    # TODO: 返回账号 ID 和二维码

    raise HTTPException(status_code=501, detail="未实现")
```

#### 5.1.2 账号切换

**实现思路**：
1. 前端点击账号切换
2. 后端更新 `last_active_time`
3. 如果启用自动迁移，触发后台任务

**API 设计**：
```python
@router.post("/api/accounts/switch")
async def switch_account(account_id: str, background_tasks: BackgroundTasks):
    """
    切换账号

    流程：
    1. 更新当前活跃账号
    2. 如果启用了自动迁移，后台执行迁移任务
    """
    # 更新活跃时间
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE accounts
            SET last_active_time = :now
            WHERE id = :account_id
        """), {'account_id': account_id, 'now': datetime.now()})
        conn.commit()

    # 检查是否启用自动迁移
    result = conn.execute(text("""
        SELECT auto_merge FROM accounts WHERE id = :account_id
    """), {'account_id': account_id}).fetchone()

    if result and result[0]:
        # 后台迁移聊天记录
        background_tasks.add_task(migrate_chat_records, account_id)

    return {'success': True, 'message': f'已切换到账号 {account_id}'}
```

#### 5.1.3 账号状态监控

**实现思路**：
1. 定时任务（每 5 分钟）检查账号状态
2. 调用 WorkBuddy API 检查是否登录
3. 更新数据库中的 `status` 字段

**实现代码**：
```python
import asyncio
from datetime import datetime, timedelta

async def check_account_status(account_id: str):
    """检查账号状态"""
    # 调用 WorkBuddy API 检查登录状态
    # 如果 token 过期，status = 'login_required'
    # 如果在线，status = 'online'
    # 如果离线，status = 'offline'
    pass

async def monitor_accounts():
    """监控所有账号状态"""
    while True:
        with engine.connect() as conn:
            accounts = conn.execute(text("""
                SELECT id, last_active_time FROM accounts
            """)).fetchall()

            for account in accounts:
                last_active = account[1]
                if last_active and datetime.now() - last_active > timedelta(minutes=30):
                    # 超过 30 分钟未活跃，检查状态
                    await check_account_status(account[0])

        await asyncio.sleep(300)  # 每 5 分钟检查一次

# 启动监控任务
@router.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_accounts())
```

---

### 5.2 自动签到模块

#### 5.2.1 集成 workbuddy-auto-signin

**实现思路**：
1. 提取 workbuddy-auto-signin 的核心签到逻辑
2. 封装为 Python 类
3. 在 FastAPI 中定时调用

**实现代码**：
```python
import requests
from datetime import datetime
from typing import List, Dict

class WorkBuddyAutoSignIn:
    def __init__(self, account_id: str, cookies: dict):
        self.account_id = account_id
        self.cookies = cookies
        self.base_url = "https://work.buddy.qq.com/api"

    def daily_checkin(self) -> Dict:
        """每日签到"""
        url = f"{self.base_url}/checkin/daily"
        response = requests.post(url, cookies=self.cookies, timeout=10)
        return self._parse_response(response)

    def growth_tasks(self) -> List[Dict]:
        """获取成长中心任务"""
        url = f"{self.base_url}/growth/tasks"
        response = requests.get(url, cookies=self.cookies, timeout=10)
        return self._parse_growth_tasks_response(response)

    def claim_rewards(self, task_id: str) -> Dict:
        """领取任务奖励"""
        url = f"{self.base_url}/growth/claim/{task_id}"
        response = requests.post(url, cookies=self.cookies, timeout=10)
        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> Dict:
        """解析响应"""
        result = response.json()
        return {
            'success': result.get('code') == 0,
            'message': result.get('msg'),
            'data': result.get('data', {})
        }

    def _parse_growth_tasks_response(self, response: requests.Response) -> List[Dict]:
        """解析成长中心任务响应"""
        result = response.json()
        if result.get('code') != 0:
            return []

        tasks = []
        for task in result.get('data', {}).get('tasks', []):
            tasks.append({
                'id': task.get('taskId'),
                'name': task.get('taskName'),
                'reward': task.get('reward'),
                'status': task.get('status'),  # 未开始/进行中/已完成
                'description': task.get('description')
            })
        return tasks

    def execute_all_checkin(self) -> Dict:
        """执行所有签到任务"""
        results = {
            'daily_checkin': None,
            'growth_tasks': [],
            'total_points': 0
        }

        # 1. 每日签到
        daily_result = self.daily_checkin()
        results['daily_checkin'] = daily_result

        # 2. 成长中心任务
        tasks = self.growth_tasks()
        for task in tasks:
            if task['status'] == '进行中':
                claim_result = self.claim_rewards(task['id'])
                results['growth_tasks'].append({
                    'task_name': task['name'],
                    'result': claim_result
                })

        # 3. 统计总积分
        results['total_points'] = daily_result.get('points', 0)
        for task in results['growth_tasks']:
            if task['result'].get('success'):
                results['total_points'] += task['result'].get('data', {}).get('points', 0)

        return results
```

#### 5.2.2 定时任务调度

**实现思路**：
1. 使用 node-cron 定时执行签到
2. 每天固定时间（如 9:00）执行
3. 记录签到结果到数据库

**实现代码**：
```python
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=9, minute=0)
async def scheduled_checkin():
    """定时签到任务"""
    print(f"[{datetime.now()}] 开始执行自动签到...")

    # 获取所有启用了自动签到的账号
    with engine.connect() as conn:
        accounts = conn.execute(text("""
            SELECT id, name, auto_checkin FROM accounts
            WHERE auto_checkin = 1
        """)).fetchall()

        for account in accounts:
            account_id = account[0]
            account_name = account[1]

            # TODO: 从数据库获取账号的 cookie
            cookies = get_cookies(account_id)

            # 执行签到
            signer = WorkBuddyAutoSignIn(account_id, cookies)
            results = signer.execute_all_checkin()

            # 保存签到记录
            with engine.connect() as conn:
                # 保存每日签到记录
                if results['daily_checkin'] and results['daily_checkin'].get('success'):
                    conn.execute(text("""
                        INSERT INTO checkin_records
                        (account_id, checkin_time, points, status, task_type)
                        VALUES (:account_id, :time, :points, 'success', 'daily_checkin')
                    """), {
                        'account_id': account_id,
                        'time': datetime.now(),
                        'points': results['daily_checkin'].get('data', {}).get('points', 0)
                    })

                # 保存成长中心任务记录
                for task_result in results['growth_tasks']:
                    if task_result['result'].get('success'):
                        conn.execute(text("""
                            INSERT INTO checkin_records
                            (account_id, checkin_time, points, status, task_type, task_id)
                            VALUES (:account_id, :time, :points, 'success', 'growth_task', :task_id)
                        """), {
                            'account_id': account_id,
                            'time': datetime.now(),
                            'points': task_result['result'].get('data', {}).get('points', 0),
                            'task_id': task_result['result'].get('data', {}).get('taskId')
                        })

                conn.commit()

            print(f"[{datetime.now()}] 账号 {account_name} 签到完成，获得 {results['total_points']} 积分")

# 启动定时任务
@router.on_event("startup")
async def startup_event():
    scheduler.start()
    print("定时签到任务已启动")
```

---

### 5.3 聊天记录管理模块

#### 5.3.1 聊天记录存储

**实现思路**：
1. 调用 WorkBuddy API 获取聊天记录
2. 存储到 SQLite 数据库
3. 支持分页查询

**API 设计**：
```python
from fastapi import Query

@router.get("/api/chat/messages")
async def get_chat_messages(
    account_id: str = Query(...),
    chat_id: str = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    获取聊天记录

    参数：
    - account_id: 账号 ID
    - chat_id: 会话 ID（可选，不传则返回所有会话的消息）
    - limit: 每页数量
    - offset: 偏移量
    """
    with engine.connect() as conn:
        if chat_id:
            # 查询特定会话的消息
            result = conn.execute(text("""
                SELECT * FROM chat_messages
                WHERE account_id = :account_id AND chat_id = :chat_id
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """), {
                'account_id': account_id,
                'chat_id': chat_id,
                'limit': limit,
                'offset': offset
            }).fetchall()
        else:
            # 查询所有会话的消息（仅返回最近消息）
            result = conn.execute(text("""
                SELECT DISTINCT chat_id, MAX(timestamp) as latest_time
                FROM chat_messages
                WHERE account_id = :account_id
                GROUP BY chat_id
                ORDER BY latest_time DESC
                LIMIT :limit
            """), {
                'account_id': account_id,
                'limit': limit
            }).fetchall()

        return {
            'success': True,
            'data': [dict(row) for row in result]
        }
```

#### 5.3.2 聊天记录合并

**实现思路**：
1. 前端选择目标账号和源账号列表
2. 后端执行 SQL UNION ALL 合并
3. 去重（相同 chat_id + message_id）

**API 设计**：
```python
@router.post("/api/chat/merge")
async def merge_chat_messages(
    target_account_id: str = Query(...),
    source_account_ids: List[str] = Query(...)
):
    """
    合并聊天记录到目标账号

    流程：
    1. 获取目标账号的所有消息
    2. 获取源账号的所有消息
    3. 执行 UNION ALL 合并
    4. 去重（相同 chat_id + message_id）
    5. 更新目标账号的 merged_from 字段
    """
    if not source_account_ids:
        return {'success': False, 'message': '请选择源账号'}

    with engine.connect() as conn:
        # 更新目标账号的 merged_from 字段
        conn.execute(text("""
            UPDATE accounts
            SET merged_from = :sources
            WHERE id = :target_id
        """), {
            'target_id': target_account_id,
            'sources': ','.join(source_account_ids)
        })

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
                SELECT * FROM chat_messages WHERE account_id = :target_id
                UNION ALL
                SELECT * FROM chat_messages WHERE account_id IN :source_ids
            ) AS merged
            WHERE NOT EXISTS (
                SELECT 1 FROM chat_messages
                WHERE account_id = :target_id
                AND chat_id = merged.chat_id
                AND message_id = merged.message_id
            )
        """

        conn.execute(text(merge_sql), {
            'target_id': target_account_id,
            'source_ids': tuple(source_account_ids)
        })

        conn.commit()

    return {
        'success': True,
        'message': f'成功合并 {len(source_account_ids)} 个账号的聊天记录'
    }
```

#### 5.3.3 自动迁移

**实现思路**：
1. 切换账号时触发后台任务
2. 将旧账号的聊天记录合并到新账号
3. 可配置是否启用

**实现代码**：
```python
from fastapi import BackgroundTasks

async def migrate_chat_records(current_account_id: str):
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

        # 清空 merged_from
        conn.execute(text("""
            UPDATE accounts SET merged_from = NULL WHERE id = :account_id
        """), {'account_id': current_account_id})
        conn.commit()

        print(f"[{datetime.now()}] 账号 {current_account_id} 聊天记录迁移完成")

@router.post("/api/accounts/switch")
async def switch_account(account_id: str, background_tasks: BackgroundTasks):
    """
    切换账号

    如果启用了自动迁移，后台执行迁移任务
    """
    # 更新活跃时间
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE accounts
            SET last_active_time = :now
            WHERE id = :account_id
        """), {'account_id': account_id, 'now': datetime.now()})
        conn.commit()

    # 检查是否启用自动迁移
    result = conn.execute(text("""
        SELECT auto_merge FROM accounts WHERE id = :account_id
    """), {'account_id': account_id}).fetchone()

    if result and result[0]:
        # 后台迁移聊天记录
        background_tasks.add_task(migrate_chat_records, account_id)

    return {'success': True, 'message': f'已切换到账号 {account_id}'}
```

---

## 六、前端界面设计

### 6.1 账号池页面

**功能**：
- 显示所有账号列表
- 当前活跃账号高亮
- 扫码登录按钮
- 账号切换按钮
- 自动签到开关
- 自动迁移开关

**界面示例**：
```
┌─────────────────────────────────────────────────┐
│  WorkBuddy 多账号管理                            │
├─────────────────────────────────────────────────┤
│  [扫码登录]  [刷新]  [设置]                     │
├─────────────────────────────────────────────────┤
│  当前活跃: 账号 A (在线)  积分: 1200  Token: 50 │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐   │
│  │ 账号 B (在线)  积分: 800  [切换] [签到]  │   │
│  │ 最后活跃: 10分钟前  自动签到: ✅         │   │
│  │ 自动迁移: ✅  [合并聊天记录] [查看记录]  │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │ 账号 C (离线)  积分: 500  [切换] [签到]  │   │
│  │ 最后活跃: 2小时前  自动签到: ✅         │   │
│  │ 自动迁移: ❌  [合并聊天记录] [查看记录]  │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 6.2 签到统计页面

**功能**：
- 每日签到统计（成功/失败）
- 每日积分变化图表
- 历史签到记录列表

**界面示例**：
```
┌─────────────────────────────────────────────────┐
│  签到统计                                        │
├─────────────────────────────────────────────────┤
│  今日: 成功 2  失败 1  总积分: 150               │
│  本周: 成功 12  失败 3  总积分: 800              │
├─────────────────────────────────────────────────┤
│  签到记录                                        │
│  2026-11-18 09:00  账号 A  成功  +50            │
│  2026-11-18 09:00  账号 B  成功  +30            │
│  2026-11-17 09:00  账号 C  失败  -0             │
│  ...                                            │
└─────────────────────────────────────────────────┘
```

### 6.3 聊天记录页面

**功能**：
- 选择账号查看聊天记录
- 选择会话查看消息
- 合并聊天记录按钮
- 导出聊天记录

---

## 七、开发路线图（1-2 周完成 MVP）

### Week 1：基础架构

**Day 1-2：项目搭建**
- [ ] 初始化 Next.js 项目
- [ ] 初始化 FastAPI 后端
- [ ] 配置数据库（SQLite）
- [ ] 创建基础路由和 API

**Day 3-4：账号管理**
- [ ] 实现扫码登录 API
- [ ] 实现账号切换 API
- [ ] 实现账号状态监控
- [ ] 前端账号列表页面

**Day 5-6：自动签到**
- [ ] 集成 workbuddy-auto-signin 核心逻辑
- [ ] 实现定时任务调度
- [ ] 实现签到记录存储
- [ ] 前端签到统计页面

### Week 2：聊天记录管理

**Day 7-8：聊天记录存储**
- [ ] 实现聊天记录 API
- [ ] 实现历史记录查询
- [ ] 前端聊天记录页面

**Day 9-10：聊天记录合并**
- [ ] 实现合并功能 API
- [ ] 实现去重逻辑
- [ ] 前端合并界面

**Day 11-12：自动迁移**
- [ ] 实现自动迁移 API
- [ ] 集成到账号切换流程
- [ ] 测试和优化

**Day 13-14：优化和测试**
- [ ] 性能优化
- [ ] 错误处理
- [ ] 用户文档
- [ ] MVP 测试

---

## 八、风险与限制

### 8.1 技术风险

1. **WorkBuddy API 变更**
   - 风险：API 接口可能变更，导致签到和聊天记录获取失败
   - 缓解：定期检查 API 文档，更新代码

2. **登录态过期**
   - 风险：账号登录态可能过期，需要重新登录
   - 缓解：实现自动检测和提醒功能

3. **并发问题**
   - 风险：多账号同时签到可能导致冲突
   - 缓解：使用队列机制，串行执行签到任务

### 8.2 功能限制

1. **聊天记录获取**
   - WorkBuddy API 可能不提供完整聊天记录
   - 需要测试 API 能力，可能需要其他方案

2. **自动迁移性能**
   - 聊天记录量大时，合并可能较慢
   - 缓解：支持异步执行，提供进度反馈

3. **数据安全**
   - 聊天记录包含敏感信息
   - 缓解：加密存储，权限控制

---

## 九、下一步行动

1. **确认 MVP 范围**：与用户确认是否需要调整功能优先级
2. **创建任务文件**：按照 AGENTS.md 规范创建任务文件
3. **开始开发**：按照开发路线图执行

---

**文档版本**：v1.0
**创建日期**：2026-11-18
**作者**：AI 助手
