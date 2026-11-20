# TASK-0051 前端显示问题修复（审计 7 项）

- **状态**：已完成
- **优先级**：高
- **项目**：tools/french-learner
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 背景

TASK-0051-audit（同日审计）通过 4 视图真机截图 + DOM/CSS 排查提出 7 项显示问题，本任务逐项修复。

## 修复清单

| # | 问题 | 修复 |
|---|------|------|
| 1 | 用户气泡中文 #FBE0D3 在橙底上对比度仅 ~2.4:1 | `.row.user .cn` 改 `#FFFFFF` |
| 2 | 「重置对话」全局页脚常驻，非对话页语境错位 | 移至对话卡头部（AI 陪练在线旁），`.chat-reset` 新样式 + hover 态；删 `.reset` 死样式 |
| 3 | 阅读标题下 readMeta 占位符「—」像残留杂线 | 初始值改空 + `#readMeta:empty{display:none}` |
| 4 | 阅读页空态仅一行孤字、大片空白 | 升级为引导卡：🌱 图标 + 文案 + 「✨ 帮我挑一篇」按钮（直调 recommendNext） |
| 5 | 顶栏「词汇 47/6,500」语义混搭（词卡数 vs 目标词汇量） | 删除该 span 与 renderTop 写入；等级进度条本就承担 A2→B2 进度；词卡数保留在「词库 47 词」徽章 |
| 6 | 成长页 4 卡 3+1 孤行、版心 860px 与其他页不一致 | minmax 230→300px（728px 容器内自然成 2×2），版心 860→760px 对齐考级页 |
| 7 | 顶栏「连续 1 天 🔥」与账本条重复 | 账本条改「💬 累计 N 轮对话」（chatTotalBadge，取 stats.dialogue_count） |

**刻意不改**：对话区消息贴底、上方留白是聊天应用标准 UX（参照 iMessage/WhatsApp），不重构。

## 改动文件

- `frontend/index.html`：chat-h 加重置按钮、foot 移除按钮、readMeta 空值、read-placeholder 引导卡、删 vocab-count、streakBadge→chatTotalBadge；css v24 / js v30
- `frontend/styles.css`：对比度、.chat-reset、#readMeta:empty、.read-placeholder 重构、删 .vocab-count/.reset 死样式、growth 网格与版心
- `frontend/app.js`：renderTop 删 vocabCount 行、renderLedger 改 chatTotalBadge

## 验收（真机全过）

- [x] 主视图：重置按钮在卡头、页脚无按钮、vocabCount 移除、中文白色、账本「💬 累计 6 轮对话」、顶栏 streak 保留（fix-main.png）
- [x] 阅读页：杂线消失、空态引导卡 + 挑一篇按钮渲染成功（点击后加载"租房"B1 文章，readMeta 有值才显示）（fix-read.png）
- [x] 成长页：2×2 网格（358px×2 列实测）、版心 760px（fix-growth.png）
- [x] 回归：重置按钮新位置点击 → 气泡回 3 条种子 + 持久化清 0；`node --check` 通过；无 streakBadge/vocabCount 残留引用
