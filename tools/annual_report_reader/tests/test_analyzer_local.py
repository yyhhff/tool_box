r"""analyzer_local.py 单元测试（零 GLM 本地带读的纯逻辑部分）。

运行方式（任选其一）：
1) 仓库根目录：
   python -X utf8 -m unittest discover -s tools/annual_report_reader/tests -t tools/annual_report_reader -p "test_*.py" -v
2) 本文件直跑：
   python tools/annual_report_reader/tests/test_analyzer_local.py

说明与边界（夜班章程红线对照）：
- 只测 analyzer_local 的规则/模板函数，不触碰 analyzer.py（GLM 计费、读注册表），
  不调用任何 LLM，不读 ZHIPU_API_KEY。
- 页文本全部内存构造；与 extractor 的联动（财务表提取、原文摘句）使用与
  test_extractor.py 同源的构造数据，保证端到端模板回归可信。
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_DIR = HERE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import analyzer_local  # noqa: E402
import extractor  # noqa: E402

# ---------------------------------------------------------------- 内存构造数据

FIN_PAGE = """第三节 公司简介和主要财务指标

主要会计数据
本年度 上年度 增减
营业收入
123,456,789.01
110,000,000.00
12.23
归属于上市公司股东的净利润
45,000,000.00
40,000,000.00
12.50
"""

MD_PAGE = ("董事会报告：公司全年经营稳健，订单持续增长，分红方案积极。\n"
           "公司存在重大诉讼风险事项需要投资者关注。\n")

META = {"name": "测试公司", "code": "600519", "year": 2025, "industry": "食品饮料",
        "title": "测试公司2025年年度报告", "ann_date": "2026-03-01"}


class TestYiAndPct(unittest.TestCase):
    """覆盖 1：_yi / _pct 数值格式化与异常值兜底。"""

    def test_yi_unit_conversion(self):
        """≥1亿 转亿元、≥1万 转万元、其余两位小数千分位；负数带符号"""
        cases = [
            (1.2e9, "12.00 亿元"), (123456, "12.35 万元"), (1234.5, "1,234.50"),
            (1e8, "1.00 亿元"), (-5e4, "-5.00 万元"), (0, "0.00"),
            (9999.0, "9,999.00"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(analyzer_local._yi(value), expected)

    def test_yi_none_and_bad_input(self):
        """None / 非数值字符串兜底为"—"（不抛异常）"""
        self.assertEqual(analyzer_local._yi(None), "—")
        self.assertEqual(analyzer_local._yi("abc"), "—")

    def test_pct_formats_and_fallbacks(self):
        """同比带正负号两位小数；None/非 dict/异常值兜底"—" """
        self.assertEqual(analyzer_local._pct({"yoy": 5.234}), "+5.23%")
        self.assertEqual(analyzer_local._pct({"yoy": -3.456}), "-3.46%")
        self.assertEqual(analyzer_local._pct({"yoy": None}), "—")
        self.assertEqual(analyzer_local._pct({}), "—")
        self.assertEqual(analyzer_local._pct(None), "—")
        self.assertEqual(analyzer_local._pct({"yoy": "abc"}), "—")


class TestQuickView(unittest.TestCase):
    """覆盖 2：_quick_view 30 秒速览（数字驱动 + 波动最大项）。"""

    FIN = {
        "营业收入": {"current": 1.2e9, "previous": 1.1e9,
                    "yoy": 10.0, "yoy_stated": True},
        "归母净利润": {"current": 6.0e8, "previous": 5.2e8,
                     "yoy": 15.0, "yoy_stated": True},
        "加权平均ROE": {"current": 19.5, "yoy_points": 1.5},
    }

    def test_full_quick_view_lines(self):
        """公司/营收净利/ROE/波动最大项四行齐全，文案与数字精确"""
        lines = analyzer_local._quick_view(
            {"name": "贵州茅台", "code": "600519", "industry": "食品饮料"}, self.FIN)
        self.assertEqual(lines, [
            "- 公司做什么：贵州茅台（600519），所属申万「食品饮料」行业。",
            "- 今年赚不赚钱：营业收入 12.00 亿元，同比 +10.00%；"
            "归母净利润 6.00 亿元，同比 +15.00%。",
            "- 股东回报：加权平均 ROE 19.50%（同比 +1.50 个百分点）。",
            "- 波动最大项：归母净利润同比增长 15.00%（详见下方财务表）。",
        ])

    def test_without_roe_and_np(self):
        """缺 ROE 不出股东回报行；缺归母净利润时占位"—"；波动最大项回落到营收"""
        meta = {"name": "贵州茅台", "code": "600519", "industry": "食品饮料"}
        lines = analyzer_local._quick_view(
            meta, {"营业收入": {"current": 1.2e9, "yoy": 10.0, "yoy_stated": True}})
        self.assertEqual(lines[0], "- 公司做什么：贵州茅台（600519），所属申万「食品饮料」行业。")
        self.assertIn("归母净利润 —，同比 —。", lines[1])
        self.assertFalse(any("股东回报" in line for line in lines))
        self.assertEqual(lines[-1],
                         "- 波动最大项：营业收入同比增长 10.00%（详见下方财务表）。")

    def test_negative_biggest_mover(self):
        """波动最大项取 |yoy| 最大者；负同比用"下降" """
        lines = analyzer_local._quick_view(
            {"name": "贵州茅台", "code": "600519", "industry": "食品饮料"},
            {"营业收入": {"current": 1.0, "yoy": 10.0, "yoy_stated": True},
             "归母净利润": {"current": 1.0, "yoy": -20.0, "yoy_stated": True}})
        self.assertEqual(lines[-1],
                         "- 波动最大项：归母净利润同比下降 20.00%（详见下方财务表）。")


class TestNarrative(unittest.TestCase):
    """覆盖 3：_narrative 业绩带读（stated/推算注记、方向措辞）。"""

    FIN = {
        "营业收入": {"current": 1.2e9, "previous": 1.1e9,
                    "yoy": 9.09, "yoy_stated": False},
        "归母净利润": {"current": 6.0e8, "previous": 5.2e8,
                     "yoy": 15.0, "yoy_stated": True},
        "经营现金流净额": {"current": 5e7, "previous": 4e7,
                        "yoy": -25.0, "yoy_stated": True},
        "扣非净利润": {"current": 100.0, "previous": 90.0},
    }

    def test_stated_and_inferred_lines(self):
        """非 stated 同比带"（按原文两期数推算）"注记；stated 不带；缺同比只报两期数"""
        self.assertEqual(analyzer_local._narrative(self.FIN), [
            "- 营业收入：本期 12.00 亿元，上年同期 11.00 亿元，"
            "同比增长 9.09%（按原文两期数推算）。",
            "- 归母净利润：本期 6.00 亿元，上年同期 5.20 亿元，同比增长 15.00%。",
            "- 扣非净利润：本期 100.00，上年同期 90.00。",
            "- 经营活动现金流净额：本期 5,000.00 万元，上年同期 4,000.00 万元，"
            "同比净流入减少 25.00%。",
        ])

    def test_missing_current_skipped(self):
        """无本期数的指标跳过；空 fin 返回空列表"""
        self.assertEqual(
            analyzer_local._narrative({"营业收入": {"current": None, "yoy": 5.0}}), [])
        self.assertEqual(analyzer_local._narrative({}), [])


class TestExtractSentences(unittest.TestCase):
    """覆盖 4：_extract_sentences 关键词摘句（页码标注、去重、截断、limit）。"""

    PAGES = [
        "第一条内容没有关键词。\n公司新产能顺利投产并实现量产，订单持续增长。\n短句。\n",
        "公司计提减值准备存在不确定性风险。\n" + "长" * 50 + "。业绩增长。尾部\n",
    ]
    RANGES = [{"title": "管理层讨论与分析", "start": 0, "end": 1}]

    def test_pos_sentences_with_page_annotation(self):
        """看点句：命中关键词、长度 12-260 过滤、截到句末、附 1 起始 PDF 页码"""
        out = analyzer_local._extract_sentences(
            self.PAGES, self.RANGES, analyzer_local._POS_KW, limit=5)
        self.assertEqual(out, [
            "- 公司新产能顺利投产并实现量产，订单持续增长。【PDF 第 1 页】",
            "- " + "长" * 50 + "。业绩增长。【PDF 第 2 页】",
        ])

    def test_risk_sentences(self):
        """风险句：命中"计提/减值/风险/不确定性"关键词"""
        out = analyzer_local._extract_sentences(
            self.PAGES, self.RANGES, analyzer_local._RISK_KW, limit=5)
        self.assertEqual(
            out, ["- 公司计提减值准备存在不确定性风险。【PDF 第 2 页】"])

    def test_dedup_within_same_page(self):
        """同页重复行去重（页码相同才能去重，跨页页码不同属预期不去重）"""
        pages = ["公司持续增长态势良好，市场份额稳步提升。\n"
                 "公司持续增长态势良好，市场份额稳步提升。\n"]
        out = analyzer_local._extract_sentences(
            pages, [{"title": "X", "start": 0, "end": 0}], analyzer_local._POS_KW)
        self.assertEqual(len(out), 1)

    def test_limit(self):
        """limit 截断输出条数，保持页内顺序"""
        pages = ["公司本期营业收入增长情况说明甲。\n"
                 "公司本期营业收入增长情况说明乙。\n"
                 "公司本期营业收入增长情况说明丙。\n"]
        out = analyzer_local._extract_sentences(
            pages, [{"title": "X", "start": 0, "end": 0}],
            analyzer_local._POS_KW, limit=2)
        self.assertEqual(out, [
            "- 公司本期营业收入增长情况说明甲。【PDF 第 1 页】",
            "- 公司本期营业收入增长情况说明乙。【PDF 第 1 页】",
        ])

    def test_overlong_and_short_lines_skipped(self):
        """超过 260 字符与不足 12 字符的行均跳过"""
        out = analyzer_local._extract_sentences(
            ["增" * 300 + "\n"], [{"title": "X", "start": 0, "end": 0}],
            analyzer_local._POS_KW)
        self.assertEqual(out, [])
        out_short = analyzer_local._extract_sentences(
            ["增长。\n"], [{"title": "X", "start": 0, "end": 0}], analyzer_local._POS_KW)
        self.assertEqual(out_short, [])


class TestAnalyzeCompanyLocal(unittest.TestCase):
    """覆盖 5：analyze_company_local 模板回归与 FIN_TABLE 占位替换。"""

    def test_template_regression(self):
        """报告头、固定小节、财务表替换、页码索引、原文摘句与免责声明"""
        report = analyzer_local.analyze_company_local(
            META, [FIN_PAGE, MD_PAGE],
            [{"title": "管理层讨论与分析", "start": 1, "end": 1}], progress=None)
        self.assertTrue(report.startswith(
            "# 测试公司（600519）2025 年年报带读\n\n"
            "> 行业：食品饮料 ｜ 年报标题：测试公司2025年年度报告"
            " ｜ 披露日期：2026-03-01 ｜ 分析方式：本地程序（未调用大模型）\n\n"))
        self.assertNotIn("<<<FIN_TABLE>>>", report)
        self.assertIn("| 指标 | 本期 | 上年同期 | 同比 |", report)
        self.assertIn("| 营业收入（元） | 1.23 亿 | 1.10 亿 | +12.23% |", report)
        for section in ("## 30 秒速览", "## 业绩带读", "## 业务与经营（原文摘录）",
                        "## 风险与重要事项（原文摘录）", "## 分红与股东回报",
                        "## 行情视角", "## 页码索引"):
            self.assertIn(section, report)
        self.assertIn("主要会计数据表：PDF 第 1 页", report)
        self.assertIn("- 董事会报告：公司全年经营稳健，订单持续增长，分红方案积极。"
                      "【PDF 第 2 页】", report)  # 看点摘句进入正文
        self.assertIn("- 公司存在重大诉讼风险事项需要投资者关注。【PDF 第 2 页】",
                      report)  # 风险摘句进入正文
        self.assertIn("| 加权平均净资产收益率（%） | 提取失败 | - | - |", report)
        self.assertTrue(report.endswith(analyzer_local.DISCLAIMER))

    def test_empty_pages_fallback(self):
        """无财务表/无摘句：兜底文案齐全，不出页码索引行"""
        report = analyzer_local.analyze_company_local(
            META, [""], [{"title": "第一节 释义", "start": 0, "end": 0}], progress=None)
        self.assertIn("自动提取失败，请人工核对年报原文", report)
        self.assertIn("关键财务指标自动提取失败，请以年报原文为准。", report)
        self.assertIn("未定位到含明确经营看点的原文段落，请查阅年报原文。", report)
        self.assertIn("未定位到含明确风险表述的原文段落，请查阅年报原文。", report)
        self.assertNotIn("主要会计数据表：PDF 第", report)

    def test_progress_callback_invoked(self):
        """progress 回调被逐步调用（财务提取、原文摘句）"""
        logs = []
        analyzer_local.analyze_company_local(
            META, [""], [{"title": "第一节 释义", "start": 0, "end": 0}],
            progress=logs.append)
        self.assertEqual(logs[:2], ["  本地提取财务数字...",
                                    "  本地摘录原文要点（看点/风险）..."])


class TestAnalyzeCrossIndustry(unittest.TestCase):
    """覆盖 6：analyze_cross_industry 横向表、排序、失败行标注。"""

    MATERIALS = [
        {"name": "A公司", "code": "600001", "industry": "行业一", "fin": {
            "营业收入": {"current": 1.5e9, "yoy": 12.0},
            "归母净利润": {"current": 3e8, "yoy": 8.0},
            "加权平均ROE": {"current": 15.0},
            "经营现金流净额": {"current": 2e8}}},
        {"name": "B公司", "code": "000002", "industry": "行业二", "year": 2024, "fin": {
            "营业收入": {"current": 8e8, "yoy": -5.0},
            "归母净利润": {"current": 1e8, "yoy": -10.0}}},
        {"name": "C公司", "code": "300003", "industry": "行业三", "fin": {}},
    ]

    def test_rows_rank_and_summary(self):
        """表行/非主流年份注记/失败行/客观排序/总览计数"""
        report = analyzer_local.analyze_cross_industry(self.MATERIALS, 2025, progress=None)
        self.assertTrue(report.startswith(
            "# 申万一级 31 行业龙头横向对比（2025 年报）\n"))
        self.assertIn(
            "实际纳入 2 家（成功提取财务数字），1 家提取失败或年报缺失（表中如实标注）。",
            report)
        self.assertIn("| 行业一 | A公司（600001） | 15.00 亿元 | +12.00% | "
                      "3.00 亿元 | +8.00% | 15.00% | 2.00 亿元 |", report)
        self.assertIn("| 行业二 | B公司（000002）（2024年报） | 8.00 亿元 | -5.00% | "
                      "1.00 亿元 | -10.00% | — | — |", report)
        self.assertIn("| 行业三 | C公司（300003） | 提取失败 | — | — | — | — |", report)
        self.assertIn("- 营业收入前三：A公司（15.00 亿元，行业一）、"
                      "B公司（8.00 亿元，行业二）。", report)
        self.assertIn("- 归母净利润前三：A公司（3.00 亿元，行业一）、"
                      "B公司（1.00 亿元，行业二）。", report)

    def test_glossary_and_disclaimer(self):
        """名词解释固定文案收尾 + 免责声明结尾"""
        report = analyzer_local.analyze_cross_industry(self.MATERIALS, 2025, progress=None)
        self.assertIn("## 五、名词解释（小白版）", report)
        self.assertIn("| 申万一级行业 | 券商给全市场股票分的 31 个大类，"
                      "本表每个大类挑市值最大的一家作代表。 |", report)
        self.assertTrue(report.endswith(analyzer_local.DISCLAIMER))


if __name__ == "__main__":
    unittest.main(verbosity=2)
