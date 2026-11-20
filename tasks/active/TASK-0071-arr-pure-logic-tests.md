# TASK-0071 annual_report_reader 补纯逻辑单元测试（unittest）

- **状态**：进行中
- **优先级**：中高
- **项目**：annual_report_reader
- **创建日期**：2026-11-20
- **完成日期**：

## 原始需求

夜班任务池 NB-002：巡库发现 annual_report_reader 无测试资产，补 fetcher/extractor 等模块纯逻辑单测。

## 需求分析

- **目标**：为不触网、不调 GLM、无重副作用的纯逻辑建立回归护栏（如章节定位、文件命名、配置读写、数据结构处理）
- **改动点**：tools/annual_report_reader/tests/（新建，含 __init__.py 避免 discover 不可导入，NB-004 教训）
- **涉及数据**：测试自建临时夹具，不读写 data/output/ 真实数据

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4；测试清单以侦察员结论为准，实现前补录）
- **改动点清单**：新增 tests/__init__.py + tests/test_pure_logic.py（或按模块拆分）
- **风险与限制**：涉及网络/GLM/PDF 下载的路径一律 mock 或不测；不改产品代码
- **用户确认日期**：2026-11-20（夜间章程代行）

## 子任务

- [ ] 侦察：可测纯逻辑清单（侦察员）
- [ ] 实现 unittest（实现者）
- [ ] 父复核全绿
- [ ] git 提交 + 归档

## 验收标准

- [ ] `python -m unittest discover -s tools/annual_report_reader/tests -t tools/annual_report_reader -p "test_*.py"` 全绿（含 __init__.py 后 discover 可用）
- [ ] 全部用例不触网、不调 GLM、不写 data/output
- [ ] 不修改产品代码

## 变更记录

- 2026-11-20 夜班创建（领号 next_id 71→72）
