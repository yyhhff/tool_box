# 任务看板（task_state）

> 当前所有活动任务的索引与状态。详细的需求分析和子任务清单在各任务文件中。
> **规则**：新任务 → 在 `tasks/active/` 建任务文件并登记到下方（**必填"项目"列**：工具名，跨项目改动填"tool_box 全局"）；完成 → 文件移入 `tasks/archive/YYYY-MM/`，下方移到归档记录。

## 活动任务

| ID | 项目 | 任务 | 优先级 | 状态 | 任务文件 |
|----|------|------|--------|------|----------|
| TASK-0002 | xhs_crawler | 小红书博文爬取工具 | 中 | 进行中（待真机验收） | tasks/active/TASK-0002-xhs-crawler.md |
| TASK-0005 | xhs_crawler | 小红书爬虫 Web 前端 + 依赖安装 | 中 | 进行中（代码完成，待验收） | tasks/active/TASK-0005-web-ui.md |
| TASK-0006 | xhs_crawler | 反爬加固 + 登录增强（Cookie 导入/风控即停） | 高 | 进行中（代码完成，待验收） | tasks/active/TASK-0006-anti-crawl-login.md |
| TASK-0007 | xhs_crawler | 修复假登录误判 + 保留 xsec_token + 异常落日志 | 高 | 进行中（代码完成，待验收） | tasks/active/TASK-0007-fix-false-login.md |
| TASK-0021 | french-learner | 生词卡前端重设计（自适应长内容 + 视觉统一） | 中 | 进行中 | tasks/active/TASK-0021-wordcard-redesign.md |
| TASK-0024 | workbuddy-multi-account | WorkBuddy 多账号管理工具（MVP） | 高 | 进行中（已接入真实协议 copilot.tencent.com：凭据快照多账号 + Bearer 认证 + 真实签到链路；单测 21/21 + 服务器冒烟通过，修复缺陷 D1-D6；待装 WorkBuddy 客户端真机验收 + git 提交 + 前端） | tasks/active/TASK-0024-workbuddy-multi-account.md |
| TASK-0026 | annual_report_reader | 本体本地功能闭环测试 | 高 | 进行中（方案已确认，测试执行中） | tasks/active/TASK-0026-local-loop-test.md |

## 归档记录

| ID | 项目 | 任务 | 完成日期 | 归档位置 |
|----|------|------|----------|----------|
| TASK-0001 | tool_box 全局 | 项目初始化：搭建目录结构与文档体系 | 2026-11-16 | tasks/archive/2026-11/TASK-0001-项目初始化.md |
| TASK-0003 | tool_box 全局 | 工作流新增"方案确认"环节 | 2026-11-16 | tasks/archive/2026-11/TASK-0003-工作流新增方案确认环节.md |
| TASK-0004 | tool_box 全局 | 新增通用经验库 lessons.md | 2026-11-16 | tasks/archive/2026-11/TASK-0004-新增通用经验库lessons.md |
| TASK-0008 | annual_report_reader | 行业龙头年报带读工具（annual_report_reader） | 2026-11-17 | tasks/archive/2026-11/TASK-0008-annual-report-reader.md |
| TASK-0009 | service_manager | 服务管理工具（启动/重启/关闭服务） | 2026-11-17 | tasks/archive/2026-11/TASK-0009-服务管理工具.md |
| TASK-0010 | service_manager | 服务管理工具：修复停止/重启在异常场景下失效 | 2026-11-17 | tasks/archive/2026-11/TASK-0010-service-manager-fix.md |
| TASK-0011 | annual_report_reader | 修复 ZHIPU_API_KEY 在已运行进程中读不到导致报错 | 2026-11-17 | tasks/archive/2026-11/TASK-0011-zhipu-key-fallback.md |
| TASK-0012 | annual_report_reader | 年报章节定位多格式修复 + 原始 PDF 持久化保存 | 2026-11-17 | tasks/archive/2026-11/TASK-0012-chapter-locate-and-pdf-persist.md |
| TASK-0013 | french-learner | 呀呀法语（french-learner）前端 Demo | 2026-11-17 | tasks/archive/2026-11/TASK-0013-french-learner-demo.md |
| TASK-0014 | french-learner | 呀呀法语全栈版本（多智能体协作） | 2026-11-17 | tasks/archive/2026-11/TASK-0014-french-learner-fullstack.md |
| TASK-0015 | french-learner | 呀呀法语：本地 Whisper 语音识别根治 network 错误 | 2026-11-17 | tasks/archive/2026-11/TASK-0015-french-asr-local-whisper.md |
| TASK-0017 | french-learner | french-learner 关联 GitHub 远程并推送（SSH over 443） | 2026-11-17 | tasks/archive/2026-11/TASK-0017-french-learner-git-remote.md |
| TASK-0018 | french-learner | french-learner git 跟踪范围审查与 .env 防泄露修复 | 2026-11-17 | tasks/archive/2026-11/TASK-0018-french-learner-gitignore-audit.md |
| TASK-0019 | annual_report_reader | 2026 A股半年报分析台（annual_report_reader 扩展） | 2026-11-18 | tasks/archive/2026-11/TASK-0019-h1-2026-dashboard.md |
| TASK-0022 | french-learner | 呀呀法语阶段 0：CEFR 定级（wave 1） | 2026-11-18 | tasks/archive/2026-11/TASK-0022-french-placement-assessment.md |
| TASK-0023 | french-learner | 呀呀法语阶段 4：DELF B2 / TCF 冲刺（wave 2） | 2026-11-18 | tasks/archive/2026-11/TASK-0023-french-exam-sprint.md |
| TASK-0025 | tool_box 全局 | 全局地图与看板索引化（详情下沉到工具内部文档） | 2026-11-18 | tasks/archive/2026-11/TASK-0025-map-index-slim.md |
| TASK-0020 | french-learner | 呀呀法语一键启动脚本（自检 + 启动 + 健康检查 + 端口自动回退） | 2026-11-19 | tasks/archive/2026-11/TASK-0020-french-learner-oneclick-start.md |
| TASK-0016 | french-learner | 呀呀法语阶段二（GLM 可插拔重述 + i+1 输入流） | 2026-11-17 | tasks/archive/2026-11/TASK-0016-french-learner-phase2.md |
