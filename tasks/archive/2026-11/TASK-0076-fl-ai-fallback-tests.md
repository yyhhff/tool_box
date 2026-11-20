# TASK-0076 french-learner backend 批 2：ai.py recast 降级判定表单元测试

- **状态**：已完成（自测通过：unittest 117/117 合并绿；urllib 全 mock 无真机验收环节）
- **优先级**：中
- **项目**：french-learner
- **创建日期**：2026-11-21
- **完成日期**：2026-11-21

## 原始需求

夜班深度巡库优化项 OP-06：ai.py 的 recast 降级判定表（ARCHITECTURE_V2.md §3 明文"9 条逐条覆盖"是契约要求）从未测过——契约关键但零覆盖。

## 需求分析

- **目标**：降级判定表 9 条逐条覆盖 + GLM 调用边界 mock（零网络零计费）
- **改动点**：backend/tests/ 新增 test_ai.py（625 行，39 例）
- **涉及数据**：全部 mock（urllib/db），零真实网络与落库

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3 + ARCHITECTURE_V2.md §3 契约）：先读源码与契约提取 9 条规则原文，逐条对照写用例；**fail-loud 兜底**——setUp 默认 GLM_API_KEY="" 且 urlopen side_effect=AssertionError，任何未编排的网络企图直接判失败（"零网络"红线的技术自证）
- **改动点清单**：仅新增 tests/test_ai.py，产品代码零改动
- **风险与限制**：契约与源码 5 处偏差已逐条记录（SYSTEM_PROMPT 滞后于 D1/D2 加固、recast_of 回填未入契约等）
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [x] 实现 unittest 39 例（实现者；降级表 9 条 → 22 个断言（含 subTest 变体）；错误协议 1 次闭环——mock.patch time.sleep 传 new 非 Mock 致 9 例 AttributeError，假设验证后改默认 MagicMock）
- [x] 父复核全绿（discover 117/117 合并绿，足迹仅 test_ai.py）
- [x] french-learner 仓库提交（b2618c3）+ 主仓库归档

## 验收标准

- [x] 9 条降级判定逐条有用例（对照 ARCHITECTURE_V2.md §3，源码条数=9 与契约一致，自测通过）
- [x] unittest 全绿（117 例合并，自测通过）
- [x] 零真实网络/GLM 调用（fail-loud 自证）；不改产品代码（自测通过）

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 76→77，提交 4aa4356）
- 2026-11-21 实现者交付 + 父复核通过，french-learner 提交 b2618c3；**契约偏差 5 处 + 产品缺陷 4 项只记录不修**（最坏耗时口径低估约 2 倍、_reply_cursor 无锁共享、recast_of 空串语义混用、translate 防御分支不可达）；实现者消耗约 93.4 万 tokens
