"""extractor.py - 年报 PDF 文本提取、章节定位与财务摘要数字抽取。

财务摘要表（主要会计数据）的数字用正则从原文提取，供报告原样引用；
LLM 只负责解读这些数字，不负责生成数字（反幻觉）。
"""

from __future__ import annotations

import re

try:
    import pymupdf as fitz  # PyMuPDF 新版
except ImportError:  # 旧版包名
    import fitz

# 指标顺序即年报"主要会计数据"表常见顺序（顺序遍历，避免扣非/归母串行）
_FIN_METRICS = [
    ("营业收入", "营业收入", "元"),
    ("归母净利润", "归属于上市公司股东的净利润", "元"),
    ("扣非净利润", "扣除非经常性损益", "元"),
    ("经营现金流净额", "经营活动产生的现金流量净额", "元"),
    ("基本每股收益", "基本每股收益", "元/股"),
    ("加权平均ROE", "加权平均净资产收益率", "%"),
    ("总资产", "总资产", "元"),
    ("归母净资产", "归属于上市公司股东的净资产", "元"),
]

_JIE = r"第[一二三四五六七八九十百]+节"
_DOTS = re.compile(r"\.{2,}|…+")

# A 股年报一级章节标准标题（交易所格式指引各版本 + 保险/券商特有模板）。
# 非"第X节"模板（如平安/人寿/中信证券）用这些标题的独立行定位章节。
_CHAPTER_TITLES = {
    "释义", "公司简介和主要财务指标", "公司情况和主要财务指标", "公司简介",
    "管理层讨论与分析", "经营情况讨论与分析", "经营情况讨论及分析",
    "公司治理", "公司治理环境和社会", "公司治理和社会责任", "公司管治",
    "重要事项", "股份变动及股东情况", "股本变动及股东情况", "债券相关情况",
    "财务报告", "财务报表", "备查文件目录", "董事长致辞", "致股东的信",
    "公司信息", "关于我们", "其他信息", "前导信息", "内含价值",
    "董事会报告", "监事会报告", "环境和社会责任", "可持续发展",
    "证券公司信息披露", "附录", "财务摘要", "核心竞争力",
}
_PUNCT = re.compile(r"[\s、，,：:．.（）()·—\-“”\"'‘’《》「」\[\]【】]")


def _norm_chapter_title(s: str) -> str:
    """规范化章节标题用于白名单比对（去标点/空白/引号）。"""
    return _PUNCT.sub("", s).lower()


class ScannedPdfError(Exception):
    """疑似扫描件，无可提取文本。"""


def load_pages(pdf_path) -> list[str]:
    """按页提取 PDF 文本。"""
    doc = fitz.open(str(pdf_path))
    try:
        pages = [p.get_text("text") or "" for p in doc]
    finally:
        doc.close()
    total = sum(len(p.strip()) for p in pages)
    if total == 0 or (len(pages) >= 20 and total < 2000):
        raise ScannedPdfError(
            f"{pdf_path} 疑似扫描件（共 {len(pages)} 页、可提取文本 {total} 字符），无法带读")
    return pages


def _match_chapter_line(line: str, next_lines: list[str]) -> str | None:
    """识别单行章节标题，返回规范化的章节名；非章节行返回 None。

    支持三种模板：
      1) "第X节 标题"（含"第X节"与标题拆成两行）—— 标准沪深模板
      2) "01 标题" / "1、标题" —— 人寿等数字编号模板
      3) "标题" 独占一行且命中标准章节白名单 —— 平安/中信等纯标题模板
    """
    s = line.strip()
    if not s or _DOTS.search(s) or re.search(r"\d+\s*$", s):
        return None  # 目录行一般带引导点或以页码结尾

    # 形态 1：第X节 标题
    m = re.match(rf"^({_JIE})\s*[、：:．.]?\s*(\S.{{0,24}})?$", s)
    if m:
        rest = (m.group(2) or "").strip()
        if not rest:  # 标题在下一行
            for nxt in next_lines:
                t = nxt.strip()
                if t and not _DOTS.search(t) and not re.search(r"\d+\s*$", t):
                    rest = t
                    break
        if rest:
            return f"{m.group(1)} {rest}"

    # 形态 2：数字编号 + 标题（"01 前导信息"/"1、释义"），编号范围收紧避免误伤正文
    m2 = re.match(r"^(\d{1,2})\s*[、.．]?\s+(\S.{0,24})$", s)
    if m2 and 1 <= int(m2.group(1)) <= 30:
        rest = m2.group(2).strip()
        if _norm_chapter_title(rest) in {_norm_chapter_title(t) for t in _CHAPTER_TITLES}:
            return rest

    # 形态 3：纯标题独立行，命中标准章节白名单
    if _norm_chapter_title(s) in {_norm_chapter_title(t) for t in _CHAPTER_TITLES}:
        return s
    return None


