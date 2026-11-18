"""fetcher.py - 巨潮资讯网（cninfo）年报公告查询与 PDF 下载。

巨潮接口为非官方公开 API：orgId 通过 topSearch 查询并缓存到 data/cache/；
年报公告按类别 category_ndbg_szsh 查询；原始年报 PDF 作为正式产出持久化保存到
data/output/annual_report_reader/pdfs/（长期保留，已存在则复用）。
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "annual_report_reader"
PDF_DIR = ROOT / "data" / "output" / "annual_report_reader" / "pdfs"  # 原始年报：正式产出，持久保存
ORG_CACHE = CACHE / "orgids.json"

QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
SEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
PDF_BASE = "http://static.cninfo.com.cn/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Accept": "application/json"}

# 排除的年报标题变体
_TITLE_SKIP = ("摘要", "英文", "已取消", "取消", "部分", "问询")


def _cache_load(path: Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _cache_save(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def _post(url: str, data: dict, timeout: int = 20) -> dict | None:
    for i in range(3):
        try:
            r = requests.post(url, data=data, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def org_id(code: str) -> str:
    """股票代码 → 巨潮 orgId（缓存到本地）。"""
    cache = _cache_load(ORG_CACHE)
    if code in cache:
        return cache[code]
    resp = _post(SEARCH_URL, {"keyWord": code, "maxNum": 10})
    items = []
    if isinstance(resp, list):
        items = resp
    elif isinstance(resp, dict):
        items = resp.get("keyBoardList") or resp.get("data") or []
    for item in items:
        if str(item.get("code", "")).split(".")[0] == code and item.get("orgId"):
            _cache_save(ORG_CACHE, {**cache, code: item["orgId"]})
            return item["orgId"]
    return ""


def _column_plate(code: str) -> tuple[str, str]:
    if code.startswith("6"):
        return "sse", "sse"
    if code.startswith(("43", "83", "87", "88", "92")):
        return "szse", "bj"
    return "szse", "sz"


def _pick_annual(anns: list[dict]) -> dict | None:
    """从公告列表中选出最新的完整年度报告。"""
    cands = []
    for a in anns or []:
        title = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
        if "年度报告" not in title:
            continue
        if any(k in title for k in _TITLE_SKIP):
            continue
        m = re.search(r"(\d{4})年年度报告", title)
        if not m:
            continue
        cands.append({"year": int(m.group(1)), "title": title,
                      "ann_time": a.get("announcementTime", 0),
                      "adjunct": a.get("adjunctUrl", "")})
    if not cands:
        return None
    cands.sort(key=lambda x: -x["ann_time"])
    return cands[0]


def latest_annual_report(code: str, name: str = "") -> dict | None:
    """查询某公司最新年度报告公告。返回 {code,name,year,title,ann_date,adjunct} 或 None。"""
    oid = org_id(code)
    col, plate = _column_plate(code)
    year_start = time.localtime().tm_year - 1
    form = {
        "pageNum": 1, "pageSize": 30, "column": col, "tabName": "fulltext",
        "plate": plate, "stock": f"{code},{oid}" if oid else code,
        "searchkey": "", "secid": "", "category": "category_ndbg_szsh",
        "trade": "", "seDate": f"{year_start}-01-01~{time.strftime('%Y-%m-%d')}",
        "sortName": "time", "sortType": "desc", "isHLtitle": "true",
    }
    pick = None
    for _ in range(2):  # 第二次去掉 plate 兜底
        resp = _post(QUERY_URL, form)
        pick = _pick_annual((resp or {}).get("announcements") or [])
        if pick:
            break
        form["plate"] = ""
    if not pick:
        return None
    ann_date = ""
    ts = pick["ann_time"]
    if ts:
        try:
            ann_date = time.strftime("%Y-%m-%d", time.localtime(int(ts) / 1000))
        except (ValueError, OSError):
            pass
    # 公告标题形如 "贵州茅台：2025年年度报告" 或 "贵州茅台2025年年度报告"，反推公司简称
    cname = name
    if not cname:
        m = re.match(r"(.+?)(?:[：:]|\d{4}年)", pick["title"])
        cname = m.group(1).strip(" -—") if m else ""
    return {"code": code, "name": cname, "year": pick["year"],
            "title": pick["title"], "ann_date": ann_date, "adjunct": pick["adjunct"]}


def download_pdf(info: dict, force: bool = False, progress=None) -> Path:
    """下载年报 PDF 到正式产出目录持久保存；已存在且校验通过时直接复用（--force 只影响分析，不重下 PDF）。"""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    path = PDF_DIR / f"{info['code']}_{info['year']}.pdf"
    if path.is_file() and path.stat().st_size > 50_000:
        return path
    url = PDF_BASE + info["adjunct"]
    log = progress or (lambda m: None)
    log(f"下载年报 PDF：{url}")
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=180)
            if r.status_code == 200 and r.content[:4] == b"%PDF" and len(r.content) > 50_000:
                tmp = path.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.replace(path)
                return path
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"年报 PDF 下载失败：{info['code']} {url}（可手动下载后放到 {path}）")
