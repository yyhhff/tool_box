# TASK-0075 french-learner backend 批 1：srs.py + assessment.py 单元测试

- **状态**：进行中
- **优先级**：中
- **项目**：french-learner
- **创建日期**：2026-11-21
- **完成日期**：

## 原始需求

夜班深度巡库优化项 OP-05：french-learner backend 仅 test_pron_coach.py（15 例），补纯模块测试批 1。

## 需求分析

- **目标**：srs.py（SM-2 纯函数，零依赖）+ assessment.py（判分定级/中文解读，读 assessment_questions.json 稳定文件）回归护栏
- **改动点**：tools/french-learner/backend/tests/ 新增测试文件（__init__.py 引导已就绪，NB-004）
- **涉及数据**：assessment_questions.json 只读；不碰 texts.json（语料量产现场）、pron_coach.py（0068 车道）、content_pipeline（0066/0069 车道）、seed_input.py

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3 + 深度巡库报告）：实现者读源码定用例；发现产品缺陷只记录不修
- **改动点清单**：仅新增 tests/test_srs.py + tests/test_assessment.py（或合理拆分）
- **风险与限制**：french-learner 独立仓库内提交（精确 add）；主仓库不动
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [ ] 实现 unittest（实现者）
- [ ] 父复核全绿（含既有 15 例）
- [ ] french-learner 仓库提交 + 主仓库归档

## 验收标准

- [ ] unittest 全绿且 discover 可用（与既有 15 例合并跑）
- [ ] 不碰并行车道文件（texts.json/pron_coach.py/content_pipeline/seed_input）
- [ ] 不修改产品代码

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 75→76）
