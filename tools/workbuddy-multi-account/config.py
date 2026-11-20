"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

# 数据库路径
DATABASE_URL = "sqlite:///./workbuddy.db"

# WorkBuddy API 配置（协议来源：github.com/88lin/workbuddy-auto-signin 实测代码）
WORKBUDDY_ENDPOINT_DEFAULT = "https://copilot.tencent.com"

# 凭据文件环境变量覆盖名（与官方签到脚本约定一致）
WORKBUDDY_AUTH_FILE_ENV = "WORKBUDDY_AUTH_FILE"

# 凭据快照存放目录（多账号 bind 时复制客户端凭据到此）
CREDENTIAL_DIR = Path(__file__).parent / "credentials"

# 签到配置
CHECKIN_HOUR = 9
CHECKIN_MINUTE = 0

# 自动迁移配置
AUTO_MIGRATE_ENABLED = False

# HTTP 配置
REQUEST_TIMEOUT = 30  # 秒

# 服务端口配置（start.bat 探测到主端口被占时自动挑备用端口并写环境变量 WORKBUDDY_MA_PORT）
PORT_ENV = "WORKBUDDY_MA_PORT"
DEFAULT_PORT = 8000
FALLBACK_PORTS = list(range(8001, 8020))


def get_port() -> int:
    """读取服务端口：优先环境变量 WORKBUDDY_MA_PORT，非法值回退默认 8000。"""
    raw = os.environ.get(PORT_ENV, "").strip()
    if raw.isdigit():
        port = int(raw)
        if 1 <= port <= 65535:
            return port
    return DEFAULT_PORT

# 客户端任务数据根目录（客户端按 uid 分目录存 sidebar-list-snapshot.json）
# 支持环境变量 WORKBUDDY_CLIENT_DATA 覆盖，便于自定义安装位置/测试
CLIENT_DATA_ROOT = Path(os.environ.get("WORKBUDDY_CLIENT_DATA") or str(Path.home() / ".workbuddy"))

# 任务快照/数据库写前备份根目录（迁移时按时间戳建子目录）
SNAPSHOT_BACKUP_DIR = BASE_DIR / "data" / "cache" / "workbuddy-multi-account" / "snapshots"

# 日志配置
LOG_LEVEL = "INFO"
LOG_DIR = BASE_DIR / "data" / "output" / "workbuddy-multi-account"
