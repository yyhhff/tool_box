# TASK-0007 修复假登录误判 + 链接参数保留 + 异常日志补全

- **状态**：进行中（代码完成，待真机验收）
- **优先级**：高
- **创建日期**：2026-11-16
- **完成日期**：

## 原始需求

用户反馈"看日志有什么问题"。诊断（见下）后用户确认修复方案。

## 需求分析

- **诊断结论**（run.log + 登录态文件证据链）：
  1. 20:01:42 任务启动时登录态文件不存在 → 走浏览器交互登录
  2. 20:01:58 "登录成功（cookie 信号）"——10 秒内用户不可能完成扫码。**根因**：匿名访客也会被下发 web_session，TASK-0006 写的弱信号兜底（`or _context_has_session`，仅看存在性）把匿名 cookie 误判为已登录，并保存了垃圾登录态（文件 mtime 20:01:58、14 个匿名会话 cookie 佐证）
  3. 带匿名身份访问博主主页 → 无卡片 → 抛 RiskControlDetected，但异常信息没写进 run.log（日志戛然而止的第二个 bug），网页横幅还误报"疑似被风控"
  4. 次要问题：工具把主页链接剥成裸 URL，丢弃 xsec_token（小红书很多场景缺 token 给空页）
- **改动点**：crawler.py（ensure_login、USER_STATE_JS、normalize_user_target、crawl 异常处理）、README

## 方案（已确认）

- **实现思路**：
  - 登录判定：页面用户态（__INITIAL_STATE__ 逐层反序列化，支持 loggedIn/userId/uid 多路径）为主信号；web_session 弱信号改为"相对基线新增/变化 + reload 后值稳定"才确认——匿名 cookie 恒等于基线，不再误判
  - normalize_user_target：链接形式原样保留（含 xsec_token），裸 ID 仍可用
  - crawl() 增加 except BaseException：异常终止先写 run.log 再抛出
  - 删除垃圾登录态文件，用户重新导入/扫码
- **改动点清单**：crawler.py 5 处、README 2 处、lessons 2 条、看板
- **风险与限制**：匿名 web_session 若在会话中自我轮换（值变化）理论上仍可能误判，已用"reload 后值稳定"约束，概率极低；__INITIAL_STATE__ 结构再变时靠弱信号兜底
- **用户确认日期**：2026-11-16（会话中确认"可以"）

## 子任务

- [x] ensure_login 基线对比修复（匿名 cookie 不再误判）
- [x] USER_STATE_JS 逐层反序列化强化
- [x] normalize_user_target 保留 xsec_token 等链接参数
- [x] crawl() 异常终止写入 run.log
- [x] 删除垃圾登录态文件
- [x] README、经验库、看板同步
- [ ] 真机验收：重新导入 Cookie → 完整抓取一次

## 验收标准

- [x] 冒烟：语法检查、模块导入、normalize_user_target 三种输入（完整链接/裸链接/裸 ID）正确
- [ ] 重新导入 Cookie 后"使用已保存的登录态"生效，完整抓取成功
- [ ] 若再失败，run.log 完整记录终止原因（不再戛然而止）

## 变更记录

- 2026-11-16 创建，完成编码与文档同步
