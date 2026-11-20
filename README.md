# tool_box 工具箱

存放各类小工具的个人项目。每个工具独立放在 `tools/` 下，互不干扰、可独立运行。

## 快速导航

| 想做什么 | 看哪里 |
|----------|--------|
| 了解项目结构、定位改动点 | [docs/project_content.md](docs/project_content.md)（项目地图） |
| 了解数据文件与流向 | [docs/data_content.md](docs/data_content.md)（数据地图） |
| 查看当前任务进度 | [tasks/task_state.md](tasks/task_state.md)（任务看板） |
| Git 操作指南 | [docs/git_guide.md](docs/git_guide.md) |
| 沉淀/查阅通用经验（跨项目可复用） | [docs/lessons.md](docs/lessons.md)（经验库） |
| AI 助手协作工作流 | [AGENTS.md](AGENTS.md) |

## 目录结构

```
tool_box/
├── README.md                 # 项目总说明（人读）
├── AGENTS.md                 # AI 协作规范：任务工作流（模型读）
├── .gitignore
├── docs/
│   ├── project_content.md    # 项目地图：结构 + 改动点定位
│   ├── data_content.md       # 数据地图：数据文件 + 流向
│   ├── git_guide.md          # Git 使用命令文档
│   ├── night_ops.md          # 夜班章程（23:00-09:00 无人值守自动迭代）
│   ├── night_ops_user_guide.md  # 夜班使用说明（人读）
│   ├── lessons.md            # 经验库：跨项目可复用的通用经验
│   └── workbuddy_*.md 等     # WorkBuddy 分析与设计文档
├── tasks/
│   ├── task_state.md         # 任务看板（活动任务索引 + 归档记录）
│   ├── next_id.txt           # 任务编号单一计数器（领号取当前值并 +1 写回）
│   ├── _TEMPLATE.md          # 任务文件模板
│   ├── night_backlog.md      # 夜班任务池（每晚巡库刷新）
│   ├── night_reports/        # 夜报目录（每晚收口产物）
│   ├── active/               # 进行中的任务文件
│   └── archive/              # 已完成任务归档（按 YYYY-MM 分目录）
├── tools/
│   ├── xhs_crawler/          # 小红书博文爬取工具
│   ├── annual_report_reader/ # 行业龙头年报带读工具
│   ├── service_manager/      # 服务管理工具（启动/重启/关闭服务）
│   ├── french-learner/       # 呀呀法语：Web 法语学习产品（独立 Git 仓库）
│   ├── workbuddy-multi-account/  # WorkBuddy 多账号管理工具
│   └── _template/            # 新工具脚手架
│       ├── README.md
│       └── main.py
├── shared/                   # 跨工具公共代码（≥2 个工具复用时才放）
└── data/
    ├── input/                # 输入数据（入 git）
    ├── output/               # 工具产出（不入 git）
    └── cache/                # 缓存，可随时删（不入 git）
```

## 新建一个工具

1. 复制 `tools/_template/` → `tools/<工具名>/`（小写英文 + 连字符命名）
2. 修改工具的 `README.md` 与 `main.py`
3. 更新 `docs/project_content.md` 的工具索引、`docs/data_content.md` 的数据登记
4. 提交 git（见 [docs/git_guide.md](docs/git_guide.md)）

## 开发约定

- 一个工具一个目录，可独立运行，不依赖其他工具；公共函数放 `shared/`
- 数据读写只碰 `data/` 目录，不散落在其他位置
- 使用 AI 助手开发时，遵守 [AGENTS.md](AGENTS.md) 的任务工作流
