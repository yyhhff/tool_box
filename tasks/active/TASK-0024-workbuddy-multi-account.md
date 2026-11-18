# TASK-0024: WorkBuddy 多账号管理工具（MVP）

## 原始需求

实现一个 WorkBuddy 多账号管理工具，支持：
1. 多账号同时登录，在软件中直接切换
2. 每天自动签到，可视化签到结果
3. 一键合并聊天记录，所有账号会话合并到当前账号
4. 切号自动迁移，聊天记录跟着自动迁移

## 已确认的方案

### 方案概述

基于成熟的 GitHub 项目 workbuddy-manager（⭐ 2869）改造，集成 workbuddy-auto-signin（⭐ 2528），实现多账号管理功能。

### 技术选型

- **前端**：Next.js 14 + React + TailwindCSS
- **后端**：FastAPI + Python 3.11+
- **数据库**：SQLite
- **任务调度**：node-cron
- **HTTP 客户端**：httpx / requests

### 架构设计

```
Next.js Web 管理面板（前端）
    ↓
FastAPI 后端（Python）
    ↓
WorkBuddy API（官方）
    ↓
SQLite 数据库（本地存储）
```

### MVP 功能范围

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

### 改动点定位

#### 新增文件
- `tools/workbuddy-multi-account/` - 新工具目录
  - `server.py` - FastAPI 后端主文件
  - `main.py` - CLI 入口（可选）
  - `models.py` - 数据库模型
  - `services/` - 服务层
    - `account_service.py` - 账号管理服务
    - `checkin_service.py` - 签到服务
    - `chat_service.py` - 聊天记录服务
  - `api/` - API 路由
    - `accounts.py` - 账号管理路由
    - `checkin.py` - 签到管理路由
    - `chat.py` - 聊天记录路由
  - `config.py` - 配置文件
  - `utils.py` - 工具函数
  - `requirements.txt` - Python 依赖
- `data/output/workbuddy-multi-account/` - 运行日志
- `data/cache/workbuddy-multi-account/` - 缓存数据

#### 修改文件
- `docs/project_content.md` - 更新工具索引
- `docs/data_content.md` - 更新数据地图

### 子任务清单

#### Phase 1：基础架构搭建（Day 1-2）
- [x] 创建项目目录结构
- [ ] 初始化 Next.js 前端项目（暂缓，先验证后端）
- [x] 初始化 FastAPI 后端项目
- [x] 配置 SQLite 数据库
- [x] 创建数据库模型（accounts, chat_messages, checkin_records, settings）
- [x] 创建基础路由和 API（GET /health）

#### Phase 2：账号管理模块（Day 3-4）
- [x] 实现扫码登录 API（服务层 mock，待接入真实 WorkBuddy API）
- [x] 实现账号切换 API
- [x] 实现账号状态监控（定时任务，每 5 分钟）
- [ ] 前端账号列表页面
- [ ] 前端账号切换功能
- [ ] 前端账号状态显示

#### Phase 3：自动签到模块（Day 5-6）
- [x] 集成 workbuddy-auto-signin 核心逻辑（服务层 mock，待接入真实 API）
- [x] 实现定时任务调度（每天 9:00）
- [x] 实现签到记录存储
- [ ] 前端签到统计页面
- [ ] 前端签到历史记录
- [ ] 前端签到成功/失败统计

#### Phase 4：聊天记录管理（Day 7-10）
- [x] 实现聊天记录存储 API
- [x] 实现历史记录查询 API
- [x] 实现聊天记录合并 API（含去重，已验证）
- [x] 实现自动迁移 API（切换账号时后台触发，依赖 merged_from）
- [ ] 前端聊天记录页面
- [ ] 前端合并聊天记录界面
- [ ] 前端自动迁移开关

#### Phase 5：优化与测试（Day 11-14）
- [x] 后端核心 API 冒烟测试（12 项全部通过）
- [ ] 性能优化
- [ ] 错误处理
- [ ] 用户文档
- [ ] MVP 测试

## 测试与缺陷记录（2026-11-19 冒烟）

### 第一轮（mock 服务层）：12 项全部通过

健康检查 / 创建账号×2 / 账号列表 / 切换 / 状态 / 签到 / 签到记录 / 签到统计 / 合并 / 消息列表 / 历史查询 / merged_from 写入。修复缺陷：
1. D1：二维码 URL 中 account_id 为 None（服务实例未绑定账号 ID）→ login 接口先赋值 account_service.account_id
2. D2：同一秒创建多账号时 ID 冲突（UNIQUE 约束失败）→ ID 追加 uuid 短后缀
3. D3：模型缺少 to_dict 方法（列表接口 500）→ 三个模型补齐 to_dict
4. D4：合并 SQL `IN ?` 非法绑定（SQLite 不支持 tuple 直接绑 IN）→ 动态展开占位符；merged_from 写入移到合并成功后保证数据一致性

### 第二轮（真实协议接入）：单测 21/21 通过 + 服务器级冒烟通过

从 github.com/88lin/workbuddy-auto-signin（⭐2528）源码提取真实协议并重写服务层：
- 端点 `https://copilot.tencent.com`，认证 `Authorization: Bearer <accessToken>`
- 凭据文件 `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`（读带重试，客户端刷新 token 会短暂独占）
- 多账号 = bind 时原样复制凭据快照，运行时各用各的快照（官方级"切号不扫码"机制）
- 签到：`POST /v2/billing/meter/checkin-activity-status` + `POST /v2/billing/meter/daily-checkin`；"已签"兼容 null 与 400+code10001（幂等）
- 成长中心：`/v2/activity/growth/` 下 tasks / tasks/{code}/claim 等接口
- 21 项单测全过：token 三态判定、dig 信封解析、api_success 双重判定、已签到三种形态、bind 无凭据 AUTH_MISSING、假凭据 load_session→client 构造、**真实端点对假 token 返回 HTTP 401（协议路径验证正确）**、CODE_NO_NETWORK
- 服务器级：login 无凭据 503+路径列表、列表 has_credential 字段、签到无凭据 422+原因、状态探测 login_required

