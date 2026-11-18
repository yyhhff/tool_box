"""
WorkBuddy 真实客户端封装

协议来源：github.com/88lin/workbuddy-auto-signin（⭐2528）实测代码，关键约定：
- 端点：https://copilot.tencent.com（凭据文件 auth.endpoint 优先）
- 认证：Authorization: Bearer <accessToken>（token 来自客户端凭据文件）
- 凭据：WorkBuddy 桌面端把登录态写到
  %LOCALAPPDATA%\\CodeBuddyExtension\\Data\\Public\\auth\\workbuddy-desktop.info
- 客户端刷新 token 时会短暂独占凭据文件，读取需带重试
- 多账号：bind 时原样复制 .info 为快照（保留明文/加密格式），运行时不解密
"""
import json
import os
import re
import shutil
import ssl
import time
import urllib.error
import urllib.request
import urllib.parse

from config import (
    WORKBUDDY_ENDPOINT_DEFAULT,
    WORKBUDDY_AUTH_FILE_ENV,
    REQUEST_TIMEOUT,
    CREDENTIAL_DIR,
)

TOKEN_LIMIT = 32768
TOKEN_RE = re.compile(r"[A-Za-z0-9._~+/-]+=*")

# 伪 HTTP 码：区分"没拿到响应"的原因（与官方脚本约定一致）
CODE_NO_NETWORK = -1

AUTH_BASENAME = os.path.join(
    "CodeBuddyExtension", "Data", "Public", "auth", "workbuddy-desktop.info")


class AuthError(Exception):
    """凭据缺失/格式非法/加密不可解"""

    def __init__(self, reason, detail=""):
        super().__init__(detail or reason)
        self.reason = reason      # AUTH_MISSING / AUTH_INVALID / AUTH_ENCRYPTED
        self.detail = detail


def valid_token(token):
    """token 仅允许 URL 安全字符集，防注入也防读错文件"""
    return (isinstance(token, str) and 0 < len(token) <= TOKEN_LIMIT
            and TOKEN_RE.fullmatch(token) is not None)


def token_format(token):
    """明文 token 符合字符集；加密 token 是 {$wbEncrypted, envelope} 对象；
    其余（空/错误类型）为 invalid。"""
    if isinstance(token, dict):
        if token.get("$wbEncrypted") == 1 and "envelope" in token:
            return "encrypted"
        return "invalid"
    if not isinstance(token, str) or not token:
        return "invalid"
    if valid_token(token):
        return "plaintext"
    return "encrypted"


def find_auth_file():
    """探测 WorkBuddy 桌面端写出的登录凭据文件。

    返回 (path_or_None, looked_in)。环境变量 WORKBUDDY_AUTH_FILE 优先。
    """
    override = os.environ.get(WORKBUDDY_AUTH_FILE_ENV)
    if override:
        return (override if os.path.exists(override) else None), [override]
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    candidates = [
        os.path.join(local, AUTH_BASENAME),                                   # Windows 桌面端
        os.path.join(home, "Library", "Application Support", AUTH_BASENAME),  # macOS 桌面端
        os.path.join(home, ".workbuddy", "auth", "workbuddy-desktop.info"),   # 兜底
    ]
    for c in candidates:
        if os.path.exists(c):
            return c, candidates
    return None, candidates


def load_session(auth_file, attempts=3, delay=2.0):
    """读取凭据 JSON：{"auth": {"accessToken": ..., "endpoint": ...}}。

    带重试：客户端刷新 token 时会短暂独占凭据文件（PermissionError 是瞬时的）。
    加密 token（{$wbEncrypted, envelope}）在运行时经 WorkBuddy 客户端解密，
    明文仅存在于内存；快照文件始终保持密文原样。
    """
    last = None
    for i in range(attempts):
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                session = json.load(f)
            auth = session.get("auth") or {}
            token = auth.get("accessToken")
            fmt = token_format(token)
            if fmt == "invalid":
                raise AuthError("AUTH_INVALID",
                                "凭据文件 accessToken 为空或格式非法：%s" % auth_file)
            if fmt == "encrypted":
                token = _decrypt_encrypted_token(token)
            endpoint = auth.get("endpoint") or WORKBUDDY_ENDPOINT_DEFAULT
            return {"auth": {"accessToken": token, "endpoint": endpoint.rstrip("/")}}
        except PermissionError as e:
            last = e
            if i < attempts - 1:
                time.sleep(delay)
    raise last


