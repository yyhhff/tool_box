# TASK-0023 呀呀法语阶段 4：DELF B2 / TCF 冲刺（wave 2）

- **状态**：已完成（QA 112 PASS，0 FAIL；总指挥集成冒烟通过，待上级验收）
- **优先级**：高
- **创建日期**：2026-11-18
- **完成日期**：2026-11-18

## 原始需求

用户："按照路线图继续开发" → 确认"两块一起做（先定级再冲刺，分两波交付）"。
路线图阶段 4「DELF B2 / TCF 冲刺 + 真题」未开始，对齐最初"终点 B2、兼顾考级"目标。

## 需求分析

- **目标**：原创模拟卷（规避真题版权）→ 题型专项 + 模拟考 + 评分反馈；客观题自动判分，写作/口语复用 GLM 评分（无 key 降级：客观题照常出分、主观题给温和占位不打断），出成绩报告。听力走现有 /api/tts，口语走现有 ASR + GLM，不重造。
- **改动点**（引用 `docs/project_content.md`）：
  - `tools/french-learner/backend/app.py`：`GET /api/exam/papers`、`GET /api/exam/papers/{id}`、`POST /api/exam/submit`
  - `tools/french-learner/backend/ai.py`：+GLM 评分函数（写作/口语），复用 `_glm_post`，带降级
  - `tools/french-learner/backend/db.py`：复用 attempts 表（kind=exam）
  - `tools/french-learner/frontend/{index.html,app.js,styles.css}`：新增「🏆 考级冲刺」Tab + 答题/成绩界面；资源版本破缓存
  - `tools/french-learner/data/input/exam_papers.json`（新增）：原创模拟卷（题型 + 答案 + 评分点）
  - `tools/french-learner/docs/`：章程 + 架构契约 v3 + QA 报告；同步两张地图、README 免责说明
- **涉及数据**（引用 `docs/data_content.md`）：
  - `data/input/exam_papers.json`（新增，入 git）
  - `tools/french-learner/backend/data/yaya.db`：attempts 表（kind=exam）

## 方案（已确认）

- **实现思路**：零新增主后端依赖；原创题替真题（写进 README 免责）；GLM 主观评分用固定 rubric + 降级兜底；一张 attempts 表复用。
- **改动点清单**：见上
- **风险与限制**：真题版权（原创模拟题，练题型非真题预测）；GLM 评分主观性+延迟（rubric+降级）；跨层改动按波次回归。
- **用户确认日期**：2026-11-18

## 子任务

- [x] 波 2 阶段①：PM + 架构师并行出契约（EXAM_BASELINE 锁定基线 / EXAM_CHARTER / ARCHITECTURE_EXAM）+ 内容原创试卷
- [x] 波 2 阶段②：后端（exam.py + 3 端点 + GLM 评分 + 6 类降级）/ 前端（第 4 Tab 答题 + 成绩报告）/ 内容（2 套原创卷）
- [x] 波 2 阶段③：总指挥代行独立验收（原 QA 因 429 中断）+ 集成联调 + Git 提交 + 向用户汇报

## 验收标准

- [x] 3 个端点契约齐全；试卷详情零答案泄露（白名单投影，4 类敏感字段命中 0）
- [x] 客观题判分 100% 正确；写作/口语 GLM 评分返回中文反馈；6 类降级不 500（16 用例全 PASS）
- [x] 前端答题→交卷→看成绩报告闭环通（无头浏览器真实点击 + 真实 GLM 交卷）；资源版本 css v11 / js v12
- [x] 现有端点零回归（含波一新增）；QA_EXAM.md 112 PASS；隔离验收主库零污染
- [x] README 写明"原创模拟题非真题"免责声明；两张地图 + task_state 同步

## 变更记录

- 2026-11-18 创建；方案经用户确认（两块一起做，波一后开工）
- 2026-11-18 契约冻结：EXAM_BASELINE v1.0（锁定项）+ PM 章程 + 架构契约；吸取波一教训先钉死基线
- 2026-11-18 完成：2 套卷 + 3 端点 + 6 类降级 + 第 4 Tab；QA 112 PASS
- 2026-11-18 总指挥裁决：口语题不复用 transcribeAudio()（会误发聊天流），采用独立录音链路，零改锁定基线，报告单列存档
- 2026-11-18 中断恢复：后端/前端角色因 429 中断，总指挥代行收口；隔离库 HTTP 50/50 + 单元边界逐项 + 真实浏览器端到端全通过
