r"""extractor.py 单元测试（TASK-0071，含 TASK-0012 章节定位回归）。

运行方式（任选其一）：
1) 仓库根目录：
   python -X utf8 -m unittest discover -s tools/annual_report_reader/tests -t tools/annual_report_reader -p "test_*.py" -v
2) 本文件直跑：
   python tools/annual_report_reader/tests/test_extractor.py

说明与边界（夜班章程红线对照）：
- 全部输入为内存构造的页文本 list[str]（模拟"第X节 …"行、千分位数字表），
  不读取任何真实 PDF，不读写 data/output 真实数据，不触网。
- 覆盖范围：章节定位三形态与目录页跳过（TASK-0012 回归）、上下文组装与切块、
  财务表定位/单位换算/数字拆分/指标匹配防串行、extract_financials 全链路、
  markdown 渲染与兜底文案。
- 断言基线来自对当前实现的行为验证（含"第1节"不匹配、"2024"裸年份被
  \\d{1,3} 上限切分等隐含行为，用边界用例固化，实现变更时测试会明确报错）。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOL_DIR = HERE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import extractor  # noqa: E402

# ---------------------------------------------------------------- 内存构造的页文本

FIN_A = """第三节 公司简介和主要财务指标

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
扣除非经常性损益的净利润
38,000,000.00
36,000,000.00
5.56
经营活动产生的现金流量净额
50,000,000.00
55,000,000.00
-9.09
基本每股收益（元/股）
1.23
1.10
11.82
加权平均净资产收益率
19.50
18.00
增加1.50个百分点
"""

CONT_PAGE = """总资产
9,000,000,000.00
8,500,000,000.00
5.88
归属于上市公司股东的净资产
8,000,000,000.00
7,500,000,000.00
6.67
分季度主要财务指标
第一季度
1,000,000.00
"""

FIN_QIANYUAN = """第二节 主要会计数据
单位：千元
营业收入
5,000.00
4,000.00
归属于上市公司股东的净利润
800.00
700.00
"""

FIN_OVER999 = """主要会计数据
营业收入
1,200,000.00
1,000,000.00
1,500.00
"""

FIN_BARE_YEAR = """主要会计数据
营业收入
1,200,000.00
1,000,000.00
2024
"""

FIN_MERGED_LABELS = """主要会计数据
归属于上市公司股东的净利润
扣除非经常性损益的净利润
1,000,000.00
900,000.00
"""

FIN_SEPARATE_BLOCKS = """主要会计数据
归属于上市公司股东的净利润
1,000,000.00
扣除非经常性损益的净利润
900,000.00
"""

FIN_ROE_DOWN = """主要会计数据
营业收入
1,000,000.00
900,000.00
加权平均净资产收益率
15.20
15.70
减少0.50个百分点
"""


class TestMatchChapterLine(unittest.TestCase):
    """覆盖 1：_match_chapter_line 三种章节标题形态与目录行排除。"""

    def test_form1_zhongwenshuzi_section(self):
        """形态1：中文数字"第X节 标题"整行识别"""
        self.assertEqual(extractor._match_chapter_line("第一节 释义", []), "第一节 释义")

    def test_form1_with_separator(self):
        """形态1：节号与标题间的顿号分隔符被归一为空格"""
        self.assertEqual(
            extractor._match_chapter_line("第二节、重要事项", []), "第二节 重要事项")

    def test_form1_title_on_next_line(self):
        """形态1：标题拆行（"第三节"独占一行，标题在下一行）"""
        self.assertEqual(
            extractor._match_chapter_line("第三节", ["财务报告"]), "第三节 财务报告")

    def test_form1_next_line_dot_leader_rejected(self):
        """形态1：下一行是带引导点的目录行时不拼标题，返回 None"""
        self.assertIsNone(extractor._match_chapter_line("第四节", ["释义.......12"]))

    def test_arabic_section_number_not_recognized(self):
        """隐含行为固化：_JIE 正则只认中文数字，"第1节"不匹配（TASK-0012 边界）"""
        self.assertIsNone(extractor._match_chapter_line("第1节 释义", []))

    def test_compound_chinese_numeral(self):
        """形态1：复合中文数字（十一节）可识别"""
        self.assertEqual(
            extractor._match_chapter_line("第十一节 附加说明", []), "第十一节 附加说明")

    def test_form2_number_prefix_with_space(self):
        """形态2：数字编号+空格+白名单标题（"01 释义"）"""
        self.assertEqual(extractor._match_chapter_line("01 释义", []), "释义")
        self.assertEqual(extractor._match_chapter_line("1、 释义", []), "释义")
        self.assertEqual(extractor._match_chapter_line("01  前导信息", []), "前导信息")

    def test_form2_requires_space_after_separator(self):
        """形态2：编号与标题之间必须有空白，"1、释义"（无空格）不匹配（隐含行为固化）"""
        self.assertIsNone(extractor._match_chapter_line("1、释义", []))

    def test_form2_number_range_1_to_30(self):
        """形态2：编号范围收紧到 1-30，31 不再识别；标题必须命中白名单"""
        self.assertEqual(extractor._match_chapter_line("30 释义", []), "释义")
        self.assertIsNone(extractor._match_chapter_line("31 释义", []))
        self.assertIsNone(extractor._match_chapter_line("12 机械设备", []))

    def test_form3_pure_whitelist_title(self):
        """形态3：标准章节白名单标题独占一行（平安/中信模板）"""
        self.assertEqual(extractor._match_chapter_line("财务报告", []), "财务报告")

    def test_toc_line_with_dots_or_page_number(self):
        """目录行排除：带引导点或以页码结尾的行不是章节行"""
        self.assertIsNone(extractor._match_chapter_line("第一节 释义......12", []))
        self.assertIsNone(extractor._match_chapter_line("第二节 重要事项 3", []))

    def test_non_whitelist_title_rejected(self):
        """非白名单标题不识别"""
        self.assertIsNone(extractor._match_chapter_line("随便什么标题", []))


class TestNormChapterTitle(unittest.TestCase):
    """覆盖 2：_norm_chapter_title 规范化。"""

    def test_strips_punctuation_and_lowercases(self):
        """去标点、去空白、转小写（汉字保留）"""
        self.assertEqual(extractor._norm_chapter_title("（一）Section One"), "一sectionone")
        self.assertEqual(
            extractor._norm_chapter_title("公司简介和主要财务指标"),
            "公司简介和主要财务指标")


class TestHitsToRanges(unittest.TestCase):
    """覆盖 3：_hits_to_ranges 命中列表转区间。"""

    def test_basic_ranges(self):
        """相邻命中切分区间，末章延伸到最后一页"""
        self.assertEqual(
            extractor._hits_to_ranges([(0, "A"), (3, "B")], 10),
            [{"title": "A", "start": 0, "end": 2},
             {"title": "B", "start": 3, "end": 9}])
        self.assertEqual(
            extractor._hits_to_ranges([(2, "C")], 5),
            [{"title": "C", "start": 2, "end": 4}])

    def test_end_clamped_when_next_hit_on_same_page(self):
        """同页两个章节起始：前一区间 end<start 时钳制到 start"""
        self.assertEqual(
            extractor._hits_to_ranges([(5, "A"), (5, "B")], 10),
            [{"title": "A", "start": 5, "end": 5},
             {"title": "B", "start": 5, "end": 9}])


class TestChapterRangesStandard(unittest.TestCase):
    """覆盖 4：_chapter_ranges_standard（TASK-0012 回归：茅台等标准沪深模板）。"""

    PAGES = [
        "第一节 释义......1\n第二节 公司简介和主要财务指标......5\n"
        "第三节 管理层讨论与分析......9\n第四节 重要事项......20\n",
        "第一节 释义\n本节无内容。",
        "第二节 公司简介和主要财务指标\n内容",
        "第三节 管理层讨论与分析\n内容",
        "第四节 重要事项\n内容",
    ]

    def test_standard_template_locates_all_sections(self):
        """标准模板：目录页跳过、去重、起始页正确（TASK-0012 回归）"""
        ranges = extractor._chapter_ranges_standard(self.PAGES)
        self.assertEqual(ranges, [
            {"title": "第一节 释义", "start": 1, "end": 1},
            {"title": "第二节 公司简介和主要财务指标", "start": 2, "end": 2},
            {"title": "第三节 管理层讨论与分析", "start": 3, "end": 3},
            {"title": "第四节 重要事项", "start": 4, "end": 4},
        ])

    def test_page_with_three_titles_treated_as_toc(self):
        """目录页判定：一页出现 ≥3 个不同章节标题则整页跳过（即使无引导点）"""
        pages = ["第一节 释义\n第二节 重要事项\n第三节 财务报告\n",
                 "第一节 释义\n正文"]
        ranges = extractor._chapter_ranges_standard(pages)
        self.assertEqual(ranges, [{"title": "第一节 释义", "start": 1, "end": 1}])


class TestChapterRangesGenericAndFallback(unittest.TestCase):
    """覆盖 5：_chapter_ranges_generic 与 chapter_ranges 回退逻辑。"""

    def test_generic_titles(self):
        """非标模板：纯标题白名单行可定位章节"""
        pages = ["公司简介\n正文", "管理层讨论与分析\n正文",
                 "财务报告\n正文", "备查文件目录\n无"]
        self.assertEqual(extractor._chapter_ranges_generic(pages), [
            {"title": "公司简介", "start": 0, "end": 0},
            {"title": "管理层讨论与分析", "start": 1, "end": 1},
            {"title": "财务报告", "start": 2, "end": 2},
            {"title": "备查文件目录", "start": 3, "end": 3},
        ])

    def test_chapter_ranges_prefers_standard_when_three_or_more(self):
        """chapter_ranges：标准模板命中 ≥3 节时直接采用，不走 generic"""
        ranges = extractor.chapter_ranges(TestChapterRangesStandard.PAGES)
        self.assertEqual(ranges[0]["title"], "第一节 释义")
        self.assertEqual(len(ranges), 4)

    def test_chapter_ranges_falls_back_to_generic_below_three(self):
        """chapter_ranges：标准模板不足 3 节时回退 generic（数字编号/纯标题补位）"""
        pages = ["第一节 释义\n正文", "第二节 重要事项\n正文",
                 "公司简介\n01 管理层讨论与分析\n"]
        titles = [r["title"] for r in extractor.chapter_ranges(pages)]
        self.assertEqual(titles, ["第一节 释义", "第二节 重要事项",
                                  "公司简介", "管理层讨论与分析"])


class TestBuildContext(unittest.TestCase):
    """覆盖 6：build_context 封面/重要提示、财务报告截页、备查目录跳过。"""

    PAGES = [f"第{i}页正文" for i in range(10)]
    RANGES = [
        {"title": "第一节 重要提示", "start": 1, "end": 2},
        {"title": "财务报告", "start": 3, "end": 9},
        {"title": "备查文件目录", "start": 9, "end": 9},
    ]

    def test_cover_finpage_truncation_and_backup_skip(self):
        """第一章前页面作"重要提示"；财务报告截前 fin_pages 页；备查文件目录丢弃"""
        ctx = extractor.build_context(self.PAGES, self.RANGES, fin_pages=3)
        self.assertEqual(len(ctx), 3)
        self.assertEqual(ctx[0]["title"], "重要提示（封面与重要提示页）")
        self.assertEqual((ctx[0]["start"], ctx[0]["end"]), (0, 0))
        self.assertEqual(ctx[0]["pages"], ["第0页正文"])
        self.assertEqual(ctx[1]["title"], "第一节 重要提示")
        self.assertEqual(ctx[1]["pages"], ["第1页正文", "第2页正文"])
        self.assertEqual(ctx[2]["title"], "财务报告（仅审计意见与主要报表前几页）")
        self.assertEqual((ctx[2]["start"], ctx[2]["end"]), (3, 5))
        self.assertEqual(ctx[2]["pages"], ["第3页正文", "第4页正文", "第5页正文"])
        self.assertFalse(any("备查文件" in c["title"] for c in ctx))

    def test_no_cover_entry_when_first_chapter_on_page_zero(self):
        """第一章从第 0 页开始：不产生封面/重要提示条目"""
        ctx = extractor.build_context(self.PAGES[:1],
                                      [{"title": "第一节 释义", "start": 0, "end": 0}])
        self.assertEqual(ctx, [{"title": "第一节 释义", "pages": ["第0页正文"],
                                "start": 0, "end": 0}])


class TestChunkContext(unittest.TestCase):
    """覆盖 7：chunk_context 按 max_chars 切块并标注 PDF 页码。"""

    def test_multi_chunk_with_page_annotations(self):
        """累计字符超阈值即切块，块内每页带"【PDF第N页】"标注（N 为 1 起始页码）"""
        ctx = {"title": "X", "start": 2, "end": 4,
               "pages": ["a" * 10, "b" * 20, "c" * 30]}
        chunks = extractor.chunk_context(ctx, max_chars=25)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["start"], 2)
        self.assertEqual(chunks[0]["end"], 3)
        self.assertEqual(chunks[0]["text"],
                         "\n【PDF第3页】\n" + "a" * 10 + "\n【PDF第4页】\n" + "b" * 20)
        self.assertEqual(chunks[1]["start"], 4)
        self.assertEqual(chunks[1]["end"], 4)
        self.assertEqual(chunks[1]["text"], "\n【PDF第5页】\n" + "c" * 30)

    def test_single_chunk_when_content_small(self):
        """内容总量小于 max_chars：整章一块"""
        ctx = {"title": "X", "start": 0, "end": 1, "pages": ["短", "页"]}
        chunks = extractor.chunk_context(ctx, max_chars=4200)
        self.assertEqual(chunks, [{"text": "\n【PDF第1页】\n短\n【PDF第2页】\n页",
                                   "start": 0, "end": 1}])


class TestFindFinPage(unittest.TestCase):
    """覆盖 8：_find_fin_page 千分位大数判定。"""

    def test_finds_page_with_thousands_separator(self):
        """命中条件：标题关键词 + 千分位数字同时出现"""
        self.assertEqual(extractor._find_fin_page(["封面", "主要会计数据\n1,234,567.89\n"]), 1)
        self.assertEqual(extractor._find_fin_page(["主要财务数据\n15,197,799.12"]), 0)

    def test_rejects_without_thousands_separator(self):
        """只有"主要会计数据"但无千分位数字：不命中"""
        self.assertIsNone(extractor._find_fin_page(["主要会计数据\n1234567\n"]))

    def test_only_first_35_pages_scanned(self):
        """只扫描前 35 页，其后不命中"""
        pages = ["x"] * 40
        pages[38] = "主要会计数据\n1,234,567.00\n"
        self.assertIsNone(extractor._find_fin_page(pages))


class TestUnitMultiplier(unittest.TestCase):
    """覆盖 9：_unit_multiplier 表头单位 → 元的换算倍数与优先级。"""

    def test_all_unit_labels(self):
        """百万元/千元/万元/亿元 各自识别，无标注按元"""
        cases = [
            (["单位：百万元"], 1e6),
            (["（人民币千元）"], 1e3),
            (["单位：万元"], 1e4),
            (["单位：亿元"], 1e8),
            (["没有任何单位标注"], 1.0),
        ]
        for text_pages, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(extractor._unit_multiplier(text_pages, 0), expected)

    def test_baiwan_priority_over_wan(self):
        """优先级：百万元 > 千元 > 万元 > 亿元（同页并存时取先判的百万元）"""
        self.assertEqual(extractor._unit_multiplier(["单位：万元\n百万元"], 0), 1e6)


class TestSplitNums(unittest.TestCase):
    """覆盖 10：_split_nums 数字拆分。"""

    def test_basic_negative_and_multiple(self):
        """千分位、小数、负数、一行多数字"""
        self.assertEqual(extractor._split_nums("1,234,567.89 2,000.5", 2),
                         [1234567.89, 2000.5])
        self.assertEqual(extractor._split_nums("-1,000.25", 2), [-1000.25])
        self.assertEqual(extractor._split_nums("19.50 18.00 1.50", 2), [19.5, 18.0, 1.5])

    def test_stuck_numbers_from_pdf_export(self):
        """容忍 PDF 导出数字粘连：一串文本拆出两个数"""
        self.assertEqual(
            extractor._split_nums("317,508,901.42119,804,210.22", 2),
            [317508901.42, 119804210.22])

    def test_no_numbers_returns_empty(self):
        """无数字文本返回空列表"""
        self.assertEqual(extractor._split_nums("abc 无数字", 2), [])


class TestTableBlocks(unittest.TestCase):
    """覆盖 11：_table_blocks 标签行+数字行切块。"""

    def test_label_then_numbers_grouping(self):
        """连续数字行归并进同一块，新标签行冲刷上一块"""
        blocks = extractor._table_blocks("指标名称\n1,000\n2,000\n文字说明\n3,000\n")
        self.assertEqual(blocks, ["指标名称\n1,000\n2,000", "文字说明\n3,000"])

    def test_pure_text_dropped(self):
        """无数字的纯文字块丢弃"""
        self.assertEqual(extractor._table_blocks("纯文字\n没有数字"), [])


class TestMatchBlock(unittest.TestCase):
    """覆盖 12：_match_block 指标-块匹配防串行。"""

    def test_yingmu_excluded_from_koufei_block(self):
        """归母净利润 ≠ 扣非净利润：同块含扣非字样时归母不命中，扣非命中"""
        norm = "归属于上市公司股东的净利润扣除非经常性损益的净利润1000000900000"
        self.assertFalse(extractor._match_block("归属于上市公司股东的净利润", norm))
        self.assertTrue(extractor._match_block("扣除非经常性损益", norm))

    def test_zongzichan_excluded_from_jingzichan_block(self):
        """总资产 ≠ 净资产：同块含净资产/归属股东字样时总资产不命中"""
        norm = "总资产归属于上市公司股东的净资产8000000"
        self.assertFalse(extractor._match_block("总资产", norm))
        self.assertTrue(extractor._match_block("归属于上市公司股东的净资产", norm))
        self.assertTrue(extractor._match_block("总资产", "总资产9000000"))

    def test_eps_roe_excluded_from_koufei_block(self):
        """每股收益/ROE ≠ 扣非变体：同块含扣非字样时不命中"""
        self.assertFalse(extractor._match_block(
            "基本每股收益", "基本每股收益扣除非经常性损益后的每股收益1.5"))
        self.assertFalse(extractor._match_block(
            "加权平均净资产收益率", "加权平均净资产收益率扣除非经常性损益19.5"))

    def test_plain_label_matching(self):
        """普通命中：label 是块文本子串即命中"""
        self.assertTrue(extractor._match_block("营业收入", "营业收入12345"))
        self.assertFalse(extractor._match_block("营业收入", "其他收入123"))


class TestExtractFinancials(unittest.TestCase):
    """覆盖 13：extract_financials 全链路（单位换算、同比 stated/推算、防串行）。"""

    def test_standard_table_all_stated(self):
        """标准表：6 项指标全提取，第 3 列 ≤999 视为原文同比（yoy_stated=True）"""
        fin, fin_page = extractor.extract_financials([FIN_A])
        self.assertEqual(fin_page, 0)
        self.assertEqual(fin["营业收入"],
                         {"current": 123456789.01, "previous": 110000000.0,
                          "yoy": 12.23, "yoy_stated": True})
        self.assertEqual(fin["归母净利润"],
                         {"current": 45000000.0, "previous": 40000000.0,
                          "yoy": 12.5, "yoy_stated": True})
        self.assertEqual(fin["扣非净利润"],
                         {"current": 38000000.0, "previous": 36000000.0,
                          "yoy": 5.56, "yoy_stated": True})
        self.assertEqual(fin["经营现金流净额"],
                         {"current": 50000000.0, "previous": 55000000.0,
                          "yoy": -9.09, "yoy_stated": True})
        self.assertEqual(fin["基本每股收益"],
                         {"current": 1.23, "previous": 1.1,
                          "yoy": 11.82, "yoy_stated": True})
        self.assertEqual(fin["加权平均ROE"],
                         {"current": 19.5, "previous": 18.0, "yoy_points": 1.5})
        self.assertNotIn("总资产", fin)  # 本页无总资产行

    def test_cross_page_continuation_with_quarter_cutoff(self):
        """跨页续表：下一页取到"分季度"之前，总资产/归母净资产续提，分季度数字不混入"""
        fin, fin_page = extractor.extract_financials([FIN_A, CONT_PAGE])
        self.assertEqual(fin_page, 0)
        self.assertEqual(fin["总资产"],
                         {"current": 9000000000.0, "previous": 8500000000.0,
                          "yoy": 5.88, "yoy_stated": True})
        self.assertEqual(fin["归母净资产"],
                         {"current": 8000000000.0, "previous": 7500000000.0,
                          "yoy": 6.67, "yoy_stated": True})

    def test_qianyuan_unit_multiplier_and_computed_yoy(self):
        """表头"单位：千元"：元类指标 ×1000；仅两期数时同比推算（yoy_stated=False）"""
        fin, _ = extractor.extract_financials([FIN_QIANYUAN])
        self.assertEqual(fin["营业收入"],
                         {"current": 5000000.0, "previous": 4000000.0,
                          "yoy": 25.0, "yoy_stated": False})
        self.assertEqual(fin["归母净利润"],
                         {"current": 800000.0, "previous": 700000.0,
                          "yoy": 14.29, "yoy_stated": False})

    def test_yoy_third_column_over_999_falls_back_to_computed(self):
        """第 3 列异常大（>999，如 "1,500.00"）不当作同比，改按两期数推算"""
        fin, _ = extractor.extract_financials([FIN_OVER999])
        self.assertEqual(fin["营业收入"],
                         {"current": 1200000.0, "previous": 1000000.0,
                          "yoy": 20.0, "yoy_stated": False})

    def test_bare_year_number_split_quirk(self):
        """隐含行为固化：裸 4 位年份 "2024" 被 \\d{1,3} 上限切成 202+4，
        第 3 列 202 ≤999 仍按原文同比收录（yoy=202.0, stated=True）"""
        fin, _ = extractor.extract_financials([FIN_BARE_YEAR])
        self.assertEqual(fin["营业收入"],
                         {"current": 1200000.0, "previous": 1000000.0,
                          "yoy": 202.0, "yoy_stated": True})

    def test_merged_labels_guard_excludes_yingmu(self):
        """防串行：归母/扣非标签连排同块时，归母被守卫排除，扣非按首两数提取"""
        fin, _ = extractor.extract_financials([FIN_MERGED_LABELS])
        self.assertNotIn("归母净利润", fin)
        self.assertEqual(fin["扣非净利润"],
                         {"current": 1000000.0, "previous": 900000.0,
                          "yoy": 11.11, "yoy_stated": False})

    def test_separate_blocks_previous_missing_yoy_none(self):
        """分块正常时：上一期缺数则 yoy=None（不做推算、不误标原文同比）"""
        fin, _ = extractor.extract_financials([FIN_SEPARATE_BLOCKS])
        self.assertEqual(fin["归母净利润"],
                         {"current": 1000000.0, "previous": None,
                          "yoy": None, "yoy_stated": False})
        self.assertEqual(fin["扣非净利润"],
                         {"current": 900000.0, "previous": None,
                          "yoy": None, "yoy_stated": False})

    def test_roe_decrease_points(self):
        """ROE：current/previous/"减少X个百分点"→ yoy_points 为负"""
        fin, _ = extractor.extract_financials([FIN_ROE_DOWN])
        self.assertEqual(fin["加权平均ROE"],
                         {"current": 15.2, "previous": 15.7, "yoy_points": -0.5})
        self.assertEqual(fin["营业收入"]["yoy"], 11.11)  # 推算：(100-90)/90*100

    def test_no_table_returns_empty(self):
        """无"主要会计数据"表：返回 ({}, None)"""
        self.assertEqual(extractor.extract_financials(["封面页", "随便"]), ({}, None))

    def test_multiplier_plumbing_mocked(self):
        """单位倍数装配：mock _unit_multiplier=100 后元类指标按倍数换算（每股类不变）"""
        with mock.patch.object(extractor, "_unit_multiplier",
                               return_value=100.0) as mult_mock:
            fin, fin_page = extractor.extract_financials([FIN_SEPARATE_BLOCKS])
        mult_mock.assert_called_once_with([FIN_SEPARATE_BLOCKS], fin_page)
        self.assertEqual(fin["归母净利润"]["current"], 100000000.0)
        self.assertEqual(fin["扣非净利润"]["current"], 90000000.0)


class TestFmtHelpers(unittest.TestCase):
    """覆盖 14：_fmt_yi / _fmt_share 数值格式化。"""

    def test_fmt_yi(self):
        """≥1亿 转亿、≥1万 转万、其余原样；负数与 None"""
        cases = [
            (1.2e9, "12.00 亿"), (1.1e9, "11.00 亿"), (5e7, "5,000.00 万"),
            (1234.5, "1,234.50"), (-2e8, "-2.00 亿"), (None, "-"), (0, "0.00"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(extractor._fmt_yi(value), expected)

    def test_fmt_share(self):
        """每股类：4 位小数去尾零；None 为 -；0 为 "0" """
        cases = [
            (1.23, "1.23"), (1.10, "1.1"), (0.0, "0"), (None, "-"),
            (12.0, "12"), (1234.5678, "1,234.5678"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(extractor._fmt_share(value), expected)


class TestFinancialTableMd(unittest.TestCase):
    """覆盖 15：financial_table_md markdown 渲染与兜底。"""

    def test_full_table_rendering(self):
        """全指标渲染：亿/万换算、stated/推算同比、缺项"提取失败"行、页码标注"""
        fin = {
            "营业收入": {"current": 1.2e9, "previous": 1.1e9,
                        "yoy": 9.09, "yoy_stated": True},
            "归母净利润": {"current": 3.0e8, "previous": None,
                          "yoy": None, "yoy_stated": False},
            "扣非净利润": {"current": 2.8e8, "previous": 2.6e8,
                          "yoy": -3.5, "yoy_stated": False},
            "经营现金流净额": {"current": 5e7, "previous": 4e7,
                              "yoy": 25.0, "yoy_stated": True},
            "基本每股收益": {"current": 1.2300, "previous": 1.1000,
                            "yoy": 11.82, "yoy_stated": True},
        }
        expected = (
            "| 指标 | 本期 | 上年同期 | 同比 |\n"
            "|---|---|---|---|\n"
            "| 营业收入（元） | 12.00 亿 | 11.00 亿 | +9.09% |\n"
            "| 归属于上市公司股东的净利润（元） | 3.00 亿 | - | - |\n"
            "| 扣除非经常性损益（元） | 2.80 亿 | 2.60 亿 | -3.50%（推算） |\n"
            "| 经营活动产生的现金流量净额（元） | 5,000.00 万 | 4,000.00 万 | +25.00% |\n"
            "| 基本每股收益（元/股） | 1.23 | 1.1 | +11.82% |\n"
            "| 加权平均净资产收益率（%） | 提取失败 | - | - |\n"
            "| 总资产（元） | 提取失败 | - | - |\n"
            "| 归属于上市公司股东的净资产（元） | 提取失败 | - | - |\n"
            "\n"
            "（提取自年报“主要会计数据”表，PDF 第 8 页）"
        )
        self.assertEqual(extractor.financial_table_md(fin, 7), expected)

    def test_roe_row_rendering(self):
        """ROE 行：百分比两位小数；yoy_points 带正负号"个百分点"；None 为 -；无页码标注"""
        md = extractor.financial_table_md(
            {"加权平均ROE": {"current": 19.5, "previous": 18.0, "yoy_points": -0.5}},
            None)
        self.assertIn("| 加权平均净资产收益率（%） | 19.50% | 18.00% | -0.50 个百分点 |", md)
        md_pos = extractor.financial_table_md(
            {"加权平均ROE": {"current": 19.5, "previous": 18.0, "yoy_points": 1.5}},
            None)
        self.assertIn("| 19.50% | 18.00% | +1.50 个百分点 |", md_pos)
        md_no_pts = extractor.financial_table_md(
            {"加权平均ROE": {"current": 19.5, "previous": 18.0}}, None)
        self.assertIn("| 19.50% | 18.00% | - |", md_no_pts)
        self.assertNotIn("PDF 第", md)

    def test_fallback_when_no_financials(self):
        """提取失败兜底：固定文案，不随 fin_page 变化"""
        fallback = ("| 指标 | 本期 | 上年同期 | 同比 |\n|---|---|---|---|\n"
                    "| - | 自动提取失败，请人工核对年报原文 | - | - |")
        self.assertEqual(extractor.financial_table_md({}, None), fallback)
        self.assertEqual(extractor.financial_table_md({}, 5), fallback)


if __name__ == "__main__":
    unittest.main(verbosity=2)
