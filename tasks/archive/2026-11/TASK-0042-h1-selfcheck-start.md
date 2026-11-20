# TASK-0042 h1_2026 分析台自检启动脚本

- **状态**：已完成
- **优先级**：低
- **项目**：tools/annual_report_reader
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

「写一个自检启动的脚本」（承接 P2-2/P2-3 交付后的 h1_2026 分析台，指本地启动前自动自检、通过后打开页面）。

## 需求分析

- **目标**：一键启动 h1_2026.html 前，先自动验证交付物完整性（结构/语法/数据/契约硬约束），防坏文件被打开；自检失败给出具体问题且不启动。
- **改动点**：`tools/annual_report_reader/` 工具内部新增 2 个文件，不动现有代码与地图（无新增工具/目录/数据文件级条目）。
- **涉及数据**：读 `data/output/h1_2026/h1_2026_market.csv`、`SNAPSHOT_DATA.json` 与 HTML 内嵌 SNAPSHOT 做一致性核对，不写任何数据文件。

## 方案

- **实现思路**：自检逻辑放 Python（`selfcheck.py`，避开 bat 非 ASCII 编码坑），`start.bat` 仅作双击入口（全英文内容 + chcp 65001 + `python -X utf8`）；自检 22 项全过才 `webbrowser` 打开页面，`--check-only` 支持纯巡检。
- **改动点清单**：
  - 新增 `tools/annual_report_reader/selfcheck.py`
  - 新增 `tools/annual_report_reader/start.bat`
  - `h1_2026_docs/USER_GUIDE.md` §2.1 增补一行用法
- **风险与限制**：SNAPSHOT/图表函数清单为锚定当前契约状态（v1.9），未来扩样/增图需同步维护检查项；依赖本机装有 Python 与 Node.js（node 做 JS 语法检查）。

## 子任务

- [x] 编写 selfcheck.py（22 项自检 + 失败退出码 1 + 通过打开页面）
- [x] 编写 start.bat 双击入口
- [x] 实跑验证通过路径（22/22 PASS，exit 0）
- [x] 实跑验证失败路径（破坏副本 → 精确报 2 FAIL + exit 1 → 还原复检全绿）
- [x] USER_GUIDE 补用法说明
- [x] bat 工具化升级（2026-11-19 追加）：start.bat 独立可用——有 Python 跑完整 22 项，无 Python 走内置检查（4 结构标签 + 6 图表函数 + CSV 存在 + node 做 JS 语法）；修复 --check-only 未透传 py 的穿透 bug；四条路径实测（完整 22/22、内置降级全绿、内置+node 语法 PASS、空 HTML 报 11 FAIL 拒启动 exit 1）

## 验收标准

- [x] `python selfcheck.py --check-only` 输出 22 PASS / 0 FAIL，exit=0
- [x] 人为破坏 HTML 后自检报 FAIL 且 exit=1，还原后复检通过
- [x] 未修改任何现有代码与数据文件（仅新增 2 文件 + 文档 1 行）
