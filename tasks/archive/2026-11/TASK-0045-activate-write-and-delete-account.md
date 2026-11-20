# TASK-0045 修切号凭据写回 PermissionError + 账号删除功能

- **状态**：进行中
- **优先级**：高
- **项目**：tools/workbuddy-multi-account
- **创建日期**：2026-11-19
- **完成日期**：2026-11-19

## 原始需求

> 任务已经成功迁移了，但切换账号有问题，切换失败:[Errno 13] Permission denied:C:\Users\Karen\AppData\Local\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info.tmp
> 确认，同时不用的测试账号就删掉，增加删除功能

## 需求分析

- **目标**：
  1. 修复切号时任务迁移成功后、凭据写回阶段撞上文件锁导致 `[Errno 13] Permission denied`，使切号真正生效；
  2. 新增账号删除功能（后端接口 + 前端按钮），并清理库中 6 个无凭据的测试账号。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `tools/workbuddy-multi-account/` 工具索引行（状态追加 TASK-0045）
- **涉及数据**（引用数据地图 `docs/data_content.md`）：
  - 客户端凭据文件 `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`（写回目标）
  - `tools/workbuddy-multi-account/workbuddy.db` 的 accounts/chat_messages/checkin_records（删除账号）
  - `tools/workbuddy-multi-account/credentials/<id>.info`（删除凭据快照）

## 方案（已确认）

> 用户 2026-11-19 16:45 确认（含新增删除功能）。

- **实现思路**：
  1. 原子写改用「PID + 随机串」唯一临时名，避开客户端自身原子写所用的固定 `.tmp` 与残留锁；
  2. 写回加短重试（5 次 × 1s）捕获 PermissionError，失败清理临时文件，耗尽后给明确错误；
  3. 记录 taskkill 输出、kill 后轮询等进程退出，替代静默失败与盲等 2s；写回后读回校验字节数；
  4. 新增 `DELETE /api/accounts/{id}`：删账号行 + 凭据快照 + 关联签到/聊天记录，返回清理计数；
  5. 前端每个账号卡加「删除」按钮（二次确认 + 提交中禁重复点击）；切号按钮同样防重复点击。
- **改动点清单**：
  - `services/account_service.py`（原子写helper / 重试 / kill 校验 / delete_account）
  - `api/accounts.py`（DELETE 端点）
  - `static/index.html`（删除按钮 + 防重复提交）
  - `tests/test_account_service.py`（新增单测）
  - `README.md`（切号与删除说明）
  - `docs/project_content.md`（工具索引状态）、`docs/lessons.md`（通用经验）
- **风险与限制**：
  - 切号强制重启 WorkBuddy 客户端是既有设计，当前客户端未保存会话会中断；
  - 若客户端看门狗在重试窗口内持续锁住 `.info`，仍可能失败，但返回明确错误而非裸异常；
  - 删除账号不可恢复，仅删工具侧数据（DB 行/凭据快照/关联记录），不动客户端私有任务与会话。
- **用户确认日期**：2026-11-19

## 子任务

- [x] 登记任务、诊断失败根因（读图 + 实测文件锁/进程）
- [x] 实现唯一临时名 + 重试 + kill 校验 + 写回校验
- [x] 实现账号删除（服务层 + API + 前端按钮）
- [x] 新增单测并跑通（不触碰真实 DB/凭据）——18/18 PASS
- [x] 清理 6 个测试账号（先备份 DB，sha256 校验）
- [x] 更新 README / 地图 / 经验库，归档任务

## 验收标准

- [x] `python -m unittest discover -s tests -v` 全绿（18/18，含新增 5 例）+ py_compile 通过
- [ ] 真机点「设为客户端登录」能切成目标账号，且此前已迁移的任务列表仍在（待用户重启服务后验收）
- [x] 前端有「删除」按钮，二次确认后调 `DELETE /api/accounts/{id}`；临时服务 :8002 验证端点 404/面板 HTML/按钮存在
- [x] 6 个无凭据测试账号已清理，`my-work` / `my-second` 保留且凭据完好（DB+凭据已备份并校验）
- [x] 地图/看板/经验库同步更新，任务归档

## 变更记录

- 2026-11-19 创建
