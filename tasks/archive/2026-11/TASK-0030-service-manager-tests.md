# TASK-0030 service_manager 补单元测试（unittest）

- **状态**：已完成
- **优先级**：高
- **项目**：service_manager
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

夜班演练（TASK-0028）巡库发现 5 个子工具均无自有测试；按夜班章程第 4 节优先级，先为 service_manager 补测试（任务池 NB-001）。原编号 0029 与并行会话任务撞号，已按章程顺延为 0030。

## 需求分析

- **目标**：为 `tools/service_manager/service_manager.py` 核心逻辑建立回归护栏，全部 mock，不触真实进程/端口。
- **改动点**（引用项目地图 `docs/project_content.md`）：`tools/service_manager/` 新增 test_service_manager.py；README 无需改（运行方式写入测试文件 docstring）。
- **涉及数据**（引用数据地图 `docs/data_content.md`）：测试用临时目录，不写 data/cache/（测试中 CACHE_DIR 被 patch 到 tmp）。

## 方案（已确认）

- **实现思路**：标准库 unittest（本机无 pytest，夜间零环境改动）；19 例覆盖状态加载/保存往返、_clear_state、未知 id、get_status 僵尸自纠、停止幂等、端口判定三场景、进程归属判定（cmdline 命中/端口兜底/双不中）。
- **改动点清单**：新增 `tools/service_manager/test_service_manager.py`。
- **风险与限制**：模块级 `manager = ServiceManager()` 导入副作用会创建 data/cache 目录（已 gitignore，预期内）；未覆盖 server.py 路由层（后续 NB-002 轮转补）。
- **用户确认日期**：2026-11-19（夜班章程代行确认，依据 docs/night_ops.md 第 2/4 节）

## 子任务

- [x] 实现：test_service_manager.py 19 例（实现者子 agent，general-purpose）
- [x] 父复核：`python -m unittest discover -s tools/service_manager -t tools/service_manager -p "test_*.py"` → 19/19 OK
- [x] git 提交
- [x] 看板登记

## 验收标准

- [x] `python -m unittest discover -s tools/service_manager -t tools/service_manager -p "test_*.py"` 输出 OK（19 tests）
- [x] 未启动真实进程、未改产品代码、未 pip 安装
- [x] 发现的疑似产品 bug 只记录不修（4 项已转 TASK-0028 夜报"次日建议"）

## 变更记录

- 2026-11-19 创建（原 0029，撞号顺延）；实现者子 agent 交付 + 父复核通过