def _decrypt_encrypted_token(token):
    """经 WorkBuddy 客户端运行时解密加密 token（仅内存）。"""
    from services import auth_helper
    try:
        return auth_helper.decrypt_token(token)
    except auth_helper.AuthHelperError as e:
        raise AuthError(e.reason, str(e)) from None


def snapshot_credential(auth_file, credential_path):
    """原样复制凭据文件为账号快照（bind 用）。保留明文/加密格式，不落运行时明文。"""
    os.makedirs(os.path.dirname(str(credential_path)), exist_ok=True)
    shutil.copyfile(auth_file, credential_path)
    return credential_path


def dig(obj, key):
    """在可能被 data/result 包裹的响应里找字段，兼容信封结构。"""
    if isinstance(obj, dict):
        if key in obj and obj[key] is not None:
            return obj[key]
        for k in ("data", "result", "resp", "response"):
            if k in obj and isinstance(obj[k], dict):
                r = dig(obj[k], key)
                if r is not None:
                    return r
    return None


def api_success(code, body):
    """HTTP 2xx 且（无业务码或业务码 == 0）才算成功，业务失败不当状态转换成功。"""
    business_code = body.get("code") if isinstance(body, dict) else None
    return 200 <= code < 300 and (
        business_code is None or (type(business_code) is int and business_code == 0))


def is_already_checked_in(cbody):
    """领取接口返回是否表示"今日已签"（兼容 null 与 400+code10001）。"""
    if cbody is None:
        return True
    if isinstance(cbody, dict):
        msg = cbody.get("msg") or ""
        if cbody.get("code") == 10001 or "已签" in msg:
            return True
    return False


class WorkBuddyClient:
    """按凭据会话调用 WorkBuddy API。get/post 返回 (http_code, body_dict_or_None)。"""

    def __init__(self, session):
        auth = session["auth"]
        self.token = auth["accessToken"]
        self.endpoint = auth.get("endpoint") or WORKBUDDY_ENDPOINT_DEFAULT
        self.headers = {
            "Authorization": "Bearer %s" % self.token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_credential_file(cls, auth_file):
        return cls(load_session(auth_file))

    def _request(self, url, method="GET", payload=None):
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as resp:
                raw = resp.read()
                try:
                    return resp.status, (json.loads(raw.decode("utf-8")) if raw else None)
                except (ValueError, UnicodeDecodeError):
                    return resp.status, None
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = None
            return e.code, body
        except (urllib.error.URLError, OSError, ssl.SSLError):
            return CODE_NO_NETWORK, None

    def get(self, path):
        return self._request(self._url(path), method="GET")

    def post(self, path, payload=None):
        return self._request(self._url(path), method="POST", payload=payload or {})

    def _url(self, path):
        return urllib.parse.urljoin(self.endpoint + "/", path.lstrip("/"))

    # ---- 高层便捷方法（协议路径与官方签到脚本一致） ----

    def checkin_status(self):
        """POST /v2/billing/meter/checkin-activity-status：查签到状态。"""
        return self.post("/v2/billing/meter/checkin-activity-status")

    def daily_checkin(self):
        """POST /v2/billing/meter/daily-checkin：领取今日积分。"""
        return self.post("/v2/billing/meter/daily-checkin")

    def growth(self, path):
        """成长中心接口基路径 /v2/activity/growth。"""
        return self.endpoint + "/v2/activity/growth/" + path.lstrip("/")


def load_client_for_account(account_id, credential_path):
    """按账号快照构建客户端；快照缺失时回退探测当前客户端凭据。"""
    if credential_path and os.path.exists(credential_path):
        return WorkBuddyClient.from_credential_file(credential_path)
    auth_file, _ = find_auth_file()
    if auth_file:
        return WorkBuddyClient.from_credential_file(auth_file)
    raise AuthError("AUTH_MISSING",
                    "账号 %s 无凭据快照，且未找到 WorkBuddy 客户端凭据文件" % account_id)
