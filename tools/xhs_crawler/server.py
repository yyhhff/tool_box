"""xhs_crawler Web 界面：Flask 本地服务。

启动：python server.py [--port 5000] [--no-browser]
浏览器打开 http://127.0.0.1:5000 操作登录、抓取、查看进度与结果。
"""

import argparse
import json
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from playwright.sync_api import sync_playwright

import crawler

ROOT = Path(__file__).resolve().parents[2]
DATA_OUT = ROOT / "data" / "output" / "xhs_crawler"

app = Flask(__name__)

_state = {
    "running": False,
    "logs": [],
    "error": None,
    "result": None,   # {"run": 目录名, "uid":..., "count":...}
}
_login = {
    "busy": False,
    "message": "",
    "started": 0.0,
    "timeout": 0,
}
_lock = threading.Lock()
MAX_LOG_LINES = 800


def _log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with _lock:
        _state["logs"].append(line)
        if len(_state["logs"]) > MAX_LOG_LINES:
            del _state["logs"][: len(_state["logs"]) - MAX_LOG_LINES]


def _login_set(**kw) -> None:
    with _lock:
        _login.update(kw)


def _annotate_local_images(run_name: str, notes: list) -> list:
    """为已下载图片的博文补充可直接访问的本地图片 URL。"""
    for n in notes:
        img_dir = DATA_OUT / run_name / "images" / n["note_id"]
        if img_dir.is_dir():
            files = sorted(p.name for p in img_dir.glob("*.jpg"))
            if files:
                n["local_images"] = [
                    f"/images/{run_name}/{n['note_id']}/{f}" for f in files]
    return notes


def _run_crawl(params: dict) -> None:
    try:
        notes, out_dir, uid, stop_reason = crawler.crawl(progress=_log, **params)
        with _lock:
            _state["result"] = {"run": out_dir.name, "uid": uid,
                                "count": len(notes)}
            if stop_reason:
                _state["error"] = stop_reason
    except SystemExit as exc:
        with _lock:
            _state["error"] = str(exc) or "任务异常结束"
    except Exception as exc:
        with _lock:
            _state["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        with _lock:
            _state["running"] = False


def _run_login(timeout: int) -> None:
    """后台执行浏览器交互登录（扫码/短信均可），成功后保存登录态。"""
    try:
        with sync_playwright() as p:
            browser = crawler.launch_browser(p, headless=False)
            try:
                crawler.ensure_login(browser, log=lambda m: _login_set(message=m),
                                     timeout=timeout)
                _login_set(busy=False, message="登录成功")
            finally:
                browser.close()
    except SystemExit as exc:
        _login_set(busy=False, message="登录失败：" + (str(exc) or "超时"))
    except Exception as exc:
        _login_set(busy=False, message=f"登录失败：{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- 路由


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/start")
def api_start():
    data = request.get_json(silent=True) or {}
    user = (data.get("user") or "").strip()
    if not user:
        return jsonify({"ok": False, "error": "请填写博主 ID 或主页链接"}), 400
    with _lock:
        if _state["running"]:
            return jsonify({"ok": False, "error": "已有任务在运行，请等待完成"}), 409
        if _login["busy"]:
            return jsonify({"ok": False, "error": "登录进行中，请先完成登录"}), 409
        _state.update(running=True, logs=[], error=None, result=None)
    params = {
        "user": user,
        "start": data.get("start") or None,
        "end": data.get("end") or None,
        "download_images": bool(data.get("download_images")),
        "max_notes": max(1, int(data.get("max_notes") or 500)),
    }
    threading.Thread(target=_run_crawl, args=(params,), daemon=True).start()
    return jsonify({"ok": True})


@app.get("/api/status")
def api_status():
    with _lock:
        return jsonify({
            "running": _state["running"],
            "error": _state["error"],
            "result": _state["result"],
            "logs": _state["logs"][-120:],
            "log_total": len(_state["logs"]),
        })


@app.post("/api/login_qr")
def api_login_qr():
    timeout = crawler.LOGIN_TIMEOUT_DEFAULT
    with _lock:
        if _state["running"]:
            return jsonify({"ok": False, "error": "抓取任务进行中，请等待完成"}), 409
        if _login["busy"]:
            return jsonify({"ok": False, "error": "登录已在进行中"}), 409
        _login.update(busy=True, message="正在打开浏览器...",
                      started=time.time(), timeout=timeout)
    threading.Thread(target=_run_login, args=(timeout,), daemon=True).start()
    return jsonify({"ok": True})


@app.post("/api/login_cookie")
def api_login_cookie():
    data = request.get_json(silent=True) or {}
    cookie = (data.get("cookie") or "").strip()
    if not cookie:
        return jsonify({"ok": False, "error": "请粘贴 cookie 内容"}), 400
    with _lock:
        if _state["running"] or _login["busy"]:
            return jsonify({"ok": False, "error": "任务/登录进行中，请稍候"}), 409
    ok, msg = crawler.import_cookie_login(cookie)
    if ok:
        _login_set(message=msg)
    return jsonify({"ok": ok, "message" if ok else "error": msg})


@app.get("/api/login_status")
def api_login_status():
    with _lock:
        remaining = 0
        if _login["busy"]:
            remaining = max(0, int(_login["started"] + _login["timeout"]
                                   - time.time()))
        return jsonify({
            "busy": _login["busy"],
            "message": _login["message"],
            "remaining": remaining,
            "has_state": crawler.LOGIN_STATE.exists(),
        })


@app.get("/api/results")
def api_results():
    run = request.args.get("run")
    with _lock:
        if not run and _state["result"]:
            run = _state["result"]["run"]
    path = DATA_OUT / str(run or "") / "notes.json"
    if not path.is_file():
        return jsonify({"ok": False, "error": "没有可展示的结果"}), 404
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return jsonify({"ok": False, "error": "结果文件读取失败"}), 500
    notes = _annotate_local_images(path.parent.name, data.get("notes", []))
    meta = {k: v for k, v in data.items() if k != "notes"}
    return jsonify({"ok": True, "run": path.parent.name, "meta": meta,
                    "notes": notes})


@app.get("/api/history")
def api_history():
    items = []
    if DATA_OUT.is_dir():
        for d in sorted(DATA_OUT.iterdir(),
                        key=lambda p: p.stat().st_mtime, reverse=True):
            f = d / "notes.json"
            if not (d.is_dir() and f.is_file()):
                continue
            try:
                meta = json.loads(f.read_text(encoding="utf-8"))
                items.append({"run": d.name, "count": meta.get("count", 0),
                              "range": meta.get("range", []),
                              "generated_at": meta.get("generated_at", "")})
            except Exception:
                continue
    return jsonify({"ok": True, "items": items})


@app.get("/images/<run_name>/<note_id>/<path:filename>")
def api_image(run_name, note_id, filename):
    directory = str(DATA_OUT / run_name / "images" / note_id)
    return send_from_directory(directory, filename)


# ---------------------------------------------------------------- 启动


def main() -> None:
    ap = argparse.ArgumentParser(description="xhs_crawler Web 界面")
    ap.add_argument("--port", type=int, default=5000, help="监听端口，默认 5000")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Timer(1.2, webbrowser.open, args=(url,)).start()
    print(f"xhs_crawler Web 界面已启动：{url} （Ctrl+C 退出）")
    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
