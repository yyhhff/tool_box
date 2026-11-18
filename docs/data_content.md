# 数据地图（data_content）

> **用途**：查"数据从哪来、到哪去、什么格式"。
> **维护规则**：任何工具新增/变更输入输出文件后，必须同步登记本文件（见 AGENTS.md 硬性规则）。
> 最后更新：2026-11-18

## 数据目录约定

| 目录 | 用途 | 是否入 git |
|------|------|-----------|
| `data/input/` | 各工具的输入数据（小型样例数据建议入库，便于复现） | 是 |
| `data/output/` | 工具产出的结果文件 | 否（.gitignore） |
| `data/cache/` | 临时缓存，可随时删除，不影响正确性 | 否（.gitignore） |
| `tools/<工具名>/` | 工具自身代码与 README（不放数据） | 是 |

**文件命名规范**：`<工具名>_<内容>.<扩展名>`，如 `pdf_merge_input_list.txt`。

**登记原则**（TASK-0025 起生效）：说明列只记"生产者→消费者 + 要点"；数据口径、契约、安全红线等详情写在对应工具内部文档（说明列给指针），本表不承载长说明。

## 数据文件登记表

### xhs_crawler

| 数据/文件 | 路径 | 格式 | 生产者 | 消费者 | 说明 |
|-----------|------|------|--------|--------|------|
| 小红书登录态 | data/cache/xhs_state.json | JSON（浏览器 storage_state） | xhs_crawler：扫码确认登录或 Cookie 导入后保存 | xhs_crawler | 失效时重新扫码/导入；不入 git |
| 博文归档结果 | data/output/xhs_crawler/<博主ID>_<start>_<end>/ | JSON/CSV/MD + images/ | xhs_crawler | 人 | 不入 git；notes.md 可直接阅读 |
| 抓取运行日志 | data/output/xhs_crawler/<博主ID>_<start>_<end>/run.log | 文本（追加式） | xhs_crawler | 人 | 事后排查风控/失败用；不入 git |

### annual_report_reader

| 数据/文件 | 路径 | 格式 | 生产者 | 消费者 | 说明 |
|-----------|------|------|--------|--------|------|
| 年报带读用户配置 | data/input/annual_report_reader/config.json | JSON（top_n、行业筛选、overrides、last_run） | annual_report_reader：Web/CLI 自动保存；可手工编辑 | annual_report_reader | 入 git；"记忆"载体之一，记录上次运行范围 |
| 年报带读分析索引 | data/output/annual_report_reader/index.json | JSON（每公司：行业/年份/状态/报告路径/时间） | annual_report_reader | annual_report_reader（增量跳过依据）+ 人 | 不入 git；"记忆"载体之二 |
| 单公司带读报告 | data/output/annual_report_reader/companies/<代码>_<年份>/report.md | Markdown | annual_report_reader（GLM 生成） | 人 / Web 报告阅读 | 不入 git；财务数字提取自年报原文并标页码 |
| 行业对比报告 | data/output/annual_report_reader/industries/<行业>_<年份>.md | Markdown | annual_report_reader（≥2 家完成后生成） | 人 / Web 报告阅读 | 不入 git |
| 原始年报 PDF | data/output/annual_report_reader/pdfs/<代码>_<年份>.pdf | PDF | fetcher：巨潮资讯网下载 | extractor | 不入 git；长期保留，已存在则复用，可手动放入兜底（TASK-0012 起改此路径） |
| 行业快照 | data/cache/annual_report_reader/industry_snapshot.json | JSON（31 行业 × 市值前 8 候选） | industry.py：申万成分（akshare）+ 腾讯行情 | industry.select / Web | 不入 git；接口失效时选股回退此快照 |
| 巨潮 orgId 映射 | data/cache/annual_report_reader/orgids.json | JSON（代码 → orgId） | fetcher：巨潮 topSearch | fetcher | 不入 git；缓存避免重复查询 |
| 半年报分析台六张数据表 | data/output/h1_2026/h1_2026_{market,chain_link,double_growth,chain_company,watch,macro}.csv | CSV（UTF-8 BOM） | data-engineer：真实检索 + 授权数据回填 | 资料库 database 节点 + 单页 HTML | 不入 git；行数与表头/口径见 h1_2026_docs/CONTRACT.md |
| 半年报分析台快照 | data/output/h1_2026/SNAPSHOT_DATA.json | JSON（六键对象数组） | data-engineer：与六 CSV 同步生成 | h1_2026.html 内嵌离线快照 | 不入 git；SDK 不可用时兜底渲染 |
| 半年报分析台单页 | tools/annual_report_reader/h1_2026.html | HTML（单文件全内联） | frontend-dev + 总指挥回填数据/DB ID | 资料库 page `yW9mpdOLsoy5AlL7dUALWI` + 发布页 | 入 git；资源零外链、数据全内嵌、含免责声明；使用说明见 h1_2026_docs/USER_GUIDE.md |
| 半年报分析台文档集 | tools/annual_report_reader/h1_2026_docs/（CONTRACT/DATA_FINANCE/DATA_MACRO/QA_REPORT/USER_GUIDE/GAP_ANALYSIS/REALTIME_AND_COST.md） | Markdown | pm / 数据研究员 / QA / 架构师 / 产品文档 | 全角色 + 人 | 入 git；数据契约与口径、35 条验收、对标差距、实时化与成本方案，详情见各文件 |

