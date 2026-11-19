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
| TASK-0024 | workbuddy-multi-account | WorkBuddy 多账号管理工具（MVP） | 高 | 进行中（真机验收核心链路通过：加密凭据解密 + bind 快照 + 真实签到 +100 积分到账确认；缺陷 D1-D10 已修复并 git 提交 b224775/73a86a6；遗留聊天记录 API 探索、第二账号 bind、前端） | tasks/active/TASK-0024-workbuddy-multi-account.md |
| TASK-0028 | tool_box 全局 | 夜班自动化 NightOps（23:00–09:00 无人值守迭代） | 高 | 进行中（章程/任务池/Cron/演练已落地，待首夜实战验证） | tasks/active/TASK-0028-night-ops.md |
| TASK-0029 | french-learner | 逐词点击学发音 + 连读教学（例句/短语） | 中 | 进行中（浏览器真机验收三步全过：token→单词卡/连读卡/零回归，待验收） | tasks/active/TASK-0029-linking-teaching.md |
| TASK-0031 | french-learner | 读音跟读闭环（P1）：🎙 ASR 近似比对 + 三档温和反馈 | 高 | 进行中（评分单测 9/9 + UI 截图全过，真麦克风端到端待用户验收） | tasks/active/TASK-0031-pron-shadow-p1.md |
| TASK-0032 | french-learner | 读音学习交互重构：贴词气泡 + 连读内嵌（取代模态跳转） | 高 | 进行中（浏览器真机四步全过：气泡原地/外点关闭/再点收起/内嵌展开收起/完整讲解回位，待用户验收） | tasks/active/TASK-0032-pron-inline-popover.md |
| TASK-0040 | french-learner | 学习进度持久化 P0：对话历史读回 + 假值清零 + 真实统计 | 高 | 进行中（方案按推荐口径拍板，多角色实施中） | tasks/active/TASK-0040-progress-persistence-p0.md |
| TASK-0041 | workbuddy-multi-account | start.bat 启动前自动清理旧服务（防旧代码残留） | 中 | 进行中（方案已确认，实施中） | tasks/active/TASK-0041-start-bat-clean-old-service.md |
| TASK-0042 | annual_report_reader | h1_2026 分析台自检启动脚本（start.bat + selfcheck.py，22 项自检通过才打开页面） | 低 | 已完成（22/22 PASS，失败路径实测 exit=1，还原复检全绿） | tasks/active/TASK-0042-h1-selfcheck-start.md |

## 归档记录

| ID | 项目 | 任务 | 完成日期 | 归档位置 |
|----|------|------|----------|----------|
| TASK-0031 | french-learner | 读音跟读闭环（P1）：🎙 ASR 近似比对 + 三档温和反馈 | 2026-11-19 | tasks/archive/2026-11/TASK-0031-pron-shadow-p1.md |
| TASK-0037 | workbuddy-multi-account | 切号任务列表迁移：接管客户端任务快照 | 2026-11-19 | tasks/archive/2026-11/TASK-0037-task-snapshot-migration.md |
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
| TASK-0026 | annual_report_reader | 本体本地功能闭环测试 | 2026-11-19 | tasks/archive/2026-11/TASK-0026-本地功能闭环测试.md |
| TASK-0027 | french-learner | 读音功能修复：patterns 断链接通 + 覆盖 97.8% + 按钮音节文案 | 2026-11-19 | tasks/archive/2026-11/TASK-0027-pron-coverage-focus.md |
| TASK-0021 | french-learner | 生词卡前端重设计（自适应长内容 + 视觉统一） | 2026-11-19 | tasks/archive/2026-11/TASK-0021-wordcard-redesign.md |
| TASK-0030 | service_manager | service_manager 补单元测试（unittest，19 例） | 2026-11-19 | tasks/archive/2026-11/TASK-0030-service-manager-tests.md |
| TASK-0033 | french-learner | P2 融入点：分级阅读页逐词点击学发音（复用贴词气泡） | 2026-11-19 | tasks/archive/2026-11/TASK-0033-reading-word-popover.md |
| TASK-0034 | french-learner | 场景对话框逐词点击 + 🔗 连读迁移到对话气泡 | 2026-11-19 | tasks/archive/2026-11/TASK-0034-chat-inline-word-linking.md |
| TASK-0035 | french-learner | 连读提示独立试听 + 示例分别试听 + 生词卡保留简洁连读按钮 | 2026-11-19 | tasks/archive/2026-11/TASK-0035-linking-segment-audio.md |
| TASK-0036 | french-learner | 生词卡：删除连读按钮 | 2026-11-19 | tasks/archive/2026-11/TASK-0036-remove-vocab-link-btn.md |
| TASK-0038 | french-learner | 分级阅读接入连读教学（逐句 + 整篇原文） | 2026-11-19 | tasks/archive/2026-11/TASK-0038-reading-linking.md |
| TASK-0039 | french-learner | 连读块：删除内部整句行与整句示范按钮（去重复） | 2026-11-19 | tasks/archive/2026-11/TASK-0039-remove-inline-sent-dup.md |
