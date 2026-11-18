# 多账号管理工具 GitHub 项目调研

## 需求总结

- 多账号同时登录，在软件中直接切换
- 每天自动签到，可视化签到结果
- 一键合并所有账号的聊天记录到当前账号
- 切号自动迁移聊天记录
- 不用反复扫码登录

## 推荐的 GitHub 项目方向

### 1. Telegram 多账号管理工具（最成熟）

**项目示例：**
- `https://github.com/paul-nameless/tg-multi-account`（多 Telegram 账号管理）
- `https://github.com/DrKLO/Telegram`（官方客户端，本身支持多设备登录）

**适合原因：**
- Telegram 官方客户端支持多设备同时登录，切换账号只需在客户端内操作
- 开源客户端（如 MTProto）可改造为多账号切换 UI
- 聊天记录存储在本地 SQLite/JSON，易于合并
- 签到功能可扩展

**改造建议：**
- 基于 MTProto 客户端或 Telegram-Desktop 源码改造
- 添加多账号配置文件（每个账号一个 profile）
- 实现自动签到脚本（定时任务）
- 实现聊天记录合并功能（SQL/JSON 合并）

### 2. 微信多开/多账号工具（最接近你的需求）

**项目示例：**
- `https://github.com/lencx/WeChaty`（微信机器人框架，支持多实例）
- `https://github.com/wechaty/wechaty-puppet-wechat`（基于 PC 端协议）
- `https://github.com/ttttupup/wechat-multi-account`（多账号管理工具）

**适合原因：**
- 微信是典型的即时通讯工具，多账号管理需求强
- WeChaty 提供了完整的机器人框架，可扩展多账号
- 支持脚本自动化（签到、消息处理）

**改造建议：**
- 基于 WeChaty 多实例架构
- 添加图形界面（Electron + React/Vue）
- 实现账号切换逻辑（切换 puppet 实例）
- 实现聊天记录迁移（数据库同步）

### 3. QQ 多开/多账号工具

**项目示例：**
- `https://github.com/pcrbot/qq-bot`（QQ 机器人框架）
- `https://github.com/Mrs4s/go-cqhttp`（QQ 逆向协议）

**适合原因：**
- QQ 支持多设备登录
- go-cqhttp 提供完整的 API
- 适合做自动化任务

**改造建议：**
- 基于 go-cqhttp 多实例
- 添加 Web UI 管理后台
- 实现自动签到和记录迁移

### 4. 通用多账号管理框架（可定制）

**项目示例：**
- `https://github.com/microsoft/terminal`（Windows Terminal，支持多标签页，可扩展）
- `https://github.com/TerminalStudio/Alacritty`（跨终端，可定制）

**适合原因：**
- 通用框架，可扩展多账号 UI
- 插件系统丰富

**改造建议：**
- 基于 Electron 框架开发
- 设计多账号配置结构
- 实现跨平台 UI

## 技术选型建议

### 推荐方案：Electron + WeChaty/MTProto

**理由：**
1. **跨平台**：Windows/Mac/Linux 通用
2. **开发效率**：Electron 生态成熟，UI 开发快
3. **多账号支持**：WeChaty 支持多实例，易于扩展
4. **聊天记录管理**：数据库结构清晰，易于合并

### 架构设计

```
┌─────────────────────────────────────┐
│         Electron GUI 界面            │
│  ┌──────────┬──────────┬──────────┐ │
│  │ 账号 A   │ 账号 B   │ 账号 C   │ │
│  └──────────┴──────────┴──────────┘ │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   多实例管理器（Node.js）            │
│  - 启动/停止/切换账号实例            │
│  - 聊天记录存储（SQLite）           │
│  - 签到任务调度器                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   协议层（WeChaty/MTProto）          │
│  - 账号登录/登出                    │
│  - 消息收发                          │
│  - 签到接口                          │
└─────────────────────────────────────┘
```

### 核心功能实现思路

#### 1. 多账号切换
- 每个账号维护一个独立的 WeChaty 实例
- 配置文件存储账号信息（token/cookie/二维码）
- UI 通过切换当前激活的实例实现切换

#### 2. 自动签到
- 定时任务（node-cron）
- 每个账号独立签到接口
- 结果记录到数据库，可视化展示

#### 3. 聊天记录合并
- 每个账号的聊天记录存储在独立数据库
- 合并时：SELECT * FROM chat_messages WHERE account_id = 'A' UNION ALL SELECT * FROM chat_messages WHERE account_id = 'B'
- 可按时间/联系人筛选

#### 4. 自动迁移
- 切换账号时触发迁移脚本
- 将旧账号的聊天记录同步到新账号数据库
- 可配置是否启用自动迁移

## 数据存储设计

### SQLite 数据库结构

```sql
-- 账号表
CREATE TABLE accounts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL, -- 'online'/'offline'/'login_required'
  last_login_time DATETIME,
  auto_checkin BOOLEAN DEFAULT 1,
  auto_merge BOOLEAN DEFAULT 0
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
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- 系统配置表
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

## 开发路线图

### Phase 1：基础架构
- [ ] Electron 项目初始化
- [ ] WeChaty 多实例集成
- [ ] 账号配置文件管理
- [ ] 基础 UI（账号列表、切换）

### Phase 2：核心功能
- [ ] 自动登录/扫码
- [ ] 多账号切换
- [ ] 聊天记录存储
- [ ] 自动签到

### Phase 3：高级功能
- [ ] 聊天记录合并
- [ ] 自动迁移
- [ ] 签到结果可视化
- [ ] 数据统计

### Phase 4：优化与完善
- [ ] 性能优化
- [ ] 错误处理
- [ ] 用户文档
- [ ] 自动更新

## 参考项目

### 直接可用的开源项目
1. **WeChaty**：https://github.com/wechaty/wechaty
   - 微信机器人框架，支持多实例
   - 可作为基础架构

2. **MTProto**：https://github.com/DrKLO/Telegram
   - Telegram 官方协议实现
   - 支持多账号登录

3. **go-cqhttp**：https://github.com/Mrs4s/go-cqhttp
   - QQ 逆向协议
   - 适合做自动化任务

### UI 框架参考
- **Electron + React**：https://www.electronjs.org/
- **Electron + Vue**：https://electronjs.org/docs/latest/tutorial/vue

## 下一步

1. 确定目标平台（微信/QQ/Telegram）
2. 选择基础框架（WeChaty/MTProto/go-cqhttp）
3. 设计数据库结构
4. 开发原型验证可行性

---

**调研日期**：2026-11-18
**调研人**：AI 助手
