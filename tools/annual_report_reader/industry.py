"""industry.py - 申万一级 31 行业与龙头公司选择。

数据源：akshare（申万指数成分 + 东财 A 股实时行情）。行业/成分接口可能变动，
故选择结果写入快照缓存（data/cache/annual_report_reader/industry_snapshot.json），
接口失效时回退快照；config.json 的 overrides 可按行业覆盖名单。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / "data" / "cache" / "annual_report_reader"
SNAPSHOT = CACHE / "industry_snapshot.json"

CANDIDATE_KEEP = 8  # 快照中每行业保留的候选公司数（供 Web 自定义挑选）

# 申万一级 2021 版 31 行业静态表（公开稳定标准；来源：申万宏源研究官网行业指数分类）。
# akshare 的 index_first_info_sw 依赖官网页面解析，页面改版即失效，故内置静态表兜底；
# 每个代码用 index_component_sw 拉成分时自检（成分数 <5 视为代码有误，写入快照时剔除）。
STATIC_SW_FIRST = {
    "农林牧渔": "801010", "基础化工": "801030", "钢铁": "801040",
    "有色金属": "801050", "电子": "801080", "家用电器": "801110",
    "食品饮料": "801120", "纺织服饰": "801130", "轻工制造": "801140",
    "医药生物": "801150", "公用事业": "801160", "交通运输": "801170",
    "房地产": "801180", "商贸零售": "801200", "社会服务": "801210",
    "综合": "801230", "建筑材料": "801710", "建筑装饰": "801720",
    "电力设备": "801730", "国防军工": "801740", "通信": "801750",
    "传媒": "801760", "计算机": "801770", "银行": "801780",
    "非银金融": "801790", "汽车": "801880", "机械设备": "801890",
    "煤炭": "801950", "石油石化": "801960", "环保": "801970",
    "美容护理": "801980",
}


def _ak():
    import akshare as ak
    return ak


def _load_snapshot() -> dict:
    if SNAPSHOT.is_file():
        try:
            return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def load_snapshot() -> dict:
    """公开读取快照（供 Web 界面用），无快照返回 {}。"""
    return _load_snapshot()


def _save_snapshot(snap: dict) -> None:
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=1),
                        encoding="utf-8")


def is_excluded_name(name: str) -> bool:
    """剔除 ST / 退市整理 / 退市风险公司。"""
    n = (name or "").upper()
    return "ST" in n or "退" in n


def list_industries() -> list[dict]:
    """申万一级行业列表 [{code, name}]，优先快照，缺失时在线抓取。"""
    snap = _load_snapshot()
    if snap.get("industries"):
        return [{"code": v.get("code", ""), "name": k}
                for k, v in snap["industries"].items()]
    return _fetch_industries()


def _fetch_industries() -> list[dict]:
    """返回申万一级行业列表：优先在线接口，失败时回退内置静态表。"""
    ak = _ak()
    fn = getattr(ak, "index_first_info_sw", None) or getattr(ak, "sw_index_first_info", None)
    if fn is not None:
        try:
            df = fn()
            if df is not None and not df.empty:
                cols = {str(c).strip(): c for c in df.columns}
                code_c = cols.get("行业代码") or cols.get("板块代码") or df.columns[0]
                name_c = cols.get("行业名称") or cols.get("板块名称") or df.columns[1]
                rows = [{"code": str(r[code_c]).split(".")[0].zfill(6),
                         "name": str(r[name_c]).strip()} for _, r in df.iterrows()]
                if len(rows) >= 25:  # 在线结果明显完整才采用
                    return rows
        except Exception:
            pass
    return [{"code": c, "name": n} for n, c in STATIC_SW_FIRST.items()]


def _sw_cons(ak, code: str) -> list[str]:
    """申万行业成分股代码列表；依次尝试多个 akshare 接口名（各版本不同）。"""
    for fname in ("index_component_sw", "sw_index_first_cons", "index_cons_cni"):
        fn = getattr(ak, fname, None)
        if fn is None:
            continue
        try:
            df = fn(symbol=code)
            col = next((c for c in ("证券代码", "品种代码", "板块代码")
                        if c in df.columns), df.columns[0])
            codes = [str(v).split(".")[0].zfill(6) for v in df[col].astype(str)]
            if len(set(codes)) >= 5:
                return codes
        except Exception:
            continue
    fn = getattr(ak, "index_detail_cni", None)  # 国证口径兜底（带月份参数的版本）
    if fn is not None:
        for back in range(0, 7):
            date = time.strftime("%Y%m", time.localtime(time.time() - back * 30 * 86400))
            try:
                df = fn(symbol=code, date=date)
                col = next((c for c in ("成分券代码", "证券代码") if c in df.columns),
                           df.columns[0])
                codes = [str(v).split(".")[0].zfill(6) for v in df[col].astype(str)]
                if len(set(codes)) >= 5:
                    return codes
            except Exception:
                continue
    return []


def _fetch_spot(ak, log) -> tuple[dict, dict]:
    """全 A 股代码 → (总市值{元}, 名称)。优先腾讯源（27 页稳定），
    东财 push2 在部分网络下翻页即被限流，仅作备选。"""
    try:
        df = ak.stock_zh_a_spot_tx()
        cap, names = {}, {}
        for _, r in df.iterrows():
            code = str(r.get("code", ""))[-6:]  # sh600519 → 600519
            try:
                cap[code] = float(r.get("zsz") or 0) * 1e8  # 腾讯 zsz 单位：亿元
            except (TypeError, ValueError):
                cap[code] = 0.0
            names[code] = str(r.get("name", "")).strip()
        if len(cap) > 4000:
            return cap, names
        log(f"  腾讯行情返回 {len(cap)} 条偏少，尝试东财源...")
    except Exception as exc:
        log(f"  腾讯行情失败（{type(exc).__name__}），尝试东财源...")
    df = ak.stock_zh_a_spot_em()
    cap, names = {}, {}
    for _, r in df.iterrows():
        code = str(r.get("代码", "")).zfill(6)
        try:
            cap[code] = float(r.get("总市值") or 0)  # 东财单位：元
        except (TypeError, ValueError):
            cap[code] = 0.0
        names[code] = str(r.get("名称", "")).strip()
    return cap, names


def refresh_snapshot(progress=None) -> dict:
    """在线抓取 31 行业成分与总市值，按市值降序写快照并返回。"""
    ak = _ak()
    industries = _fetch_industries()
    log = progress or (lambda m: None)
    log(f"获取全 A 股行情（总市值）...")
    cap, names = _fetch_spot(ak, log)
    log(f"  行情就绪：{len(cap)} 只")

    result = {}
    for ind in industries:
        log(f"抓取行业成分：{ind['name']}（{ind['code']}）")
        rows = []
        for c in _sw_cons(ak, ind["code"]):
            name = names.get(c, "")
            if is_excluded_name(name):
                continue
            rows.append({"code": c, "name": name, "mktcap": cap.get(c, 0.0)})
        if len(rows) < 5:  # 自检：静态表代码有误或接口异常时剔除该行业
            log(f"  警告：{ind['name']}（{ind['code']}）有效成分仅 {len(rows)} 家，"
                f"疑似行业代码有误，已从快照剔除")
            continue
        rows.sort(key=lambda x: -x["mktcap"])
        result[ind["name"]] = {"code": ind["code"], "stocks": rows[:CANDIDATE_KEEP]}

    snap = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "industries": result}
    _save_snapshot(snap)
    log(f"行业快照已保存：{SNAPSHOT}")
    return snap


def select(cfg: dict, progress=None) -> dict[str, dict]:
    """按配置选出行业 → 龙头名单。返回 {行业名: {"code": 指数代码, "stocks": [...]}}。

    cfg 相关字段：top_n、industries_include(None=全部)、industries_exclude、
    overrides({行业: [股票代码...]})。
    """
    snap = _load_snapshot()
    if not snap.get("industries"):
        log = progress or (lambda m: None)
        log("本地无行业快照，开始在线抓取（约 1-3 分钟）...")
        refresh_snapshot(progress=progress)
        snap = _load_snapshot()
        if not snap.get("industries"):
            raise RuntimeError("行业快照获取失败：请检查 akshare 接口或网络后重试")

    include = cfg.get("industries_include")
    exclude = set(cfg.get("industries_exclude") or [])
    top_n = int(cfg.get("top_n") or 3)
    overrides = cfg.get("overrides") or {}

    out = {}
    for name, info in snap["industries"].items():
        if include is not None and name not in include:
            continue
        if name in exclude:
            continue
        by_code = {s["code"]: s for s in info["stocks"]}
        if name in overrides:
            stocks = []
            for w in overrides[name]:
                code = str(w).split(":")[0].zfill(6)
                stocks.append(by_code.get(code, {"code": code, "name": "", "mktcap": 0}))
        else:
            stocks = info["stocks"][:top_n]
        out[name] = {"code": info["code"], "stocks": stocks}
    return out


def snapshot_age_days() -> float | None:
    snap = _load_snapshot()
    ts = snap.get("updated_at")
    if not ts:
        return None
    try:
        t = time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))
        return (time.time() - t) / 86400
    except ValueError:
        return None
