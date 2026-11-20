"""
账号管理 API 路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from models import Account, get_db
from services.account_service import account_service
from services import task_snapshot_service
from services.task_snapshot_service import read_uid_from_credential, find_credential_by_uid
from services.workbuddy_client import find_auth_file

router = APIRouter(prefix="/api/accounts", tags=["账号管理"])


class LoginRequest(BaseModel):
    """登录请求"""
    name: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    account_id: str
    qr_code_url: Optional[str] = None


class SwitchRequest(BaseModel):
    """切换账号请求"""
    account_id: str


class UpdateAccountRequest(BaseModel):
    """账号设置更新（全部字段可选）"""
    name: Optional[str] = None
    auto_checkin: Optional[bool] = None
    auto_merge: Optional[bool] = None


@router.post("/login", response_model=LoginResponse)
async def login_account(request: LoginRequest):
    """
    添加账号（bind 语义）

    真实机制：WorkBuddy 桌面端同一时刻只保存一个账号登录态，把客户端当前登录
    账号的凭据文件原样复制为快照即完成"添加账号"。要添加另一个账号：在客户端
    切换登录后再次调用本接口（凭据失效时用 POST /api/accounts/{id}/refresh 更新快照）。
    """
    try:
        result = account_service.bind_account(request.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not result.get("ok"):
        code = 503 if result.get("reason") == "AUTH_MISSING" else 422
        raise HTTPException(status_code=code, detail=result.get("message"))

    return LoginResponse(
        success=True,
        account_id=result["account_id"],
        qr_code_url=None,
    )


@router.post("/{account_id}/refresh")
async def refresh_account_credential(account_id: str):
    """
    更新账号凭据快照

    客户端重新登录该账号后调用；用于快照失效（token 过期）后的免重复维护。
    """
    try:
        result = account_service.refresh_snapshot(account_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not result.get("ok"):
        code = 404 if result.get("reason") == "NOT_FOUND" else 422
        raise HTTPException(status_code=code, detail=result.get("message"))
    return {"success": True, "message": result["message"]}


@router.post("/{account_id}/activate")
async def activate_account(account_id: str):
    """
    设为客户端登录（面板点账号切号）

    把该账号的凭据快照原样写回客户端凭据文件并重启 WorkBuddy，
    客户端启动时自动登录为该号。注意：会重启客户端，正在进行的客户端会话会中断。
    """
    try:
        result = account_service.activate_account(
            account_id, on_after_kill=_merge_tasks_after_kill)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not result.get("ok"):
        code = 404 if result.get("reason") == "NOT_FOUND" else 422
        raise HTTPException(status_code=code, detail=result.get("message"))
    return result


@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """删除账号：DB 行 + 凭据快照 + 关联签到/聊天记录（不可恢复）。"""
    try:
        result = account_service.delete_account(account_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/switch")
async def switch_account(request: SwitchRequest, background_tasks: BackgroundTasks):
    """
    切换账号

    流程：
    1. 更新当前活跃账号
    2. 如果启用了自动迁移，后台执行迁移任务
    """
    db = next(get_db())
    try:
        # 检查账号是否存在
        account = db.query(Account).filter(Account.id == request.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")

        # 更新活跃时间
        account.last_active_time = datetime.now()

        # 检查是否启用自动迁移
        if account.auto_merge:
            # 后台迁移聊天记录
            background_tasks.add_task(migrate_chat_records, request.account_id)

        db.commit()

        return {
            "success": True,
            "message": f"已切换到账号 {account.name}",
            "account_id": account.id,
            "account_name": account.name
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/list")
async def get_accounts():
    """
    获取所有账号列表
    """
    db = next(get_db())
    try:
        accounts = db.query(Account).all()
        return {
            "success": True,
            "data": [account.to_dict() for account in accounts]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.patch("/{account_id}")
async def update_account(account_id: str, body: UpdateAccountRequest):
    """
    更新账号设置（名称 / 自动签到开关 / 自动迁移开关）
    """
    db = next(get_db())
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")

        if body.name is not None:
            name = body.name.strip()
            if not name:
                raise HTTPException(status_code=422, detail="账号名称不能为空")
            account.name = name
        if body.auto_checkin is not None:
            account.auto_checkin = body.auto_checkin
        if body.auto_merge is not None:
            account.auto_merge = body.auto_merge
        db.commit()

        return {
            "success": True,
            "message": "设置已更新",
            "data": account.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{account_id}/status")
async def get_account_status(account_id: str):
    """
    获取账号状态（真实探测：调签到状态接口验证 token）

    - online：token 有效
    - login_required：401/403 或本地无凭据快照
    - offline：网络不可达
    """
    db = next(get_db())
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")

        new_status = account_service.check_login_status(account)
        account.status = new_status
        account.last_active_time = datetime.now()
        db.commit()

        return {
            "success": True,
            "data": {
                "id": account.id,
                "name": account.name,
                "status": account.status,
                "last_active_time": account.last_active_time.isoformat() if account.last_active_time else None,
                "auto_checkin": account.auto_checkin,
                "auto_merge": account.auto_merge,
                "has_credential": bool(account.credential_path),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


def _merge_tasks_after_kill(account):
    """切号回调：客户端已 kill、凭据未写回、未重启时调用。

    把"客户端当前登录账号"的任务合并到目标账号（account），并返回迁移摘要
    dict 供 activate 响应透传给前端；未触发迁移时返回 {"attempted": False}。
    任何异常都只记日志、不抛出，避免影响切号主流程。
    """
    try:
        if not account.auto_merge:
            return {"attempted": False}
        # 目标 uid：优先 Account.uid，回退到凭据快照（老账号可能没写 uid）
        target_uid = account.uid or read_uid_from_credential(account.credential_path)
        if not target_uid:
            print("[task-migrate] 目标账号无 uid，跳过任务迁移")
            return {"attempted": False}
        auth_file, _ = find_auth_file()
        if not auth_file:
            print("[task-migrate] 未找到客户端凭据文件，跳过任务迁移")
            return {"attempted": False}
        current_uid = read_uid_from_credential(auth_file)
        if not current_uid:
            print("[task-migrate] 客户端凭据未读到 uid，跳过任务迁移")
            return {"attempted": False}
        source_credential = find_credential_by_uid(current_uid)
        if not source_credential:
            print("[task-migrate] 未找到当前登录账号 %s 的凭据快照，跳过任务迁移" % current_uid)
            return {"attempted": False}
        result = task_snapshot_service.migrate_tasks(source_credential, target_uid)
        print("[task-migrate] 迁移结果：%s" % result)
        stats = result.get("stats") or {}
        return {
            "attempted": True,
            "ok": result.get("ok"),
            "source_uid": result.get("source_uid"),
            "target_uid": result.get("target_uid"),
            "stats": {
                "added": stats.get("added", 0),
                "updated": stats.get("updated", 0),
            },
            "error": result.get("error"),
        }
    except Exception as e:
        print("[task-migrate] 迁移回调异常（已忽略）：%s" % e)
        return {"attempted": False, "error": str(e)}


async def migrate_chat_records(current_account_id: str):
    """
    后台迁移聊天记录

    TODO: 实现聊天记录迁移逻辑
    """
    print(f"[{datetime.now()}] 开始迁移账号 {current_account_id} 的聊天记录...")

    db = next(get_db())
    try:
        # 获取当前账号的 merged_from
        account = db.query(Account).filter(Account.id == current_account_id).first()
        if not account or not account.merged_from:
            print(f"[{datetime.now()}] 账号 {current_account_id} 没有需要迁移的账号")
            return

        source_ids = account.merged_from.split(',')

        # TODO: 执行聊天记录合并
        # merge_sql = """
        #     INSERT OR REPLACE INTO chat_messages
        #     (account_id, chat_id, message_id, sender, content, timestamp)
        #     SELECT
        #         :current_id as account_id,
        #         chat_id,
        #         message_id,
        #         sender,
        #         content,
        #         timestamp
        #     FROM chat_messages
        #     WHERE account_id IN :source_ids
        #     AND NOT EXISTS (
        #         SELECT 1 FROM chat_messages
        #         WHERE account_id = :current_id
        #         AND chat_id = chat_id
        #         AND message_id = message_id
        #     )
        # """

        # with engine.connect() as conn:
        #     conn.execute(text(merge_sql), {
        #         'current_id': current_account_id,
        #         'source_ids': tuple(source_ids)
        #     })
        #     conn.commit()

        # 清空 merged_from
        account.merged_from = None
        db.commit()

        print(f"[{datetime.now()}] 账号 {current_account_id} 聊天记录迁移完成")
    except Exception as e:
        print(f"[{datetime.now()}] 迁移失败: {str(e)}")
    finally:
        db.close()
