# TASK-0041 start.bat 启动前自动清理旧服务

- **状态**：进行中
- **优先级**：中
- **项目**：tools/workbuddy-multi-account
- **创建日期**：2026-11-19
- **完成日期**：

## 原始需求

> 我切换号后在客户端没有看到迁过去的任务。（排查发现是工具服务进程从凌晨 01:15 启动、早于 12:09 写入的迁移代码，一直跑旧代码）
> 删除旧服务的功能也放到这个启动脚本中。

## 需求分析

- **目标**：`start.bat` 启动时自动终止仍在运行的旧服务进程（占用 8000 端口、命令行含 `uvicorn server:app`），避免改了代码却因旧进程残留而跑旧代码；不再需要用户手动 `taskkill`。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `tools/workbuddy-multi-account/start.bat`（新增清理段）
- **涉及数据**（引用数据地图 `docs/data_content.md`）：无持久化数据改动，仅进程管理。

## 方案（已确认）

> 2026-11-19 会话中提交方案，用户回复"可以"确认。

- **实现思路**：start.bat 顶部（依赖检查前）用 `netstat -ano` 找监听 8000 端口的 PID → 用 PowerShell `Get-CimInstance Win32_Process` 核对该 PID 命令行同时含 `uvicorn` 与 `server:app`（本工具服务特征）→ 确认是自己人才 `taskkill /F`，否则只提示不杀；杀完等 1 秒再走原启动流程。
- **改动点清单**：
  - `tools/workbuddy-multi-account/start.bat`：加清理段（含异常兜底，不让脚本崩）
  - `tools/workbuddy-multi-account/README.md`：启动说明补一句"自动清理旧服务"
- **风险与限制**：
  - 命令行核对依赖 PowerShell（Windows 自带），查询失败则降级为按端口兜底并提示，不阻断启动；
  - 只针对 8000 端口，不动 8001（french-learner）；
  - 不误杀：非本工具进程占用 8000 只提示不 kill。
- **用户确认日期**：2026-11-19

## 子任务

- [x] 1. 登记任务 + 看板（总指挥）
- [x] 2. 改 start.bat：清理旧服务段（总指挥）
- [x] 3. 新增 cleanup_old_service.ps1 + README 启动说明同步（总指挥）
- [x] 4. 只读演练验证：识别逻辑正确、不误杀、异常兜底
- [ ] 5. 收尾：看板 + 地图 + 提醒 git

## 验收标准

- [x] 旧服务在跑（8000 被本工具 uvicorn 占用）→ DryRun 精确识别 PID 26988（命令行含 uvicorn+server:app），演练不真杀（复验 26988 仍在监听）
- [x] 8000 被无关程序占用 → 只提示、不 kill（实测 PID 25056 命令行不匹配，被跳过；未误伤）
- [x] 无旧服务 → 端口空闲分支提示正常（临时副本用 59999 验证，无报错）
- [x] PowerShell 查询异常 → 脚本全 ASCII 避免 5.1 GBK 解码崩溃；ps1 语法解析通过；netstat 降级路径保留
- [x] 不改变原有依赖检查与启动行为（仅前置一段 ps1 调用）
- [x] 真机双击 start.bat 验证（用户授权后执行）：首次跑暴露 bat 编码 bug → 修复后重跑，日志显示 `[cleanup] found stale service PID=26988, stopping...` / `stopped 1 stale service(s)`，实测 PID 26988 已死亡（清理生效）

## 变更记录

- 2026-11-19 创建
- 2026-11-19 真机验证发现并修复 start.bat 编码缺陷：UTF-8 无 BOM + 中文，cmd 在 chcp 65001 生效前用 GBK 预读缓冲，中文被解码出危险字节把 `powershell -File` 行拦腰截断（`'p_old_service.ps1" 不是内部命令`），清理从未执行。修法：start.bat 全部改 ASCII 英文（与 ps1 一致），重跑验证通过
- 2026-11-19 附：原脚本依赖检查行 `python -c "import ..."` 每次都返回非 0 触发"首次运行安装依赖"（pip 全 already-satisfied，无害），属既有行为，本任务未改
