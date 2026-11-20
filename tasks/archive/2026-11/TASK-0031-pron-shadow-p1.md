# TASK-0031 读音跟读闭环（P1）：🎙 录音 + ASR 近似比对 + 三档温和反馈

- **状态**：进行中
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：

## 原始需求

持续自动迭代模式（用户 2026-11-19 授权："继续自动迭代，尽量不征求我的同意…开发新功能并优化功能"）。本任务为读音方案 PRONUNCIATION_PLAN §8 既定分期 P1（上级 2026-11-18 已批准 P0→P1→P2 路线），属既有确认范围。

## 需求分析

- **目标**：规则卡内 🎙 跟读 shadow_text_fr → 本地 ASR 转写 → 六档判据纯函数评分 → 用户可见三档温和反馈 → 练习计数入 pronunciation_progress。
- **红线**（沿用 PLAN §3/§4）：ASR 转写 ≠ 真实发音，从宽不判错；C 档永远给"再来一次/没听清"；自评兜底"我觉得读对了"；不存音频不存转写文本（隐私）；单音 syllable 模式不打分只作口型练习。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `frontend/app.js`：buildPronIndex 建 IPA Map + scoreShadow 六档纯函数 + toggleShadowRecord 独立录音链路（复用 transcribeExamAudio 模式，绝不调 transcribeAudio 误发聊天流）+ renderPronCard 跟读区
  - `frontend/styles.css`：跟读区样式
  - `frontend/index.html`：js v15→v16
- **涉及数据**：无数据文件/端点/数据库结构改动；复用 `/api/asr/transcribe` 与 `/api/pronunciation/progress`（服务端 practice_count +1）

## 方案（持续迭代模式，依据既有已批准方案实施）

- **评分判据**（PLAN §4.3 按序短路）：UNSURE（低置信/音频<2s/查不到词典且近似不够）→ EXACT（归一化相等）→ CLOSE（字符串相似度 ≥0.8）→ CLOSE_SOUND（IPA 距离 ≤1，易混集 ɛ̃≈œ̃、j≈i 记 0）→ RETRY（距离 ≥2）；ASR 不可用 → 降级不评分。
- **映射**：EXACT→A「听起来很接近啦…」；CLOSE/CLOSE_SOUND→B「差不多啦…再听一遍示范就好～」；RETRY→C「想再听一遍示范吗？」；UNSURE/降级→C「没太听清，可能是收音的小问题…」。
- **进度**：每次开口 → POST {rule_id}（服务端 +1，不改已学状态）；自评达标 → POST {rule_id, stage:'confident', self_assessed:true}（只增不减）。
- **风险**：浏览器麦克风权限与 ASR 实听无法自动化（真机验收由用户完成）；自动化覆盖 = 评分纯函数页内单测 + UI 存在性 + 零回归。

## 子任务

- [x] 子任务 1：IPA Map + scoreShadow 纯函数 + 三档映射
- [x] 子任务 2：跟读 UI + 独立录音 + 转写接评分 + 进度 POST
- [x] 子任务 3：样式 + 版本号 js v16
- [x] 子任务 4：node --check + 页内评分单测 + UI/零回归检查 + 留痕

## 验收标准

- [x] scoreShadow 页内单测 **9/9 全过**：EXACT、标点归一 EXACT、CLOSE（maizon sim 0.83）、RETRY（chat→chaise IPA 距离 2）、CLOSE_SOUND（oui→si IPA 距离 1）、UNSURE×3（低置信/短音频/无词典）、ipaEq 易混集——IPA Map 133 词真实构建
- [x] 规则卡跟读区渲染正常（截图）：跟读目标 maison、🎙 开始跟读、反馈区模拟 A 档话术（teal）；syllable 规则显示"不打分"说明
- [x] 录音走独立链路（FormData→/api/asr/transcribe，hints=目标词+同规则例词），未触碰 transcribeAudio；切卡/关卡自动 pronShadowReset
- [x] 每次开口 POST progress（服务端 +1，不改已学状态）；C 档出现「我觉得读对了」自评 → POST confident+self_assessed；降级（ASR 不可用/非 0）不评分不中断
- [x] `node --check` 通过；词卡/复习/阅读零回归；隐私：转写文本仅内存评分，不显示不落库
- [x] 真麦克风端到端（权限/实听/反馈）——用户 2026-11-19 验收通过

## 变更记录

- 2026-11-19 创建（持续迭代模式，依据既有已批准 P1 分期）
- 2026-11-19 完成：app.js 新增 P1 块（levDistance/ipaEq/scoreShadow/shadowFeedback/pronShadowSection/pronShadowReset/toggleShadowRecord/transcribeShadowAudio/shadowSelfAssess + IPA_CONFUSABLE_PAIRS）+ buildPronIndex 建 ipaMap（normIpa 归一化）+ renderPronCard 插跟读区（切卡先 pronShadowReset）；styles.css 跟读样式组；js v15→v16。真机页内验收：9/9 单测 + UI 截图全过
- 2026-11-19 用户真麦克风端到端验收通过，全部验收标准达成
