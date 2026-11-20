# 项目地图（project_content）

> **用途**：接到需求后先查本文件，定位改动点，再动手。
> **维护规则**：新增/删除/变更任何工具或目录后，必须同步更新本文件（见 AGENTS.md 硬性规则）。
> 最后更新：2026-11-19

## 地图维护原则（TASK-0025 起生效）

1. 本文件是**全局索引**：每个工具条目 ≤ 2 行（功能一句话 + 状态 + 详情指针），不承载详情。
2. 工具/产品的详情（功能说明、架构契约、QA 报告、使用说明）一律写在 `tools/<工具名>/` 的 README.md 或 docs/ 内，本文件只留指针。
3. 条目描述超过 2 行视为缺陷：先把多出的内容下沉到工具内部文档，再瘦身本文件。
4. 数据地图（`docs/data_content.md`）同理：说明列只记要点，口径/契约详情登记在工具内部文档。

## 目录结构

```
tool_box/
├── README.md                 # 项目总说明（人读）
├── AGENTS.md                 # AI 协作规范：任务工作流（模型读）
├── .gitignore
├── docs/
│   ├── project_content.md    # 本文件：项目地图
│   ├── data_content.md       # 数据地图
│   ├── git_guide.md          # Git 使用命令文档
│   ├── night_ops.md          # 夜班章程（23:00-09:00 无人值守自动迭代，TASK-0028）
│   └── lessons.md            # 经验库：跨项目通用经验
├── tasks/
│   ├── task_state.md         # 任务看板（活动任务索引 + 归档记录）
│   ├── next_id.txt           # 任务编号单一计数器（领号取当前值并 +1 写回）
│   ├── _TEMPLATE.md          # 任务文件模板（验收三态 + 状态取值）
│   ├── night_backlog.md      # 夜班任务池（每晚巡库刷新）
│   ├── night_reports/        # 夜报目录（每晚收口产物）
│   ├── active/               # 进行中的任务文件
│   └── archive/              # 已完成任务归档（按 YYYY-MM 分目录）
├── tools/
│   ├── xhs_crawler/          # 小红书博文爬取（详见下方工具索引）
│   └── _template/            # 新工具脚手架（README + main.py）
├── shared/                   # 跨工具公共代码
└── data/
    ├── input/                # 输入数据（入 git）
    ├── output/               # 工具产出（不入 git）
    └── cache/                # 缓存（不入 git）
```

## 目录职责

| 目录 | 职责 | 说明 |
|------|------|------|
| `docs/` | 项目文档、地图与经验库 | 地图是需求的定位入口，必须与实际同步 |
| `tasks/active/` | 进行中的任务文件 | 一任务一文件，从 `_TEMPLATE.md` 复制 |
| `tasks/archive/` | 已完成任务归档 | 按 `YYYY-MM/` 分目录存放 |
| `tools/<工具名>/` | 每个小工具的全部代码 | 互相独立，可单独运行 |
| `tools/_template/` | 新工具脚手架 | 复制后改造，不要直接在模板里开发 |
| `shared/` | 跨工具公共代码 | 只放被 ≥2 个工具使用的代码 |
| `data/` | 全局数据 | 三个子目录职责见数据地图 |

## 工具索引

| 工具 | 路径 | 入口 | 功能一句话 | 状态 | 详情 |
|------|------|------|-----------|------|------|
| xhs_crawler | tools/xhs_crawler/ | server.py（Web）/ main.py（CLI） | Python 爬取指定博主、指定时间范围内的小红书博文，本地 Web 界面 + CLI | 待真机验收 | tools/xhs_crawler/README.md |
| annual_report_reader | tools/annual_report_reader/ | server.py（Web，:5001）/ main.py（CLI）/ h1_2026.html（单页分析台） | 行业龙头年报带读（申万一级 31 行业龙头，GLM 或 --local 零 GLM 本地模式，记忆增量续跑）；扩展「2026 A股半年报分析台」六板块单页 | 31行业本地带读完成29家+横向对比（TASK-0046）；半年报分析台已发布 | README.md；半年报详见 h1_2026_docs/USER_GUIDE.md |
| service_manager | tools/service_manager/ | server.py（Web，:5002） | Python 启动、重启、关闭服务，查看服务状态与日志 | 待真机验收 | tools/service_manager/README.md |
| french-learner | tools/french-learner/ | start.bat 一键启动（后端 :8000 被占自动回退 8001-8019 + 本地语音 :8011；可离线直开 frontend/index.html） | 呀呀法语：Web 法语学习产品（重述式 AI 口语陪练 + i+1 分级输入 + CEFR 定级 + 生词卡 SM-2 复习 + 读音规则 + DELF/TCF 冲刺 + 面客建设里程图 + 留存激励 + 使用反馈收集）；独立 Git 仓库 | 阶段 0-4 及读音/成长/成就/留存反馈均已验收；面客路线图 6/6 点亮；Wave 0 地基已合并（后端 12 routers + 前端 js/ ES modules + worktree 脚本，A/B 行为一致） | tools/french-learner/README.md（总纲/认领看板见 docs/MASTER_PLAN.md；架构见 docs/ARCHITECTURE.md；Roadmap/FEEDBACK 见对应 docs） |
| workbuddy-multi-account | tools/workbuddy-multi-account/ | server.py（FastAPI，bind-first 自定端口，专属段 8010-8029，事实文件 data/cache/workbuddy-multi-account/port.json） | WorkBuddy 多账号管理：多账号登录、自动签到、聊天记录合并与迁移、切号任务快照迁移、账号删除，Web 管理面板 | 进行中（端口根治 TASK-0052；任务迁移诚实降级 TASK-0056；此前 TASK-0037/0041/0043/0044/0045 已完成） | tools/workbuddy-multi-account/README.md |

## 常见需求 → 改动点定位

| 需求类型 | 去哪里改 | 需要同步更新 |
|----------|----------|--------------|
| 新增一个小工具 | 复制 `tools/_template/` → `tools/<工具名>/` | 本文件工具索引、`data_content.md` |
| 修改某工具逻辑 | `tools/<工具名>/` | 工具 README（详情写工具内部文档） |
| 工具新增功能/特性 | 工具代码 + 工具内 README/docs | 本文件索引行（一行内更新状态） |
| 修改工具的输入/输出 | 工具目录 + `data/` 下对应文件 | `data_content.md` |
| 抽取/新增公共函数 | `shared/` | 本文件目录职责（如有新目录） |
| 调整 AI 工作流/规范 | `AGENTS.md` | 无 |
| 夜班自动化调整（NightOps） | `docs/night_ops.md`（夜间 agent 无权修改章程，须用户白天确认） | 无 |
| 更新文档/地图 | `docs/` | 结构变更必须同步地图 |
| 任务管理 | `tasks/task_state.md` + `tasks/active/` | 完成后归档 |
| 沉淀/查阅通用经验 | `docs/lessons.md` | 收录标准见该文件头 |

## 新工具接入流程

1. 复制 `tools/_template/` 为 `tools/<工具名>/`（小写英文 + 连字符命名）
2. 填写工具 `README.md`（用途、用法、输入输出、依赖）
3. 实现逻辑，数据读写遵循 `data/` 目录约定（见数据地图）
4. 更新本文件"工具索引"（一行索引，详情写进工具 README）+ `docs/data_content.md` 数据登记
5. 按 AGENTS.md 工作流登记任务，完成后提交 git
