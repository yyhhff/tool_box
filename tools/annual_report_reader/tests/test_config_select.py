r"""memory / industry / main 选股与记忆逻辑单元测试（全部 mock 外部路径与数据源）。

运行方式（任选其一）：
1) 仓库根目录：
   python -X utf8 -m unittest discover -s tools/annual_report_reader/tests -t tools/annual_report_reader -p "test_*.py" -v
2) 本文件直跑：
   python tools/annual_report_reader/tests/test_config_select.py

说明与边界（夜班章程红线对照）：
- memory.load_config 用 mock 把 CONFIG_PATH 指向临时目录，严禁读写真实
  data/input/annual_report_reader/config.json。
- memory.should_skip 的 report_path 一律指向临时文件，不碰真实 data/output。
- industry.select 用 mock 替换 _load_snapshot（构造快照），refresh_snapshot 也被
  mock，杜绝 akshare 在线抓取与真实快照读写；industry._fetch_*/snapshot_age_days
  不测。
- main.build_targets 用 mock 替换 industry.select，只测纯逻辑。
- memory.save_config/remember_last_run/load_index/save_index/record/company_dir/
  industry_dir 的持久化测试在 tests/test_memory_persist.py（全部路径常量 mock
  到临时目录，不写真实 data/），本文件不再排除（TASK-0074）。
- main.run_pipeline/main.main/_utf8_console 不测（触发全流程）。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOL_DIR = HERE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import industry  # noqa: E402
import main  # noqa: E402
import memory  # noqa: E402

# ---------------------------------------------------------------- 内存构造数据

SNAPSHOT = {"industries": {
    "食品饮料": {"code": "801120", "stocks": [
        {"code": "600519", "name": "贵州茅台", "mktcap": 2e12},
        {"code": "000858", "name": "五粮液", "mktcap": 6e11},
        {"code": "600809", "name": "山西汾酒", "mktcap": 3e11},
        {"code": "000568", "name": "泸州老窖", "mktcap": 2.5e11}]},
    "银行": {"code": "801780", "stocks": [
        {"code": "601398", "name": "工商银行", "mktcap": 2e12},
        {"code": "601939", "name": "建设银行", "mktcap": 1.5e12}]},
    "医药生物": {"code": "801150", "stocks": [
        {"code": "600276", "name": "恒瑞医药", "mktcap": 3e11}]},
}}

SELECTION = {
    "食品饮料": {"code": "801120", "stocks": [
        {"code": "600519", "name": "贵州茅台"},
        {"code": "000858", "name": "五粮液"}]},
    "银行": {"code": "801780", "stocks": [
        {"code": "601398", "name": "工商银行"},
        {"code": "600519", "name": "贵州茅台"}]},
}


class TestShouldSkip(unittest.TestCase):
    """覆盖 1：memory.should_skip 增量跳过判断（report_path 指向临时文件）。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="arr_ut_skip_")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.report = self.tmp / "report.md"
        self.report.write_text("测试报告", encoding="utf-8")

    def test_skip_when_done_same_year_and_report_exists(self):
        """同代码 + status=done + 同年份 + 报告文件存在 → 跳过"""
        index = {"600519": {"status": "done", "year": 2025,
                            "report_path": str(self.report)}}
        self.assertTrue(memory.should_skip(index, "600519", 2025, False))

    def test_force_never_skips(self):
        """force=True 强制重跑：即使满足全部条件也不跳过"""
        index = {"600519": {"status": "done", "year": 2025,
                            "report_path": str(self.report)}}
        self.assertFalse(memory.should_skip(index, "600519", 2025, True))

    def test_conditions_not_met_do_not_skip(self):
        """年份不符 / 状态非 done / 报告文件缺失 / 代码不在索引 / report_path 缺失 → 不跳过"""
        index = {"600519": {"status": "done", "year": 2025,
                            "report_path": str(self.report)}}
        self.assertFalse(memory.should_skip(index, "600519", 2024, False))
        index["600519"]["year"] = 2024
        self.assertFalse(memory.should_skip(index, "600519", 2025, False))
        index["600519"]["year"] = 2025
        index["600519"]["status"] = "error"
        self.assertFalse(memory.should_skip(index, "600519", 2025, False))
        index["600519"]["status"] = "done"
        index["600519"]["report_path"] = str(self.tmp / "missing.md")
        self.assertFalse(memory.should_skip(index, "600519", 2025, False))
        self.assertFalse(memory.should_skip(index, "000858", 2025, False))
        self.assertFalse(memory.should_skip({"600519": {}}, "600519", 2025, False))


