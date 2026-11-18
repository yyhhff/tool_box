# 夜班任务池（night_backlog）

> **用途**：每晚 23:00 夜班总指挥巡库后刷新本文件（章程见 `docs/night_ops.md` 第 4 节），白天用户也可往里添加想让我夜间做的事。
> **规则**：每晚启动时全量刷新（不是追加）；条目编号 NB-NNN 每晚从 NB-001 重新计；"来源"写白名单文档路径；级别=实施（可直接做）/ 提案（超范围，只写方案）。

## 今晚任务池

> 2026-11-19 演练巡库刷新（ drill ）。巡库摘要：5 个子工具均**无自有测试**；python 环境无 pytest（约定夜间测试一律用标准库 unittest，零环境改动）；xhs_crawler 4 个活动任务均"待真机验收"，受红线 2.3 约束夜间不可真机推进。

| 编号 | 项目 | 描述 | 来源 | 级别 | 优先级 | 状态 |
|------|------|------|------|------|--------|------|
| NB-001 | service_manager | 补 service_manager.py 单元测试（state 往返/get_status 自纠/停止幂等/端口判定，mock psutil） | 巡库红测扫描 + README 行为契约 | 实施 | 高 | 已完成（TASK-0030，19 例全绿，2026-11-19 演练） |
| NB-002 | 全部 | 各工具补 unittest 覆盖（夜班常规任务源，按工具轮转：annual_report_reader → xhs_crawler 纯逻辑 → workbuddy） | 巡库 | 实施 | 高 | 待排产 |
| NB-003 | workbuddy-multi-account | TASK-0024 遗留项之 Web 前端（管理面板） | tasks/active/TASK-0024 | 实施 | 中 | 待排产 |
| NB-004 | annual_report_reader | 补 fetcher/extractor 纯逻辑单测（不触网、不调 GLM） | 巡库 + TASK-0026 无测试资产 | 实施 | 中 | 待排产 |
| NB-005 | xhs_crawler | TASK-0005/0006/0007 真机验收——**夜间不可做（红线 2.3）**，只可做 mock 测试与静态检查 | 看板活动任务 | 提案 | 低 | 晨起定夺 |
| NB-006 | service_manager | _load_state 容错：补缺失服务默认键 + JSON 损坏时备份原文件并重建默认结构（方案经总指挥推荐、用户未否决；晨起夜报可否决回滚） | TASK-0030 子 agent 发现的真实缺陷 | 实施 | 高 | 待今晚实施 |

## 历史参考

- 每晚执行结果见 `tasks/night_reports/YYYY-MM-DD.md`；blocked 项的处理建议也记录在夜报中。
