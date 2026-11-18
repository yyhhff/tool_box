"""annual_report_reader - 行业龙头年报带读。

默认：申万一级 31 行业 × 每行业总市值前 3 龙头，批量下载最新年报并用 GLM 带读，
产出单公司报告与行业对比汇总；支持自定义行业/公司；有记忆（增量续跑）。
用法见 README.md。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import analyzer
import extractor
import fetcher
import industry
import memory


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower() not in ("utf-8", "utf8"):
                stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def build_targets(cfg: dict, industries: list[str] | None, stocks: list[str] | None,
                  progress=print) -> list[dict]:
    """确定本次要分析的公司清单 [{code, name, industry}]。"""
    if industries:
        cfg = {**cfg, "industries_include": industries}
    selection = industry.select(cfg, progress=progress)
    targets: dict[str, dict] = {}
    if stocks:
        want = [s.strip().split(".")[0].zfill(6) for s in stocks if s.strip()]
        for ind_name, info in selection.items():
            for s in info["stocks"]:
                if s["code"] in want and s["code"] not in targets:
                    targets[s["code"]] = {"code": s["code"], "name": s["name"],
                                          "industry": ind_name}
        for code in want:  # 不在任何已选行业里的（如行业被排除）→ 自定义
            if code not in targets:
                targets[code] = {"code": code, "name": "", "industry": "自定义"}
        return list(targets.values())

    for ind_name, info in selection.items():
        for s in info["stocks"]:
            if s["code"] not in targets:
                targets[s["code"]] = {"code": s["code"], "name": s["name"],
                                      "industry": ind_name}
    return list(targets.values())


def _resolve_last_run(cfg: dict) -> tuple[list[str] | None, list[str] | None]:
    """无参数时沿用上次范围（记忆）。"""
    last = cfg.get("last_run")
    if not last:
        return None, None
    industries = last.get("industries") or None
    stocks = last.get("stocks") or None
    return industries, stocks


def run_pipeline(cfg: dict, industries: list[str] | None = None,
                 stocks: list[str] | None = None, top_n: int | None = None,
                 limit: int = 0, force: bool = False, model: str | None = None,
                 policy_file: str | None = None,
                 progress=print) -> dict:
    """主流水线：选股 → 查年报 → 下载 → 提取 → GLM 带读 → 行业汇总。"""
    cfg = {**cfg}
    if industries:
        cfg["industries_include"] = industries
    if top_n:
        cfg["top_n"] = top_n
    if stocks:
        cfg["stocks_include"] = stocks
    model = model or cfg.get("model") or analyzer.DEFAULT_MODEL

    targets = build_targets(cfg, industries, stocks, progress)
    if limit and limit > 0:
        targets = targets[:limit]
    if not targets:
        progress("没有匹配的公司，请检查行业/代码或行业快照")
        return {"total": 0, "done": 0, "skipped": 0, "failed": 0}

    progress(f"本次共 {len(targets)} 家公司，模型 {model}"
             + ("，强制重跑" if force else "（增量模式，已有同年份报告的自动跳过）"))

    policy_context = None
    if policy_file:
        policy_context = Path(policy_file).read_text(encoding="utf-8")
        progress(f"已载入政策背景：{policy_file}")

    cli = analyzer.client()
    index = memory.load_index()
    done_materials: dict[str, list] = {}
    stats = {"total": len(targets), "done": 0, "skipped": 0, "failed": 0}

    for i, t in enumerate(targets, 1):
        code = t["code"]
        tag = f"[{i}/{len(targets)}] {t['name'] or code}（{t['industry']}）"
        progress(f"{tag} 查询最新年报...")
        try:
            info = fetcher.latest_annual_report(code, t["name"])
        except Exception as exc:
            info = None
            progress(f"{tag} 年报查询异常：{exc}")
        if not info:
            memory.record(index, code, name=t["name"], industry=t["industry"],
                          status="no_report")
            progress(f"{tag} 未找到年度报告公告（可能为次新股/北交所无匹配），跳过")
            stats["failed"] += 1
            continue
        year = info["year"]
        if memory.should_skip(index, code, year, force):
            entry = index[code]
            progress(f"{tag} 已有 {year} 年报报告（{entry['report_path']}），跳过")
            stats["skipped"] += 1
            continue
        try:
            pdf = fetcher.download_pdf(info, force=force, progress=progress)
            progress(f"{tag} 解析 PDF：{info['title']}")
            pages = extractor.load_pages(pdf)
            ranges = extractor.chapter_ranges(pages)
            if len(ranges) < 3:
                raise RuntimeError("章节定位失败（未识别出年报'第X节'结构），可能为非标准模板")
            meta = {**t, "name": info["name"] or t["name"], "year": year,
                    "title": info["title"], "ann_date": info["ann_date"]}
            report = analyzer.analyze_company(
                meta, pages, ranges, model, cli=cli, progress=progress,
                policy_context=policy_context)
            out_dir = memory.company_dir(code, year)
            out_path = out_dir / "report.md"
            out_path.write_text(report, encoding="utf-8")
            fin, fin_page = extractor.extract_financials(pages)
            memory.record(index, code, name=info["name"], industry=t["industry"],
                          year=year, title=info["title"], status="done",
                          report_path=str(out_path), pdf_path=str(pdf),
                          ann_date=info["ann_date"])
            done_materials.setdefault(t["industry"], []).append({
                "name": info["name"], "code": code,
                "fin_md": extractor.financial_table_md(fin, fin_page),
                "digest": report[:3000],
            })
            progress(f"{tag} ✔ 报告完成：{out_path}")
            stats["done"] += 1
        except Exception as exc:
            memory.record(index, code, name=t["name"] or info["name"],
                          industry=t["industry"], status="error",
                          error=f"{type(exc).__name__}: {exc}")
            progress(f"{tag} ✘ 失败：{exc}")
            stats["failed"] += 1

    # 行业对比汇总：本轮完成 ≥2 家的行业才生成
    for ind_name, mats in done_materials.items():
        if len(mats) < 2:
            continue
        try:
            year = max(int((index.get(m["code"]) or {}).get("year") or 0) for m in mats)
            report = analyzer.analyze_industry(ind_name, year, mats, model,
                                               cli=cli, progress=progress)
            out_path = memory.industry_dir() / f"{ind_name}_{year}.md"
            out_path.write_text(report, encoding="utf-8")
            progress(f"行业汇总完成：{out_path}")
        except Exception as exc:
            progress(f"行业汇总失败（{ind_name}）：{exc}")

    progress(f"全部结束：完成 {stats['done']}，跳过 {stats['skipped']}，"
             f"失败 {stats['failed']}，共 {stats['total']}")
    return stats


def _print_selection(cfg: dict, industries, stocks, top_n, limit) -> None:
    targets = build_targets(cfg, industries, stocks, progress=lambda m: None)
    if limit and limit > 0:
        targets = targets[:limit]
    print(f"共 {len(targets)} 家：")
    for t in targets:
        print(f"  {t['code']}  {t['name'] or '?':<8}  {t['industry']}")


def main() -> None:
    _utf8_console()
    ap = argparse.ArgumentParser(description="行业龙头年报带读（annual_report_reader）")
    ap.add_argument("--industries", help="行业名列表，逗号分隔，如：银行,食品饮料")
    ap.add_argument("--stocks", help="公司代码列表，逗号分隔，如：600519,000858")
    ap.add_argument("--top", type=int, help="每行业龙头数，默认 3")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 家（小规模验收）")
    ap.add_argument("--force", action="store_true", help="强制重跑（忽略记忆跳过）")
    ap.add_argument("--model", help="GLM 模型名，默认 glm-4-flash")
    ap.add_argument("--auto", action="store_true", help="忽略上次范围，全行业全量")
    ap.add_argument("--list", action="store_true", help="只列出将分析的公司")
    ap.add_argument("--policy", help="政策背景文本文件路径（预留，二期）")
    args = ap.parse_args()

    cfg = memory.load_config()
    industries = args.industries.split(",") if args.industries else None
    stocks = args.stocks.split(",") if args.stocks else None
    top_n = args.top

    if not industries and not stocks and not args.auto:
        industries, stocks = _resolve_last_run(cfg)  # 记忆：沿用上次范围
        if industries or stocks:
            print(f"（沿用上次范围：行业={industries or '全部'} 公司={stocks or '自动'}）")

    if args.list:
        _print_selection(cfg, industries, stocks, top_n, args.limit)
        return

    mode = "stocks" if stocks else ("industries" if industries else "auto")
    memory.remember_last_run(cfg, mode, industries, stocks, top_n or cfg["top_n"],
                             args.model or cfg.get("model"))
    stats = run_pipeline(cfg, industries=industries, stocks=stocks, top_n=top_n,
                         limit=args.limit, force=args.force, model=args.model,
                         policy_file=args.policy)
    sys.exit(0 if stats["done"] + stats["skipped"] > 0 or stats["total"] == 0 else 1)


if __name__ == "__main__":
    main()
