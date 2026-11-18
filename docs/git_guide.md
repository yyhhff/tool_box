# Git 使用命令文档

> 目标：覆盖日常 90% 的场景，命令可直接复制。完整教程见 [Pro Git 中文版](https://git-scm.com/book/zh/v2)。

## 0. 一次性准备

### 安装（本机尚未安装时）

1. 下载安装：https://git-scm.com/download/win （一路下一步即可）
2. 安装后**重开终端**，验证：`git --version`

### 首次配置（装机后执行一次）

```bat
git config --global user.name "你的名字"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.autocrlf true
```

> `core.autocrlf true`：Windows 下推荐，统一换行符，避免大量假差异警告。

## 1. 仓库初始化（本项目只需做一次）

```bat
git init -b main     :: 在项目根目录执行，把当前目录变成 git 仓库
git status           :: 随时查看：哪些文件被修改/新增（最常用的命令）
```

## 2. 日常三步曲：改代码 → 暂存 → 提交

```bat
git status                                :: 1) 看看改了什么
git add <文件>                             :: 2) 暂存指定文件
git add .                                 ::    或暂存全部改动（先确认 status 干净）
git commit -m "feat: xxx工具支持批量输入"   :: 3) 提交到本地仓库
```

**提交信息规范**：`<类型>: <做了什么>`

| 类型 | 含义 |
|------|------|
| feat | 新功能（新工具 / 新命令） |
| fix | 修 bug |
| docs | 只改文档 |
| refactor | 重构（不改功能） |
| chore | 杂务（依赖、配置、.gitignore） |

## 3. 查看历史与差异

```bat
git log --oneline        :: 一行一条提交历史
git log --oneline -5     :: 最近 5 条
git diff                 :: 还没 add 的改动
git diff --staged        :: 已 add 未 commit 的改动
git show <commit-id>     :: 看某次提交的完整改动
```

## 4. 撤销与补救

```bat
git restore <文件>         :: 丢弃某文件未暂存的修改（不可恢复，慎用）
git restore --staged <文件> :: 把已 add 的文件移出暂存区（改动保留）
git commit --amend         :: 修正最近一次提交（信息写错 / 漏加文件）
git reset --soft HEAD~1    :: 撤销最近一次提交，改动退回暂存区（最安全的回退）
git reset --hard HEAD~1    :: 彻底丢弃最近一次提交（危险！确认不需要才用）
```

## 5. 分支（做较大改动时用，避免弄脏 main）

```bat
git branch               :: 列出分支
git switch -c feat-xxx   :: 新建并切换到分支 feat-xxx
git switch main          :: 切回 main
git merge feat-xxx       :: 在 main 上合并 feat-xxx
git branch -d feat-xxx   :: 删除已合并的分支
```

## 6. 远程仓库（GitHub / Gitee，可选）

```bat
git remote add origin <仓库URL>   :: 关联远程仓库
git push -u origin main           :: 首次推送 main（-u 记住关联，之后免写）
git push                          :: 之后推送
git pull                          :: 拉取远程更新
git clone <仓库URL>               :: 把已有仓库克隆到本地
```

## 7. .gitignore 说明

根目录 `.gitignore` 中列出的文件/目录不会被 git 跟踪。本项目已忽略：

- 临时产物：`data/output/`、`data/cache/`、`__pycache__/`
- 本地环境：`.venv/`、`.idea/`、`.vscode/`

注意：**已被跟踪的文件**再加入 ignore 不生效，需先执行 `git rm --cached <文件>` 再提交。

## 8. 常见场景速查表

| 场景 | 命令 |
|------|------|
| 完成了一个功能 | `git add .` → `git commit -m "feat: xxx"` |
| 提交信息写错了 | `git commit --amend` |
| 错误地 add 了文件 | `git restore --staged <文件>` |
| 撤销某个文件的本地修改 | `git restore <文件>`（慎用，不可恢复） |
| 回退到历史某版本 | `git log --oneline` 查 id → `git reset --hard <id>`（危险） |
| 误提交了大文件 | 改 `.gitignore` → `git rm --cached <文件>` → 提交 |
| 想试试大改动又怕搞坏 | `git switch -c try-xxx`，在分支上折腾 |

## 本项目建议节奏

每完成一个任务（归档后）提交一次；一次提交只做一件事，提交信息写清楚。
