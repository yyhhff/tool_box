r"""fetcher.py 单元测试（仅两个纯函数：板块归列与年报公告挑选）。

运行方式（任选其一）：
1) 仓库根目录：
   python -X utf8 -m unittest discover -s tools/annual_report_reader/tests -t tools/annual_report_reader -p "test_*.py" -v
2) 本文件直跑：
   python tools/annual_report_reader/tests/test_fetcher.py

说明与边界（夜班章程红线对照）：
- 只测 _column_plate / _pick_annual 两个纯函数；org_id/_post/latest_annual_report/
  download_pdf/_cache_* 涉及网络与真实缓存，一律不测。
- 公告列表全部内存构造；选错报告 = 全链路错，故用对抗用例覆盖
  摘要/英文版/已取消/取消/部分/问询 六类干扰标题与半年度报告、HTML 标题标签、
  "2025年度报告"无"年"字变体。
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_DIR = HERE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import fetcher  # noqa: E402


class TestColumnPlate(unittest.TestCase):
    """覆盖 1：_column_plate 股票代码 → (column, plate) 归列。"""

    def test_shanghai(self):
        """6 开头（含科创板 688）→ 上交所"""
        self.assertEqual(fetcher._column_plate("600519"), ("sse", "sse"))
        self.assertEqual(fetcher._column_plate("688111"), ("sse", "sse"))

    def test_beijing(self):
        """43/83/87/88/92 开头 → 北交所（column 仍走 szse 通道）"""
        cases = ["430047", "830799", "873223", "880000", "920002"]
        for code in cases:
            with self.subTest(code=code):
                self.assertEqual(fetcher._column_plate(code), ("szse", "bj"))

    def test_shenzhen(self):
        """其余（0/3 开头主板、中小板、创业板）→ 深交所"""
        cases = ["000001", "002594", "300750"]
        for code in cases:
            with self.subTest(code=code):
                self.assertEqual(fetcher._column_plate(code), ("szse", "sz"))


class TestPickAnnual(unittest.TestCase):
    """覆盖 2：_pick_annual 从公告列表选最新完整年度报告。"""

    def test_filter_keywords_each_blocked(self):
        """六类干扰标题逐个验证被过滤（列表中只有该变体时选不出结果）"""
        variants = [
            "测试公司2025年年度报告摘要",
            "测试公司2025年年度报告（英文版）",
            "测试公司2025年年度报告（已取消）",
            "测试公司2025年年度报告（取消）",
            "测试公司2025年年度报告（部分更正）",
            "关于对测试公司2025年年度报告问询函的回复",
            "测试公司2025年半年度报告",  # 半年度含"年度报告"子串，但年份正则不匹配
        ]
        for title in variants:
            with self.subTest(title=title):
                anns = [{"announcementTitle": title, "announcementTime": 999,
                         "adjunctUrl": "x.pdf"}]
                self.assertIsNone(fetcher._pick_annual(anns))

    def test_picks_latest_full_report_from_adversarial_list(self):
        """对抗列表：跳过全部干扰项，按 announcementTime 降序选最新完整年报，
        兼容 HTML 标题标签与"2025年度报告"无"年"字变体"""
        anns = [
            {"announcementTitle": "测试公司2024年年度报告",
             "announcementTime": 1700000000000, "adjunctUrl": "old2024.pdf"},
            {"announcementTitle": "测试公司2025年年度报告摘要",
             "announcementTime": 1739999999999, "adjunctUrl": "summary.pdf"},
            {"announcementTitle": "测试公司2025年年度报告（英文版）",
             "announcementTime": 1739999999998, "adjunctUrl": "en.pdf"},
            {"announcementTitle": "测试公司2025年年度报告（已取消）",
             "announcementTime": 1739999999997, "adjunctUrl": "cancel.pdf"},
            {"announcementTitle": "关于对测试公司2025年年度报告问询函的回复",
             "announcementTime": 1739999999996, "adjunctUrl": "inquiry.pdf"},
            {"announcementTitle": "测试公司2025年年度报告（部分更正）",
             "announcementTime": 1739999999995, "adjunctUrl": "partial.pdf"},
            {"announcementTitle": "测试公司2025年半年度报告",
             "announcementTime": 1720000000000, "adjunctUrl": "h1.pdf"},
            {"announcementTitle": "测试公司2025年年度报告（更正后）",
             "announcementTime": 1735567000000, "adjunctUrl": "fixed.pdf"},
            {"announcementTitle": "<em>测试公司</em>2025年度报告",
             "announcementTime": 1735689600000, "adjunctUrl": "main2025.pdf"},
            {"announcementTitle": "测试公司2023年年度报告",
             "announcementTime": 1700000000001, "adjunctUrl": "old2023.pdf"},
            {"announcementTime": 1739999999994, "adjunctUrl": "notitle.pdf"},
        ]
        self.assertEqual(
            fetcher._pick_annual(anns),
            {"year": 2025, "title": "测试公司2025年度报告",
             "ann_time": 1735689600000, "adjunct": "main2025.pdf"})

    def test_year_only_variant_no_nian(self):
        """"2025年度报告"（工行/神华/中石油式，无"年"字）可识别年份并参与择新"""
        anns = [
            {"announcementTitle": "工行2024年年度报告",
             "announcementTime": 100, "adjunctUrl": "a.pdf"},
            {"announcementTitle": "2025年度报告",
             "announcementTime": 200, "adjunctUrl": "b.pdf"},
        ]
        self.assertEqual(
            fetcher._pick_annual(anns),
            {"year": 2025, "title": "2025年度报告",
             "ann_time": 200, "adjunct": "b.pdf"})

    def test_empty_and_none_input(self):
        """空列表 / None → None（无候选不崩溃）"""
        self.assertIsNone(fetcher._pick_annual([]))
        self.assertIsNone(fetcher._pick_annual(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
