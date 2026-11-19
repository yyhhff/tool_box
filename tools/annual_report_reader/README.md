# annual_report_reader

行业龙头年报带读：默认覆盖申万一级 31 个行业，每行业自动选总市值前 3 龙头，批量下载最新年报 PDF，用智谱 GLM 生成分公司带读报告与行业对比汇总。支持自定义行业/公司，并有记忆（记住上次范围与历史，无新年报自动跳过）。

## 用法

```bat
:: 全部 31 行业 × 每行业前 3 龙头（无参数默认沿用上次范围；首次为全量）
python main.py

:: 只分析指定行业 / 指定公司
python main.py --industries 银行,食品饮料
python main.py --stocks 600519,000858

:: 只列出将分析的公司，不实际运行
python main.py --list

:: 其他：--top 3（每行业龙头数）--limit 2（只跑前 N 家）--force 强制重跑 --model glm-4-flash
python main.py --auto --limit 2

:: Web 界面（勾选行业、看进度、读报告）
python server.py

:: 本地分析模式（零 GLM、无需 ZHIPU_API_KEY）：31行业龙头带读 + 跨行业横向对比
python main.py --auto --top 1 --local --force
:: 只跑指定行业/公司也支持
python main.py --stocks 600519,002594 --local --force
```

`--local` 走 `analyzer_local.py`：财务数字由 `extractor` 从年报原文提取（带 PDF 页码），
带读文字由本地规则+模板生成，不调用任何大模型、不读取 `ZHIPU_API_KEY`。
失败/无年报的公司如实标注跳过，不编造数据。报告末尾标注"分析方式：本地程序（未调用大模型）"。

前置：设置环境变量 `ZHIPU_API_KEY`（智谱开放平台申请）。Windows 下若已用 `setx` 设置但当前终端/服务读不到（setx 不更新已运行进程），代码会自动从用户级注册表读取并回填，无需重开终端。

## 输入 / 输出

- 输入：`data/input/annual_report_reader/config.json`（自定义名单/偏好/上次范围，入 git，登记到 docs/data_content.md）
- 数据源：akshare（申万行业成分 + 个股市值）、巨潮资讯网（年报 PDF）
- 输出：`data/output/annual_report_reader/`（**pdfs/ 原始年报，持久保留**、index.json 记忆索引 + companies/ 单公司报告 + industries/ 行业汇总，不入 git）
- 缓存：`data/cache/annual_report_reader/`（行业快照、orgId 映射，不入 git；年报 PDF 已移出缓存到 output/pdfs/）

## 依赖

- Python 3.10+；`pip install -r requirements.txt`
- akshare / pymupdf / openai / flask / requests

## 扩展：2026 A 股半年报分析台

- 入口：`h1_2026.html`（单文件全内联单页，可离线直开；六板块 + 四级联动，资料库 SDK + 内嵌快照双数据源）
- 文档：`h1_2026_docs/`（CONTRACT 数据契约与口径、USER_GUIDE 使用说明、QA_REPORT 验收、GAP_ANALYSIS 对标差距、REALTIME_AND_COST 实时化与成本方案，详情见各文件）