### service_manager

| 数据/文件 | 路径 | 格式 | 生产者 | 消费者 | 说明 |
|-----------|------|------|--------|--------|------|
| 服务状态记录 | data/cache/service_manager/services.json | JSON | service_manager：Web 界面操作后保存 | service_manager | 入 git；记录各服务运行状态与进程ID |
| 服务日志 | data/cache/service_manager/logs/<service_id>.log | 文本（追加式） | 各工具 server.py 输出 | service_manager：日志查看 | 不入 git；排查服务问题用 |

### french-learner（独立 Git 仓库；详情见其 README.md 与 docs/）

| 数据/文件 | 路径 | 格式 | 生产者 | 消费者 | 说明 |
|-----------|------|------|--------|--------|------|
| 呀呀法语对话脚本（历史原型） | tools/french-learner/demo.html（内嵌 SCENARIOS） | JS 对象 | 内置于 Demo | demo.html 前端交互 | 入 git；历史单文件原型，保留供对照 |
| 呀呀法语应用数据库 | tools/french-learner/backend/data/yaya.db | SQLite（9 表） | backend/seed.py 首次启动灌入；seed_input.py 同步语料；app.py 运行时读写 | backend/app.py API | 不入 git；删库重启自动重建种子数据；表结构见其 docs/ARCHITECTURE*.md |
| 呀呀法语架构与章程 | tools/french-learner/docs/ | Markdown（架构契约、章程、QA 报告等） | 架构师 / PM / 测试 | 前后端开发、独立验收 | 入 git；契约 v1/v2、定级/考级契约与安全红线、QA 报告，详情见各文件 |
| 呀呀法语分级语料 | tools/french-learner/data/input/texts.json | JSON（21 篇，A2/B1/B2 各 7，157 生词） | 内容角色原创编写 | seed_input.py 启动加载入 input_* 三表 | 入 git；原创教学示例，CEFR 为教学标注；改动需重启服务同步 |
| 呀呀法语定级题库 | tools/french-learner/data/input/assessment_questions.json | JSON（12 题，A2/B1/B2 各 4） | 内容角色原创编写 | backend/assessment.py 启动加载、进程内缓存 | 入 git；原创教学示例非官方真题；answer_idx/explanation_zh 仅服务端判分用，GET 零下发；详见其 docs/ARCHITECTURE_PLACEMENT.md；改动需重启服务同步 |
| 呀呀法语考级模拟卷 | tools/french-learner/data/input/exam_papers.json | JSON（2 套原创卷 delf_b2_01/tcf_b2_01，每套 8 题） | 内容角色原创编写 | backend/exam.py 启动加载、进程内缓存 | 入 git；原创模拟非官方真题；四类敏感字段 GET 白名单投影零下发、重复交卷不幂等；详见其 docs/ARCHITECTURE_EXAM.md；改动需重启服务同步 |
| 呀呀法语 Whisper 模型缓存 | C:\Users\Karen\.cache\huggingface\hub\models--Systran--faster-whisper-tiny | 模型权重（~75MB） | faster-whisper 首次加载自动下载 | asr_service/server.py | 不入 git；已下载则离线可用；换模型改 YAYA_ASR_MODEL 环境变量 |

### workbuddy-multi-account

| 数据/文件 | 路径 | 格式 | 生产者 | 消费者 | 说明 |
|-----------|------|------|--------|--------|------|
| WorkBuddy 多账号管理数据 | tools/workbuddy-multi-account/workbuddy.db | SQLite（accounts/chat_messages/checkin_records/settings 四表） | server.py：启动时自动初始化 | server.py + 前端 | 不入 git（.gitignore）；含测试/账号数据；结构定义在 models.py，删库后重启自动重建 |
| WorkBuddy 凭据快照 | tools/workbuddy-multi-account/credentials/<account_id>.info | JSON（客户端凭据原样复制，含 accessToken） | account_service.bind_account：添加账号时从客户端凭据文件复制 | workbuddy_client：构建 Bearer 请求 | 不入 git（.gitignore）；**含登录态 token，严禁入库**；失效后在客户端重新登录并调 POST /api/accounts/{id}/refresh |
| WorkBuddy 运行日志 | data/output/workbuddy-multi-account/*.log | 文本（追加式） | server.py 输出 | 人 | 不入 git；排查问题用 |

## 数据流示意

```
data/input/ ────> tools/<工具> ────> data/output/
                        │
                        └──────────> data/cache/（临时，可删）
```

## 登记示例（虚构，供参考格式）

| 数据/文件 | 路径 | 格式 | 生产者 | 消费者 | 说明 |
|-----------|------|------|--------|--------|------|
| 待合并文件清单 | data/input/pdf_merge_list.txt | txt（每行一个路径） | 人工准备 | pdf_merge | UTF-8 |
| 合并结果 | data/output/merged.pdf | PDF | pdf_merge | 人 | 每次运行覆盖 |
