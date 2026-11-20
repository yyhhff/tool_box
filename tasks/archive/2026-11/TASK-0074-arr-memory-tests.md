# TASK-0074 annual_report_reader memory.py save/record 系单元测试

- **状态**：已完成（自测通过：unittest 118/118 合并绿；mock 路径测试无真机验收环节）
- **优先级**：中
- **项目**：annual_report_reader
- **创建日期**：2026-11-21
- **完成日期**：2026-11-21

## 原始需求

夜班深度巡库优化项 OP-02：现有测试文件 docstring 明文"save/record 系不测（写真实 data/）"，但该理由已过时——同文件 test_load_config 已有 `mock.patch.object(memory, "CONFIG_PATH", tmp)` 成熟模式，照搬即可补齐持久化层回归护栏。

## 需求分析

- **目标**：memory.py 持久化函数回归护栏：save_config / remember_last_run / load_index / save_index / record / company_dir / industry_dir
- **改动点**：tests/ 新增 test_memory_persist.py（213 行）+ test_config_select.py 仅更新过时 docstring
- **涉及数据**：CONFIG_PATH/INDEX_PATH/DATA_OUT 三常量 mock 重定向临时目录，零真实 data/ 读写

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3）：全部路径常量 mock；**关键发现：INDEX_PATH 是导入期由 DATA_OUT 派生的独立常量，patch DATA_OUT 不联动，三常量须齐 mock**，缺一必写真实 data/output/
- **改动点清单**：test_memory_persist.py 新增（17 例）+ test_config_select.py docstring 更新（排除说明移除 + 指向新文件）
- **风险与限制**：company_dir 短代码补零行为不固化断言（zfill 在 select 层，避免把疑似缺陷固化成契约）
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [x] 实现 unittest 17 例（实现者；record 的 None 条目边界补 1 例锁定隐含语义）
- [x] 父复核全绿（discover 118/118 合并绿，变更面仅 2 个测试文件）
- [x] git 提交（9f9578f）+ 归档

## 验收标准

- [x] unittest 全绿且 discover 可用（118 例合并绿，自测通过）
- [x] 零真实 data/ 读写（红线自证方式：所有路径断言指向临时目录，mock 失效必失败）（自测通过）
- [x] 不修改产品代码（git status 确认，自测通过）

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 74→75，提交 439066a）
- 2026-11-21 实现者交付 + 父复核通过，提交 9f9578f；实现者消耗约 20.6 万 tokens
