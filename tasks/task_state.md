# 任务看板（task_state）

> 当前所有活动任务的索引与状态。详细的需求分析和子任务清单在各任务文件中。
> **规则**：新任务 → 在 `tasks/active/` 建任务文件并登记到下方；完成 → 文件移入 `tasks/archive/YYYY-MM/`，下方移到归档记录。

## 活动任务

| ID | 任务 | 优先级 | 状态 | 任务文件 |
|----|------|--------|------|----------|
| TASK-0002 | 小红书博文爬取工具 | 中 | 进行中（待真机验收） | tasks/active/TASK-0002-xhs-crawler.md |
| TASK-0005 | 小红书爬虫 Web 前端 + 依赖安装 | 中 | 进行中（代码完成，待验收） | tasks/active/TASK-0005-web-ui.md |
| TASK-0006 | 反爬加固 + 登录增强（Cookie 导入/风控即停） | 高 | 进行中（代码完成，待验收） | tasks/active/TASK-0006-anti-crawl-login.md |
| TASK-0007 | 修复假登录误判 + 保留 xsec_token + 异常落日志 | 高 | 进行中（代码完成，待验收） | tasks/active/TASK-0007-fix-false-login.md |
| TASK-0016 | 呀呀法语阶段二（GLM 可插拔重述 + i+1 输入流） | 高 | 完成（独立 QA 109/109 通过；真实 ZHIPU_API_KEY 端到端冒烟通过；验收期缺陷 D1/D2 已修复并回归，待验收） | tasks/active/TASK-0016-french-learner-phase2.md |
| TASK-0020 | 呀呀法语一键启动脚本（自检 + 启动 + 健康检查） | 中 | 进行中（真机三场景验证通过，待验收） | tasks/active/TASK-0020-french-learner-oneclick-start.md |
| TASK-0021 | 生词卡前端重设计（自适应长内容 + 视觉统一） | 中 | 进行中 | tasks/active/TASK-0021-wordcard-redesign.md |

## 归档记录

| ID | 任务 | 完成日期 | 归档位置 |
|----|------|----------|----------|
| TASK-0001 | 项目初始化：搭建目录结构与文档体系 | 2026-11-16 | tasks/archive/2026-11/TASK-0001-项目初始化.md |
| TASK-0003 | 工作流新增"方案确认"环节 | 2026-11-16 | tasks/archive/2026-11/TASK-0003-工作流新增方案确认环节.md |
| TASK-0004 | 新增通用经验库 lessons.md | 2026-11-16 | tasks/archive/2026-11/TASK-0004-新增通用经验库lessons.md |
| TASK-0008 | 行业龙头年报带读工具（annual_report_reader） | 2026-11-17 | tasks/archive/2026-11/TASK-0008-annual-report-reader.md |
| TASK-0009 | 服务管理工具（启动/重启/关闭服务） | 2026-11-17 | tasks/archive/2026-11/TASK-0009-服务管理工具.md |
| TASK-0010 | 服务管理工具：修复停止/重启在异常场景下失效 | 2026-11-17 | tasks/archive/2026-11/TASK-0010-service-manager-fix.md |
| TASK-0011 | 修复 ZHIPU_API_KEY 在已运行进程中读不到导致报错 | 2026-11-17 | tasks/archive/2026-11/TASK-0011-zhipu-key-fallback.md |
| TASK-0012 | 年报章节定位多格式修复 + 原始 PDF 持久化保存 | 2026-11-17 | tasks/archive/2026-11/TASK-0012-chapter-locate-and-pdf-persist.md |
| TASK-0013 | 呀呀法语（french-learner）前端 Demo | 2026-11-17 | tasks/archive/2026-11/TASK-0013-french-learner-demo.md |
| TASK-0014 | 呀呀法语全栈版本（多智能体协作） | 2026-11-17 | tasks/archive/2026-11/TASK-0014-french-learner-fullstack.md |
| TASK-0015 | 呀呀法语：本地 Whisper 语音识别根治 network 错误 | 2026-11-17 | tasks/archive/2026-11/TASK-0015-french-asr-local-whisper.md |
| TASK-0017 | french-learner 关联 GitHub 远程并推送（SSH over 443） | 2026-11-17 | tasks/archive/2026-11/TASK-0017-french-learner-git-remote.md |
| TASK-0018 | french-learner git 跟踪范围审查与 .env 防泄露修复 | 2026-11-17 | tasks/archive/2026-11/TASK-0018-french-learner-gitignore-audit.md |
| TASK-0019 | 2026 A股半年报分析台（annual_report_reader 扩展） | 2026-11-18 | tasks/archive/2026-11/TASK-0019-h1-2026-dashboard.md（六角色协作；六表入库、单页发布、QA 35/35 PASS） |
| TASK-0022 | 呀呀法语阶段 0：CEFR 定级（wave 1） | 2026-11-18 | tasks/active/TASK-0022-french-placement-assessment.md（待上级验收；QA 16/16 PASS；总指挥裁决契约冲突、真实服务冒烟通过） |
| TASK-0023 | 呀呀法语阶段 4：DELF B2 / TCF 冲刺（wave 2） | 2026-11-18 | tasks/active/TASK-0023-french-exam-sprint.md（待上级验收；QA 112 PASS；总指挥裁决口语独立录音链路、隔离库零污染、真实 GLM + 无头浏览器端到端冒烟通过） |
