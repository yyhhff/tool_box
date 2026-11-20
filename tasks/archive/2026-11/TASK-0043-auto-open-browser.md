# TASK-0043 启动后自动在浏览器打开管理面板

- 项目：workbuddy-multi-account
- 创建：2026-11-19
- 优先级：低
- 状态：进行中

## 需求

像呀呀法语（french-learner）那样，双击 `start.bat` 启动服务后自动在默认浏览器打开 Web 管理面板，省去手动输入 `http://127.0.0.1:8000`。

## 方案

- 关键差异：呀呀法语服务是后台启动、脚本能继续往下走等 health；本工具是 `python server.py` 前台阻塞（保留"关窗即停"语义），脚本停在这行不会往下走。
- 实现：在 `python server.py` 之前用 `start "" /min powershell ...` 拉起一个后台 helper，轮询 `/health` 就绪后 `Start-Process` 打开默认浏览器；最多等 30 秒。
- 复用呀呀法语约定：`start "" url`（空标题）、就绪后再开、`MULTIACCT_NO_BROWSER=1` 可禁用（对应 `YAYA_NO_BROWSER`）。
- 全程 ASCII（沿用 TASK-0041 编码坑教训）。
- 新增 `open_browser.ps1`（ASCII、可 `-DryRun` 演练）；`start.bat` 接线；README 启动说明同步。

## 子任务

- [x] 1. 登记任务 + 看板（总指挥）
- [x] 2. 新增 open_browser.ps1（轮询 /health + 开浏览器 + DryRun）
- [x] 3. start.bat 接线（后台拉起 helper + 禁用开关）
- [x] 4. README 启动说明同步
- [x] 5. 验证：语法 + DryRun 两分支 + 真机开浏览器（全过：ps1 语法 OK、两文件纯 ASCII、DryRun 就绪/未就绪分支正确、真机浏览器进程 20→22）
- [x] 6. 收尾：看板 + 地图 + 提醒 git

## 验收标准

- [x] 双击 start.bat → 服务起来后浏览器自动打开面板（真机验证：health 就绪后 helper `Start-Process` 生效，浏览器进程 20→22）
- [x] 设 MULTIACCT_NO_BROWSER=1 → 不自动打开（start.bat 用 `if defined` 跳过拉起 helper；DryRun 未就绪分支另验证超时跳过不报错）
- [x] 服务启动失败/超时 → 脚本不受影响，最多控制台提示（helper 独立后台进程 + 30s 超时兜底，不阻塞前台 server）
- [x] 原有清理旧服务、依赖检查、前台运行不受影响（仅在其后追加一段，未改动原逻辑）

## 变更记录

- 2026-11-19 创建并实施完成，真机验证通过
