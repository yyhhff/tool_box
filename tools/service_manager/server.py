"""service_manager Web 界面：Flask 本地服务。

启动：python server.py [--port 5002]
浏览器打开 http://127.0.0.1:5002 管理服务。
"""

from flask import Flask, jsonify, render_template, request
from service_manager import manager

app = Flask(__name__)


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取所有服务状态"""
    status = manager.get_status()
    return jsonify({"status": status})


@app.route("/api/start/<service_id>", methods=["POST"])
def start_service(service_id):
    """启动服务"""
    result = manager.start_service(service_id)
    return jsonify(result)


@app.route("/api/stop/<service_id>", methods=["POST"])
def stop_service(service_id):
    """停止服务"""
    result = manager.stop_service(service_id)
    return jsonify(result)


@app.route("/api/restart/<service_id>", methods=["POST"])
def restart_service(service_id):
    """重启服务"""
    result = manager.restart_service(service_id)
    return jsonify(result)


@app.route("/api/logs/<service_id>", methods=["GET"])
def get_logs(service_id):
    """获取服务日志"""
    log_file = manager.CACHE_DIR / "logs" / f"{service_id}.log"
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            logs = f.read()
    else:
        logs = "日志文件不存在"
    return jsonify({"logs": logs})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="服务管理工具")
    parser.add_argument("--port", type=int, default=5002, help="Web 端口（默认 5002）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    app.run(host="127.0.0.1", port=args.port, debug=False)
