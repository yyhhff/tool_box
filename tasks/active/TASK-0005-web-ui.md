# TASK-0005 小红书爬虫 Web 前端

- **状态**：进行中（代码完成，待真机验收）
- **优先级**：中
- **创建日期**：2026-11-16
- **完成日期**：

## 原始需求

小红书博文爬取工具做成有前端展示的工具，帮我安装缺少的依赖。

## 需求分析

- **目标**：本地 Web 界面操作爬虫（填参数 → 实时进度 → 结果表格/详情/图片/历史记录）；补齐缺失依赖
- **改动点**：`tools/xhs_crawler/` 重构（拆出 crawler.py）+ 新增 server.py、templates/index.html；更新 README.md、requirements.txt
- **涉及数据**：读 `data/output/xhs_crawler/`（历史记录列表、图片静态服务）；登录态、产出不变

## 方案（已确认）

- **实现思路**：Flask + 原生 HTML/JS 单页；crawler.py 承载核心逻辑并增加进度回调，CLI 与 Web 共用；爬虫跑在单一后台线程（Playwright sync API 需在同一线程使用），前端轮询 /api/status 取进度；已下载图片经 /images/ 路由服务；同一时间仅允许一个抓取任务
- **改动点清单**：新增 crawler.py、server.py、templates/index.html；重写 main.py 为薄 CLI；更新 README、requirements、地图、看板
- **风险与限制**：小红书页面结构变化风险同 CLI 版（选择器集中在 SEL）；首次扫码需人在场；端口默认 5000
- **用户确认日期**：2026-11-16（会话中确认"ok"）

## 子任务

- [x] 拆分 crawler.py（核心逻辑 + 进度回调）
- [x] server.py（后台线程 + 轮询 API + 图片服务 + 历史记录）
- [x] templates/index.html（表单/日志/表格/详情弹层/历史）
- [x] main.py 薄化为 CLI 入口
- [x] 更新 README、requirements、地图、看板
- [x] 安装依赖 flask、playwright、chromium（flask 3.1.3 / playwright 1.65.2 / Chromium 159）
- [ ] 真机验收：页面实际抓取一位博主

## 验收标准

- [x] `python server.py` 启动，页面渲染正常（冒烟：页面 200、/api/status、/api/history 均通过）
- [x] `pip list` 可见 flask、playwright，chromium 就绪
- [x] CLI 用法 `python main.py --help` 正常（与 Web 共用 crawler.crawl）
- [x] 文档与地图同步
- [ ] 待真机：页面实际操作，进度实时刷新
- [ ] 待真机：完整抓取一位博主，结果表格 + 详情（正文/图片）正常

## 变更记录

- 2026-11-16 创建，完成编码；依赖安装后台执行中
- 2026-11-16 依赖安装完成；冒烟测试通过（服务启动/页面渲染/API/CLI --help），测试服务已停止
