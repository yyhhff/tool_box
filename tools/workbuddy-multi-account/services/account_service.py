"""
账号服务层

多账号机制（与官方签到脚本一致）：
- WorkBuddy 桌面端同一时刻只保存一个账号的登录态（凭据文件）
- "添加账号" = 客户端当前登录的账号原样复制凭据为快照（bind）
- 运行时各账号用各自快照请求，互不影响，也不打扰客户端当前登录
- 快照失效（token 过期）时，需在客户端重新登录该账号后重新 bind
- activate（面板点账号切号）：把该账号快照原样写回客户端凭据文件并重启客户端，
  客户端启动时读到目标凭据即自动登录为该号（加密信封与客户端密钥绑定，同机可解）
"""
import os
import subprocess
import time
import uuid
from datetime import datetime

from models import Account, ChatMessage, CheckinRecord, get_db
from config import CREDENTIAL_DIR
from services.workbuddy_client import (
    AuthError,
    WorkBuddyClient,
    find_auth_file,
    load_session,
    snapshot_credential,
    api_success,
    CODE_NO_NETWORK,
    AUTH_BASENAME,
)
from services.task_snapshot_service import read_uid_from_credential

# 凭据写回：客户端自己原子写 .info 时也会占用固定名 .tmp，撞名会报 Errno 13。
# 用唯一临时名 + 短重试，容忍切号后残留的短暂文件锁。
AUTH_WRITE_RETRIES = 5
AUTH_WRITE_DELAY = 1.0


def stop_client() -> bool:
    """强关客户端并轮询等其退出；返回是否已无 WorkBuddy.exe。

    taskkill 失败以前被静默吞掉，导致凭据还在被客户端占用时就去写，报 Errno 13。
    """
    stopped = subprocess.run(["taskkill", "/IM", "WorkBuddy.exe", "/F"],
                             capture_output=True, text=True,
                             errors="replace")
    print("[client-kill] taskkill rc=%s %s" % (
        stopped.returncode, ((stopped.stdout or "") + (stopped.stderr or "")).strip()))
    for _ in range(10):
        listing = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WorkBuddy.exe"],
                                 capture_output=True, text=True, errors="replace")
        if "WorkBuddy.exe" not in (listing.stdout or ""):
            return True
        time.sleep(0.5)
    print("[client-kill] 5s 后仍有 WorkBuddy.exe 存活，继续尝试写回凭据")
    return False


