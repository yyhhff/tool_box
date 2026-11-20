"""
数据库模型
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "workbuddy.db")

# 创建数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


class Account(Base):
    """账号表"""
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, comment="账号 ID")
    name = Column(String, nullable=False, comment="账号名称")
    status = Column(String, default="offline", comment="状态：online/offline/login_required")
    last_active_time = Column(DateTime, comment="最后活跃时间")
    auto_checkin = Column(Boolean, default=True, comment="是否自动签到")
    auto_merge = Column(Boolean, default=False, comment="是否自动迁移")
    merged_from = Column(String, comment="合并来源账号（逗号分隔）")
    credential_path = Column(String, comment="凭据快照文件路径")
    uid = Column(String, comment="客户端用户 uid")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    def to_dict(self):
        """转换为字典（JSON 序列化用）"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "last_active_time": self.last_active_time.isoformat() if self.last_active_time else None,
            "auto_checkin": self.auto_checkin,
            "auto_merge": self.auto_merge,
            "merged_from": self.merged_from,
            "has_credential": bool(self.credential_path),
            "uid": self.uid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChatMessage(Base):
    """聊天消息表"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, nullable=False, comment="所属账号")
    chat_id = Column(String, nullable=False, comment="会话 ID")
    message_id = Column(String, nullable=False, comment="消息 ID")
    sender = Column(String, nullable=False, comment="发送者")
    content = Column(Text, nullable=False, comment="消息内容")
    timestamp = Column(DateTime, nullable=False, comment="发送时间")

    def to_dict(self):
        """转换为字典（JSON 序列化用）"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class CheckinRecord(Base):
    """签到记录表"""
    __tablename__ = "checkin_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, nullable=False, comment="账号 ID")
    checkin_time = Column(DateTime, nullable=False, comment="签到时间")
    points = Column(Integer, nullable=False, comment="获得积分")
    status = Column(String, nullable=False, comment="状态：success/failed")
    task_type = Column(String, nullable=False, comment="任务类型：daily_checkin/growth_task/...")
    task_id = Column(String, comment="任务 ID（可选）")

    def to_dict(self):
        """转换为字典（JSON 序列化用）"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "checkin_time": self.checkin_time.isoformat() if self.checkin_time else None,
            "points": self.points,
            "status": self.status,
            "task_type": self.task_type,
            "task_id": self.task_id,
        }


class Setting(Base):
    """系统配置表"""
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)


# 初始化数据库
def init_db():
    """初始化数据库表（含轻量列迁移：老库缺列时 ALTER TABLE 补齐）"""
    Base.metadata.create_all(bind=engine)
    _ensure_columns()

    # 初始化默认配置
    db = SessionLocal()
    try:
        # 检查是否已有配置
        existing = db.query(Setting).filter(Setting.key == "checkin_hour").first()
        if not existing:
            db.add(Setting(key="checkin_hour", value="9"))
            db.add(Setting(key="checkin_minute", value="0"))
            db.add(Setting(key="auto_merge_enabled", value="false"))
            db.commit()
    finally:
        db.close()


def _ensure_columns():
    """SQLite 轻量迁移：模型新增列在老库上补齐（ADD COLUMN 不破坏数据）"""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    migrations = {
        "accounts": {"credential_path": "TEXT", "uid": "TEXT"},
    }
    with engine.connect() as conn:
        for table, cols in migrations.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col, col_type in cols.items():
                if col not in existing:
                    conn.execute(text(
                        "ALTER TABLE %s ADD COLUMN %s %s" % (table, col, col_type)))
        conn.commit()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
