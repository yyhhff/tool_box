# TASK-0012 年报章节定位多格式修复 + 原始 PDF 持久化保存

- **状态**：已完成
- **优先级**：高
- **创建日期**：2026-11-17
- **完成日期**：2026-11-17

## 原始需求

"这个修复方案可以。每次爬取的原年报文件，需要下载保存到本地。"

承接上一轮日志分析：平安/人寿/中信证券 3 家非银金融年报解析失败（`章节定位失败`，因目录无"第X节"格式）；用户确认章节定位修复方案，并新增要求：原始年报 PDF 作为正式产出持久保存到本地。

## 需求分析

- **目标**：
  1. 让章节定位支持非"第X节"模板（数字编号+标题、纯标题独立行），修复 3 家失败。
  2. 原始年报 PDF 从"缓存"改到"正式产出"目录长期保存，已有文件复用不重复下载。
- **改动点**（引用 `docs/project_content.md` 工具索引）：
  - `tools/annual_report_reader/extractor.py`（章节定位）
  - `tools/annual_report_reader/fetcher.py`（PDF 保存路径）
  - `tools/annual_report_reader/main.py`（pdf_path 记录随路径变化，自动来自 fetcher 返回值）
- **涉及数据**（引用 `docs/data_content.md`）：
  - 原：`data/cache/annual_report_reader/pdfs/<代码>_<年份>.pdf`（缓存，不入 git）
  - 新：`data/output/annual_report_reader/pdfs/<代码>_<年份>.pdf`（正式产出，不入 git，长期保留、可手动放入兜底）
  - 需更新 `docs/data_content.md` 登记表

## 方案（已确认）

- **实现思路**：
  - 章节定位：保留现有"第X节"识别路径；新增从目录页提取章节候选，在正文用「数字编号+标题」和「纯标题独立行」定位；用常见章节关键词集合约束候选，排除"第X季度/第一大股东"等噪声；确保茅台不回归。
  - PDF 持久化：`PDF_DIR` 指向 `data/output/annual_report_reader/pdfs/`；已存在且校验通过则复用（同 `--force` 语义：强跑分析不重下 PDF）；迁移现有 4 份 PDF 到新目录。
- **改动点清单**：
  - `tools/annual_report_reader/extractor.py`、`fetcher.py`
  - `data/output/annual_report_reader/pdfs/`（迁移 4 份 PDF）
  - `docs/data_content.md`（数据登记更新）
  - `tools/annual_report_reader/README.md`（视情况）
  - `docs/lessons.md`（章节模板差异经验）
- **风险与限制**：
  - 纯标题行定位需在目录页提取候选 + 正文多次出现时取首次章节首页，可能误判页眉重复——用关键词白名单和"页码递增"约束缓解。
  - PDF 移出 cache 后，旧缓存路径若有残留不影响（新代码只读 output 路径）；`.gitignore` 已 ignore `data/output/`，无需改。
  - 真实 GLM 全链路分析耗时（数分钟/家）——本轮验证以"定位到章节 + 可选单家真实跑通"为主。
- **用户确认日期**：2026-11-17

## 子任务

- [x] 1. 修复 chapter_ranges 支持多格式（标准第X节优先 + 回退数字编号/纯标题）
- [x] 2. PDF 保存路径改为 data/output/annual_report_reader/pdfs 并迁移现有 4 份
- [x] 3. 更新数据地图 data_content.md 的 PDF 路径登记
- [x] 4. 验证 4 份年度报告都能定位章节、PDF 持久化与复用正确

## 验收标准

- [x] 茅台（第X节）定位不回归（8 节）；平安 15 节 / 人寿 12 节 / 中信证券 12 节，均 >=3
- [x] 原始 PDF 持久化到 data/output/annual_report_reader/pdfs/，4 份文件可达；已存在时复用不重复下载（download_pdf 验证返回缓存路径、未触发网络）
- [x] data_content.md 的 PDF 路径登记与实际一致
- [x] 编译通过；从 output 新路径解析章节正常；平安 build_context 得 15 块 + 真实 GLM map 调用成功
  - 说明：全量 GLM 分析（370 页多次调用）超出单次测试超时，属已知耗时非缺陷；核心链路（定位→上下文→单次 LLM）已验证

## 变更记录

- 2026-11-17 创建（方案已经用户确认）
- 2026-11-17 完成：extractor 加多格式章节定位（标准优先+通用回退），fetcher PDF 改存 output/pdfs 并迁移 4 份，更新数据地图/README/lessons；4 份年报定位全部通过，真实 GLM 调用成功
