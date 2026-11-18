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

# 日志配置
LOG_LEVEL = "INFO"
LOG_DIR = BASE_DIR / "data" / "output" / "workbuddy-multi-account"