class TestLoadConfig(unittest.TestCase):
    """覆盖 2：memory.load_config（CONFIG_PATH mock 到临时文件，含损坏 JSON 兜底）。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="arr_ut_cfg_")
        self.addCleanup(tmp.cleanup)
        self.cfg_path = Path(tmp.name) / "config.json"
        patcher = mock.patch.object(memory, "CONFIG_PATH", self.cfg_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_defaults_when_no_file(self):
        """配置文件不存在：返回默认配置全部键值"""
        cfg = memory.load_config()
        self.assertEqual(cfg, dict(memory.DEFAULT_CONFIG))
        self.assertEqual(cfg["top_n"], 3)
        self.assertIsNone(cfg["industries_include"])

    def test_valid_json_merged_over_defaults(self):
        """合法 JSON：用户字段覆盖默认，其余保持默认"""
        self.cfg_path.write_text(
            '{"top_n": 5, "industries_exclude": ["银行"], "model": "glm-4-flash"}',
            encoding="utf-8")
        cfg = memory.load_config()
        self.assertEqual(cfg["top_n"], 5)
        self.assertEqual(cfg["industries_exclude"], ["银行"])
        self.assertEqual(cfg["model"], "glm-4-flash")
        self.assertEqual(cfg["industries_include"], None)
        self.assertEqual(cfg["stocks_include"], [])

    def test_corrupted_json_falls_back_to_defaults(self):
        """损坏 JSON：静默兜底为默认配置，不抛异常"""
        self.cfg_path.write_text("{broken json!!", encoding="utf-8")
        self.assertEqual(memory.load_config(), dict(memory.DEFAULT_CONFIG))


class TestIsExcludedName(unittest.TestCase):
    """覆盖 3：industry.is_excluded_name 剔除 ST / 退市。"""

    def test_st_and_delisted(self):
        """含 ST（不区分大小写）或"退"字 → 剔除"""
        for name in ["*ST海润", "ST天成", "st天成", "退市锐电", "已退市"]:
            with self.subTest(name=name):
                self.assertTrue(industry.is_excluded_name(name))

    def test_normal_names_kept(self):
        """正常名称 / 空串 / None → 保留"""
        for name in ["贵州茅台", "美的集团", "", None]:
            with self.subTest(name=name):
                self.assertFalse(industry.is_excluded_name(name))


class TestIndustrySelect(unittest.TestCase):
    """覆盖 4：industry.select（mock _load_snapshot 返回构造快照）。
    覆盖 include/exclude/top_n/overrides 的"600519:名称"格式与 zfill。"""

    def setUp(self):
        patcher = mock.patch.object(industry, "_load_snapshot",
                                    return_value=SNAPSHOT)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_top_n_default_3(self):
        """缺省 top_n=3：全部行业、每行业取快照前 3（快照已按市值降序）"""
        out = industry.select({}, progress=lambda m: None)
        self.assertEqual(sorted(out), ["医药生物", "银行", "食品饮料"])
        self.assertEqual(out["银行"], {"code": "801780", "stocks": [
            {"code": "601398", "name": "工商银行", "mktcap": 2e12},
            {"code": "601939", "name": "建设银行", "mktcap": 1.5e12}]})
        self.assertEqual([s["code"] for s in out["食品饮料"]["stocks"]],
                         ["600519", "000858", "600809"])

    def test_industries_include_filter(self):
        """industries_include 白名单：只出指定行业"""
        out = industry.select({"top_n": 2, "industries_include": ["食品饮料"]},
                              progress=lambda m: None)
        self.assertEqual(list(out), ["食品饮料"])
        self.assertEqual([s["code"] for s in out["食品饮料"]["stocks"]],
                         ["600519", "000858"])

    def test_industries_exclude_filter(self):
        """industries_exclude 黑名单：剔除指定行业，其余保留"""
        out = industry.select({"industries_exclude": ["银行"]},
                              progress=lambda m: None)
        self.assertEqual(sorted(out), ["医药生物", "食品饮料"])

    def test_overrides_code_name_format_keeps_snapshot_entry(self):
        """overrides 支持"代码:名称"写法与裸代码：命中快照成分时返回完整成分数据"""
        out = industry.select(
            {"overrides": {"食品饮料": ["000858:五粮液", "600519"]}},
            progress=lambda m: None)
        self.assertEqual(out["食品饮料"]["stocks"], [
            {"code": "000858", "name": "五粮液", "mktcap": 6e11},
            {"code": "600519", "name": "贵州茅台", "mktcap": 2e12}])

    def test_override_unknown_code_fallback(self):
        """override 代码不在快照成分中：回退 {code, name:"", mktcap:0} 占位"""
        out = industry.select({"overrides": {"食品饮料": ["000999"]}},
                              progress=lambda m: None)
        self.assertEqual(out["食品饮料"]["stocks"],
                         [{"code": "000999", "name": "", "mktcap": 0}])

    def test_override_code_zfill(self):
        """override 短代码 zfill 补齐 6 位后再匹配（"858"→"000858"）"""
        out = industry.select({"overrides": {"食品饮料": ["858"]}},
                              progress=lambda m: None)
        self.assertEqual(out["食品饮料"]["stocks"],
                         [{"code": "000858", "name": "五粮液", "mktcap": 6e11}])

    def test_missing_snapshot_refreshes_then_raises(self):
        """快照为空：先尝试 refresh_snapshot（已 mock，不触网），仍为空则抛 RuntimeError"""
        with mock.patch.object(industry, "_load_snapshot", return_value={}), \
                mock.patch.object(industry, "refresh_snapshot",
                                  return_value={}) as refresh_mock:
            with self.assertRaises(RuntimeError):
                industry.select({}, progress=lambda m: None)
        refresh_mock.assert_called_once()


class TestBuildTargets(unittest.TestCase):
    """覆盖 5：main.build_targets（mock industry.select，只测纯逻辑）。"""

    def setUp(self):
        patcher = mock.patch.object(industry, "select", return_value=SELECTION)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.select_mock = industry.select
        self.noop = lambda m: None

    def test_all_stocks_dedup_first_industry_wins(self):
        """无 stocks 参数：全部行业公司按序返回，重复代码以先出现行业为准"""
        targets = main.build_targets({}, None, None, progress=self.noop)
        self.assertEqual(targets, [
            {"code": "600519", "name": "贵州茅台", "industry": "食品饮料"},
            {"code": "000858", "name": "五粮液", "industry": "食品饮料"},
            {"code": "601398", "name": "工商银行", "industry": "银行"},
        ])

    def test_stock_filter_with_suffix_and_space_normalization(self):
        """stocks 过滤："600519.SH" → "600519" 规范化、去空白；命中行业成分带行业名"""
        targets = main.build_targets({}, None, ["600519.SH", " 000858 "],
                                     progress=self.noop)
        self.assertEqual(targets, [
            {"code": "600519", "name": "贵州茅台", "industry": "食品饮料"},
            {"code": "000858", "name": "五粮液", "industry": "食品饮料"},
        ])

    def test_out_of_industry_stock_marked_custom(self):
        """不在任何已选行业里的代码 → industry="自定义"，名称留空"""
        targets = main.build_targets({}, None, ["300750"], progress=self.noop)
        self.assertEqual(targets,
                         [{"code": "300750", "name": "", "industry": "自定义"}])

    def test_industries_param_passed_to_select_and_cfg_not_mutated(self):
        """industries 参数：以 industries_include 传入 select；原 cfg 不被修改"""
        cfg = {"top_n": 2}
        main.build_targets(cfg, ["食品饮料"], None, progress=self.noop)
        self.select_mock.assert_called_once()
        passed_cfg = self.select_mock.call_args.args[0]
        self.assertEqual(passed_cfg["industries_include"], ["食品饮料"])
        self.assertNotIn("industries_include", cfg)
        targets = main.build_targets(cfg, ["食品饮料"], None, progress=self.noop)
        # select 已被 mock（不响应 include 过滤），返回其固定选择中的全部公司
        self.assertEqual([t["code"] for t in targets],
                         ["600519", "000858", "601398"])

    def test_duplicate_codes_in_stocks_input(self):
        """stocks 输入重复代码：只产出一个目标"""
        targets = main.build_targets({}, None, ["600519", "600519"],
                                     progress=self.noop)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["code"], "600519")


class TestResolveLastRun(unittest.TestCase):
    """覆盖 6：main._resolve_last_run 记忆范围解析。"""

    def test_no_last_run(self):
        """无 last_run：返回 (None, None)"""
        self.assertEqual(main._resolve_last_run({}), (None, None))

    def test_industries_and_stocks_restored(self):
        """上次范围：行业与公司原样返回"""
        cfg = {"last_run": {"industries": ["银行"], "stocks": ["600519"]}}
        self.assertEqual(main._resolve_last_run(cfg), (["银行"], ["600519"]))

    def test_empty_lists_become_none(self):
        """空列表按"未指定"处理（or None）；last_run 为空字典返回 (None, None)"""
        self.assertEqual(
            main._resolve_last_run({"last_run": {"industries": [], "stocks": ["600519"]}}),
            (None, ["600519"]))
        self.assertEqual(
            main._resolve_last_run({"last_run": {"industries": ["银行"], "stocks": []}}),
            (["银行"], None))
        self.assertEqual(main._resolve_last_run({"last_run": {}}), (None, None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
