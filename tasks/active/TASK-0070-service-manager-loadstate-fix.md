# TASK-0070 service_manager `_load_state` 容错修复

- **状态**：进行中
- **优先级**：高
- **项目**：service_manager
- **创建日期**：2026-11-20
- **完成日期**：

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
- **风险与限制**：备份文件落在 data/cache/（gitignore 内，不入库）
- **用户确认日期**：2026-11-20（夜间章程代行）

## 子任务

- [ ] 实现 `_load_state` 容错（实现者子 agent）
- [ ] 增补 unittest 用例（损坏 JSON/缺键/备份生成/正常回归）
- [ ] 父复核全绿
- [ ] git 提交 + 看板登记

## 验收标准

- [ ] `python -m unittest discover -s tools/service_manager -t tools/service_manager -p "test_*.py"` 全绿（原 19 例 + 新增用例）
- [ ] 损坏 JSON 场景：工具可正常导入启动，原文件有 .bak 备份
- [ ] 缺键场景：缺失服务补默认结构，已有键数据不变

## 变更记录

- 2026-11-20 夜班创建（领号 next_id 70→71）