修复缺陷：
5. D5：api/checkin.py 残留 `from services.checkin_service import checkin_service`（实例已重构为函数）导致服务器启动失败 → 改为按需 import run_account_checkin
6. D6：api/checkin.py 清理 import 时误删 get_db 导致签到端点 NameError 500 → 补回

### 环境限制说明

- 本机无独立安装的 git；实际使用 WorkBuddy 桌面端自带 PortableGit（G:\WorkBuddy\resources\vendor\PortableGit），已加入用户 PATH

### 第三轮（真机验收，2026-11-19）：核心链路全部通过 ✅

用户登录 WorkBuddy 桌面端后验收：
- 凭据文件落盘，但 accessToken 为**加密信封**（{$wbEncrypted:1, envelope: base64(sym-v1)）
- 移植官方 auth helper 解密机制（MIT, 88lin）：以 ELECTRON_RUN_AS_NODE=1 用 WorkBuddy.exe 执行内嵌 JS，AES-256-GCM + 原生存储密钥解密；probe 验证 Electron 37.10.3 可用；明文仅内存不落盘
- 真机验收结果：
  1. bind 快照成功（acc_20261119004740_1a45a6 / my-work）
  2. 真实状态探测 **online**（解密 → Bearer → copilot.tencent.com）
  3. **真实签到 +100 积分到账**（服务端回读：今日 100 / 连续 4 天 / 累计 400）；成长任务领 3 成功、1 真实业务拒绝（公众号任务未完成，正确处理未崩溃）
  4. 签到记录 4 条入库、分账号统计正确、账号列表真实状态在线

修复缺陷：
7. D7：auth_helper.decrypt_token 入口校验假设 token 为字符串，但真实凭据是 dict（{$wbEncrypted, envelope}）→ 入口接受 dict/str 两种形态
8. D8：token_format 对 dict 形态误判 invalid → 增加加密对象判定
9. D9：probe 的 closing(Popen) 用法错误（Popen 无 close）→ 改 try/finally
10. D10：api/checkin.py 清理 import 时误删 datetime/CheckinRecord（与 D6 同类）→ 补回

遗留：聊天记录获取接口未在 auto-signin/2api-panel 中发现（它们只覆盖签到/任务/网关），聊天合并功能依赖后续探索 WorkBuddy 会话 API 或本地会话数据导出；多账号第二账号 bind 待用户切换登录后验收。

### 输出物与验收标准

#### 输出物
1. **代码文件**
   - FastAPI 后端代码
   - Next.js 前端代码
   - 数据库模型
   - API 路由

2. **文档**
   - README.md（使用说明）
   - API 文档（自动生成）
   - 用户文档

3. **数据文件**
   - SQLite 数据库（运行时生成）
   - 运行日志（data/output/workbuddy-multi-account/）

#### 验收标准
1. **账号管理**
   - [ ] 可以成功扫码登录多个账号
   - [ ] 可以在软件中切换账号
   - [ ] 账号状态实时更新

2. **自动签到**
   - [ ] 每天自动执行签到任务
   - [ ] 签到成功/失败正确记录
   - [ ] 积分变化正确统计

3. **签到可视化**
   - [ ] 可以查看签到历史记录
   - [ ] 可以查看成功/失败统计
   - [ ] 可以查看每日积分变化

4. **聊天记录合并**
   - [ ] 可以合并多个账号的聊天记录
   - [ ] 合并后可以正常查看
   - [ ] 去重逻辑正确

5. **自动迁移**
   - [ ] 切换账号时自动迁移聊天记录
   - [ ] 迁移后聊天记录完整
   - [ ] 可以配置是否启用自动迁移

### 风险与限制

#### 技术风险
1. **WorkBuddy API 变更**
   - 风险：API 接口可能变更
   - 缓解：定期检查 API 文档，更新代码

2. **登录态过期**
   - 风险：账号登录态可能过期
   - 缓解：实现自动检测和提醒功能

3. **并发问题**
   - 风险：多账号同时签到可能导致冲突
   - 缓解：使用队列机制，串行执行签到任务

#### 功能限制
1. **聊天记录获取**
   - WorkBuddy API 可能不提供完整聊天记录
   - 需要测试 API 能力

2. **自动迁移性能**
   - 聊天记录量大时，合并可能较慢
   - 缓解：支持异步执行，提供进度反馈

3. **数据安全**
   - 聊天记录包含敏感信息
   - 缓解：加密存储，权限控制

### 参考资料

1. **workbuddy-manager**：https://github.com/ithtelab/workbuddy-manager（⭐ 2869）
2. **workbuddy-auto-signin**：https://github.com/88lin/workbuddy-auto-signin（⭐ 2528）
3. **workbuddy2api-panel**：https://github.com/linguo2625469/workbuddy2api-panel（⭐ 4914）

### 经验沉淀

- 基于成熟项目改造可以大幅缩短开发时间
- SQLite 适合本地存储，零配置
- 前后端分离架构易于扩展
- 定时任务调度使用 node-cron 简单可靠

---

**任务状态**：进行中
**创建日期**：2026-11-18
**负责人**：AI 助手
**预计完成**：2026-12-01（2 周后）
