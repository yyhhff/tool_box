"""annual_report_reader Web 界面：Flask 本地服务。

启动：python server.py [--port 5001] [--no-browser]
浏览器打开 http://127.0.0.1:5001 操作：勾选行业/公司 → 批量分析 → 进度 → 阅读报告。
"""

from __future__ import annotations

import argparse
import re
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template, request

import analyzer
import industry
import main as pipeline
import memory

DATA_OUT = memory.DATA_OUT

app = Flask(__name__)

_state = {
    "running": False,
    "logs": [],
    "error": None,
    "done": 0,
    "total": 0,
    "current": "",
}
_refresh = {"busy": False, "error": None}
_lock = threading.Lock()
MAX_LOG_LINES = 800


def _log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with _lock:
        _state["logs"].append(line)
        if len(_state["logs"]) > MAX_LOG_LINES:
            del _state["logs"][: len(_state["logs"]) - MAX_LOG_LINES]
    m = re.match(r"\[(\d+)/(\d+)\]", msg)
    if m:
        with _lock:
            _state["done"] = max(0, int(m.group(1)) - 1)
            _state["total"] = int(m.group(2))
        return
    m2 = re.search(r"共 (\d+) 家公司", msg)
    if m2:
        with _lock:
            _state["total"] = int(m2.group(1))
    elif "✔" in msg:
        with _lock:
            _state["done"] = _state["done"] + 1
            _state["current"] = ""
    elif msg.endswith("..."):
        with _lock:
            _state["current"] = msg


def _run_pipeline(params: dict) -> None:
    try:
        pipeline.run_pipeline(**params)
    except Exception as exc:
        with _lock:
            _state["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        with _lock:
            _state["running"] = False


def _refresh_snapshot() -> None:
    try:
        industry.refresh_snapshot(progress=_log)
        _log("行业快照就绪")
    except Exception as exc:
        with _lock:
            _refresh["error"] = str(exc)
        _log(f"行业快照抓取失败：{exc}")
    finally:
        with _lock:
            _refresh["busy"] = False


# ---------------------------------------------------------------- 路由


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/industries")
def api_industries():
    snap = industry.load_snapshot()
    cfg = memory.load_config()
    if not snap.get("industries"):
        with _lock:
            busy = _refresh["busy"]
            if not busy:
                _refresh.update(busy=True, error=None)
        if not busy:
            threading.Thread(target=_refresh_snapshot, daemon=True).start()
        return jsonify({"ok": False, "refreshing": True})
    return jsonify({
        "ok": True,
        "updated_at": snap.get("updated_at"),
        "top_n": cfg.get("top_n", 3),
        "last_run": cfg.get("last_run"),
        "industries": [
            {"name": k, "code": v["code"], "stocks": v["stocks"]}
            for k, v in snap["industries"].items()
        ],
    })


@app.post("/api/start")
def api_start():
    data = request.get_json(silent=True) or {}
    with _lock:
        if _state["running"]:
            return jsonify({"ok": False, "error": "已有任务在运行，请等待完成"}), 409
        _state.update(running=True, logs=[], error=None, done=0, total=0, current="")
    industries = [s.strip() for s in (data.get("industries") or []) if s.strip()]
    stocks = [str(s).strip().split(".")[0].zfill(6)
              for s in (data.get("stocks") or []) if str(s).strip()]
    top_n = int(data.get("top_n") or 0) or None
    force = bool(data.get("force"))
    model = (data.get("model") or "").strip() or None

    cfg = memory.load_config()
    mode = "stocks" if stocks and not industries else (
        "industries" if industries else "auto")
    memory.remember_last_run(cfg, mode, industries or None, stocks or None,
                             top_n or cfg.get("top_n", 3), model)
    _log(f"任务开始：行业={industries or '全部'} 自定义代码={stocks or '无'} "
         f"top={top_n or cfg.get('top_n', 3)} force={force} model={model or '默认'}")
    params = {
        "cfg": cfg,
        "industries": industries or None,
        "stocks": stocks or None,
        "top_n": top_n,
        "force": force,
        "model": model,
        "progress": _log,
    }
    threading.Thread(target=_run_pipeline, args=(params,), daemon=True).start()
    return jsonify({"ok": True})


@app.get("/api/status")
def api_status():
    with _lock:
        return jsonify({
            "running": _state["running"],
            "error": _state["error"],
            "done": _state["done"],
            "total": _state["total"],
            "current": _state["current"],
            "logs": _state["logs"][-150:],
        })


@app.get("/api/history")
def api_history():
    index = memory.load_index()
    companies = [
        {"code": code, **entry} for code, entry in sorted(
            index.items(), key=lambda kv: -(kv[1].get("year") or 0))
    ]
    reports = []
    ind_dir = DATA_OUT / "industries"
    if ind_dir.is_dir():
        for f in sorted(ind_dir.glob("*.md"), key=lambda p: p.stat().st_mtime,
                        reverse=True):
            reports.append({"name": f.name, "path": f"industries/{f.name}"})
    return jsonify({"ok": True, "companies": companies, "industries": reports})


@app.get("/api/report")
def api_report():
    rel = request.args.get("path", "")
    if rel:
        p = (DATA_OUT / rel).resolve()
        if not str(p).startswith(str(DATA_OUT.resolve())) or not p.is_file():
            return jsonify({"ok": False, "error": "路径无效"}), 404
    else:
        code = request.args.get("code", "")
        year = request.args.get("year", "")
        p = DATA_OUT / "companies" / f"{code}_{year}" / "report.md"
        if not p.is_file():
            return jsonify({"ok": False, "error": "报告不存在"}), 404
    try:
        return jsonify({"ok": True, "path": p.name,
                        "content": p.read_text(encoding="utf-8")})
    except Exception as exc:
        return jsonify({"ok": False, "error": f"读取失败：{exc}"}), 500


# ---------------------------------------------------------------- 启动


def main() -> None:
    ap = argparse.ArgumentParser(description="annual_report_reader Web 界面")
    ap.add_argument("--port", type=int, default=5001, help="监听端口，默认 5001")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Timer(1.2, webbrowser.open, args=(url,)).start()
    print(f"annual_report_reader Web 界面已启动：{url} （Ctrl+C 退出）")
    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
