# TASK-0076 french-learner backend 批 2：ai.py recast 降级判定表单元测试

- **状态**：进行中
- **优先级**：中
- **项目**：french-learner
- **创建日期**：2026-11-21
- **完成日期**：

## 原始需求

夜班深度巡库优化项 OP-06：ai.py 的 recast 降级判定表（docstring 明文"降级判定表 9 条逐条覆盖"是契约要求，ARCHITECTURE_V2.md §3）从未测过——契约关键但零覆盖。

## 需求分析

- **目标**：recast 降级判定表 9 条逐条覆盖 + GLM 调用边界 mock（urllib 全 mock，零网络零计费）
- **改动点**：backend/tests/ 新增 test_ai.py
- **涉及数据**：全部 mock（urllib.request 等），不碰并行车道文件

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3 + ARCHITECTURE_V2.md §3 契约）：先读 ai.py 源码与 ARCHITECTURE_V2.md §3 提取 9 条降级规则原文，逐条写用例
- **改动点清单**：仅新增 tests/test_ai.py，不改产品代码
- **风险与限制**：urllib 全 mock（含超时/HTTP 错误/非 JSON 响应路径）
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [ ] 实现 unittest（实现者）
- [ ] 父复核全绿（含既有 78 例）
- [ ] french-learner 仓库提交 + 主仓库归档

## 验收标准

- [ ] 9 条降级判定逐条有用例（对照 ARCHITECTURE_V2.md §3）
- [ ] unittest 全绿（与既有 78 例合并）
- [ ] 零真实网络/GLM 调用；不改产品代码

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 76→77）
