"""
账号服务层

多账号机制（与官方签到脚本一致）：
- WorkBuddy 桌面端同一时刻只保存一个账号的登录态（凭据文件）
- "添加账号" = 客户端当前登录的账号原样复制凭据为快照（bind）
- 运行时各账号用各自快照请求，互不影响，也不打扰客户端当前登录
- 快照失效（token 过期）时，需在客户端重新登录该账号后重新 bind
"""
import os
import uuid
from datetime import datetime

from models import Account, get_db
from config import CREDENTIAL_DIR
from services.workbuddy_client import (
    AuthError,
    WorkBuddyClient,
    find_auth_file,
    load_session,
    snapshot_credential,
    api_success,
    CODE_NO_NETWORK,
)


class AccountService:
    """WorkBuddy 账号服务（基于客户端凭据快照的多账号管理）"""

    def bind_account(self, name: str) -> dict:
        """
        把客户端当前登录的账号绑定为快照。

        返回 {ok, account_id, account_name, credential_path, uid_hint, message}
        失败时 ok=False 并带原因（AUTH_MISSING/AUTH_INVALID/AUTH_ENCRYPTED）。
        """
        auth_file, looked_in = find_auth_file()
        if not auth_file:
            return {
                "ok": False,
                "reason": "AUTH_MISSING",
                "message": "未找到 WorkBuddy 客户端凭据文件；请先登录 WorkBuddy 桌面端。"
                           "尝试过的路径：%s" % "; ".join(looked_in),
            }
        try:
            session = load_session(auth_file)
        except AuthError as e:
            return {"ok": False, "reason": e.reason, "message": e.detail}

        account_id = "acc_%s_%s" % (
            datetime.now().strftime("%Y%m%d%H%M%S"), uuid.uuid4().hex[:6])
        credential_path = str(CREDENTIAL_DIR / ("%s.info" % account_id))
        snapshot_credential(auth_file, credential_path)

        db = next(get_db())
        try:
            account = Account(
                id=account_id,
                name=name,
                status="offline",
                credential_path=credential_path,
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            return {
                "ok": True,
                "account_id": account_id,
                "account_name": name,
                "credential_path": credential_path,
                "endpoint": session["auth"]["endpoint"],
                "message": "已绑定客户端当前登录账号（凭据快照已保存）",
            }
        except Exception as e:
            db.rollback()
            # 库写失败则回滚快照文件，避免留下无主凭据
            try:
                os.remove(credential_path)
            except OSError:
                pass
            raise
        finally:
            db.close()

    def refresh_snapshot(self, account_id: str) -> dict:
        """客户端重新登录后，更新该账号的凭据快照（等价 bind --force）。"""
        db = next(get_db())
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"ok": False, "reason": "NOT_FOUND", "message": "账号不存在"}
            auth_file, looked_in = find_auth_file()
            if not auth_file:
                return {"ok": False, "reason": "AUTH_MISSING",
                        "message": "未找到客户端凭据文件：%s" % "; ".join(looked_in)}
            try:
                load_session(auth_file)
            except AuthError as e:
                return {"ok": False, "reason": e.reason, "message": e.detail}
            snapshot_credential(auth_file, account.credential_path
                                or str(CREDENTIAL_DIR / ("%s.info" % account_id)))
            account.credential_path = account.credential_path \
                or str(CREDENTIAL_DIR / ("%s.info" % account_id))
            db.commit()
            return {"ok": True, "message": "凭据快照已更新（请在客户端登录目标账号后再执行）"}
        finally:
            db.close()

    def check_login_status(self, account: Account) -> str:
        """
        真实探测账号登录态：调签到状态接口。
        返回 'online' / 'offline' / 'login_required'。
        """
        try:
            client = self.client_for(account)
        except AuthError:
            return "login_required"
        code, _body = client.checkin_status()
        if api_success(code, _body):
            return "online"
        if code in (401, 403):
            return "login_required"
        if code == CODE_NO_NETWORK:
            return "offline"
        # 其他非 2xx（如 400 业务态）也说明 token 仍在被服务端接受
        return "online" if code not in (401, 403) else "login_required"

    def client_for(self, account: Account) -> WorkBuddyClient:
        """按账号构建 API 客户端（快照优先，回退当前客户端凭据）。"""
        from services.workbuddy_client import load_client_for_account
        return load_client_for_account(account.id, account.credential_path)


# 全局服务实例
account_service = AccountService()