def _hits_to_ranges(hits: list[tuple[int, str]], page_count: int) -> list[dict]:
    """把 (起始页, 标题) 命中列表转成 [{title, start, end}]。"""
    ranges = []
    for k, (start, title) in enumerate(hits):
        end = hits[k + 1][0] - 1 if k + 1 < len(hits) else page_count - 1
        if end < start:
            end = start
        ranges.append({"title": title, "start": start, "end": end})
    return ranges


def _chapter_ranges_standard(pages: list[str]) -> list[dict]:
    """标准沪深模板：只认"第X节 标题"（含拆行）。茅台等走此路径。"""
    hits: list[tuple[int, str]] = []
    seen: set[str] = set()
    for i, text in enumerate(pages):
        lines = text.splitlines()
        page_titles: list[str] = []
        for k, line in enumerate(lines):
            s = line.strip()
            if not s or _DOTS.search(s) or re.search(r"\d+\s*$", s):
                continue
            m = re.match(rf"^({_JIE})\s*[、：:．.]?\s*(\S{{1,24}})?$", s)
            if not m:
                continue
            rest = (m.group(2) or "").strip()
            if not rest:
                for nxt in lines[k + 1:k + 4]:
                    t = nxt.strip()
                    if t and not _DOTS.search(t) and not re.search(r"\d+\s*$", t):
                        rest = t
                        break
            if rest:
                page_titles.append(f"{m.group(1)} {rest}")
        if len(set(page_titles)) >= 3:  # 目录页
            continue
        for title in page_titles:
            if title not in seen:
                seen.add(title)
                hits.append((i, title))
    return _hits_to_ranges(hits, len(pages))


def _chapter_ranges_generic(pages: list[str]) -> list[dict]:
    """非标模板：数字编号+标题 / 纯标题独立行（平安、人寿、中信证券等）。"""
    hits: list[tuple[int, str]] = []
    seen: set[str] = set()
    for i, text in enumerate(pages):
        lines = text.splitlines()
        page_titles: list[str] = []
        for k, line in enumerate(lines):
            title = _match_chapter_line(line, lines[k + 1:k + 4])
            if title:
                page_titles.append(title)
        # 目录页：一页出现 ≥3 个不同章节标题
        norm_set = {_norm_chapter_title(t) for t in page_titles}
        if len(norm_set) >= 3:
            continue
        for title in page_titles:
            key = _norm_chapter_title(title) or title
            if key not in seen:
                seen.add(key)
                hits.append((i, title))
    return _hits_to_ranges(hits, len(pages))


def chapter_ranges(pages: list[str]) -> list[dict]:
    """定位各章节起始页（跳过目录页），返回 [{title, start, end}]。

    优先标准"第X节"模板（保证茅台等不回归）；不足 3 节时回退到
    数字编号/纯标题模板（平安、人寿、中信证券等保险/券商非标年报）。
    """
    ranges = _chapter_ranges_standard(pages)
    if len(ranges) >= 3:
        return ranges
    return _chapter_ranges_generic(pages)


def build_context(pages: list[str], ranges: list[dict], fin_pages: int = 8) -> list[dict]:
    """把章节整理成喂给 LLM 的上下文；财务报告节只取前 fin_pages 页（审计意见+主表）。"""
    out = []
    first_start = ranges[0]["start"] if ranges else len(pages)
    if first_start > 0:
        # 第一章之前的页面（封面/重要提示/目录）：分红预案等关键信息常在"重要提示"
        out.append({"title": "重要提示（封面与重要提示页）",
                    "pages": pages[:first_start], "start": 0, "end": first_start - 1})
    for r in ranges:
        title = r["title"]
        if "备查文件" in title or "目录" in title:
            continue
        if "财务报告" in title:
            end = min(r["end"], r["start"] + fin_pages - 1)
            out.append({"title": f"{title}（仅审计意见与主要报表前几页）",
                        "pages": pages[r["start"]:end + 1],
                        "start": r["start"], "end": end})
        else:
            out.append({"title": title, "pages": pages[r["start"]:r["end"] + 1],
                        "start": r["start"], "end": r["end"]})
    return out


