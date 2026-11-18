# TASK-0011 修复 ZHIPU_API_KEY 在已运行进程中读不到导致报错

- **状态**：已完成
- **优先级**：高
- **创建日期**：2026-11-17
- **完成日期**：2026-11-17

## 原始需求

报错：`LLMError: 未设置环境变量 ZHIPU_API_KEY（在智谱开放平台 bigmodel.cn 申请后：setx ZHIPU_API_KEY <你的key>，重开终端生效）`

## 需求分析

- **目标**：key 其实已在用户级注册表设置（49 位），但进程环境读不到——setx 不更新已运行进程。根治：让代码能自行从注册表读取，CLI/Web/子进程都拿得到，无需重开终端。
- **改动点**（引用 `docs/project_content.md`）：
  - 修改 `tools/annual_report_reader/analyzer.py` 的 `client()` key 读取逻辑
  - 视情况更新 `tools/annual_report_reader/README.md`
- **涉及数据**（引用 `docs/data_content.md`）：无数据文件结构变更，两张地图无需改（工具索引内容不变）。

## 方案（已确认）

- **实现思路**：
  - `client()` 先读 `os.environ`；读不到且是 Windows 时，用 `winreg` 从 `HKEY_CURRENT_USER\Environment` 读取 `ZHIPU_API_KEY`，回填 `os.environ` 再返回 client。
  - 注册表读取失败/不存在时保持原有报错，不吞异常、不打印 key 明文。
  - 改善错误提示：说明"已设置的 key 可能因进程未重启读不到，代码已自动尝试注册表读取"。
  - 非 Windows 平台行为不变（只读 os.environ）。
- **改动点清单**：
  - `tools/annual_report_reader/analyzer.py`
  - `tools/annual_report_reader/README.md`（视情况）
  - `docs/lessons.md`（更新 TASK-0008 那条经验，补"代码层兜底优于临时脚本注入"）
- **风险与限制**：
  - 只解决"读取"，不验证 key 是否有效/是否有额度——那需真实 API 调用，由用户侧确认。
  - winreg 仅 Windows 有，需做平台判断与 import 容错。
- **用户确认日期**：2026-11-17

## 子任务

- [x] 1. 实现注册表兜底读取函数（winreg / 平台判断 / 回填 os.environ）
- [x] 2. 改造 client() 使用兜底并改善错误提示
- [x] 3. 验证：无进程环境下能读到 key、client 构造成功、编译通过、不泄露明文

## 验收标准

- [x] 当前进程无 ZHIPU_API_KEY 时，代码能从注册表读到并构造出 OpenAI client（不打印 key 明文）——进程环境清空后成功读到 49 位 key 并构造 client
- [x] 跨平台安全：非 Windows 平台不报错（读取逻辑被跳过），key 缺失时给出清晰提示——模拟 posix 验证跳过注册表、缺失时抛 LLMError
- [x] 编译通过，analyzer 既有函数签名/行为不变，无回归
- [x] 额外：用注册表读到的 key 做真实 GLM API 调用成功（key 有效有额度），端到端确认

## 变更记录

- 2026-11-17 创建（方案已经用户确认）
- 2026-11-17 完成：analyzer.py 加 _key_from_registry/_resolve_api_key 兜底，README 说明，lessons 更新；真实 API 调用验证通过
