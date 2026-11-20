# TASK-0075 french-learner backend 批 1：srs.py + assessment.py 单元测试

- **状态**：已完成（自测通过：unittest 78/78 合并绿；mock 路径测试无真机验收环节）
- **优先级**：中
- **项目**：french-learner
- **创建日期**：2026-11-21
- **完成日期**：2026-11-21

## 原始需求

夜班深度巡库优化项 OP-05：french-learner backend 仅 test_pron_coach.py（15 例），补纯模块测试批 1。

## 需求分析

- **目标**：srs.py（SM-2 纯函数）+ assessment.py（判分定级/中文解读）回归护栏
- **改动点**：backend/tests/ 新增 test_srs.py（24 例）+ test_assessment.py（39 例）
- **涉及数据**：assessment_questions.json 只读；不碰并行车道（texts.json/pron_coach.py/content_pipeline/seed_input）

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3）：实现者读源码按真实行为覆盖；源码无兜底处固化为现状契约并注明
- **改动点清单**：仅两个新测试文件（584 行），产品代码零改动
- **风险与限制**：grade 未知 id/缺 answer_idx 抛 KeyError 依赖 API 层兜底（app.py 未核查）
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [x] 实现 unittest 63 例（实现者；一次自我纠错——定级门槛误预期经分析修正，非机械重试）
- [x] 父复核全绿（discover 78/78 合并绿；并行车道 app.py/growth.js 现场未触碰）
- [x] french-learner 仓库提交（adc1791）+ 主仓库归档

## 验收标准

- [x] unittest 全绿且 discover 可用（78 例合并绿，自测通过）
- [x] 不碰并行车道文件（git status 确认足迹仅两个测试文件）（自测通过）
- [x] 不修改产品代码（自测通过）

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 75→76，提交 eb6781a）
- 2026-11-21 实现者交付 + 父复核通过，french-learner 提交 adc1791；**产品缺陷清单 7 项只记录不修**（grade 未知 id KeyError / 缺 answer_idx KeyError / answers 不去重可致 rate>1 / schedule rating 无校验 / state 缺 key KeyError / 百分比银行家舍入观感 / weak_skill 空作答语义）；实现者消耗约 53.3 万 tokens
