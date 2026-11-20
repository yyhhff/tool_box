# TASK-0022 呀呀法语阶段 0：CEFR 定级（wave 1）

- **状态**：已完成（已验收，2026-11-19）
- **优先级**：高
- **创建日期**：2026-11-18
- **完成日期**：2026-11-18

## 原始需求

用户："按照路线图继续开发" → 确认"两块一起做（先定级再冲刺，分两波交付）"。
路线图阶段 0「用户档案 + CEFR 定级 + 场景词库数据管线」中，定级待做——当前 `users.cefr_level` 写死 A2，需做成可测。

## 需求分析

- **目标**：用户做一组分级选择题 → 后端算分映射到 A2/B1/B2 → 写回 users.cefr_level → 自动驱动现有 `/api/input/recommend` 的 i+1 推荐。定位"快速自评"，不冒充官方权威定级。
- **改动点**（引用 `docs/project_content.md`）：
  - `tools/french-learner/backend/db.py`：+`attempts` 表（kind=placement，幂等建表）；+写入/读取方法
  - `tools/french-learner/backend/app.py`：`GET /api/assessment/questions`、`POST /api/assessment/submit`
  - `tools/french-learner/frontend/{index.html,app.js,styles.css}`：新增「🎯 定级」Tab + 答题/结果界面；资源版本破缓存
  - `tools/french-learner/data/input/assessment_questions.json`（新增）：定级题库
  - `tools/french-learner/docs/`：定级契约补充 + QA 报告；同步两张地图
- **涉及数据**（引用 `docs/data_content.md`）：
  - `data/input/assessment_questions.json`（新增，入 git）
  - `tools/french-learner/backend/data/yaya.db`：+attempts 表；users.cefr_level 更新

## 方案（已确认）

- **实现思路**：零新增主后端依赖（FastAPI/SQLite/urllib + 现成 GLM）。出题→交卷→算分定级→写库→recommend 按新等级推荐。一张 attempts 表（kind 区分 placement/exam）复用两波。
- **改动点清单**：见上
- **风险与限制**：定级非权威（快速自评口径）；跨前后端+库+文档需重启服务破缓存；按波次回归。
- **用户确认日期**：2026-11-18

## 子任务

- [x] 波 1 阶段①：PM + 架构师并行出定级契约（题目 schema / 2 端点 / 算分规则 / attempts 表）——双盲抓出契约冲突，总指挥裁决"产品语义以 PM 为准、技术细节以架构为准"，逐项核查后冻结 v1.1
- [x] 波 1 阶段②：后端（assessment.py + db.py + app.py）/ 前端（定级三态 Tab）/ 内容（12 题题库）三角色并行
- [x] 波 1 阶段③：QA 独立验收 16/16 PASS + 总指挥真实服务集成冒烟（新端点/脱敏/零回归）+ Git 提交 + 向用户汇报

## 验收标准

- [x] `GET /api/assessment/questions` 返回分级题目，字段齐全（QA A1/A2：12题各4、5字段、零答案泄露）
- [x] `POST /api/assessment/submit` 算分正确、映射 A2/B1/B2 分级边界正确（TC1-TC8 8/8 含 TC8(2,4,4)→A2）、写回 users.cefr_level、存 attempts、幂等
- [x] 定级后 `/api/input/recommend` 按新等级推荐（QA D14：B2 写回后 target_level=C1，i+1 链通）
- [x] 非法参数返回 40001（QA 14 种非法入参全 PASS），零 500；题库空 GET 降级不500、submit 50001
- [x] 前端定级 Tab 出题→交卷→看结果闭环通（node --check + 5 新函数 + 现有函数零破坏）；资源版本 css v10/js v11
- [x] 现有 15 端点零回归（QA 抽样 6 端点）；独立 QA 报告 docs/QA_PLACEMENT.md 16/16；主库 sha256 零污染

## 变更记录

- 2026-11-18 创建；方案经用户确认（两块一起做，先定级）
- 2026-11-18 完成：契约冻结 v1.1（总指挥裁决 PM 产品语义 + 架构技术细节）、QA 16/16 PASS、真实服务冒烟通过；版本 css v10/js v11；提交见 git log
- 2026-11-19 用户验收通过，归档至 `tasks/archive/2026-11/`
