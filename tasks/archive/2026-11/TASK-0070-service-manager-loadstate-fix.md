# TASK-0070 service_manager `_load_state` 容错修复

- **状态**：已完成（自测通过：unittest 22/22 绿；纯逻辑修复，验收标准均为单测可断言项，无真机验收环节）
- **优先级**：高
- **项目**：service_manager
- **创建日期**：2026-11-20
- **完成日期**：2026-11-20

## 原始需求

夜班任务池 NB-001（2026-11-19 演练 TASK-0030 子 agent 发现的真实缺陷，用户指示"优化项直接实施"）。

## 需求分析

- **缺陷**（tools/service_manager/service_manager.py:40-48）：
  1. services.json 缺某服务键时，`get_status`/`_start_service` 取 `self.state[service_id]` 抛 KeyError
  2. JSON 损坏时 `__init__` 抛 JSONDecodeError → 模块导入失败 → server.py 起不来
- **目标**：状态文件损坏/缺键时服务管理器仍可启动，且不丢原数据

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3；备选取舍：损坏时报错退出（保持显式失败）被否——服务管理工具的 README 契约是"启动/重启/关闭服务"，状态文件损坏不应阻断工具启动）：加载时逐键补默认结构（已有键数据保留）；JSON 解析失败时先把原文件重命名为 `services.json.corrupt-<YYYYmmdd-HHMMSS>.bak` 再重建默认结构并落盘；日志打印一条警示。
- **改动点清单**：`tools/service_manager/service_manager.py` 仅改 `_load_state`；`tools/service_manager/test_service_manager.py` 增补用例
- **风险与限制**：备份文件落在 data/cache/（gitignore 内，不入库）；已知限制：同秒内两次损坏会因 rename 重名抛错（概率可忽略）；键内层结构非法（非 dict）未防御，可作后续任务
- **用户确认日期**：2026-11-20（夜间章程代行）

## 子任务

- [x] 实现 `_load_state` 容错（实现者子 agent，含顶层非 dict 按损坏处理的方案内最小扩展）
- [x] 增补 unittest 用例（损坏 JSON 备份重建/顶层非 dict/缺键补默认，共 +3 例）
- [x] 父复核全绿（22/22，diff 精确限定两文件）
- [x] git 提交（a7af9e3）+ 看板登记

## 验收标准

- [x] `python -m unittest discover -s tools/service_manager -t tools/service_manager -p "test_*.py"` 全绿（22 例，自测通过）
- [x] 损坏 JSON 场景：不抛异常、默认结构、原文件有 .bak 备份且内容为损坏原文（自测通过）
- [x] 缺键场景：缺失服务补默认结构，已有键数据（running=True/process=2222/error）不变（自测通过）

## 变更记录

- 2026-11-20 夜班创建（领号 next_id 70→71，提交 0d9886f）
- 2026-11-20 实现者交付 + 父复核通过，提交 a7af9e3；错误协议执行 1 次（测试断言与"重建落盘"自相矛盾 → 修正断言，假设获印证）
