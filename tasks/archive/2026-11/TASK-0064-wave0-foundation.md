# TASK-0064 Wave 0 地基拆分（routers + ES modules + worktree 脚本）

- **状态**：已完成（真机验收通过）
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-20
- **完成日期**：2026-11-20

## 原始需求

用户（2026-11-20）：「呀呀法语产品，读 MASTER_PLAN.md → 认领 Wave 0 地基任务 → 领号 → 向你确认地基方案后开工。」

多会话并行开发的总纲（TASK-0063 / `docs/MASTER_PLAN.md`）要求：一切功能版本并行开工前，先由单会话完成 Wave 0 地基拆分，消除 `app.py` / `app.js` 单文件多会话必冲突的问题。

## 需求分析

- **目标**：把 `backend/app.py`（1137 行）按域拆 FastAPI APIRouter、把 `frontend/app.js`（2927 行）拆 ES modules，并提供 worktree 并行脚本；零行为变更，为后续 Wave 1–4 多车道并行铺路。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `tools/french-learner/backend/app.py`（拆出 routers，`app.py` 只留装配/中间件/异常/静态托管 + ROADMAP_DEFS）
  - `tools/french-learner/backend/routers/<域>.py`（新增：chat / input / cards / assessment / exam / translate / pron / asr / misc）
  - `tools/french-learner/frontend/js/api.js` + `frontend/js/views/*.js` + `frontend/js/main.js`（新增）
  - `tools/french-learner/frontend/app.js`（保留为兼容层或删除，方案待确认）
  - `tools/french-learner/frontend/index.html`（`<script type="module">` 挂载点）
  - `tools/french-learner/scripts/worktree.bat`（新增）
  - `tools/french-learner/docs/MASTER_PLAN.md`（认领看板回填）
- **涉及数据**（引用数据地图 `docs/data_content.md`）：无新增数据文件；仅代码结构变更。

## 方案（已确认）

> 开发前先在会话中向用户提交方案，经用户确认后填写此节再动手。

- **实现思路**：
  1. 后端：新增 `backend/common.py` 收纳共享件（ApiError/ok/json_body/normalize_user_text/_parse_multipart/ROADMAP_DEFS/logger）避免循环依赖；按域建 `backend/routers/{chat,input,cards,assessment,exam,pron,translate,asr,tts,misc}.py`，每域一个 APIRouter，36 端点路径与逻辑原样搬迁；`app.py` 只留实例/CORS/异常/router 注册/启动初始化/静态托管（仍最后 mount）。
  2. 前端：新增 `frontend/js/store.js`（state+常量+跨模块可变状态+纯工具函数）、`api.js`（apiRequest）、`views/{chat,reading,pron,profile,roadmap,exam,feedback}.js`、`main.js`（入口 import+全局事件+初始渲染）；`index.html` 改 `<script type="module" src="js/main.js">`；module 作用域不共享，跨文件引用改显式 import/export，逐段迁移逐段回归。
  3. worktree：`scripts/worktree.bat <车道名>` 从 main 拉独立分支+独立目录，校验目录/分支不重复并输出路径提示。
  4. 零行为变更：只搬代码不改逻辑；验收对照 README 36 端点 + 前端四 Tab 冒烟。
- **改动点清单**：`backend/app.py` + 新增 `backend/routers/`、`backend/common.py`；`frontend/app.js`/`index.html` + 新增 `frontend/js/`；新增 `scripts/worktree.bat`；回填 MASTER_PLAN 看板；同步两张地图。
- **风险与限制**：基线不干净（0059–0063 改动未提交，须先提交）；前端 157 函数共享大量可变状态是最大风险点，逐段迁移+回归；计数号非原子（已独立提交）；真机未验不勾 `[x]`。
- **用户确认日期**：2026-11-20（AskUserQuestion 三决策：先提交干净基线 / 独立 feature 分支 / 完整 ES module 拆分）

## 子任务

- [x] 读 MASTER_PLAN.md + 两张地图，确认 Wave 0 未认领
- [x] 领号 TASK-0064（next_id 64→65，独立提交 fe316b1）
- [x] 建本任务文件 + 回填认领看板 + 登记 task_state.md
- [x] 提交地基方案，等用户确认（三决策已确认 2026-11-20）
- [x] 后端：app.py 按域拆 APIRouter（12 routers + common，commit 7542142）
- [x] 前端：app.js 拆 ES modules（store/api/views/main，commit 88794c5）
- [x] worktree 并行脚本（commit 88794c5 + 路径修复 8f8708b）
- [x] 全端点回归 + 前端六 Tab 冒烟
- [x] 收尾归档 + 地图/看板/lessons 同步

## 验收标准

> 每条验收标注状态：`[x]` 已完成并真机验收 / `[~]` 开发完成或自测通过、待真机 / `[ ]` 未完成。

- [x] `python -m py_compile` 全部 backend py 通过；OpenAPI 36 operations，拆分前后 schema 字节一致（diff 无输出）
- [x] 浏览器真机 A/B：原版单文件（:18082）vs 拆分版（:18081）首屏气泡数组逐字相同；六 Tab（对话/阅读/定级/考级/成长/路线图）逐一点击可见性切换正确，控制台/errors 无报错；window 41 个 inline handler 函数全部挂载
- [x] `scripts/worktree.bat <车道名>` 真机建独立目录（tool_box/_worktrees/，仓库外）+ 独立分支 feature/<lane>，基于 main；已 create/verify/remove 全流程验证
- [x] 零行为变更：后端 22 个 GET 端点原版/拆分版真实 HTTP 响应 0 差异（含 404 错误码）；前端 DOM/交互 A/B 一致

## 变更记录

- 2026-11-20 创建。Wave 0 为多会话并行的先决地基任务；认领会话已领号，方案三决策经用户确认后开工。
- 2026-11-20 完成并真机验收：后端 36 端点 A/B 0 差异、前端六 Tab 浏览器 A/B 一致、worktree 脚本 create→remove 全流程通过。分支已合并 main（merge 20503e7 + 路径修复 8f8708b）。
