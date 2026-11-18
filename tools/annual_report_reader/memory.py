"""memory.py - 工具记忆。

config.json（data/input/，入 git）：用户自定义名单、偏好、上次运行范围；
index.json（data/output/，不入 git）：每家公司的分析历史，用于增量续跑
（年报未更新自动跳过，--force 强制重跑）。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_OUT = ROOT / "data" / "output" / "annual_report_reader"
CACHE_DIR = ROOT / "data" / "cache" / "annual_report_reader"
CONFIG_PATH = ROOT / "data" / "input" / "annual_report_reader" / "config.json"
INDEX_PATH = DATA_OUT / "index.json"

DEFAULT_CONFIG = {
    "top_n": 3,
    "industries_include": None,   # None=全部行业；列表=仅这些行业
    "industries_exclude": [],
    "stocks_include": [],         # 额外指定的公司代码
    "overrides": {},              # {"行业名": ["600519", ...]} 覆盖该行业名单
    "model": None,                # 默认 glm-4-flash
    "last_run": None,             # {"mode","industries","stocks","top_n","ts"}
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.is_file():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=1),
                           encoding="utf-8")


def remember_last_run(cfg: dict, mode: str, industries, stocks, top_n: int,
                      model: str | None) -> None:
    """把本次运行范围写入 config 的 last_run（记忆功能）。"""
    cfg["last_run"] = {
        "mode": mode,
        "industries": industries or [],
        "stocks": stocks or [],
        "top_n": top_n,
        "model": model,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_config(cfg)


def load_index() -> dict:
    if INDEX_PATH.is_file():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_index(index: dict) -> None:
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=1),
                          encoding="utf-8")


def should_skip(index: dict, code: str, year: int, force: bool) -> bool:
    """增量判断：已有同年份完成报告且未强制重跑 → 跳过。"""
    if force:
        return False
    entry = index.get(code) or {}
    return (entry.get("status") == "done" and entry.get("year") == year
            and Path(entry.get("report_path", "")).is_file())


def record(index: dict, code: str, **fields) -> None:
    entry = index.get(code) or {}
    entry.update(fields)
    entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    index[code] = entry
    save_index(index)


def company_dir(code: str, year: int) -> Path:
    d = DATA_OUT / "companies" / f"{code}_{year}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def industry_dir() -> Path:
    d = DATA_OUT / "industries"
    d.mkdir(parents=True, exist_ok=True)
    return d
