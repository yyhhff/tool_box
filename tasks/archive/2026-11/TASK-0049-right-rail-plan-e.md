# TASK-0049 右栏布局方案 E：账本吸顶条 + 生词满高

- **状态**：已完成
- **优先级**：中
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

用户：换序后「本场景生词又出去了」，要求多画几版前端设计稿、比较方案、有审美、参考 GitHub 优秀设计后实施。

## 设计过程

产出 `docs/design/right-rail-layouts.html`：5 版高保真 mockup（A 现状 / B Tab 切换 / C KPI 压缩条 / D 融入顶栏 / E C+吸顶），全部使用应用现有设计变量；参考 Tabler / shadcn dashboard 的 KPI strip 模式与 GitHub 详情页右栏 sticky 模式。含对比矩阵。用户拍板：**方案 E，生词要满高**。

## 方案（已确认）

- 右栏并为一个生词面板：顶部「账本吸顶条」（待复习 / 本周新词 / 连续天数 / 📝 复习按钮），`position:sticky` 页面滚动时常驻
- 生词列表 `.vocab` 满高：`max-height:calc(100vh - 300px)` 内部滚动（沿用现有 max-height+overflow 惯用法）
- 次级指标（已掌握/累计对话/正确率）职责归「🌱 我的成长」页（该页已有全部数据）

## 改动点

- `frontend/index.html`：右侧两面板并为一生词面板 + 账本吸顶条；js v27 / css v22
- `frontend/app.js`：renderLedger 适配新结构（保留 dueNum/weekNew/streakBadge，移除已删元素写入）
- `frontend/styles.css`：账本吸顶条样式 + .vocab 满高；清理失去宿主的 .ring/.stat 死样式

## 子任务

- [x] 子任务 1：设计稿 5 版 + 对比矩阵 + 用户拍板
- [x] 子任务 2：面板重构 + 吸顶条 + renderLedger 适配 + 样式 + 版本号
- [x] 子任务 3：真机验收（账本条首屏+吸顶 / 生词满高 / 复习入口 / 零回归）+ 留痕

## 验收标准

- [x] 无滚动状态下账本条与生词列表同时可见；生词列表占满剩余高度
- [x] 页面下滚时账本条吸顶常驻，复习按钮随时可点
- [x] renderLedger 无空引用报错；复习弹层、成长页、对话区零回归；`node --check` 通过

## 变更记录

- 2026-11-19 创建并完成（设计稿先行，用户确认方案 E 后实施）
