r"""memory 持久化函数单元测试（全部路径常量 mock 到临时目录）。

覆盖：save_config / remember_last_run / load_index / save_index / record /
company_dir / industry_dir。TASK-0074（夜班优化项 OP-02）。

运行方式（任选其一）：
1) 仓库根目录：
   python -X utf8 -m unittest discover -s tools/annual_report_reader/tests -t tools/annual_report_reader -p "test_*.py" -v
2) 本文件直跑：
   python tools/annual_report_reader/tests/test_memory_persist.py

说明与边界（夜班章程红线对照）：
- CONFIG_PATH / INDEX_PATH / DATA_OUT 三个路径常量在 setUp 统一 mock 重定向到
  TemporaryDirectory，严禁读写真实 data/input/config.json 与 data/output/。
- 缺失/损坏 JSON 的兜底行为与写盘编码（ensure_ascii=False）一并覆盖。
- main.run_pipeline/main.main/_utf8_console 仍不测（触发全流程）。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOL_DIR = HERE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import memory  # noqa: E402

TS_RE = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"


class TestMemoryPersist(unittest.TestCase):
    """覆盖 7：memory 持久化函数（路径常量统一 mock 到临时目录）。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="arr_ut_persist_")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.cfg_path = self.tmp / "input" / "annual_report_reader" / "config.json"
        self.out_dir = self.tmp / "output" / "annual_report_reader"
        self.index_path = self.out_dir / "index.json"
        for attr, val in (("CONFIG_PATH", self.cfg_path),
                          ("INDEX_PATH", self.index_path),
                          ("DATA_OUT", self.out_dir)):
            patcher = mock.patch.object(memory, attr, val)
            patcher.start()
            self.addCleanup(patcher.stop)

    # ------------------------------------------------------ save_config

    def test_save_config_writes_json_readable_back(self):
        """正常写：文件落盘，utf-8 JSON 回读内容与传入 cfg 一致"""
        cfg = dict(memory.DEFAULT_CONFIG, top_n=5, model="glm-4-flash")
        memory.save_config(cfg)
        self.assertTrue(self.cfg_path.is_file())
        self.assertEqual(
            json.loads(self.cfg_path.read_text(encoding="utf-8")), cfg)

    def test_save_config_creates_missing_parent_dirs(self):
        """父目录不存在：逐级自动创建（mkdir parents=True）后写入"""
        self.assertFalse(self.cfg_path.parent.exists())
        memory.save_config({"top_n": 1})
        self.assertTrue(self.cfg_path.parent.is_dir())
        self.assertTrue(self.cfg_path.is_file())

    def test_save_config_overwrites_corrupted_old_file(self):
        """旧文件为损坏 JSON：save_config 直接整文件覆盖，不读旧内容不报错"""
        self.cfg_path.parent.mkdir(parents=True)
        self.cfg_path.write_text("{broken json!!", encoding="utf-8")
        memory.save_config({"top_n": 9})
        self.assertEqual(
            json.loads(self.cfg_path.read_text(encoding="utf-8")), {"top_n": 9})

    def test_save_config_ensure_ascii_keeps_chinese_raw(self):
        """ensure_ascii=False：中文字面直接落盘（非 \\uXXXX 转义），utf-8 回读一致"""
        cfg = {"industries_exclude": ["银行", "医药生物"]}
        memory.save_config(cfg)
        raw = self.cfg_path.read_text(encoding="utf-8")
        self.assertIn("银行", raw)
        self.assertNotIn("\\u94f6", raw)  # ensure_ascii=True 时会出现该转义
        self.assertEqual(json.loads(raw), cfg)

    # ------------------------------------------------------ remember_last_run

    def test_remember_last_run_fields_complete_and_persisted(self):
        """last_run 写入 cfg（mode/industries/stocks/top_n/model/ts 齐全）并落盘"""
        cfg = dict(memory.DEFAULT_CONFIG)
        memory.remember_last_run(cfg, "industries", ["食品饮料"], ["600519"],
                                 5, "glm-4-flash")
        lr = cfg["last_run"]
        self.assertEqual(lr["mode"], "industries")
        self.assertEqual(lr["industries"], ["食品饮料"])
        self.assertEqual(lr["stocks"], ["600519"])
        self.assertEqual(lr["top_n"], 5)
        self.assertEqual(lr["model"], "glm-4-flash")
        self.assertRegex(lr["ts"], TS_RE)
        disk = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(disk["last_run"], lr)

    def test_remember_last_run_none_normalizes_to_empty_lists(self):
        """industries/stocks 传 None：按 or [] 规范化为空列表；model=None 保留"""
        cfg = {}
        memory.remember_last_run(cfg, "stocks", None, None, 3, None)
        lr = cfg["last_run"]
        self.assertEqual(lr["industries"], [])
        self.assertEqual(lr["stocks"], [])
        self.assertIsNone(lr["model"])
        self.assertEqual(json.loads(
            self.cfg_path.read_text(encoding="utf-8"))["last_run"], lr)

    def test_remember_last_run_overwrites_previous_scope(self):
        """重复调用：last_run 以最后一次为准（整字典替换，不残留旧键值）"""
        cfg = {}
        memory.remember_last_run(cfg, "all", ["银行"], [], 3, None)
        memory.remember_last_run(cfg, "stocks", [], ["000858"], 2, "glm-4-flash")
        lr = cfg["last_run"]
        self.assertEqual(lr["mode"], "stocks")
        self.assertEqual(lr["stocks"], ["000858"])
        self.assertEqual(lr["top_n"], 2)
        self.assertEqual(lr["industries"], [])
        disk = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(disk["last_run"]["mode"], "stocks")

    # ------------------------------------------------------ load_index / save_index

    def test_load_index_missing_file_returns_empty_dict(self):
        """index 文件不存在：返回空字典（不抛异常）"""
        self.assertFalse(self.index_path.exists())
        self.assertEqual(memory.load_index(), {})

    def test_load_index_corrupted_json_returns_empty_dict(self):
        """index 文件损坏 JSON：静默兜底空字典"""
        self.index_path.parent.mkdir(parents=True)
        self.index_path.write_text("{oops", encoding="utf-8")
        self.assertEqual(memory.load_index(), {})

    def test_save_index_creates_out_dir_and_roundtrip(self):
        """save_index 自动创建 DATA_OUT 目录；save→load 往返一致（含中文）"""
        self.assertFalse(self.out_dir.exists())
        index = {"600519": {"status": "done", "year": 2025,
                            "industry": "食品饮料", "report_path": "r.md"}}
        memory.save_index(index)
        self.assertTrue(self.index_path.is_file())
        self.assertEqual(memory.load_index(), index)

    def test_save_index_ensure_ascii_keeps_chinese_raw(self):
        """ensure_ascii=False：中文行业名直接落盘（非 \\uXXXX 转义）"""
        memory.save_index({"600519": {"industry": "食品饮料"}})
        raw = self.index_path.read_text(encoding="utf-8")
        self.assertIn("食品饮料", raw)
        self.assertNotIn("\\u98df", raw)  # "食" 的 ensure_ascii 转义形式

    # ------------------------------------------------------ record

    def test_record_new_code_creates_entry_with_timestamp(self):
        """新代码：创建条目、追加 updated_at，并同步落盘"""
        index = {}
        memory.record(index, "600519", status="done", year=2025,
                      report_path="r.md")
        entry = index["600519"]
        self.assertEqual(entry["status"], "done")
        self.assertEqual(entry["year"], 2025)
        self.assertEqual(entry["report_path"], "r.md")
        self.assertRegex(entry["updated_at"], TS_RE)
        self.assertEqual(memory.load_index(), index)

    def test_record_updates_existing_entry_in_place(self):
        """已有条目：新字段覆盖、旧字段保留（update 语义），落盘一致"""
        index = {"600519": {"status": "error", "year": 2024, "note": "初跑失败"}}
        memory.record(index, "600519", status="done", year=2025)
        entry = index["600519"]
        self.assertEqual(entry["status"], "done")
        self.assertEqual(entry["year"], 2025)
        self.assertEqual(entry["note"], "初跑失败")
        self.assertRegex(entry["updated_at"], TS_RE)
        self.assertEqual(memory.load_index()["600519"], entry)

    def test_record_null_entry_treated_as_empty(self):
        """索引中已有键但值为 None：按空字典处理不抛异常（entry = get or {}）"""
        index = {"000858": None}
        memory.record(index, "000858", status="done")
        self.assertEqual(index["000858"],
                         {"status": "done", "updated_at": index["000858"]["updated_at"]})

    # ------------------------------------------------------ company_dir / industry_dir

    def test_company_dir_naming_rule_and_creation(self):
        """目录名规则 {code}_{year}，位于 DATA_OUT/companies 下且自动逐级创建"""
        d = memory.company_dir("600519", 2025)
        self.assertEqual(d, self.out_dir / "companies" / "600519_2025")
        self.assertTrue(d.is_dir())

    def test_company_dir_idempotent_repeat_call(self):
        """重复调用同一 (code, year)：exist_ok 幂等，路径不变不报错"""
        d1 = memory.company_dir("600519", 2025)
        d2 = memory.company_dir("600519", 2025)
        self.assertEqual(d1, d2)
        self.assertTrue(d2.is_dir())

    def test_industry_dir_path_creation_and_idempotent(self):
        """industry_dir 位于 DATA_OUT/industries：自动创建且重复调用幂等"""
        d = memory.industry_dir()
        self.assertEqual(d, self.out_dir / "industries")
        self.assertTrue(d.is_dir())
        self.assertEqual(memory.industry_dir(), d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
