# 夜班任务池（night_backlog）

> **用途**：每晚 23:00 夜班总指挥巡库后刷新本文件（章程见 `docs/night_ops.md` 第 4 节），白天用户也可往里添加想让我夜间做的事。
> **规则**：每晚启动时全量刷新（不是追加）；条目编号 NB-NNN 每晚从 NB-001 重新计；"来源"写白名单文档路径；级别=实施（可直接做）/ 提案（超范围，只写方案）/ 观察（让路或记录）。

## 今晚任务池

> 2026-11-20 23:0x 首启巡库。摘要：service_manager 19/19 绿、french-learner pron_coach 15/15 绿；workbuddy 处并行会话工作现场（暂缓全线）；annual_report_reader / xhs_crawler 无测试（补测任务有效）。

| 编号 | 项目 | 描述 | 来源 | 级别 | 优先级 | 状态 |
|------|------|------|------|------|--------|------|
| NB-001 | service_manager | `_load_state` 容错：补缺失服务默认键 + JSON 损坏时备份原文件并重建默认结构（昨 NB-006 转正，属优化项，用户指示直接实施） | TASK-0030 子 agent 发现的真实缺陷 | 实施 | 高 | 已完成（TASK-0070，22 例绿，2026-11-20 夜班） |
| NB-002 | annual_report_reader | 补 fetcher/extractor 纯逻辑 unittest（不触网、不调 GLM） | 巡库：无测试资产 | 实施 | 中高 | 已完成（TASK-0071，101 例绿，2026-11-20 夜班） |
| NB-003 | xhs_crawler | 纯逻辑 mock 测试（登录双信号判定/风控熔断等 TASK-0006/0007 逻辑单元，**不真机**） | 巡库 + 红线 2.3 | 实施 | 中 | 已完成（TASK-0072，126 例绿，2026-11-21 凌晨） |
| NB-004 | french-learner | backend/tests 缺 `__init__.py`，`unittest discover` 不可导入（现用 `python -m unittest tests.test_pron_coach` 可跑，15 例绿）；补 `__init__.py` 使两种方式兼容 | 巡库发现 | 实施 | 低 | 已完成（french-learner 提交 6dbb075，discover 15/15 绿） |
| NB-005 | workbuddy-multi-account | **并行会话现场**：TASK-0052 端口注册表根治未提交（10 文件 M + port_registry.py 未跟踪）+ TASK-0068/0069 已领号 → 夜班让路，workbuddy 全线暂缓至现场提交 | §6.1 基线观察 | 观察 | - | 让路 |
| NB-006 | xhs_crawler | TASK-0005/0006/0007 真机验收——**夜间禁区（红线 2.3）** | 看板活动任务 | 提案 | 低 | 晨起定夺 |
| NB-007 | french-learner | TASK-0029/0032 待用户真机验收（夜间不碰）；TASK-0068/0069 并行会话进行中（不碰） | 看板 | 观察 | - | 不碰 |

**任务池耗尽预案**（§4.3）：深度巡库 → 智能生成提案：优化项直接实施 / 新增需求写入本表提案行等用户排期。

## 历史参考

- 每晚执行结果见 `tasks/night_reports/YYYY-MM-DD.md`；blocked 项的处理建议也记录在夜报中。
- 2026-11-19 演练：service_manager 单测 19 例落地（TASK-0030，已归档）。
