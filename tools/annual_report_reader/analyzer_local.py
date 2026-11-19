"""analyzer_local.py - 零 GLM 本地带读：只用 extractor 提取的真实数字 + 原文段落。

与 analyzer.py 的区别：不调用任何 LLM / 不读 ZHIPU_API_KEY，全部由规则+模板生成。
数字一律来自 extractor.extract_financials（带 PDF 页码），文字解读只做「数字因果的
客观重述 + 原文摘录」，不推断、不编造、不给买卖建议。
"""

from __future__ import annotations

import extractor

DISCLAIMER = (
    "\n---\n*本报告由本地程序基于公开年报自动生成（未调用大模型），仅供学习参考，"
    "不构成任何投资建议；数据以公司公告原文为准。*\n"
)

# 关键数字字段的中文解读模板：(key, 展示名, 同比为正时的说法, 为负时的说法)
_FIN_NARRATIVE = [
    ("营业收入", "营业收入", "增长", "下降"),
    ("归母净利润", "归母净利润", "增长", "下降"),
    ("扣非净利润", "扣非净利润", "增长", "下降"),
    ("经营现金流净额", "经营活动现金流净额", "净流入增加", "净流入减少"),
]

# 从原文段落里筛"看点/风险"句的关键词（命中即摘录，均为客观陈述）
_POS_KW = ("增长", "增加", "提升", "突破", "创新高", "中标", "投产", "扩产",
           "回购", "分红", "派发现金", "市场份额", "订单", "投产", "量产")
_RISK_KW = ("风险", "下降", "减少", "损失", "计提", "减值", "诉讼", "处罚",
            "担保", "承压", "不确定性", "波动", "下滑")


def _yi(v) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(f) >= 1e8:
        return f"{f / 1e8:,.2f} 亿元"
    if abs(f) >= 1e4:
        return f"{f / 1e4:,.2f} 万元"
    return f"{f:,.2f}"


def _pct(e: dict) -> str:
    yoy = e.get("yoy") if isinstance(e, dict) else None
    if yoy is None:
        return "—"
    try:
        return f"{float(yoy):+.2f}%"
    except (TypeError, ValueError):
        return "—"


# ---------------------------------------------------------------- 单公司带读


def _quick_view(meta: dict, fin: dict) -> list[str]:
    """30 秒速览：全部由数字驱动。"""
    lines = []
    name = meta.get("name", "")
    lines.append(f"- 公司做什么：{name}（{meta.get('code', '')}），所属申万「{meta.get('industry', '')}」行业。")

    rev = fin.get("营业收入")
    np = fin.get("归母净利润")
    if rev:
        lines.append(f"- 今年赚不赚钱：营业收入 {_yi(rev.get('current'))}，同比 {_pct(rev)}；"
                     f"归母净利润 {_yi(np.get('current')) if np else '—'}，同比 {_pct(np) if np else '—'}。")
    roe = fin.get("加权平均ROE")
    if roe and roe.get("current") is not None:
        pts = roe.get("yoy_points")
        delta = f"（同比 {pts:+.2f} 个百分点）" if isinstance(pts, (int, float)) else ""
        lines.append(f"- 股东回报：加权平均 ROE {roe['current']:.2f}%{delta}。")
    # 找同比波动最大的一项作为"最大看点"
    cands = []
    for key, label, _, _ in _FIN_NARRATIVE:
        e = fin.get(key)
        if isinstance(e, dict) and isinstance(e.get("yoy"), (int, float)):
            cands.append((abs(e["yoy"]), label, e["yoy"]))
    if cands:
        cands.sort(reverse=True)
        _, label, yoy = cands[0]
        word = "增长" if yoy >= 0 else "下降"
        lines.append(f"- 波动最大项：{label}同比{word} {abs(yoy):.2f}%（详见下方财务表）。")
    return lines


