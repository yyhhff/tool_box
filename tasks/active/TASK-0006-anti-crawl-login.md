# TASK-0006 反爬加固 + 登录增强

- **状态**：进行中（代码完成，待真机验收）
- **优先级**：高
- **创建日期**：2026-11-16
- **完成日期**：

## 原始需求

查看执行的日志，应该是被反爬了，看看怎么规避，例如 ua 手机的等。而且使用时有问题，给的扫码时间太短，还需要增加使用 cookie 登录的功能。

## 需求分析

- **目标**：降低被风控概率；扫码等待加长；支持 Cookie 导入登录；被风控时立即停止后续任务（用户补充确认）
- **诊断**：产出 count=0 且登录态文件不存在 → 疑似 `has_session()` 把匿名 web_session cookie 误判为已登录，匿名状态抓不到内容；另有 UA 版本指纹矛盾（写死 Chrome/130 vs 实际 Chromium 159）；日志仅存内存无法事后排查
- **改动点**：crawler.py / server.py / templates/index.html / main.py / README；数据地图（run.log、登录态来源）
- **涉及数据**：`data/cache/xhs_state.json`（扫码确认或 Cookie 导入后写入）、`data/output/.../run.log`（新增）

## 方案（已确认）

- **实现思路**：
  - 登录：判定改双信号（web_session + 页面用户态 __INITIAL_STATE__，reload 复核后才持久化）；交互登录等待 180s→600s，扫码/短信均可；新增 Cookie 字符串导入（合成 storage_state 直写登录态文件）
  - 反爬：去掉写死 UA 用浏览器默认（版本一致），`--disable-blink-features=AutomationControlled` + 抹除 navigator.webdriver，详情页带主页 referer，默认间隔 2–4s→3–6s
  - 风控即停：主页 0 卡片 / 详情连续 5 篇全空 / 连续 8 次异常 → 立即停止后续任务，保留已抓内容并落盘，给出明确中文提示
  - 日志落盘：每次运行 tee 到 <输出目录>/run.log
  - Web 新增「登录管理」卡片（状态 + 扫码按钮带倒计时 + Cookie 导入）；CLI 新增 --cookie/--cookie-file/--login-timeout/--ua
- **关于手机 UA**：桌面 Chromium 配手机 UA 是指纹自相矛盾更易被识别，故不默认采用；留 --ua 参数供实验
- **改动点清单**：crawler.py（重写登录/风控/日志）、server.py（+3 登录 API、stop_reason 透传）、index.html（登录卡片）、main.py（新参数）、README、docs/data_content.md、docs/lessons.md
- **风险与限制**：小红书风控策略不可见，措施只能降低概率不能保证不被拦；__INITIAL_STATE__ 结构变化时有 cookie 弱信号兜底
- **用户确认日期**：2026-11-16（确认方案，补充"被风控就停止后面的任务"）

## 子任务

- [x] 登录判定双信号修复（匿名 cookie 不再误判）
- [x] 扫码等待 600s + 任意登录方式
- [x] Cookie 字符串导入登录（crawler + API + 前端 + CLI）
- [x] 反爬加固（默认 UA / webdriver 抹除 / referer / 降速）
- [x] 风控即停（主页 0 卡片 / 详情空页连击 / 异常连击，保留部分结果）
- [x] 日志落盘 run.log
- [x] README、数据地图、经验库、看板同步
- [ ] 真机验收：Cookie 导入登录 + 完整抓取一次

## 验收标准

- [x] 冒烟：语法检查、服务启动、API 正常（含 login_status / login_cookie）
- [ ] Cookie 粘贴导入后显示已登录，重启服务仍保持
- [ ] 扫码窗口 10 分钟，倒计时可见
- [ ] 每次运行生成 run.log
- [ ] 被风控时明确提示并停止，不再静默 count=0
- [ ] 完整抓取一次成功（结果表格 + 详情正常）

## 变更记录

- 2026-11-16 创建，完成编码与文档同步
