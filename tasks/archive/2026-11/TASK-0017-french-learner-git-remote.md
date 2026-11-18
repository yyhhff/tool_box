# TASK-0017 french-learner 关联 GitHub 远程并推送

- **状态**：已完成
- **优先级**：中
- **创建日期**：2026-11-17
- **完成日期**：2026-11-17

## 原始需求

> @docs/project_content.md 这个项目的 git 是本地仓库吗，有远程吗，仓库信息
> （后续）french-learner 关联远程
> 远程地址：https://github.com/yyhhff/french-learner
> 推送策略：只推现有提交、改动先留本地
> 认证方式：改用 SSH

## 需求分析

- **目标**：为独立仓库 `tools/french-learner/` 关联 GitHub 远程 `yyhhff/french-learner`，并把本地 `main` 现有提交推送上去建立追踪；工作区未提交改动保留在本地。
- **改动点**（引用项目地图 `docs/project_content.md`）：
  - `tools/french-learner/` 的 git 远程配置（`.git/config`，非项目文件）
  - `docs/lessons.md`（沉淀 Git 代理/SSH 通用经验）
- **涉及数据**（引用数据地图 `docs/data_content.md`）：无（纯 git 运维，不碰 `data/`）

## 方案（已确认）

- **实现思路**：
  1. 探测仓库可达性与空仓库状态
  2. 先尝试 HTTPS：解决 Windows MITM 代理下的 `CRYPT_E_NO_REVOCATION_CHECK`（openssl 后端 + 系统 CA）
  3. HTTPS 推送因凭据管理器 GUI 弹窗被沙箱拦截 → 改用 SSH
  4. 校验现有 SSH key → 走 443 端口 → 切换 origin → `git push -u origin main`
- **改动点清单**：
  - `.git/config`：remote.origin.url 改为 SSH；新增 `core.sshCommand`（443 端口 + 指定密钥 + BatchMode）；新增 local `http.sslBackend` / `http.sslCAInfo`（HTTPS 阶段遗留，无害）
  - `~/.git-ca-bundle-wb.pem`：从 Windows 证书库导出的系统 CA（持久文件）
  - `docs/lessons.md`：新增 2 条通用经验
- **风险与限制**：
  - 期间另一会话在同一仓库持续提交（HEAD 从 b22b549 → c0b1f5e → 488a8ded），推送的是推送时刻的最新 HEAD `488a8ded`
  - SSH key 原未加入 GitHub，需用户手动添加公钥（已完成）
- **用户确认日期**：2026-11-17

## 子任务

- [x] 查清项目 git 现状（根目录非仓库；仅 french-learner 是独立仓库、无远程）
- [x] 探测远程仓库可达性（空仓库）
- [x] 解决 HTTPS + MITM 代理的证书校验问题
- [x] HTTPS 推送受阻（GUI 凭据弹窗被拦）→ 与用户确认改 SSH
- [x] 用户添加公钥到 GitHub，SSH 认证通过
- [x] 切换 origin 为 SSH over 443，推送 main 建立追踪
- [x] 验证本地与远程一致、工作区改动保留

## 验收标准

- [x] `git remote -v` 显示 origin 指向 `git@ssh.github.com:yyhhff/french-learner.git`
- [x] `git status -sb` 显示 `## main...origin/main`（追踪关系已建立）
- [x] 本地与 `origin/main` commit 一致（`488a8ded`）
- [x] 远程 refs 可见 main 分支
- [x] 未提交改动仍在工作区（满足"改动留本地"）

## 变更记录

- 2026-11-17 创建并完成
