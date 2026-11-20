# TASK-0027 读音功能修复：patterns 断链接通 + 生词覆盖硬指标 + 按钮音节文案

- **状态**：完成（已验收，2026-11-19）
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户反馈："怎么读语病未解决，功能还是没有覆盖70-80%的生词"；方案讨论中追加："能否提取规则里的元音等需学习的音节出来，替换按钮中的规则 title 🎵 怎么读"。

## 需求分析

- **目标**：①「🎵 怎么读」入口覆盖率从 26% 提到 ≥70-80% 硬指标；②修复已实锤的语病（法语拼写 giraffe→girafe、gateau→gâteau；que 中文释义混英文 "that"；按钮文案两个"读"叠用）；③按钮按用户要求显示提取的音节（如 "ai / ay 🎵 怎么读"）。
- **根因（诊断坐实）**：内容层 38/39 条规则已带 `patterns` 拼读字段 → 后端 `pronunciation.py` 10 字段严格投影把它剥掉 → 前端 pattern 引擎（app.js:1712 已写好）永远收不到数据 → 只剩 156 例词精确匹配。实测 DB 46 生词仅 12 命中（26.1%），接通后模拟 97.8%。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `tools/french-learner/backend/pronunciation.py`（投影/校验补 patterns+focus）
  - `tools/french-learner/data/input/pronunciation_rules.json`（focus 39 条 + patterns 锚定改造 + 3 处语病）
  - `tools/french-learner/frontend/app.js`（pronKey œ 映射、双形态匹配、锚定解析、最长优先、按钮 focus 文案）+ `index.html`（js 版本破缓存）
  - `tools/french-learner/docs/PRONUNCIATION_CONTRACT.md`（契约补丁 v1.1）
- **涉及数据**（引用数据地图 `docs/data_content.md`）：
  - `data/input/pronunciation_rules.json`（已有数据文件的字段级修补，入 git）
  - 不动数据库、不动端点数量（零新端点、零新依赖）

## 方案（已确认）

- **实现思路**：
  1. 契约 v1.0→v1.1：规则对象新增可选 `patterns`（拼读匹配，锚定语法：`^h` 词首锚 / `er$` 词尾锚 / 普通子串）与可选 `focus`（按钮展示音节，与匹配语义分离）
  2. 后端：RULE_FIELDS + 校验补两字段；投影透传（缺失字段不产出）
  3. 内容：39 条补 focus；patterns 锚定改造（词末组/联诵组改 `s$` 类词尾锚；except_01/03 改全词锚 `^je$`/`^six$`；嘘音 h 改全词例；联诵/连音两条跨词规则 patterns 置空不参与词卡匹配）；修 girafe/gâteau/que
  4. 前端：pronKey 加 œ→oe；pattern 编译支持 `^`/`$` 锚定；匹配对归一化+原始小写双形态（带重音 patterns 可命中）；排序 全词锚 > 部分锚 > 子串、同级长 pattern 优先；按钮文案 `focus 🎵 怎么读`（兜底 patterns 去锚连接 → 裸「🎵 怎么读」），规则 title 移入悬停提示
- **改动点清单**：见上
- **风险与限制**：patterns 语义三方需一致（契约冻结为准）；skip 词表仍跳过 un/une 等功能词（本期不改，已知限制）；联诵/连音为跨词现象，词卡单 token 匹配不适用（小册子入口可达）
- **用户确认日期**：2026-11-19（按钮方案 2026-11-19 按"提取音节"意见更新后确认开工）

## 子任务

- [x] 子任务 1：契约补丁 v1.1（PRONUNCIATION_CONTRACT.md）
- [x] 子任务 2：后端 pronunciation.py 投影/校验
- [x] 子任务 3：内容 JSON（focus + patterns 锚定 + 语病修复）
- [x] 子任务 4：前端匹配引擎 + 按钮文案 + 版本号（js v13→v14）
- [x] 子任务 5：测试角色验证（覆盖率硬指标 + 隔离沙箱 API + node --check + 零回归）
- [x] 子任务 6：地图/留痕/汇报

## 验收标准

- [x] 覆盖率硬指标：DB 生词 45/46=**97.8%**（仅 skip 词表中的 "un"），语料全词表 155/155=**100%**（离线复刻新匹配器实测）
- [x] 隔离沙箱 HTTP **24/24 PASS**：39 条详情下发 patterns/focus（38 有 focus、39 有 patterns）、缺失键不产出非 null、锚定语法生效、girafe/gâteau/que 三处语病已修、坏 id 40401、既有 5 端点零回归、GET-only 零写入（就绪后 sha 一致）
- [x] 按钮文案抽样：maison→「ai / ay 🎵 怎么读」、parler→「-er 🎵 怎么读」、bon→「on / om 🎵 怎么读」、que→「词末 -e 🎵 怎么读」、cœur→「eu / œu 🎵 怎么读」、été→「é / è / ê / ë 🎵 怎么读」；规则 title 移入悬停提示；`node --check` 通过
- [x] 主库 integrity ok、词表行数与基线一致（46/157）；首测 sha 变化为 init_db 幂等触碰（用户每次正常启动同此），数据零损伤

## 变更记录

- 2026-11-19 创建；方案经用户确认（含按钮音节化修改意见）
- 2026-11-19 完成：契约 v1.1（patterns+focus 可选字段 + 锚定语法）；pronunciation.py 投影/校验透传；JSON 39 条 focus、10 条 patterns 锚定改造（词末组改 s$ 类、except 组改全词锚、联诵/连音置空）、3 处语病修复；前端 pronKey œ→oe、双形态匹配、spec 排序（全词锚>部分锚>子串、同级长优先）、按钮 focus 文案 + 首选有 focus 规则（été 瑕疵修正）、js v14
- 2026-11-19 测试：覆盖率 DB 97.8%/语料 100%（硬指标 PASS）；隔离沙箱 24/24；node --check OK；主库完好；待用户真机验收
- 2026-11-19 用户初看仍只见少量按钮 → 排查为旧后端进程（启动时缓存规则，改代码未重启）仍在服务；重启后端（8001）后新字段下发正常，用户刷新页面验收通过；归档至 `tasks/archive/2026-11/`
