# TASK-0074 annual_report_reader memory.py save/record 系单元测试

- **状态**：进行中
- **优先级**：中
- **项目**：annual_report_reader
- **创建日期**：2026-11-21
- **完成日期**：

## 原始需求

夜班深度巡库优化项 OP-02：现有测试文件 docstring 明文"save/record 系不测（写真实 data/）"，但该理由已过时——同文件 test_load_config 已有 `mock.patch.object(memory, "CONFIG_PATH", tmp)` 成熟模式，照搬即可补齐持久化层回归护栏。

## 需求分析

- **目标**：memory.py 持久化函数回归护栏：save_config / remember_last_run / load_index / save_index / record / company_dir / industry_dir
- **改动点**：tools/annual_report_reader/tests/ 新增或扩充测试文件（沿用 4 文件组织，建议并入 test_config_select.py 或新建 test_memory_persist.py）
- **涉及数据**：CONFIG_PATH/INDEX_PATH/输出根 mock 重定向临时目录，零真实 data/ 读写

## 方案（已确认）

- **实现思路**（夜间章程代行确认，依据 docs/night_ops.md §2/§4.3 + 深度巡库侦察报告）：全部路径常量 mock patch，先读源码确认各函数签名与落盘路径再写
- **改动点清单**：仅新增/扩充 tests 文件，不改产品代码
- **风险与限制**：禁止真实读写 data/input/config.json 与 data/output/**
- **用户确认日期**：2026-11-21（夜间章程代行）

## 子任务

- [ ] 实现 unittest（实现者）
- [ ] 父复核全绿
- [ ] git 提交 + 归档

## 验收标准

- [ ] unittest 全绿且 discover 可用（与既有 101 例合并跑）
- [ ] 零真实 data/ 读写（全 mock 重定向）
- [ ] 不修改产品代码

## 变更记录

- 2026-11-21 夜班创建（领号 next_id 74→75）
