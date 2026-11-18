"""analyzer.py - 智谱 GLM 带读：分段摘要（map）→ 汇总成报告（reduce）。

关键数字由 extractor 正则提取并注入报告，LLM 只做解读（prompt 中明令不得编造数字）。
预留 policy_context 参数：二期接入国家政策信息后传入文本即可参与解读。
"""

from __future__ import annotations

import os
import time

from openai import OpenAI

import extractor

BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
DEFAULT_MODEL = "glm-4-flash"

DISCLAIMER = (
    "\n---\n*本报告由 AI 基于公开年报自动生成，仅供学习参考，不构成任何投资建议；"
    "数据以公司公告原文为准。*\n"
)


class LLMError(Exception):
    pass


def _key_from_registry() -> str:
    """Windows 下从用户级注册表环境变量读取 key（setx 写入处）。

    setx 只写注册表，已运行进程的环境不会更新；这里主动读一次作为兜底。
    非 Windows 或读取失败时返回空串，由调用方按"未设置"处理，不泄露任何 key 内容。
    """
    if os.name != "nt":
        return ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as hk:
            value, _ = winreg.QueryValueEx(hk, "ZHIPU_API_KEY")
            return str(value).strip() if value else ""
    except (OSError, FileNotFoundError, ImportError):
        return ""


def _resolve_api_key() -> str:
    """解析 key：优先进程环境，读不到再查注册表并回填当前进程环境。"""
    key = os.environ.get("ZHIPU_API_KEY", "").strip()
    if key:
        return key
    key = _key_from_registry()
    if key:
        # 回填当前进程环境，让后续调用及本进程拉起的子进程都能继承
        os.environ["ZHIPU_API_KEY"] = key
    return key


def client() -> OpenAI:
    key = _resolve_api_key()
    if not key:
        raise LLMError(
            "未设置环境变量 ZHIPU_API_KEY（在智谱开放平台 bigmodel.cn 申请后："
            "setx ZHIPU_API_KEY <你的key>；代码会尝试从注册表读取已设置的 key，"
            "若仍报此错请确认注册表用户级变量已正确写入）")
    return OpenAI(api_key=key, base_url=BASE_URL)


def chat(cli: OpenAI, model: str, prompt: str, retries: int = 3) -> str:
    last = None
    for i in range(retries):
        try:
            resp = cli.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            content = resp.choices[0].message.content
            if content:
                return content
            last = RuntimeError("空回复")
        except Exception as exc:  # 网络/限流，退避重试
            last = exc
            time.sleep(2 * (i + 1))
    raise LLMError(f"LLM 调用失败：{last}")


_MAP_PROMPT = """你是资深证券分析师。以下是 A 股公司《{year}年年度报告》的第 {p1}-{p2} 页（章节：{sec}）。
请只依据原文提取三类要点，输出 markdown（### 业务与经营 / ### 业绩 / ### 风险与重要事项），每条一行：
- 业务与经营：公司做什么业务、怎么赚钱、本期重要经营举措与进展
- 业绩：收入/利润/成本/现金流等变动及其原因（原因要具体）
- 风险与重要事项：诉讼、担保、处罚、政策影响、大股东变动等
- 分红与股东回报：利润分配预案、分红比例、回购计划等（若有）
要求：关键数字照抄原文并注明（PDF第X页）；该页没有对应内容的小节可省略；不要推测和编造。
【原文】
{chunk}"""


def _reduce_prompt(meta: dict, fin_md: str, summaries: str) -> str:
    policy_block = ""
    if meta.get("policy_context"):
        policy_block = (
            "\n【国家政策背景（由用户提供）】\n" + meta["policy_context"] +
            "\n请在“业绩带读”“风险”等小节结合上述政策背景解读。\n")
    return f"""你是资深证券分析师，为普通投资者写《{meta['name']}（{meta['code']}）{meta['year']}年年度报告带读》。公司所属申万行业：{meta['industry']}。
【已核实的财务数据（系统从年报原文提取，将由系统原样插入报告，你不要重复输出表格）】
{fin_md}
【各章节要点摘录（含 PDF 页码，均来自年报原文）】
{summaries}
{policy_block}
请输出 markdown 正文，章节结构固定、顺序如下：
## 30 秒速览
（3-5 条：公司做什么、今年赚不赚钱、最大看点、最大风险）
在“30 秒速览”小节结束后，单独输出一行占位符：<<<FIN_TABLE>>>
## 业绩带读
（结合同比变动解释为什么，引用页码）
## 业务与经营
## 风险与重要事项
## 分红与股东回报
（年报中提到的利润分配预案/回购等；没有就写"年报未提及"）
## 行情视角
（客观陈列 2-3 条看多逻辑、2-3 条看空/谨慎逻辑，不给出买卖建议）
## 页码索引
（主要结论对应的 PDF 页码列表）
硬性要求：1) 不要输出"关键财务数据"表格章节，用 <<<FIN_TABLE>>> 占位即可；2) 所有数字必须来自已核实财务数据或摘录（保留 PDF 页码标注），严禁编造；3) 语言精炼面向非专业读者，全文 800-1500 字。"""


