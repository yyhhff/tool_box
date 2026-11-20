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
| TASK-0032 | french-learner | 读音学习交互重构：贴词气泡 + 连读内嵌（取代模态跳转） | 高 | 进行中（浏览器真机四步全过：气泡原地/外点关闭/再点收起/内嵌展开收起/完整讲解回位，待用户验收） | tasks/active/TASK-0032-pron-inline-popover.md |
| TASK-0071 | french-learner | Wave 2 车道 B：v3.1 耳朵开口（听力强化：变速 + 精听 + 真实语速适应） | 高 | 进行中（方案已确认，开发中） | tasks/active/TASK-0071-v3.1-listening.md |
| TASK-0078 | french-learner | Wave 2 车道 B：v3.3 语法微卡（50 显性语法卡 + 阅读 chip/复习 banner/对话第 3 次推卡三嵌入） | 高 | 待集成（开发+自测完成：153 单测全绿 + GUI 冒烟三嵌入全过；真机验收待用户；⚠️ 分支基于 v3.0 合并前 006ece4，集成时先对齐 main） | tasks/active/TASK-0078-v3.3-grammar-cards.md |

## 归档记录

> **编号说明**：TASK-0051、TASK-0052、TASK-0056 各有两条不同项目的记录（并发领号重号遗留）。为免破坏文档与经验库引用，不重命名；新任务一律走 `tasks/next_id.txt` 单一计数器。**注意：计数器的"读号→用号→写回"非原子，并行会话同时领号仍会重号（TASK-0056 于 2026-11-20 复发）；根治需加文件锁或由协调方统一发号。**

