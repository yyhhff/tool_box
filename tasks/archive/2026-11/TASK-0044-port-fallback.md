# TASK-0044 端口可配 + 占用时自动回退（修复页面显示旧 JSON）

- 项目：workbuddy-multi-account
- 创建：2026-11-19
- 优先级：高
- 状态：进行中

## 需求

双击 start.bat 自动打开的页面显示旧版 JSON `{"message":"WorkBuddy 多账号管理工具 API"...}`，而非管理面板。根因：凌晨旧服务 PID 25056 已成僵尸（进程查不到但端口未释放，taskkill 无效），新服务绑上 8000 却收不到流量。用户裁决：不跟僵尸纠缠，改用端口可配 + 自动回退。

## 方案（已确认）

前端 `const API = ""` 用相对路径，页面在哪个端口开、API 就请求哪个端口 → 换端口天然可行。

1. **config.py**：新增 `PORT_ENV = "WORKBUDDY_MA_PORT"`、`DEFAULT_PORT = 8000`、`FALLBACK_PORTS = range(8001, 8020)`，提供 `get_port()` 读环境变量（非法值回退默认）。
2. **server.py**：`uvicorn.run(port=get_port())`；关闭 `reload=True`（reload spawn 子进程是僵尸来源，单进程更干净）；host 保持 0.0.0.0。
3. **cleanup_old_service.ps1**：降级为尽力而为——能查到的旧服务照杀；僵尸查不到不阻塞。新增 `-Port` 参数（默认 8000）。
4. **open_browser.ps1**：新增 `-Port` 参数，URL/health URL 由端口拼出（现有 `-Url`/`-HealthUrl` 保留兼容）。
5. **start.bat**（全 ASCII）：启动前探测选定端口——被占用**且健康端点不是本工具面板**（返回 JSON 而非 HTML）→ 视为僵尸/他人占用，自动从 8001–8019 挑空闲端口 → `set WORKBUDDY_MA_PORT=<port>` → 传给 cleanup/open_browser → 启动服务 → 浏览器打开新端口。支持 `WORKBUDDY_MA_PORT` 手动固定（固定时被占用则不自动换、给出提示）。
6. README / 两张地图 / 经验库 / 看板 / 工作日志同步。

## 端口契约（核心）

- 唯一端口来源：`WORKBUDDY_MA_PORT` 环境变量（server.py 通过 config.get_port 读取）。
- start.bat 负责探测 + 选定 + `set`，并把选定值传给 cleanup（-Port）和 open_browser（-Port）。
- 前端相对路径，无需改。
- 判定"本工具在跑"：health 200 且根路径 Content-Type 含 `text/html`（面板）；根路径返回 JSON（旧版）视为不可用。

## 子任务

- [x] 1. 登记任务 + 看板（总指挥）
- [x] 2. config.py + server.py：端口可配 + 关 reload
- [x] 3. cleanup_old_service.ps1：-Port 参数 + 尽力而为
- [x] 4. open_browser.ps1：-Port 参数
- [x] 5. start.bat：探测 + 选端口 + 接线（全 ASCII）
- [x] 6. 真机验证：双击后浏览器显示面板（非 JSON），API 正常
- [x] 7. 收尾：README/地图/看板/经验库/日志 + 提醒 git

## 验收标准

- [x] 双击 start.bat → 自动选空闲端口 → 浏览器打开该端口 → 显示管理面板（非 JSON）（真机：8000 被僵尸占→自动选 8001→返回 `text/html` 面板，僵尸 8000 仍返回旧 JSON）
- [x] `WORKBUDDY_MA_PORT` 手动固定时使用该端口；被占用时给出提示不自动换（get_port 单测：合法/非法/越界值均正确；start.bat `PORT_MANUAL` 分支提示不换）
- [x] 前端 API 请求（相对路径）在新端口正常工作（8001 `/api/accounts/list` 正常返回账号数据含 uid；对比僵尸 8000 报 `to_dict` 错）
- [x] 服务单进程运行（无 reload 子进程残留，杜绝新僵尸）（server.py `reload=False`）
- [x] 所有脚本纯 ASCII、语法正确（三脚本非 ASCII 字节=0，两 ps1 语法 OK，config/server 编译过）

## 变更记录

- 2026-11-19 创建并实施完成，真机验证通过（端口自动回退 8001 + 面板 HTML + API 正常 + 浏览器打开 8001）
