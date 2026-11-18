# TASK-0015 呀呀法语：本地 Whisper 语音识别根治 network 错误

- **状态**：已完成（代码完成，真实转写与端到端闭环实测通过，待上级验收）
- **优先级**：高
- **创建日期**：2026-11-17
- **完成日期**：2026-11-17

## 原始需求

用户反馈："我对话点击麦克风，识别出错：network"。经 AskUserQuestion 确认，用户选择「本地 Whisper」路线根治（而非国内云 ASR 或放弃语音）。

## 需求分析

- **根因**：浏览器原生 Web Speech API 的法语识别依赖 Google 服务器，国内网络无法访问，报 `network` 错误。这是架构限制，改代码无法解决，必须换识别引擎。
- **目标**：改用本地 Whisper 离线识别，浏览器录音 → 上传 → 本地转写 → 进入对话，全程不依赖境外服务、免费、音频不出本机。
- **改动点**（引用 `docs/project_content.md`）：
  - 新增 `tools/french-learner/asr_service/`（独立语音服务）
  - 修改 `backend/app.py`（新增 2 个 ASR 端点）
  - 修改 `frontend/app.js`、`index.html`（麦克风改录音上传）
  - 更新 `README.md`、`.gitignore`、两张地图

## 方案（已确认）

- **独立 ASR 服务**：faster-whisper 重量级依赖不塞进主后端（保持主后端 requirements 两行契约）；独立 venv `.venv-asr`，端口 8010，模型懒加载（tiny 档 CPU int8）。
- **主后端代理**：`/api/asr/status`（探测可用性）+ `/api/asr/transcribe`（转发音频），手写 multipart 解析避免引入 python-multipart。
- **三级降级**：本地 ASR → 浏览器识别（境外网络可用时）→ 打字，任一环节失败都不中断对话。
- **兼容性决策**：Python 3.13 只能用 PyAV 19，而 faster-whisper 1.2.1 与 PyAV 19 的 `metadata_errors` 参数不兼容。采用 ffmpeg 转 16kHz 单声道 PCM + numpy ndarray 传给模型，绕开 PyAV 解码路径，不降包。

## 子任务

- [x] 探测环境（Python 3.13.14、ffmpeg 4.1 已有、无 Whisper 包）
- [x] 实测 faster-whisper 在 3.13 可装（清华镜像缺 cp313 wheel，官方/阿里云镜像有；大包 ctranslate2 下载慢，单独下载解决）
- [x] 编写独立 ASR 服务 `asr_service/server.py` + 启动脚本 `start_asr.bat`
- [x] 主后端新增 `/api/asr/status`、`/api/asr/transcribe` 代理端点
- [x] 前端麦克风改为 MediaRecorder 录音上传 + 三级降级
- [x] 修复 PyAV 19 兼容问题（ffmpeg→ndarray 绕开）
- [x] 修复代理端点 2 处变量残留 bug（`file.filename`/`file.content_type` → 解析变量）
- [x] 真实转写测试（edge-tts 生成法语句 → Whisper 转写正确）
- [x] 端到端闭环测试（语音→转写→chat 重述，正确句与错误句均验证）
- [x] 清理测试数据、更新 .gitignore/README、Git 提交（`0687252`）

## 验收标准

- [x] 点击麦克风不再报 `network`；本地 ASR 服务不可用时给出清晰提示并自动定位输入框
- [x] 本地 Whisper 法语转写准确（实测 "Je voudrais un café" 转写正确，语言 fr 置信度 1.0）
- [x] 说错话的语音能触发温柔重述（实测 "Je veux un thé" → recast_of 非空、ai_text="Je voudrais un thé"）
- [x] 全程不依赖境外服务、不花钱
- [x] 主后端 requirements 仍保持两行（未引入新依赖）
- [x] 大文件（venv/wheelhouse/数据库）均被 .gitignore 忽略

## 关键验证数据

- 本地 ASR 直连：TTS "Je voudrais un café, s'il vous plaît." → 转写 "Je voudrais un café, si vous plait."，fr 置信度 1.0，纯转写 0.81s
- 代理链路：`POST /api/asr/transcribe` → 200/code=0，0.7s
- 完整闭环：错误句语音 → 转写 "Je veux un thé." → chat → recast_of="Je veux un thé"、ai_text="Je voudrais un thé"

## 风险与限制

- 首次启动需下载 Whisper tiny 模型约 75MB（已下载并缓存到 `C:\Users\Karen\.cache\huggingface`）
- tiny 模型对法语重音符号识别有细微误差（如 "plaît"→"plait"），不影响理解；可换 small 模型提升精度（牺牲速度）
- 语音服务需单独启动（start_asr.bat），未启动时自动降级打字
- 浏览器录音需麦克风权限，建议 Chrome / Edge

## 变更记录

- 2026-11-17 创建；本地 Whisper 方案实施完成，端到端闭环实测通过
