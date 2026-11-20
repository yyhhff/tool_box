# TASK-0072 xhs_crawler 纯逻辑 mock 单元测试（unittest，不真机）

- **状态**：已完成（自测通过：unittest 126/126 绿；红线 2.3 下纯 mock 测试，无真机验收环节）
- **优先级**：中
- **项目**：xhs_crawler
- **创建日期**：2026-11-20
- **完成日期**：2026-11-21（凌晨，跨午夜续跑）

## 原始需求

夜班任务池 NB-003：巡库发现 xhs_crawler 无测试资产；红线 2.3 禁真机抓取，只可 mock 测试与静态检查。

## 需求分析

- **目标**：为 TASK-0006/0007 落地的关键逻辑建立回归护栏：登录双信号判定、风控熔断三计数器、xsec_token 保留、异常落日志、Cookie 导入、Web API 分支
- **改动点**：tools/xhs_crawler/ 新增 test_xhs_crawler.py（crawler+main）+ test_xhs_server.py（server API）
- **涉及数据**：全部 mock（LOGIN_STATE/DATA_OUT 重定向临时目录、浏览器层全 fake、test_client 进程内），零真实网络

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4）：侦察员产出 ~120 例建议清单 + 红线落法 5 条；实现者落地 126 例，熔断断言用"非空+关键词"降低文案脆性；单文件改两文件（server API 独立）
- **改动点清单**：仅上述两个新测试文件，产品代码零改动
- **风险与限制**：JS 本体（USER_STATE_JS/STEALTH_JS 语义）需真浏览器，只测 Python 侧透传与参数传递到位；collect_note_links 滚动交互参数不断言；NOTE_ID_RE 33 位贪婪匹配怪癖未固化断言
- **用户确认日期**：2026-11-20（夜间章程代行）

## 子任务

- [x] 侦察：可测纯逻辑清单（侦察员 Explore，21 组函数/路由 + 排除清单 + 红线落法）
- [x] 实现 unittest 126 例（实现者 general-purpose；错误协议 1 次闭环：FakeContext.cookies() 返回结构假设验证）
- [x] 父复核全绿（discover 126/126，git status 仅两个新测试文件）
- [x] git 提交（ba3ad9c）+ 归档

## 验收标准

- [x] unittest 全绿且 discover 可用（126 例，自测通过）
- [x] 全部用例零真实网络请求（LOGIN_STATE→tmp、DATA_OUT→tmp、sync_playwright/ensure_login/collect/crawl_note_detail 全 fake、test_client 进程内）（自测通过）
- [x] 不修改产品代码（git status 确认）（自测通过）

## 变更记录

- 2026-11-20 夜班创建（领号 next_id 72→73，提交 ec03c39）
- 2026-11-21（凌晨续跑）实现者交付 126 例 + 父复核通过，提交 ba3ad9c；实现者消耗约 103.5 万 tokens
