# TASK-0073 service_manager server.py Flask 路由单元测试

- **状态**：进行中
- **优先级**：中
- **项目**：service_manager
- **创建日期**：2026-11-21
- **完成日期**：

## 原始需求

夜班深度巡库优化项 OP-01：server.py 6 条 Flask 路由零测试，照 xhs_crawler test_xhs_server.py 先例补齐。

## 需求分析

- **目标**：Web 管理界面 API 回归护栏（status/start/stop/restart/logs 等），零真实进程/端口
- **改动点**：tools/service_manager/ 新增 test_server_api.py
- **涉及数据**：CACHE_DIR/LOGS_DIR mock 重定向临时目录

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3 + 侦察报告）：`app.test_client()` 进程内 + mock.patch ServiceManager 实例方法（get_status/start_service/stop_service/restart_service）+ 模块级 CACHE_DIR/LOGS_DIR patch 到 tmp；logs 路由补"日志文件不存在"分支
- **改动点清单**：仅新增 tests 文件，不改 server.py / service_manager.py
- **风险与限制**：导入 server.py 会创建真实 data/cache/service_manager 目录（gitignore 内，预期）；不真实启动服务
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [ ] 实现 unittest（实现者）
- [ ] 父复核全绿
- [ ] git 提交 + 归档

## 验收标准

- [ ] unittest 全绿且 discover 可用（与既有 22 例合并跑）
- [ ] 零真实进程/端口操作
- [ ] 不修改产品代码

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 73→74）
