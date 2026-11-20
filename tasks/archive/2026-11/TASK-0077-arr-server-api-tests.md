# TASK-0077 annual_report_reader server.py 路由单元测试

- **状态**：已完成（自测通过：unittest 154/154 合并绿；test_client 进程内无真机验收环节）
- **优先级**：中
- **项目**：annual_report_reader
- **创建日期**：2026-11-21
- **完成日期**：2026-11-21

## 原始需求

夜班深度巡库优化项 OP-03：ARR server.py（219 行，6 路由 api_industries/start/status/history/report）零测试，照 xhs_crawler/service_manager 先例补 test_client 测试。

## 需求分析

- **目标**：Web API 回归护栏（行业列表/启动分析/状态/历史/报告读取 + _log 状态机 + 刷新线程），零网络零 GLM
- **改动点**：tests/ 新增 test_server.py（547 行，36 例）
- **涉及数据**：DATA_OUT/CONFIG_PATH/INDEX_PATH 重定向临时目录；industry/pipeline 全 mock

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3 + 深度巡库侦察报告）：test_client 进程内 + threading.Thread 全 mock（_run_pipeline/_refresh_snapshot 同步直调）；mock 点按源码实际（server.industry / server.pipeline，非侦察建议的 industry.select——它在 main.run_pipeline 内）
- **改动点清单**：仅新增 tests/test_server.py，产品代码零改动
- **风险与限制**：selfcheck.py 未收集未导入（-p "test_*.py" 模式安全）
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [x] 实现 unittest 36 例（实现者）
- [x] 父复核全绿（discover 154/154 合并绿，足迹仅 test_server.py）
- [x] git 提交（0753aba）+ 归档

## 验收标准

- [x] unittest 全绿且 discover 可用（154 例合并绿，自测通过）
- [x] 零网络零 GLM 零真实 data/ 读写（mock 失效必失败断言方式，自测通过）
- [x] 不修改产品代码（git status 确认，自测通过）

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 77→78，提交 8603e67）
- 2026-11-21 实现者交付 + 父复核通过，提交 0753aba；**产品缺陷 2 项只记录不修**（api_report 目录穿越前缀比对未补分隔符，同级目录可绕过；api_start 非数字 top_n 500 而非 400）；实现者消耗约 45.3 万 tokens