| ID | 项目 | 任务 | 完成日期 | 归档位置 |
|----|------|------|----------|----------|
| TASK-0079 | french-learner | Wave 2 车道 A：v3.0 每天十五分钟（今日三件事 + XP 等级 + 真猫贴纸陪伴态，路线图点亮） | 2026-11-21 | tasks/archive/2026-11/TASK-0079-v3.0-daily-path.md |
| TASK-0069 | french-learner | Wave 1 收尾：v2.3 批次续跑（四轮补量至 106 篇四档各 ≥20 + 音频 536 条 + 抽检 0/5 误放，路线图 v2.3 点亮） | 2026-11-21 | tasks/archive/2026-11/TASK-0069-v2.3-batch-continue.md |
| TASK-0068 | french-learner | Wave 1 收尾：v3.2 发音教练端到端 ≤3s 调参（coach 专用 tiny 模型实测 0.62–0.84s；切页重叠缺陷+协商缓存根治 251d0e6） | 2026-11-21 | tasks/archive/2026-11/TASK-0068-v3.2-latency-tuning.md |
| TASK-0066 | french-learner | Wave 1 车道 B：v2.3 内容工厂（语料量产管线 + AI 审校 + 音频批量，批次 1 口径修订后达标） | 2026-11-21 | tasks/archive/2026-11/TASK-0066-v2.3-content-factory.md |
| TASK-0063 | french-learner | 补强总纲 v2.2–v4.1 落地 + 多会话并行开发机制（Wave 0/1 实战闭环，Wave 2 解锁） | 2026-11-21 | tasks/archive/2026-11/TASK-0063-master-plan-parallel.md |
| TASK-0070 | service_manager | `_load_state` 容错修复（损坏 JSON 备份重建 + 缺键补默认；unittest 22 例绿） | 2026-11-20 | tasks/archive/2026-11/TASK-0070-service-manager-loadstate-fix.md |
| TASK-0067 | french-learner | Wave 1 车道 C：v3.2 发音教练（词级时间戳 + 三池选句器 + 三维评分 + 中文反馈；端到端实测 ~3.6s 略超 3s 待调参） | 2026-11-20 | tasks/archive/2026-11/TASK-0067-v3.2-pron-coach.md |
| TASK-0065 | french-learner | Wave 1 车道 A：v2.2 零基础 A1 通路（定级四档24题 + A1语料10篇 + onboarding台阶路径，真机验收通过） | 2026-11-20 | tasks/archive/2026-11/TASK-0065-v2.2-a1-path.md |
| TASK-0064 | french-learner | Wave 0 地基拆分（app.py→12 routers + app.js→ES modules + worktree 脚本，A/B 行为一致） | 2026-11-20 | tasks/archive/2026-11/TASK-0064-wave0-foundation.md |
| TASK-0062 | french-learner | 使用反馈收集入口 v1：页脚按钮 + 方向+文字浮层 + 汇总端点 + 决策文档 | 2026-11-20 | tasks/archive/2026-11/TASK-0062-feedback-v1.md |
| TASK-0061 | french-learner | 路线图 v2.1 点亮（留存深化闭环，6/6 全亮） | 2026-11-20 | tasks/archive/2026-11/TASK-0061-roadmap-v21-lightup.md |
| TASK-0060 | french-learner | 留存激励 v1：今日小目标 + 接着上次 + 微进步 + streak 正向 | 2026-11-20 | tasks/archive/2026-11/TASK-0060-retention-v1.md |
| TASK-0059 | french-learner | 面客建设里程图 v1：大版本主题闭环 + 点亮 | 2026-11-20 | tasks/archive/2026-11/TASK-0059-roadmap-v1.md |
| TASK-0058 | french-learner | 成就系统 v1：真实事件判定 + GET /api/achievements | 2026-11-20 | tasks/archive/2026-11/TASK-0058-achievements-v1.md |
| TASK-0057 | french-learner | SM-2 到期调度：待复习队列端点 GET /api/review/due + 前端到期入口 | 2026-11-20 | tasks/archive/2026-11/TASK-0057-review-due-scheduler.md |
| TASK-0056 | workbuddy-multi-account | 任务迁移诚实降级：云端覆盖检测与明确提示 | 2026-11-20 | tasks/archive/2026-11/TASK-0056-migration-cloud-override-notice.md |
| TASK-0055 | tool_box 全局 | 工作流提效与状态一致性（三态验收/单一编号/两次规则） | 2026-11-20 | tasks/archive/2026-11/TASK-0055-工作流提效与状态一致性.md |
| TASK-0042 | annual_report_reader | h1_2026 分析台自检启动脚本（start.bat + selfcheck.py，22 项自检通过才打开页面） | 2026-11-20 | tasks/archive/2026-11/TASK-0042-h1-selfcheck-start.md |
| TASK-0052 | workbuddy-multi-account | 根治端口漂移与自动打开错服务（bind-first + 端口事实文件 + 服务身份校验 + 专属段 8010-8029） | 2026-11-20 | tasks/archive/2026-11/TASK-0052-port-registry-root-fix.md |
| TASK-0051 | annual_report_reader | 横向对比表补充「名词解释（小白版）」 | 2026-11-20 | tasks/archive/2026-11/TASK-0051-glossary-for-layman.md |
| TASK-0047 | french-learner | 「我的成长」视图 v1（真实数据聚合 + FALLBACK 假值修复） | 2026-11-19 | tasks/archive/2026-11/TASK-0047-growth-view-v1.md |
| TASK-0048 | french-learner | 复习卡加读音 + 记忆小账本上移免滚动 | 2026-11-19 | tasks/archive/2026-11/TASK-0048-review-audio-ledger-above.md |
| TASK-0049 | french-learner | 右栏布局方案E：账本吸顶条 + 生词满高（5版设计稿对比） | 2026-11-19 | tasks/archive/2026-11/TASK-0049-right-rail-plan-e.md |
| TASK-0050 | french-learner | 重置对话：UI 初始化 + 持久化同步清空（DELETE /api/chat/history） | 2026-11-19 | tasks/archive/2026-11/TASK-0050-reset-chat-persisted.md |
| TASK-0051 | french-learner | 前端显示审计 7 项修复（对比度/重置入口/空态/进度条/网格） | 2026-11-19 | tasks/archive/2026-11/TASK-0051-fix-display-audit-7.md |
| TASK-0052 | french-learner | 阅读完成落库 + 成长页阅读卡真实数据（幂等 reading_logs） | 2026-11-20 | tasks/archive/2026-11/TASK-0052-reading-complete-persist.md |
| TASK-0053 | french-learner | 首次引导 onboarding（≤3 步可跳过，方案F） | 2026-11-20 | tasks/archive/2026-11/TASK-0053-onboarding-3steps.md |
| TASK-0040 | french-learner | 学习进度持久化 P0：对话历史读回 + 假值清零 + 真实统计 | 2026-11-19 | tasks/archive/2026-11/TASK-0040-progress-persistence-p0.md |
| TASK-0031 | french-learner | 读音跟读闭环（P1）：🎙 ASR 近似比对 + 三档温和反馈 | 2026-11-19 | tasks/archive/2026-11/TASK-0031-pron-shadow-p1.md |
| TASK-0037 | workbuddy-multi-account | 切号任务列表迁移：接管客户端任务快照 | 2026-11-19 | tasks/archive/2026-11/TASK-0037-task-snapshot-migration.md |
| TASK-0041 | workbuddy-multi-account | start.bat 启动前自动清理旧服务（防旧代码残留） | 2026-11-19 | tasks/archive/2026-11/TASK-0041-start-bat-clean-old-service.md |
| TASK-0043 | workbuddy-multi-account | start.bat 启动后自动在浏览器打开面板（仿呀呀法语） | 2026-11-19 | tasks/archive/2026-11/TASK-0043-auto-open-browser.md |
| TASK-0045 | workbuddy-multi-account | 修切号凭据写回 PermissionError + 账号删除功能 | 2026-11-19 | tasks/archive/2026-11/TASK-0045-activate-write-and-delete-account.md |
| TASK-0046 | annual_report_reader | 31行业龙头年报本地带读（零GLM）+ 跨行业横向对比 | 2026-11-19 | tasks/archive/2026-11/TASK-0046-31行业龙头年报本地带读.md |
| TASK-0044 | workbuddy-multi-account | 端口可配 + 占用时自动回退（修复页面显示旧 JSON/僵尸端口） | 2026-11-19 | tasks/archive/2026-11/TASK-0044-port-fallback.md |
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
| TASK-0054 | french-learner | 页脚手动重温引导入口（reopenOnboarding） | 2026-11-20 | tasks/archive/2026-11/TASK-0054-onboarding-reopen.md |
| TASK-0055 | french-learner | 水平画像 v1（skill_events+EWMA 懒计算+成长页五维卡） | 2026-11-20 | tasks/archive/2026-11/TASK-0055-skill-profile-v1.md |
| TASK-0056 | french-learner | ASR 端口冲突根治：8010→8011（避开 WorkBuddy multi-account） | 2026-11-20 | tasks/archive/2026-11/TASK-0056-asr-port-8011.md |
