# TASK-0035 连读提示独立试听 + 生词卡保留简洁连读按钮

- **状态**：已完成
- **优先级**：中
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户 2026-11-19："请在当前连读位置提示区域增加独立试听入口：点击每个提示时，只播放该连读位置对应的音频片段，不触发整句播放。下方示例 les amis /le.za.mi/ 和 unhomme /œ̃.nɔm/ 也需分别提供单独试听，并保持文本与音标清晰对应。生词卡的连读按钮保留一个简结的小按钮，放在怎么读的右侧。"

## 需求分析

- **目标**：①连读块的「连读位置提示」每行加独立试听（只播该词对 p.a+p.b，不触发整句）；②规则速览里的示例（les amis /le.za.mi/、un homme /œ̃.nɔm/）各自单独试听，文本与音标清晰对应；③生词卡连读按钮从「全部隐藏」改为「保留一个简洁小按钮，放在怎么读右侧」
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `frontend/app.js`：toggleLinkingInline 的 pairsHTML（每行加🔊，data-text=`p.a + ' ' + p.b`）、ruleMini 的 exHtml（加🔊 data-text=`word_fr`，文本音标分行）；renderVocab 恢复一个连读小按钮置于 pronEntry 右侧
  - `frontend/styles.css`：lk-pair-row 行内按钮样式、lk-mini-ex 文本/音标分行样式、生词卡连读按钮样式；移除 `.lk-legacy{display:none}`
  - `frontend/index.html`：js v19→v20、css v16→v17
- **涉及数据**：无

## 方案（持续迭代模式，需求明确直接实施）

- **实现思路**：复用现有 `speak(this)`（读 data-text 走 /api/tts），连读片段用 `p.a + ' ' + p.b`（如 "les amis"）作为片段文本，天然只播该处、不会触发整句；整句试听按钮独立保留。示例试听用 `word_fr` 作 data-text，文本与音标分两行显示保持对应。
- **改动点清单**：
  - pairsHTML：`<div class="lk-pair-row">` 内加 `<button class="lk-pair-say" onclick="speak(this)" data-text="a b">🔊</button>`，保留原词对与类型标签
  - ruleMini：示例 `<span>` 改列布局——上 `word_fr`、下 `phonetic`，各自带独立🔊按钮
  - renderVocab：`pronEntry` 右侧加一个 🔗 连读按钮（复用现有 toggleLinkingInline，data-text 用词的 example 或 word），文案精简为「🔗 连读」
  - 样式 + 版本号
- **风险与限制**：
  - 连读片段用 TTS 读两个词的组合，效果依赖本地神经语音（已有，le/la/les 连读准确）
  - 「音标清晰对应」指 text 与 IPA 分列展示，不做音素级逐音对齐（无逐音时间戳数据）
  - 气泡内新增多个小按钮，注意不撑破窄屏（flex-wrap）

## 子任务

- [x] 子任务 1：pairsHTML 每行独立试听 + ruleMini 示例独立试听与文本音标分行
- [x] 子任务 2：生词卡保留一个简洁连读按钮置于怎么读右侧 + 样式 + 版本号
- [x] 子任务 3：浏览器真机验收（片段试听不触发整句 / 示例试听 / 生词卡按钮 / 零回归）+ 留痕

## 验收标准

- [x] 连读位置提示每行有独立🔊，点击只播该词对片段（如 les amis），不触发整句按钮播放
  - 实测（:8001，fetch 拦截）：提示行试听 data-text=`veux un`，点击后 TTS 只请求 `veux un`，整句 `Je veux un café, s'il vous plaît.` 未被触发；按钮进 speaking 态
- [x] 示例 les amis /le.za.mi/、un homme /œ̃.nɔm/ 各有独立🔊，文本与音标清晰分行对应
  - 实测：示例试听 4 个（les amis/un homme/il est/elle a），各带独立🔊；点 les amis 只请求 `les amis`；文本（.lk-mini-ex-w）与音标（.lk-mini-ipa）分两行对应，配对实测 les amis↔/le.za.mi/、un homme↔/œ̃.nɔm/ 正确
- [x] 生词卡「怎么读」右侧有一个简洁 🔗 连读按钮（非隐藏），点击仍可展开连读
  - 实测：`.pron-entries` 容器内「🎵 怎么读」后紧跟「🔗 连读」（linkPositionRight:true），共 35 个；点击后 `.lk-inline` 正常展开（含逐句+试听）；旧 lk-legacy 全部移除（残留 0）
- [x] `node --check` 通过；数据库零改动；整句试听与既有功能零回归
  - `node --check` PASS；整句按钮 `lk-play` 保留；逐词 47/对话 20/中文 0 词位；版本号 js v20/css v17

## 变更记录

- 2026-11-19 创建（持续迭代模式，需求明确）
- 2026-11-19 完成：pairsHTML 每行加 `.lk-pair-say`（data-text=p.a+' '+p.b）；ruleMini 示例改列布局（上词下音标）各带独立🔊；生词卡移除两处旧按钮、改为 pronEntry 右侧一个 `.pron-link-entry`（data-text 优先 example）；样式新增 lk-pair-say/pron-entries/pron-link-entry、移除 lk-legacy 隐藏规则；版本号 v20/v17。多角色分工 + 浏览器真机验收全过、留痕如上。数据库零改动
