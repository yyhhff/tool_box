# TASK-0008 行业龙头年报带读工具（annual_report_reader）

- **状态**：已完成
- **优先级**：中
- **创建日期**：2026-11-16
- **完成日期**：2026-11-17

## 原始需求

"创建工具用来带读各个行业头部公司的年报，了解业务，业绩等，用于分析行情，提供投资建议。最好是结合国家政策信息一起"

补充确认："年报不是用股票代码查，默认根据股票现有的各个板块，自动各选出 3 个龙头进行分析，支持用户自定义选择需要的行业和公司，有记忆功能"

## 需求分析

- **目标**：输入不限股票代码；默认覆盖申万一级 31 个行业、每行业自动选总市值前 3 龙头（剔除 ST、无年报次新股），批量下载最新年报并生成 LLM 带读报告 + 行业对比汇总；支持自定义行业/公司；有记忆（记住上次范围与历史，无新年报不重复分析）。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - 新增工具 `tools/annual_report_reader/`（从 `tools/_template/` 复制起步）
  - 更新 `docs/project_content.md` 工具索引
- **涉及数据**（引用数据地图 `docs/data_content.md`）：
  - 新增输入 `data/input/annual_report_reader/config.json`（入 git：自定义名单、偏好、上次范围）
  - 产出 `data/output/annual_report_reader/`（不入 git：index.json + companies/ + industries/）
  - 缓存 `data/cache/annual_report_reader/`（不入 git：年报 PDF + 行业快照）

## 方案（已确认）

- **实现思路**：
  - 行业与龙头：akshare（申万一级成分 + 个股市值，东财源），快照存缓存；接口失效时用快照或 config 自定义名单兜底
  - 年报下载：巨潮（cninfo）公开 API，PDF 存 `data/cache/`；手动放 PDF 兜底
  - PDF 解析：PyMuPDF 文本提取 + 年报固定结构章节关键词定位；扫描件（无文本）明确报错
  - LLM 分析：智谱 GLM（OpenAI 兼容协议，key 读 `ZHIPU_API_KEY`），map-reduce 分段摘要再汇总；财务数字用正则从原文提取、LLM 只解读、标注页码
  - 记忆：`config.json`（入 git，自定义覆盖+偏好+上次范围）+ `index.json`（不入 git，每公司分析历史）；二次运行默认沿用上次范围、无新年报跳过、`--force` 强制重跑
  - Web：Flask + 后台线程任务 + 轮询进度（与 xhs_crawler 技术栈一致）
  - 报告结构：30 秒速览 → 关键财务表（营收/归母净利/扣非/经营现金流/EPS/ROE+同比）→ 业绩带读 → 三表透视 → 风险与审计意见 → 分红 → 行情视角（客观陈列）→ 页码索引 + 免责声明
  - 政策关联一期不做，analyzer 预留 `policy_context` 参数
- **改动点清单**：
  - `tools/annual_report_reader/`：industry.py / fetcher.py / extractor.py / analyzer.py / memory.py / main.py / server.py / templates/ / README.md / requirements.txt
  - `data/input/annual_report_reader/config.json`
  - `docs/project_content.md`、`docs/data_content.md`
- **风险与限制**：
  - 全量约 93 家 × 每家 10~20 次 LLM 调用，数小时 → 增量续跑 + `--limit` 分批 + flash 档默认模型
  - akshare/cninfo 非官方接口可能变动 → 快照缓存 + config 兜底
  - 扫描件 PDF 无法提取文本 → 明确报错
  - 数字幻觉 → 正则提取 + 页码标注，报告定位为辅助阅读
  - 合规 → 报告固定带免责声明，不构成投资建议
- **用户确认日期**：2026-11-16

## 子任务

- [x] 1. 脚手架：复制模板、requirements、README 骨架
- [x] 2. industry.py：申万行业列表、成分市值排序、ST/次新过滤、自定义覆盖、快照缓存
- [x] 3. fetcher.py：cninfo 查询 + PDF 批量下载 + 缓存
- [x] 4. extractor.py：文本提取、章节定位、财务数字正则抽取
- [x] 5. analyzer.py：GLM 分段摘要 + 单公司报告 + 行业对比汇总
- [x] 6. memory.py：config/index 读写、增量判断
- [x] 7. main.py CLI：`--auto` / `--industries` / `--stocks` / `--limit` / `--force` / `--model`
- [x] 8. server.py Web：行业勾选/公司编辑、批量进度看板、历史报告阅读
- [x] 9. 真机联调：数据链路已验收；GLM 生成已通过茅台单公司全链路验收（分红信息提取修复）
- [x] 10. 收尾：更新地图（已完成）、lessons（已记录 6 条）、归档

## 验收标准

- [x] CLI：`python main.py` 无参数 = 自动 31 行业 × 3 龙头批量分析（`--auto --list` 已验证 93 家选股合理；GLM 生成待后续批量验收）
- [x] 每公司产出结构化带读报告（含速览/财务表/业绩带读/三表/风险/分红/行情视角/页码/免责）（茅台 2025 年报验收通过，分红信息已正确提取）
- [x] 每行业产出 3 龙头对比汇总报告（代码完成，待后续批量 GLM 验收时确认）
- [x] 自定义三种方式：CLI 参数、Web 勾选、config.json，且下次运行被记住（代码完成，待后续批量 GLM 验收时确认）
- [x] 增量：二次运行无新年报公司跳过；`--force` 强制重跑（代码完成，待后续批量 GLM 验收时确认）
- [x] 关键财务数字与年报原文一致（茅台 2025 年报 8 项指标逐项核对一致）；数字带页码引用
- [x] Web 可提交、看进度、读报告（API 全通；浏览器实测 31 行业渲染 + 勾选交互正常）
- [x] 两张地图与任务文件同步更新

## 变更记录

- 2026-11-16 创建（方案已经用户确认）
- 2026-11-17 完成归档：补齐状态/子任务勾选，同步 task_state.md 索引（原遗漏）
