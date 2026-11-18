"""
签到服务层（真实协议）

接口路径与判定均来自 github.com/88lin/workbuddy-auto-signin（⭐2528）实测代码：
- POST /v2/billing/meter/checkin-activity-status  查签到状态
- POST /v2/billing/meter/daily-checkin            领取今日积分（{"credit": 100}）
- "今日已签" 兼容 null 与 400 + {"code": 10001}
- 成长中心 base：/v2/activity/growth/（tasks / tasks/accept / tasks/{code}/claim ...）
"""
from datetime import datetime

from models import Account, CheckinRecord, get_db
from services.workbuddy_client import (
    AuthError,
    api_success,
    dig,
    is_already_checked_in,
)


class CheckinService:
    """WorkBuddy 签到服务（真实 API）"""

    def __init__(self, client):
        self.client = client

    # ---- 每日签到 ----

    def daily_checkin(self) -> dict:
        """查状态 + 领取今日积分；已签到幂等返回（points=0）。"""
        scode, sbody = self.client.checkin_status()
        if not api_success(scode, sbody):
            if scode == -1:
                return {"success": False, "points": 0, "message": "网络不可达"}
            if scode in (401, 403):
                return {"success": False, "points": 0, "message": "登录态失效，请重新 bind"}
            return {"success": False, "points": 0,
                    "message": "查询签到状态失败（HTTP %s）" % scode}

        ccode, cbody = self.client.daily_checkin()
        if is_already_checked_in(cbody):
            status = self._status_fields(sbody)
            return {"success": True, "points": 0, "already": True,
                    "message": "今日已签到",
                    "status": status}
        if not api_success(ccode, cbody):
            msg = dig(cbody, "msg") or ("HTTP %s" % ccode)
            return {"success": False, "points": 0, "message": "领取失败：%s" % msg}

        credit = dig(cbody, "credit") or 0
        # 领取成功后回查一次累计积分
        _scode2, sbody2 = self.client.checkin_status()
        return {
            "success": True,
            "points": int(credit),
            "already": False,
            "message": "成功领取 %s 积分" % credit,
            "status": self._status_fields(sbody2 or sbody),
        }

    @staticmethod
    def _status_fields(body):
        return {
            "today_credit": dig(body, "today_credit") or dig(body, "daily_credit"),
            "streak_days": dig(body, "streak_days"),
            "total_credits": dig(body, "total_credits"),
        }

    # ---- 成长中心 ----

    def growth_tasks(self) -> list:
        """GET /v2/activity/growth/tasks：任务列表。"""
        code, body = self.client.get(self.client.growth("tasks"))
        if not api_success(code, body):
            return []
        raw = dig(body, "tasks") or dig(body, "list") or []
        tasks = []
        for t in raw if isinstance(raw, list) else []:
            tasks.append({
                "id": dig(t, "code") or dig(t, "task_code") or dig(t, "id"),
                "name": dig(t, "title") or dig(t, "name") or "",
                "reward": dig(t, "reward_credit"),
                "status": dig(t, "status"),
            })
        return tasks

    def claim_reward(self, task_id: str) -> dict:
        """POST /v2/activity/growth/tasks/{code}/claim：领取任务奖励。"""
        code, body = self.client.post(self.client.growth("tasks/%s/claim" % task_id), {})
        if api_success(code, body):
            credit = dig(body, "credit") or dig(body, "reward_credit") or 0
            return {"success": True, "points": int(credit), "message": "领取成功"}
        msg = dig(body, "msg") or ("HTTP %s" % code)
        # 403 连续天数不足等属于常态，不算异常，但仍按失败返回
        return {"success": False, "points": 0, "message": "领取失败：%s" % msg}

    # ---- 组合执行 ----

    def execute_all_checkin(self, do_growth: bool = True) -> dict:
        """签到 +（可选）成长中心任务领取；返回汇总与总积分。"""
        daily = self.daily_checkin()

        growth_results = []
        if do_growth and daily["success"]:
            for task in self.growth_tasks():
                if not task["id"] or task.get("status") not in (None, "doing", "pending", "available"):
                    continue
                result = self.claim_reward(task["id"])
                growth_results.append({"task_name": task["name"], "result": result})

        total_points = daily.get("points", 0)
        for g in growth_results:
            if g["result"].get("success"):
                total_points += g["result"].get("points", 0)

        return {
            "daily_checkin": daily,
            "growth_tasks": growth_results,
            "total_points": total_points,
        }

    def save_checkin_record(self, account_id: str, checkin_result: dict):
        """把签到结果写入 checkin_records（只记 success，失败计入 message）"""
        db = next(get_db())
        try:
            daily = checkin_result.get("daily_checkin") or {}
            if daily.get("success"):
                db.add(CheckinRecord(
                    account_id=account_id,
                    checkin_time=datetime.now(),
                    points=daily.get("points", 0),
                    status="success",
                    task_type="daily_checkin",
                ))
            for g in checkin_result.get("growth_tasks") or []:
                r = g.get("result") or {}
                if r.get("success"):
                    db.add(CheckinRecord(
                        account_id=account_id,
                        checkin_time=datetime.now(),
                        points=r.get("points", 0),
                        status="success",
                        task_type="growth_task",
                    ))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def run_account_checkin(account_id: str) -> dict:
    """对单个账号执行完整签到（供 API 与定时任务复用）。

    无凭据/凭据失效时返回 ok=False 而不抛异常，调用方直接落日志。
    """
    db = next(get_db())
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return {"ok": False, "message": "账号不存在"}
        try:
            from services.account_service import account_service
            client = account_service.client_for(account)
        except AuthError as e:
            return {"ok": False, "message": e.detail, "reason": e.reason}
    finally:
        db.close()

    service = CheckinService(client)
    result = service.execute_all_checkin()
    service.save_checkin_record(account_id, result)
    return {"ok": True, **result}