def _narrative(fin: dict) -> list[str]:
    """业绩带读：逐项客观重述数字（因果只在原文有依据时才写，这里只陈述变动）。"""
    lines = []
    for key, label, up_word, down_word in _FIN_NARRATIVE:
        e = fin.get(key)
        if not isinstance(e, dict) or e.get("current") is None:
            continue
        yoy = e.get("yoy")
        if isinstance(yoy, (int, float)):
            word = up_word if yoy >= 0 else down_word
            lines.append(f"- {label}：本期 {_yi(e['current'])}，上年同期 {_yi(e.get('previous'))}，"
                         f"同比{word} {abs(yoy):.2f}%"
                         + ("" if e.get("yoy_stated") else "（按原文两期数推算）") + "。")
        else:
            lines.append(f"- {label}：本期 {_yi(e['current'])}，上年同期 {_yi(e.get('previous'))}。")
    return lines


def _extract_sentences(pages: list[str], ranges: list[dict], keywords: tuple,
                       limit: int = 6, max_chars: int = 90) -> list[str]:
    """从年报正文中按关键词摘录客观陈述句，附 PDF 页码。"""
    out = []
    want = set(keywords)
    for ctx in extractor.build_context(pages, ranges):
        for p in range(ctx["start"], ctx["end"] + 1):
            idx = p - ctx["start"]
            if idx < 0 or idx >= len(ctx["pages"]):
                continue
            text = ctx["pages"][idx]
            for raw in text.splitlines():
                s = raw.strip()
                if not (12 <= len(s) <= 260):
                    continue
                if not any(k in s for k in want):
                    continue
                # 截到句末，避免半句
                cut = s[:max_chars]
                for stop in ("。", "；", "!"):
                    pos = cut.rfind(stop)
                    if pos > max_chars * 0.5:
                        cut = cut[:pos + 1]
                        break
                line = f"- {cut}【PDF 第 {p + 1} 页】"
                if line not in out:
                    out.append(line)
                if len(out) >= limit:
                    return out
    return out


def analyze_company_local(meta: dict, pages: list[str], ranges: list[dict],
                          progress=None) -> str:
    """单公司本地带读。meta 需含 name/code/year/industry/title/ann_date。"""
    log = progress or (lambda m: None)
    log("  本地提取财务数字...")
    fin, fin_page = extractor.extract_financials(pages)
    fin_md = extractor.financial_table_md(fin, fin_page)

    log("  本地摘录原文要点（看点/风险）...")
    plus = _extract_sentences(pages, ranges, _POS_KW, limit=5)
    risk = _extract_sentences(pages, ranges, _RISK_KW, limit=5)

    body = []
    body.append("## 30 秒速览")
    body.extend(_quick_view(meta, fin))
    body.append("")
    body.append("<<<FIN_TABLE>>>")
    body.append("")
    body.append("## 业绩带读")
    body.extend(_narrative(fin) or ["- 关键财务指标自动提取失败，请以年报原文为准。"])
    body.append("")
    body.append("## 业务与经营（原文摘录）")
    body.extend(plus or ["- 未定位到含明确经营看点的原文段落，请查阅年报原文。"])
    body.append("")
    body.append("## 风险与重要事项（原文摘录）")
    body.extend(risk or ["- 未定位到含明确风险表述的原文段落，请查阅年报原文。"])
    body.append("")
    body.append("## 分红与股东回报")
    body.append("- 分红/回购信息以年报「重要提示」及利润分配预案原文为准；本表仅陈列已提取到的 ROE 指标，未提取到分红数字时不做填充。")
    body.append("")
    body.append("## 行情视角")
    body.append("- 客观陈列：营收/净利同比、ROE 变动及现金流方向见上表；本报告不含估值与买卖判断。")
    body.append("")
    body.append("## 页码索引")
    if fin_page is not None:
        body.append(f"- 主要会计数据表：PDF 第 {fin_page + 1} 页")
    body.append("- 看点/风险摘录：见各条末尾 PDF 页码标注")

    text = "\n".join(body)
    text = text.replace("<<<FIN_TABLE>>>", fin_md, 1)

    head = (f"# {meta['name']}（{meta.get('code', '')}）{meta['year']} 年年报带读\n\n"
            f"> 行业：{meta.get('industry', '')} ｜ 年报标题：{meta.get('title', '')}"
            f" ｜ 披露日期：{meta.get('ann_date', '')}"
            f" ｜ 分析方式：本地程序（未调用大模型）\n\n")
    return head + text + DISCLAIMER


