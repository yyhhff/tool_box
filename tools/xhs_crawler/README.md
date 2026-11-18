# xhs_crawler 小红书博文爬取工具

爬取**指定博主**、**指定时间范围**内的小红书博文。提供本地 **Web 界面**（推荐）与 **CLI** 两种用法。个人存档用途。

## 快速开始（Web 界面）

```bat
pip install -r requirements.txt
playwright install chromium
python server.py
```

自动打开 `http://127.0.0.1:5000`：先在「登录管理」登录 → 填博主与时间范围 → 开始 → 实时看进度日志 → 结果表格，点行看详情（正文/图片），支持载入历史抓取记录。

> 端口被占用时：`python server.py --port 5001`；不想自动开浏览器加 `--no-browser`。

## 登录管理（三种方式）

| 方式 | 操作 | 说明 |
|------|------|------|
| 已保存登录态 | 无需操作 | 有效则直接使用；每次启动会验证 |
| 扫码登录 | 点「扫码登录」按钮 | 弹浏览器，**扫码/短信均可**，最长等 10 分钟；确认登录后保存状态 |
| Cookie 导入 | 粘贴 cookie → 点「导入」 | 浏览器登录小红书 → F12 → 网络 → 任一请求 → 请求头复制 cookie（须含 `web_session`） |

登录态保存在 `data/cache/xhs_state.json`。失效时页面会明确提示，重新扫码或再导入一次即可。

> **注意**：请**先完成登录**（导入 Cookie 或扫码），**再**点开始抓取——运行中无法导入。博主链接建议直接粘贴浏览器地址栏复制的**完整链接（含 xsec_token 参数）**，比裸 ID 更稳（小红书很多场景缺 token 会给空页）。

## CLI 用法（与 Web 等价，适合脚本调用）

```bat
python main.py <博主ID或主页链接> --start 2026-01-01 --end 2026-11-16 [--download-images]
python main.py --cookie "a1=...; web_session=..." <博主ID> --start 2026-01-01
```

| 参数 | 说明 | 默认 |
|------|------|------|
| user | 博主用户 ID 或主页完整链接（推荐含 xsec_token 的完整链接）（必填） | — |
| --start | 起始日期 YYYY-MM-DD（含） | 不限 |
| --end | 结束日期 YYYY-MM-DD（含） | 今天 |
| --download-images | 同时下载博文图片 | 关 |
| --max-notes | 最多抓取详情数（安全上限） | 500 |
| --min-delay / --max-delay | 详情页间隔秒数（区间内随机） | 3.0 / 6.0 |
| --login-timeout | 扫码登录最长等待秒数 | 600 |
| --cookie / --cookie-file | 导入浏览器复制的 cookie | — |
| --ua | 自定义 User-Agent | 浏览器自带 |
| --headless | 无头模式（易被风控，不建议） | 关 |

> 博主 ID 获取：浏览器打开博主主页，地址栏 `xiaohongshu.com/user/profile/` 后面那串字符就是。

## 输出

`data/output/xhs_crawler/<博主ID>_<start>_<end>/`

| 文件 | 内容 |
|------|------|
| notes.json | 全量数据（正文全文、图片链接、原始日期文本） |
| notes.csv | 表格汇总，Excel 可直接打开 |
| notes.md | 可读的归档文档 |
| images/<note_id>/ | 博文图片（--download-images 时） |
| run.log | 每次运行的完整日志（追加式），事后排查用 |

## 反爬措施与风控策略

已内置：
- 浏览器默认 UA（与真实 Chromium 版本一致，避免版本指纹矛盾），不写死 UA
- 启动参数 `--disable-blink-features=AutomationControlled` + 抹除 `navigator.webdriver` 标记
- 详情页访问带博主主页 referer，模拟真实点击路径
- 默认每篇 3–6 秒随机间隔

**风控即停**（重要）：
- 主页加载不出博文卡片 → 判定风控，立即报错停止
- 详情连续 5 篇解析为空（验证页特征）或连续 8 次异常 → 停止后续任务
- 提前停止时：已抓到的内容**保留并落盘**，页面/CLI 给出明确中文提示
- 被风控后建议：暂停几小时再试、降低频率（调大 delay）、或重新登录换登录态

> 为什么不用手机 UA：桌面版 Chromium 配手机 UA 是指纹自相矛盾，反而更容易被识别。如需实验可加 `--ua`。

## 文件结构

| 文件 | 职责 |
|------|------|
| crawler.py | 核心逻辑（登录/抓取/风控检测/日志落盘，CLI/Web 共用） |
| server.py | Flask Web 服务（后台线程 + 轮询 API + 图片服务 + 登录管理） |
| templates/index.html | 前端单页（登录管理/表单/日志/结果表/详情/历史） |
| main.py | CLI 入口（薄封装） |

## 原理与限制

- 技术方案：Playwright 真实浏览器，避开接口签名（x-s/x-t 头）问题
- 登录判定为双重信号（web_session cookie + 页面用户态），避免匿名 cookie 误判
- Web 模式：抓取/登录在后台线程执行，同一时间仅允许一个任务；Playwright sync API 需在创建它的同一线程使用
- 时间过滤：主页卡片不带日期，需逐篇打开详情页读取日期再过滤；主页博文大致倒序，连续 15 篇早于起始日期会提前停止
- 视频笔记只保存文字与链接，不下载视频
- 日期解析覆盖：`YYYY-MM-DD`、`今天/昨天/N天前`、`MM-DD`（跨年自动回退一年）；解析失败的保留并标"未知"
- 小红书页面结构常变：所有 CSS 选择器集中在 crawler.py 顶部 `SEL` 常量，抓不到内容时优先更新它

## 注意

- 仅供个人学习与存档；请勿调低频率做大规模抓取或商用
- 频繁抓取可能触发账号风控，建议一次抓一位博主、控制单次总量
