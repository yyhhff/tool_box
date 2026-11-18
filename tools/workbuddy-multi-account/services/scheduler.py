"""
定时任务调度器
负责定时执行签到任务和账号状态监控（真实 API）
"""
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from models import Account, get_db

from services.checkin_service import run_account_checkin

# 定时任务调度器
scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=9, minute=0)
async def scheduled_checkin():
    """
    定时签到任务（每天 9:00）

    流程：
    1. 获取所有启用了自动签到的账号
    2. 依次执行真实签到（凭据快照轮转，互不影响）
    3. 结果落签到记录表
    """
    print(f"[{datetime.now()}] 开始执行自动签到任务...")

    db = next(get_db())
    try:
        accounts = db.query(Account).filter(Account.auto_checkin == True).all()
        summary = []
    finally:
        db.close()

    for account in accounts:
        print(f"[{datetime.now()}] 签到账号 {account.name} ({account.id})...")
        result = run_account_checkin(account.id)
        if result.get("ok"):
            summary.append((account.name, True, result.get("total_points", 0)))
            print(f"  完成：本次 +{result.get('total_points', 0)} 积分")
        else:
            summary.append((account.name, False, result.get("message", "")))
            print(f"  失败：{result.get('message')}")

    ok_count = sum(1 for _, ok, _ in summary if ok)
    print(f"[{datetime.now()}] 自动签到任务完成：{ok_count}/{len(summary)} 成功")


@scheduler.scheduled_job(IntervalTrigger(minutes=5), id='check_account_status')
async def check_account_status():
    """
    账号状态监控任务（每 5 分钟）：真实探测各账号登录态。
    """
    db = next(get_db())
    try:
        accounts = db.query(Account).all()
        changed = []
        from services.account_service import account_service
        for account in accounts:
            new_status = account_service.check_login_status(account)
            if account.status != new_status:
                changed.append((account.name, account.status, new_status))
                account.status = new_status
                if new_status == "login_required":
                    print(f"  账号 {account.name} 登录已过期，需在客户端重新登录后 bind/refresh")
        if changed:
            db.commit()
            for name, old, new in changed:
                print(f"  账号状态变更 {name}: {old} -> {new}")
        else:
            db.commit()
    except Exception as e:
        print(f"[{datetime.now()}] 账号状态检查失败: {str(e)}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """启动定时任务调度器"""
    scheduler.start()
    print("定时任务调度器已启动")
    print("  - 每天上午 9:00 自动签到")
    print("  - 每 5 分钟检查账号状态")


def stop_scheduler():
    """停止定时任务调度器"""
    scheduler.shutdown()
    print("定时任务调度器已停止")