# ---------------------------------------------------------------- 跨行业横向对比


def analyze_cross_industry(materials: list[dict], year: int, progress=None) -> str:
    """31 家龙头横向对比。materials: [{name, code, industry, fin, fin_page}]。"""
    log = progress or (lambda m: None)
    log(f"  生成 {len(materials)} 家跨行业横向对比...")

    rows = []
    ok_count = 0
    for m in materials:
        fin = m.get("fin") or {}
        rev, np = fin.get("营业收入"), fin.get("归母净利润")
        roe, ocf = fin.get("加权平均ROE"), fin.get("经营现金流净额")
        # 年报年份：主流年份不标注，非主流年份（如只有2024年报）在名称后标注
        yr = m.get("year")
        yr_note = f"（{yr}年报）" if yr and yr != year else ""
        if not rev and not np:
            rows.append(f"| {m.get('industry', '')} | {m['name']}（{m['code']}）{yr_note} | "
                        f"提取失败 | — | — | — | — |")
            continue
        ok_count += 1
        roe_s = f"{roe['current']:.2f}%" if isinstance(roe, dict) and roe.get("current") is not None else "—"
        rows.append(
            f"| {m.get('industry', '')} | {m['name']}（{m['code']}）{yr_note} | "
            f"{_yi(rev.get('current')) if rev else '—'} | {_pct(rev) if rev else '—'} | "
            f"{_yi(np.get('current')) if np else '—'} | {_pct(np) if np else '—'} | "
            f"{roe_s} | {_yi(ocf.get('current')) if ocf else '—'} |"
        )

    # 营收/净利 top3（客观排序）
    def rank(key):
        r = []
        for m in materials:
            e = (m.get("fin") or {}).get(key)
            if isinstance(e, dict) and isinstance(e.get("current"), (int, float)):
                r.append((e["current"], m["name"], m.get("industry", "")))
        r.sort(reverse=True)
        return r[:3]

    rev_top, np_top = rank("营业收入"), rank("归母净利润")
    top_lines = []
    if rev_top:
        top_lines.append("- 营业收入前三：" + "、".join(
            f"{n}（{_yi(v)}，{ind}）" for v, n, ind in rev_top) + "。")
    if np_top:
        top_lines.append("- 归母净利润前三：" + "、".join(
            f"{n}（{_yi(v)}，{ind}）" for v, n, ind in np_top) + "。")

    head = (f"# 申万一级 31 行业龙头横向对比（{year} 年报）\n\n"
            f"> 口径：每个申万一级行业取总市值第 1 龙头，共 {len(materials)} 家；"
            f"财务数字由本地程序从各公司年报「主要会计数据」表提取，未调用大模型。\n"
            f"> 说明：本表为跨行业龙头比较，不代表行业整体；不同行业会计口径与周期不同，"
            f"数字仅供客观对照，不构成投资建议。\n\n")
    body = [
        "## 一、总览",
        f"实际纳入 {ok_count} 家（成功提取财务数字），{len(materials) - ok_count} 家提取失败或年报缺失（表中如实标注）。",
        "",
        "## 二、龙头公司对比表",
        "| 申万行业 | 公司 | 营业收入 | 营收同比 | 归母净利润 | 净利同比 | 加权ROE | 经营现金流净额 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    body.extend(rows)
    body.append("")
    body.append("## 三、客观排序")
    body.extend(top_lines or ["- 未提取到足够的营收/净利数字，无法排序。"])
    body.append("")
    body.append("## 四、口径与限制")
    body.append("- 营收/净利/ROE/现金流均为年报「主要会计数据」表口径，逐公司带读报告标注了 PDF 页码。")
    body.append("- 金融行业（银行/非银）的营收、现金流口径与实业不同，跨行业比较时需注意。")
    body.append("- 新上市公司若无对应年度年报，或扫描件无法提取文本，表中标注提取失败，不做填充。")
    return head + "\n".join(body) + "\n" + DISCLAIMER