def write_auth_file(auth_file: str, snapshot_bytes: bytes) -> None:
    """原子写回客户端凭据；临时名带 pid+随机串，避开客户端自身/残留的 .tmp 锁。

    写后读回比对字节，避免 os.replace 成功但内容不对仍去重启客户端。
    """
    os.makedirs(os.path.dirname(auth_file), exist_ok=True)
    last_error = None
    for attempt in range(1, AUTH_WRITE_RETRIES + 1):
        tmp_path = "%s.%d.%s.tmp" % (auth_file, os.getpid(), uuid.uuid4().hex[:8])
        try:
            with open(tmp_path, "wb") as f:
                f.write(snapshot_bytes)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, auth_file)
            with open(auth_file, "rb") as f:
                if f.read() != snapshot_bytes:
                    raise OSError("凭据写回后内容校验不一致")
            return
        except OSError as e:
            last_error = e
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            if attempt < AUTH_WRITE_RETRIES:
                print("[auth-write] 第 %d/%d 次写回失败：%s；%.1fs 后重试" % (
                    attempt, AUTH_WRITE_RETRIES, e, AUTH_WRITE_DELAY))
                time.sleep(AUTH_WRITE_DELAY)
    raise OSError("凭据写回失败（已重试 %d 次）：%s" % (AUTH_WRITE_RETRIES, last_error))


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
                uid=read_uid_from_credential(credential_path),
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

    def activate_account(self, account_id: str, restart_client: bool = True,
                         on_after_kill=None) -> dict:
        """
        设为客户端登录：把该账号的凭据快照原样写回客户端凭据文件并重启 WorkBuddy。

        注意：会强制关闭并重启 WorkBuddy 客户端（正在进行的客户端会话会中断）。
        on_after_kill(account)：可选回调，在 taskkill 之后、写回凭据与重启之前调用；
        API 层借此把"客户端当前登录账号"的任务合并到目标账号（此时客户端已退出、
        db 无锁，且客户端凭据仍是源账号登录态，可据此识别源账号）。
        """
        db = next(get_db())
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"ok": False, "reason": "NOT_FOUND", "message": "账号不存在"}
            if not account.credential_path or not os.path.exists(account.credential_path):
                return {"ok": False, "reason": "NO_CREDENTIAL",
                        "message": "该账号没有凭据快照，无法切换"}
            with open(account.credential_path, "rb") as f:
                snapshot_bytes = f.read()
        finally:
            db.close()

        # 1. 关闭客户端（运行中会短暂独占凭据文件，先退场再写）
        stop_client()

        # 1.5 切号后任务迁移（回调）：必须在 kill 之后、写回凭据与重启之前执行。
        #     此时客户端已退出（sidebar 快照 / db 无写入锁），且客户端凭据文件仍保存
        #     源账号登录态，可据此识别源账号。回调异常只记日志，不影响切号主流程。
        task_migration = None
        if callable(on_after_kill):
            try:
                task_migration = on_after_kill(account)
            except Exception as e:
                print("[task-migrate] 切号后迁移回调异常（已忽略）：%s" % e)

        # 2. 原子写回凭据文件（客户端从未登录过时用标准路径构造）
        auth_file, _ = find_auth_file()
        if not auth_file:
            home = os.path.expanduser("~")
            local = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
            auth_file = os.path.join(local, AUTH_BASENAME)
        write_auth_file(auth_file, snapshot_bytes)

        # 3. 重启客户端（分离进程，正常显示 UI）
        restarted = False
        if restart_client:
            try:
                from services.auth_helper import find_runtime
                exe = find_runtime()
                creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | \
                    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                subprocess.Popen([exe], creationflags=creationflags, close_fds=True)
                restarted = True
                time.sleep(1.0)
            except Exception:
                restarted = False

        result = {
            "ok": True,
            "message": "已将客户端登录切换为 %s%s" % (
                account.name, "（客户端已重启）" if restarted else "（客户端未运行，启动后生效）"),
            "account_id": account_id,
            "client_restarted": restarted,
        }
        if task_migration is not None:
            # 迁移摘要透传前端（auto_merge 未触发时为 {"attempted": False}）
            result["task_migration"] = task_migration
        return result

    def delete_account(self, account_id: str) -> dict:
        """删除账号：DB 行 + 凭据快照 + 关联签到/聊天记录（不可恢复）。

        只动工具自身数据；客户端当前登录态与客户端私有任务/会话不受影响。
        """
        db = next(get_db())
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"ok": False, "reason": "NOT_FOUND", "message": "账号不存在"}
            name = account.name
            credential_path = account.credential_path
            chat_count = db.query(ChatMessage).filter(
                ChatMessage.account_id == account_id).delete(synchronize_session=False)
            checkin_count = db.query(CheckinRecord).filter(
                CheckinRecord.account_id == account_id).delete(synchronize_session=False)
            db.delete(account)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        credential_removed = False
        if credential_path:
            try:
                os.remove(credential_path)
                credential_removed = True
            except FileNotFoundError:
                pass
            except OSError as e:
                print("[delete] 凭据快照删除失败：%s" % e)
        return {
            "ok": True,
            "message": "账号「%s」已删除" % name,
            "deleted_chat_messages": chat_count,
            "deleted_checkin_records": checkin_count,
            "credential_removed": credential_removed,
        }


# 全局服务实例
account_service = AccountService()