def analyze_company(meta: dict, pages: list[str], ranges: list[dict],
                    model: str, cli: OpenAI | None = None,
                    progress=None, policy_context: str | None = None) -> str:
    """单公司带读：分块摘要 → 汇总。meta 需含 name/code/year/industry。"""
    log = progress or (lambda m: None)
    meta = {**meta, "policy_context": policy_context}
    cli = cli or client()

    # map：逐块摘要
    parts = []
    for ctx in extractor.build_context(pages, ranges):
        chunks = extractor.chunk_context(ctx)
        for ck in chunks:
            log(f"  GLM 摘要：{ctx['title']} 第{ck['start'] + 1}-{ck['end'] + 1}页")
            prompt = _MAP_PROMPT.format(
                year=meta["year"], p1=ck["start"] + 1, p2=ck["end"] + 1,
                sec=ctx["title"], chunk=ck["text"])
            parts.append(f"### 摘录（{ctx['title']}，PDF第{ck['start'] + 1}-{ck['end'] + 1}页）\n"
                         + chat(cli, model, prompt))
    summaries = "\n\n".join(parts)
    if len(summaries) > 48000:  # 极端情况压缩，防超出上下文
        summaries = summaries[:48000]

    # reduce：汇总成报告
    fin, fin_page = extractor.extract_financials(pages)
    fin_md = extractor.financial_table_md(fin, fin_page)
    log("  GLM 汇总生成报告...")
    body = chat(cli, model, _reduce_prompt(meta, fin_md, summaries))
    if "<<<FIN_TABLE>>>" in body:
        body = body.replace("<<<FIN_TABLE>>>", fin_md, 1)
    else:
        body += "\n\n" + fin_md

    head = (f"# {meta['name']}（{meta['code']}）{meta['year']} 年年报带读\n\n"
            f"> 行业：{meta['industry']} ｜ 年报标题：{meta.get('title', '')}"
            f" ｜ 披露日期：{meta.get('ann_date', '')}\n\n")
    return head + body + DISCLAIMER


_INDU_PROMPT = """你是资深证券分析师。基于以下 {year} 年 {industry} 行业 {n} 家龙头公司的年报带读材料，写一份行业对比报告（markdown）：
{materials}
章节结构固定：
## 行业景气度
（从各公司业绩共性信号判断行业景气方向，引用公司名与数字）
## 龙头公司对比
（markdown 表：公司 | 营业收入 | 归母净利润 | 同比 | ROE | 最大看点；数字一律来自下面材料中"已核实财务数据"，不要改动）
## 分歧与个股逻辑
（各公司看点差异、分歧点，客观陈述）
硬性要求：数字只允许照抄材料；不给买卖建议；全文 600-1200 字。"""


def analyze_industry(industry: str, year: str, materials: list[dict],
                     model: str, cli: OpenAI | None = None,
                     progress=None) -> str:
    """行业对比汇总。materials: [{name, code, fin_md, digest}]。"""
    log = progress or (lambda m: None)
    cli = cli or client()
    blocks = []
    for m in materials:
        blocks.append(f"### {m['name']}（{m['code']}）\n"
                      f"【已核实财务数据】\n{m['fin_md']}\n【带读要点】\n{m['digest']}\n")
    prompt = _INDU_PROMPT.format(year=year, industry=industry,
                                 n=len(materials), materials="\n".join(blocks))
    log(f"  GLM 生成行业对比报告：{industry}")
    body = chat(cli, model, prompt)
    head = f"# {industry} 行业龙头年报对比（{year} 年报）\n\n"
    return head + body + DISCLAIMER
