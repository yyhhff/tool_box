# TASK-0018 french-learner git 跟踪范围审查与 .env 防泄露修复

- **状态**：已完成
- **优先级**：中
- **创建日期**：2026-11-17
- **完成日期**：2026-11-17

## 原始需求

> 现在哪些文件 git，哪些不需要 git，是否合理
> （确认后）全部修复

## 需求分析

- **目标**：审查 french-learner 独立仓库的 git 跟踪范围是否合理，修复发现的问题。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `tools/french-learner/.gitignore`
- **涉及数据**（引用数据地图 `docs/data_content.md`）：无

## 方案（已确认）

- **实现思路**：盘点被跟踪（23 个）、被忽略、未跟踪文件 → 评估合理性 → 用户确认后修复问题。
- **改动点清单**：
  - `.gitignore`：新增 `.env`/`.env.*` 忽略规则（放行 `.env.example` 模板）+ Python 测试/覆盖率产物忽略规则
- **风险与限制**：
  - 原计划移除过时的 `demo.html`，但发现 README/seed.py/ARCHITECTURE.md/PROJECT_CHARTER.md 均引用它（作为历史基线与数据来源注释），删除会破坏文档一致性 → **决定保留**，不改

## 审查结论

**被跟踪（合理）**：代码（`backend/`、`asr_service/`、`frontend/`）、配置模板（`.env.example` 空值）、核心语料（`data/input/texts.json` 67KB）、5 份设计/QA 文档、v1 原型 `demo.html`。
**被忽略（合理）**：`.venv-asr/`(315MB)、`.wheelhouse/`(32MB)、`__pycache__/`、`backend/data/yaya.db`（运行时 DB，可重建）、`*.log`、`*.mp3/*.webm/*.wav`。

发现并修复的问题：
1. 🔴 `.gitignore` 无 `.env` 规则——README 让用户把真实智谱 key 填进 `backend/.env`，`git add .` 会泄露密钥。**已修复**。
2. 🟡 `demo.html` 过时——但有 4 处文档引用，属有意基线存档。**保留**。
3. 🟢 缺 Python 测试产物忽略规则（预防性）。**已补**。

## 子任务

- [x] 盘点被跟踪/忽略/未跟踪文件
- [x] 评估跟踪范围合理性
- [x] 用户确认修复范围
- [x] 修复 .gitignore（.env 防泄露 + 测试产物）
- [x] 验证规则（真实 .env 被忽略、.env.example 仍跟踪）
- [x] 收尾归档

## 验收标准

- [x] `git check-ignore -v backend/.env` 命中 `.gitignore` 的 `.env` 规则
- [x] `backend/.env.example` 未被忽略、仍被 git 跟踪
- [x] `git status` 仅显示 `.gitignore` 一处修改

## 变更记录

- 2026-11-17 创建并完成
