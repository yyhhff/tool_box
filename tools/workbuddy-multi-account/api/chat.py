"""
聊天记录管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from sqlalchemy import text

from models import Account, ChatMessage, get_db

router = APIRouter(prefix="/api/chat", tags=["聊天记录管理"])


class MergeChatRequest(BaseModel):
    """合并聊天记录请求"""
    target_account_id: str
    source_account_ids: List[str]


@router.get("/messages")
async def get_chat_messages(
    account_id: str = Query(..., description="账号 ID"),
    chat_id: Optional[str] = Query(None, description="会话 ID（可选）"),
    limit: int = Query(50, ge=1, le=1000, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取聊天记录

    参数：
    - account_id: 账号 ID（必填）
    - chat_id: 会话 ID（可选，不传则返回所有会话的消息）
    - limit: 每页数量
    - offset: 偏移量
    """
    db = next(get_db())
    try:
        if chat_id:
            # 查询特定会话的消息
            messages = db.query(ChatMessage).filter(
                ChatMessage.account_id == account_id,
                ChatMessage.chat_id == chat_id
            ).order_by(ChatMessage.timestamp.asc()).limit(limit).offset(offset).all()

            # 转换为字典
            result = []
            for msg in messages:
                result.append({
                    'id': msg.id,
                    'account_id': msg.account_id,
                    'chat_id': msg.chat_id,
                    'message_id': msg.message_id,
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
                })
        else:
            # 查询所有会话的消息（仅返回最近消息）
            result = db.execute(text("""
                SELECT DISTINCT chat_id, MAX(timestamp) as latest_time
                FROM chat_messages
                WHERE account_id = :account_id
                GROUP BY chat_id
                ORDER BY latest_time DESC
                LIMIT :limit
            """), {
                'account_id': account_id,
                'limit': limit
            }).fetchall()

            # 转换为字典
            result = [
                {
                    'chat_id': row[0],
                    'latest_time': row[1].isoformat() if row[1] else None,
                    'message_count': db.query(ChatMessage).filter(
                        ChatMessage.account_id == account_id,
                        ChatMessage.chat_id == row[0]
                    ).count()
                }
                for row in result
            ]

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/merge")
async def merge_chat_messages(request: MergeChatRequest):
    """
    合并聊天记录到目标账号

    流程：
    1. 更新目标账号的 merged_from 字段
    2. 执行 UNION ALL 合并
    3. 去重（相同 chat_id + message_id）
    4. 返回合并结果
    """
    if not request.source_account_ids:
        raise HTTPException(status_code=400, detail="请选择源账号")

    db = next(get_db())
    try:
        # 检查目标账号是否存在
        target_account = db.query(Account).filter(Account.id == request.target_account_id).first()
        if not target_account:
            raise HTTPException(status_code=404, detail="目标账号不存在")

        # 检查源账号是否存在
        for source_id in request.source_account_ids:
            source_account = db.query(Account).filter(Account.id == source_id).first()
            if not source_account:
                raise HTTPException(status_code=404, detail=f"源账号 {source_id} 不存在")

        # 动态生成 IN 子句的绑定占位符（SQLite 不支持直接绑定 tuple 给 IN）
        params = {'target_id': request.target_account_id}
        src_placeholders = []
        for i, src_id in enumerate(request.source_account_ids):
            key = f'src_{i}'
            params[key] = src_id
            src_placeholders.append(f':{key}')

        # 执行合并 SQL：源账号消息插入目标账号，按 (chat_id, message_id) 去重
        merge_sql = f"""
            INSERT OR REPLACE INTO chat_messages
            (account_id, chat_id, message_id, sender, content, timestamp)
            SELECT
                :target_id as account_id,
                chat_id,
                message_id,
                sender,
                content,
                timestamp
            FROM chat_messages
            WHERE account_id IN ({', '.join(src_placeholders)})
            AND NOT EXISTS (
                SELECT 1 FROM chat_messages AS existing
                WHERE existing.account_id = :target_id
                AND existing.chat_id = chat_messages.chat_id
                AND existing.message_id = chat_messages.message_id
            )
        """

        # 获取数据库连接
        from models import engine
        with engine.connect() as conn:
            conn.execute(text(merge_sql), params)
            conn.commit()

        # 合并成功后才记录来源，保证 merged_from 与实际数据一致
        target_account.merged_from = ','.join(request.source_account_ids)
        db.commit()

        return {
            "success": True,
            "message": f"成功合并 {len(request.source_account_ids)} 个账号的聊天记录",
            "data": {
                "target_account_id": request.target_account_id,
                "source_account_ids": request.source_account_ids,
                "merged_from": target_account.merged_from
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/history/{account_id}")
async def get_chat_history(account_id: str, days: int = 30):
    """
    获取账号的聊天历史统计

    参数：
    - account_id: 账号 ID
    - days: 统计天数（默认 30 天）
    """
    db = next(get_db())
    try:
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)

        # 查询所有聊天记录
        messages = db.query(ChatMessage).filter(
            ChatMessage.account_id == account_id,
            ChatMessage.timestamp >= start_date
        ).all()

        # 按会话分组
        chat_groups = {}
        for msg in messages:
            if msg.chat_id not in chat_groups:
                chat_groups[msg.chat_id] = {
                    'chat_id': msg.chat_id,
                    'message_count': 0,
                    'sender_count': set(),
                    'total_messages': 0
                }
            chat_groups[msg.chat_id]['message_count'] += 1
            chat_groups[msg.chat_id]['sender_count'].add(msg.sender)
            chat_groups[msg.chat_id]['total_messages'] += 1

        # 转换为字典
        result = [
            {
                'chat_id': group['chat_id'],
                'message_count': group['message_count'],
                'sender_count': len(group['sender_count']),
                'total_messages': group['total_messages']
            }
            for group in chat_groups.values()
        ]

        # 按消息数量降序排序
        result.sort(key=lambda x: x['message_count'], reverse=True)

        return {
            "success": True,
            "data": {
                "account_id": account_id,
                "days": days,
                "total_messages": len(messages),
                "total_chats": len(result),
                "chat_groups": result
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
