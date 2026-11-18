"""
签到管理 API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

from models import Account, CheckinRecord, get_db

router = APIRouter(prefix="/api/checkin", tags=["签到管理"])


class CheckinRequest(BaseModel):
    """签到请求"""
    account_id: str


@router.post("/start")
async def start_checkin(request: CheckinRequest):
    """
    开始签到（手动触发，真实 API）

    流程：
    1. 校验账号存在
    2. 按账号凭据快照构建客户端
    3. 执行签到（每日签到 + 成长中心任务领取）
    4. 结果落签到记录表
    """
    db = next(get_db())
    try:
        account = db.query(Account).filter(Account.id == request.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
    finally:
        db.close()

    from services.checkin_service import run_account_checkin
    result = run_account_checkin(request.account_id)

    if not result.get("ok"):
        # 无凭据/凭据失效：明确告知前端原因
        raise HTTPException(status_code=422, detail=result.get("message", "签到失败"))

    return {
        "success": True,
        "message": result["daily_checkin"].get("message", "签到完成"),
        "data": result,
    }


@router.get("/records")
async def get_checkin_records(
    account_id: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    获取签到记录

    参数：
    - account_id: 账号 ID（可选，不传则返回所有记录）
    - limit: 每页数量
    - offset: 偏移量
    """
    db = next(get_db())
    try:
        if account_id:
            # 查询特定账号的签到记录
            records = db.query(CheckinRecord).filter(
                CheckinRecord.account_id == account_id
            ).order_by(CheckinRecord.checkin_time.desc()).limit(limit).offset(offset).all()
        else:
            # 查询所有签到记录
            records = db.query(CheckinRecord).order_by(CheckinRecord.checkin_time.desc()).limit(limit).offset(offset).all()

        return {
            "success": True,
            "data": [record.to_dict() for record in records]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/stats")
async def get_checkin_stats(
    account_id: str = None,
    days: int = 30
):
    """
    获取签到统计

    参数：
    - account_id: 账号 ID（可选，不传则统计所有账号）
    - days: 统计天数（默认 30 天）
    """
    db = next(get_db())
    try:
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)

        if account_id:
            # 查询特定账号的统计
            records = db.query(CheckinRecord).filter(
                CheckinRecord.account_id == account_id,
                CheckinRecord.checkin_time >= start_date
            ).all()
        else:
            # 查询所有账号的统计
            records = db.query(CheckinRecord).filter(
                CheckinRecord.checkin_time >= start_date
            ).all()

        # 统计成功和失败次数
        success_count = sum(1 for r in records if r.status == 'success')
        failed_count = sum(1 for r in records if r.status == 'failed')

        # 统计总积分
        total_points = sum(r.points for r in records)

        # 按账号分组统计
        account_stats = {}
        for record in records:
            if record.account_id not in account_stats:
                account_stats[record.account_id] = {
                    'success': 0,
                    'failed': 0,
                    'points': 0
                }
            account_stats[record.account_id]['success'] += (1 if record.status == 'success' else 0)
            account_stats[record.account_id]['failed'] += (1 if record.status == 'failed' else 0)
            account_stats[record.account_id]['points'] += record.points

        return {
            "success": True,
            "data": {
                "total_records": len(records),
                "success_count": success_count,
                "failed_count": failed_count,
                "total_points": total_points,
                "account_stats": account_stats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/tasks")
async def get_checkin_tasks():
    """
    获取签到任务列表
    """
    db = next(get_db())
    try:
        # TODO: 调用 WorkBuddy API 获取任务列表
        tasks = [
            {
                'id': 'daily_checkin',
                'name': '每日签到',
                'description': '每天固定时间签到，获得基础积分',
                'reward': '50 积分',
                'status': 'available'
            },
            {
                'id': 'growth_task_1',
                'name': '每日登录奖励',
                'description': '每日登录即可获得奖励',
                'reward': '30 积分',
                'status': 'available'
            },
            {
                'id': 'growth_task_2',
                'name': '成长中心任务',
                'description': '完成成长中心任务获得额外积分',
                'reward': '100-500 积分',
                'status': 'available'
            }
        ]

        return {
            "success": True,
            "data": tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
