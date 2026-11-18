# 项目地图（project_content）

> **用途**：接到需求后先查本文件，定位改动点，再动手。
> **维护规则**：新增/删除/变更任何工具或目录后，必须同步更新本文件（见 AGENTS.md 硬性规则）。
> 最后更新：2026-11-18

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
│   └── lessons.md            # 经验库：跨项目通用经验
├── tasks/
│   ├── task_state.md         # 任务看板（活动任务索引 + 归档记录）
│   ├── _TEMPLATE.md          # 任务文件模板
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

| 工具 | 路径 | 入口 | 语言 | 功能一句话 | 状态 |
|------|------|------|------|-----------|------|
| xhs_crawler | tools/xhs_crawler/ | server.py（Web）/ main.py（CLI） | Python | 爬取指定博主、指定时间范围内的小红书博文，本地 Web 界面 + CLI | 待真机验收 |
| annual_report_reader | tools/annual_report_reader/ | server.py（Web，默认 5001）/ main.py（CLI）/ h1_2026.html（单页分析台） | Python + HTML/JS | 申万一级 31 行业 × 每行业市值前 3 龙头批量年报带读（GLM），自定义行业/公司，有记忆增量续跑；新增「2026 A股半年报分析台」六板块单页（资料库 SDK + 内嵌快照双数据源） | 核心链路已验收，GLM 生成待验收；半年报分析台已发布 |
| service_manager | tools/service_manager/ | server.py（Web，默认 5002） | Python | 启动、重启、关闭服务，查看服务状态与日志 | 待真机验收 |
| french-learner | tools/french-learner/ | start.bat（一键自检+启动，推荐）+ uvicorn app:app（后端 8000）+ asr_service/server.py（本地语音 8010）/ frontend/index.html（可离线直开） | Python + HTML/JS | 呀呀法语：Web 法语学习产品，重述式 AI 口语陪练（智谱 GLM 可插拔 + 降级）+ i+1 分级输入流（21 篇）+ 本地 Whisper 语音识别 + 神经语音朗读 + 生词卡 + SM-2 复习；独立 Git 仓库（已关联远程 `yyhhff/french-learner`，SSH over 443），六角色三波协作 | 阶段二完成，独立 QA 109/109 通过；已接入本机 `ZHIPU_API_KEY` 真实验收；对话双方均支持 🔊 标准发音 + 中文翻译；一键启动脚本 start.bat（TASK-0020）真机三场景验证通过，待上级验收 |

## 常见需求 → 改动点定位

| 需求类型 | 去哪里改 | 需要同步更新 |
|----------|----------|--------------|
| 新增一个小工具 | 复制 `tools/_template/` → `tools/<工具名>/` | 本文件工具索引、`data_content.md` |
| 修改某工具逻辑 | `tools/<工具名>/` | 视情况更新工具 README |
| 修改工具的输入/输出 | 工具目录 + `data/` 下对应文件 | `data_content.md` |
| 抽取/新增公共函数 | `shared/` | 本文件目录职责（如有新目录） |
| 调整 AI 工作流/规范 | `AGENTS.md` | 无 |
| 更新文档/地图 | `docs/` | 结构变更必须同步地图 |
| 任务管理 | `tasks/task_state.md` + `tasks/active/` | 完成后归档 |
| 沉淀/查阅通用经验 | `docs/lessons.md` | 收录标准见该文件头 |

## 新工具接入流程

1. 复制 `tools/_template/` 为 `tools/<工具名>/`（小写英文 + 连字符命名）
2. 填写工具 `README.md`（用途、用法、输入输出、依赖）
3. 实现逻辑，数据读写遵循 `data/` 目录约定（见数据地图）
4. 更新本文件"工具索引" + `docs/data_content.md` 数据登记
5. 按 AGENTS.md 工作流登记任务，完成后提交 git