def chunk_context(ctx: dict, max_chars: int = 4200) -> list[dict]:
    """把一个章节的页面文本切成块，块内标注 PDF 页码。"""
    out = []
    cur, size, p_start = [], 0, ctx["start"]
    for p in range(ctx["start"], ctx["end"] + 1):
        t = ctx["pages"][p - ctx["start"]] if p - ctx["start"] < len(ctx["pages"]) else ""
        cur.append(f"\n【PDF第{p + 1}页】\n{t}")
        size += len(t)
        if size >= max_chars and p < ctx["end"]:
            out.append({"text": "".join(cur), "start": p_start, "end": p})
            cur, size, p_start = [], 0, p + 1
    if cur:
        out.append({"text": "".join(cur), "start": p_start, "end": ctx["end"]})
    return out


def _find_fin_page(pages: list[str]) -> int | None:
    """定位"主要会计数据"表所在页（要求同时出现带千分位的大额数字）。

    数字可能带小数（15,197,799.12）也可能是整数千分位（317,508），故小数部分可选。
    """
    for i, text in enumerate(pages[:35]):
        if ("主要会计数据" in text or "主要财务数据" in text) and re.search(
                r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?", text):
            return i
    return None


def _unit_multiplier(pages: list[str], fin_page: int) -> float:
    """从财务表页面解析金额单位，返回换算到「元」的倍数。

    单位标注可能在页眉（「单位：百万元」）或指标名括号内（「营业收入（千元）」），
    故扫描整页；优先级 百万元>千元>万元>亿元。无标注时按元（1.0）。
    只影响元类指标，不改变每股/百分比字段。
    """
    text = pages[fin_page]
    if re.search(r"(单位[：:]?)?\s*(人民币)?百万元|百万人民币", text):
        return 1e6
    if re.search(r"(单位[：:]?)?\s*(人民币)?千元|千元人民币", text):
        return 1e3
    if re.search(r"单位[：:]\s*万元|人民币万元", text):
        return 1e4
    if re.search(r"单位[：:]\s*亿元|人民币亿元", text):
        return 1e8
    return 1.0


def _split_nums(text: str, decimals: int) -> list[float]:
    """从表格行文本提取数字（容忍 PDF 导出时空格丢失导致的数字粘连）。"""
    pat = rf"-?\d{{1,3}}(?:,\d{{3}})*(?:\.\d{{1,{decimals}}})?"
    out = []
    for tok in re.findall(pat, text):
        try:
            out.append(float(tok.replace(",", "")))
        except ValueError:
            continue
    return out


def _table_blocks(text: str) -> list[str]:
    """把页面行切成"label 行 + 数字行"块（PyMuPDF 常把表格列拆成多行）。

    连续数字行归并进同一块；无数字的纯文字块丢弃。
    """
    blocks, buf, nums = [], [], []
    for line in text.splitlines():
        if re.search(r"\d", line):
            nums.append(line)
        else:
            if nums:
                blocks.append("\n".join(buf + nums))
                buf, nums = [], []
            buf.append(line)
    if nums:
        blocks.append("\n".join(buf + nums))
    return [b for b in blocks if re.search(r"\d", b)]


def _match_block(label: str, norm: str) -> bool:
    if label not in norm:
        return False
    if label == "归属于上市公司股东的净利润" and "扣除非经常性损益" in norm:
        return False
    if label == "总资产" and ("净资产" in norm or "归属于上市公司股东的" in norm):
        return False
    if label in ("基本每股收益", "加权平均净资产收益率") and "扣除非经常性损益" in norm:
        return False
    return True


def extract_financials(pages: list[str]) -> tuple[dict, int | None]:
    """从"主要会计数据"表提取指标。返回 ({指标: {...}}, 表所在页 idx)。

    元类指标：{current, previous, yoy(%)，yoy_stated 是否原文同比}
    ROE：{current, previous, yoy_points(百分点，原文"增加/减少X个百分点")}
    """
    fin_page = _find_fin_page(pages)
    if fin_page is None:
        return {}, None
    mult = _unit_multiplier(pages, fin_page)  # 表头金额单位 → 元的换算倍数
    blocks = _table_blocks(pages[fin_page])
    # 表可能跨页：下一页只取到"分季度/非经常性损益"之前，避免混入其他表
    if fin_page + 1 < len(pages):
        nxt = pages[fin_page + 1]
        for stop_kw in ("分季度", "非经常性损益项目"):
            idx = nxt.find(stop_kw)
            if idx >= 0:
                nxt = nxt[:idx]
        if nxt.strip():
            blocks += _table_blocks(nxt)

    result: dict = {}
    consumed: set[int] = set()
    for key, label, unit in _FIN_METRICS:
        found = None
        for i, block in enumerate(blocks):
            if i in consumed:
                continue
            if _match_block(label, re.sub(r"\s+", "", block)):
                found = i
                break
        if found is None:
            continue
        consumed.add(found)
        block = blocks[found]
        decimals = 4 if unit == "元/股" else 2
        nums = _split_nums(block, decimals)
        if not nums:
            continue
        if key == "加权平均ROE":
            entry = {"current": nums[0],
                     "previous": nums[1] if len(nums) > 1 else None}
            m = re.search(r"(增加|减少)([\d.]+)\s*个百分点", block)
            if m:
                pts = float(m.group(2))
                entry["yoy_points"] = -pts if m.group(1) == "减少" else pts
            result[key] = entry
        else:
            current, previous = nums[0], (nums[1] if len(nums) > 1 else None)
            # 元类指标按表头单位换算成元；每股/百分比类不变（unit != "元"）
            if unit == "元" and mult != 1.0:
                current = current * mult if current is not None else None
                previous = previous * mult if previous is not None else None
            yoy, stated = None, False
            # 第 3 个数是同比列；但异常大的值可能是"2023 年"第三列而非同比
            if len(nums) > 2 and abs(nums[2]) <= 999:
                yoy, stated = nums[2], True
            elif current is not None and previous not in (None, 0):
                yoy = round((current - previous) / abs(previous) * 100, 2)
            result[key] = {"current": current, "previous": previous,
                           "yoy": yoy, "yoy_stated": stated}
    return result, fin_page


def _fmt_yi(v: float | None) -> str:
    if v is None:
        return "-"
    if abs(v) >= 1e8:
        return f"{v / 1e8:,.2f} 亿"
    if abs(v) >= 1e4:
        return f"{v / 1e4:,.2f} 万"
    return f"{v:,.2f}"


def _fmt_share(v: float | None) -> str:
    """每股类数值：保留有效位数，去尾零。"""
    if v is None:
        return "-"
    s = f"{v:,.4f}".rstrip("0").rstrip(".")
    return s if s else "-"


def financial_table_md(fin: dict, fin_page: int | None) -> str:
    """把提取到的指标渲染成 markdown 表（含页码标注），供报告原样引用。"""
    if not fin:
        return ("| 指标 | 本期 | 上年同期 | 同比 |\n|---|---|---|---|\n"
                "| - | 自动提取失败，请人工核对年报原文 | - | - |")
    year_now = "本期"
    rows = []
    for key, label, unit in _FIN_METRICS:
        e = fin.get(key)
        if not e:
            rows.append(f"| {label}（{unit}） | 提取失败 | - | - |")
            continue
        if key == "加权平均ROE":
            cur = f"{e['current']:.2f}%" if e.get("current") is not None else "-"
            prev = f"{e['previous']:.2f}%" if e.get("previous") is not None else "-"
            pts = e.get("yoy_points")
            yoy = ("+" if pts and pts > 0 else "") + (
                f"{pts:.2f} 个百分点" if pts is not None else "-")
            rows.append(f"| {label}（%） | {cur} | {prev} | {yoy} |")
            continue
        cur = _fmt_yi(e.get("current")) if unit == "元" else _fmt_share(e.get("current"))
        prev = _fmt_yi(e.get("previous")) if unit == "元" else _fmt_share(e.get("previous"))
        if e.get("yoy") is not None:
            yoy = f"{e['yoy']:+.2f}%" + ("" if e.get("yoy_stated") else "（推算）")
        else:
            yoy = "-"
        rows.append(f"| {label}（{unit}） | {cur} | {prev} | {yoy} |")
    page_note = f"（提取自年报“主要会计数据”表，PDF 第 {fin_page + 1} 页）" if fin_page is not None else ""
    head = (f"| 指标 | 本期 | 上年同期 | 同比 |\n|---|---|---|---|\n")
    return head + "\n".join(rows) + f"\n\n{page_note}"
