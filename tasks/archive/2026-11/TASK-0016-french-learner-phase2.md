# TASK-0016 呀呀法语阶段二（GLM 可插拔重述 + i+1 输入流）

- **状态**：完成（已验收，2026-11-19）
- **优先级**：高
- **创建日期**：2026-11-17
- **完成日期**：2026-11-17

## 原始需求

用户要求：继续推进产品，沿用四角色分工并可增加测试等角色；**开始前需经确认**。

## 需求分析

- **先确认后开工**：多轮 AskUserQuestion 拍板——范围 A+B 双主线、国内大模型 API、独立 QA+报告、智谱 GLM key、环境变量+.env.example 保管、测试角色独立验收；B2 考级真题暂缓。
- **目标**：主线 A 让重述覆盖任意错句（当前仅 4 条本地规则）；主线 B 补上完全空缺的 i+1 可理解输入流。
- **组织方式**：团队 `yaya-french-v2`，七角色（team-lead 总指挥 + pm + architect + backend + frontend + content + tester），三波：
  - 第一波：PM + 架构师并行（契约 v2 是四方共同输入）
  - 第二波：后端 + 前端 + 内容并行（目录隔离）
  - 第三波：测试角色独立验收 + 总指挥集成交付

## 方案（已确认）

- **主线 A**：智谱 GLM OpenAI 兼容适配（`open.bigmodel.cn/api/paas/v4`，`glm-4-flash`），`GLM_*` 优先、`LLM_*` 兼容后备；无 key/401/超时/格式异常一律降级本地规则，永不 500；零新依赖（urllib），requirements 仍两行。
- **主线 B**：i+1 输入流，3 张新表 + 5 端点 + 语料加载器 + 阅读界面；i+1 打分（A2→B1，coverage∈[0.7,0.9] 加权）。
- **不破坏 v1**：7 业务端点 + 3 ASR/TTS 代理 + 5 表 + ChatResult 4 字段 + version 1.0.0 全不动。

## 子任务

- [x] 团队建立 + 7 任务登记（先 TeamCreate 后建任务，编号有效）
- [x] PM 章程 `docs/PHASE2_CHARTER.md`（双主线量化目标、10 项风险、DoD）
- [x] 架构契约 v2 `docs/ARCHITECTURE_V2.md`（5 端点、GLM 适配、语料 schema、字段一致性）
- [x] 后端：ai.py（GLM+降级9条+合并收词）、db.py（3 表）、app.py（5 端点）、seed_input.py、.env.example
- [x] 内容：21 篇分级语料（A2/B1/B2 各 7）+ 157 生词 + README（`data/input/`）
- [x] 前端：对话/阅读双 Tab、逐句研读、音频兜底、一键收词、i+1 推荐（v4）
- [x] 独立 QA：`docs/QA_REPORT.md`（109 用例 PASS 109 / FAIL 0 / BLOCK 0）
- [x] 端到端联调：v1 零回归 + 输入流入库 + recommend + chat 降级
- [x] 总指挥独立核查（后端零依赖、前端无红叉、语料全合规、QA 报告真实）
- [x] Git 分阶段提交：b22b549（文档）、5acf5ba（实现）、c0b1f5e（QA）

## 验收标准

- 任意法语错句能得到温柔重述（无 key 时降级本地规则仍 200/4 字段）—— 达成
- 输入流三级可浏览、逐句对照、一键收词、i+1 推荐可用 —— 达成
- 测试报告独立出具（非开发自报）：109/109 PASS、零阻塞缺陷 —— 达成
- v1 零回归 —— 达成

## 风险与限制

- ~~真实智谱 GLM key 的端到端调用未测~~ **已关闭**：19:40 用本机用户环境变量 `ZHIPU_API_KEY` 真实调用智谱端点，直调 + HTTP `/api/chat` 两路均返回自然重述且未降级；QA_REPORT 第七节有证据。
- 前端未做浏览器交互 E2E（仅验证资源与端点字符串）；可人工点开阅读 Tab 验证。
- 语料为原创教学示例，CEFR 为教学标注；后续扩词库须注意 CC BY-NC-SA 商业化限制。
- 语料更新需重启服务（或手动调 load_input_corpus()）才同步。

## 变更记录

- 2026-11-17 建任务；六角色三波完成；独立 QA 通过；验收待上级确认。
- 2026-11-17 19:40 用户告知 key 在 `ZHIPU_API_KEY`；`ai.py` 提为最高优先级，文档/QA 同步，真实冒烟通过；提交 `8869b2f`。
- 2026-11-17 19:57 对话双方补 🔊 标准发音 + 中文翻译（新增 `/api/translate`，前端回填）；真实翻译与 chat 回归通过；提交 `e1929e6`、`e2df849`。
- 2026-11-17 20:15 四角色修复 `Show !/Chef Onti` 误识别（ASR beam/prompt/保守纠正 + 主后端透传 + 前端修正小字）与 explanation 强制中文；QA 最终 28/28 PASS；提交 `26bbc40`、`22d38a3`、`5e0d491`。
- 2026-11-17 20:45 三角色调研 + 三角色实施 ASR 升级：置信度三阈值门控、低置信不自动提交改重录、默认换 small（tiny 一行回退）；QA 门控 12/12 + 回归 9/9 PASS，15 句 A/B WER 0.048→0.008（合成语音，不可外推真人）；提交 `23b866f`、`b1f71e8`，报告 `docs/QA_ASR_UPGRADE_REPORT.md`。
- 2026-11-18 验收期缺陷 **D1**（上级发现：explanation 正确/错误形式颠倒）修复：SYSTEM_PROMPT 消除自相矛盾 + 顺序硬约束，新增 `_validate_explanation_order` 确定性兜底交换；离线单测 9/9、真实 GLM 直调 2 次、HTTP 端到端均通过；`docs/QA_REPORT.md` 第八节留痕。
- 2026-11-18 验收期缺陷 **D2**（上级发现：伪重述——片段句 `S'en va ?` 被硬凑 recast_of、ai_text 与原句无关联且角色错位、recast_of 回填截断）修复：SYSTEM_PROMPT 定义纠错充要条件 + `_validate_recast_relevance` 词汇锚兜底降级 + recast_of 用户原句权威覆盖 + 方位词方向提示词加固；离线 8/8、真实 GLM（含兜底真实拦截证据）、HTTP 端到端 ×2 通过；`docs/QA_REPORT.md` 第九节留痕。
- 2026-11-19 用户验收通过；经验提炼 1 条（LLM 关键语义字段确定性兜底）入 `docs/lessons.md`；归档至 `tasks/archive/2026-11/`。
