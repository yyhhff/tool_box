# TASK-0073 service_manager server.py Flask 路由单元测试

- **状态**：已完成（自测通过：unittest 44/44 合并绿；路由层 mock 测试，无真机验收环节）
- **优先级**：中
- **项目**：service_manager
- **创建日期**：2026-11-21
- **完成日期**：2026-11-21

## 原始需求

夜班深度巡库优化项 OP-01：server.py 6 条 Flask 路由零测试，照 xhs_crawler test_xhs_server.py 先例补齐。

## 需求分析

- **目标**：Web 管理界面 API 回归护栏（root/status/start/stop/restart/logs），零真实进程/端口
- **改动点**：tools/service_manager/ 新增 test_server_api.py
- **涉及数据**：目录常量 mock 重定向临时目录

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3 + 深度巡库侦察报告）：`app.test_client()` 进程内 + mock manager 实例方法 + 目录常量 patch tmp
- **改动点清单**：仅新增 test_server_api.py（352 行）
- **风险与限制**：导入 server.py 创建 data/cache/service_manager 目录（gitignore 内，预期）
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [x] 实现 unittest 22 例（实现者；错误协议执行 1 次——运行方式操作失误经假设分析纠正，非代码问题）
- [x] 父复核全绿（discover 44/44 合并绿，仅新增一个文件）
- [x] git 提交（e7a48d0）+ 归档

## 验收标准

- [x] unittest 全绿且 discover 可用（与既有 22 例合并 44/44，自测通过）
- [x] 零真实进程/端口操作（manager 四方法全 mock、test_client 进程内，自测通过）
- [x] 不修改产品代码（git status 确认，自测通过）

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 73→74，提交 79760e2）
- 2026-11-21 实现者交付 + 父复核通过，提交 e7a48d0；**附带发现真实缺陷**：server.py:50 `manager.CACHE_DIR` 引用未绑实例属性（ServiceManager.__init__ 未绑 self.CACHE_DIR）→ /api/logs 生产环境必 500；红线禁改源码，测试以 create=True 规避，**待白天修复**（__init__ 绑 self.CACHE_DIR/self.LOGS_DIR）；实现者消耗约 56.8 万 tokens
