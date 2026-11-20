# TASK-0039 连读块：删除内部整句行与整句示范按钮

- **状态**：已完成
- **优先级**：低
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户 2026-11-19：连读块展开后，内部顶部的整句行（如 "La gare ? C'est tout droit, puis à gauche."）与「🔊 听整条连读示范」按钮和外层正文重复——"可以不要内部卡片的整句连读"。

## 需求分析与方案

- **目标**：连读块只留「连读位置提示（含独立试听）+ 规则小卡」；整句展示与整句试听交给正文（正文已逐词可点、句旁已有 🔊）。
- **改动点**：`frontend/app.js`（toggleLinkingInline 删 sentHTML/pairAt/raws 死代码与 block 内 lk-inline-sent、lk-play 两行；空态文案改指正文 🔊）；`frontend/styles.css`（删 .lk-hl*/.lk-inline-sent/.lk-play 死样式）；`frontend/index.html`（js v22→v23、css v18→v19）。
- **涉及数据**：无。

## 验收标准

- [x] 连读块内无整句行、无「听整条连读示范」按钮；位置提示 + 独立试听 + 规则小卡保留
  - 实测（:8001）：对话气泡与阅读逐句块均 sentLine:false / wholePlay:false，pairRows、lk-pair-say（5 个）、ruleMini（2 张）、lk-sub 小标题均在
- [x] 独立试听仍只播片段不触发整句；正文 🔊 与逐词零回归；收起正常
  - 实测（fetch 拦截）：点提示试听只请求 `veux un`；阅读页 rplay 6、逐词 41；收起后块消失
- [x] `node --check` 通过；死代码（lk-inline-sent/lk-play/lk-hl/sentHTML）零残留；数据库零改动

## 变更记录

- 2026-11-19 创建并完成（持续迭代模式，单一删除操作；真机验收留痕）
