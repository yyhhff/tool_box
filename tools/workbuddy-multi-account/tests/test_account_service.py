# -*- coding: utf-8 -*-
"""
TASK-0045 单元测试：切号凭据写回 + 账号删除。

全部在 tempfile 临时目录 + 临时 SQLite 库中进行，绝不触碰真实 workbuddy.db、
凭据快照或客户端私有数据。
"""
import builtins
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from unittest import mock

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

import models  # noqa: E402
from models import Account, Base, ChatMessage, CheckinRecord  # noqa: E402
from services import account_service as svc  # noqa: E402


class AuthWriteTest(unittest.TestCase):
    """凭据原子写：唯一临时名 / 重试 / 耗尽后明确报错。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wb_authwrite_")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.auth_file = self.root / "workbuddy-desktop.info"

    def test_writes_and_cleans_unique_tmp(self):
        sources = []
        real_replace = os.replace

        def track_replace(src, dst):
            sources.append(str(src))
            return real_replace(src, dst)

        with mock.patch.object(svc.os, "replace", track_replace):
            svc.write_auth_file(str(self.auth_file), b"snapshot-bytes")

        self.assertEqual(self.auth_file.read_bytes(), b"snapshot-bytes")
        self.assertEqual(len(sources), 1)
        self.assertNotEqual(sources[0], str(self.auth_file) + ".tmp")
        self.assertTrue(sources[0].startswith(str(self.auth_file) + "."))
        self.assertTrue(sources[0].endswith(".tmp"))
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_retries_on_permission_error_then_succeeds(self):
        real_open = builtins.open
        attempts = {"n": 0}

        def flaky_open(file, mode="r", *args, **kwargs):
            if str(file).endswith(".tmp") and "w" in mode:
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise PermissionError(13, "denied", str(file))
            return real_open(file, mode, *args, **kwargs)

        with mock.patch("builtins.open", flaky_open), \
                mock.patch.object(svc.time, "sleep"):
            svc.write_auth_file(str(self.auth_file), b"ok")

        self.assertEqual(attempts["n"], 2)
        self.assertEqual(self.auth_file.read_bytes(), b"ok")
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_raises_clear_error_after_retries(self):
        def denied(*args, **kwargs):
            raise PermissionError(13, "denied", "x")

        with mock.patch("builtins.open", denied), \
                mock.patch.object(svc.time, "sleep"):
            with self.assertRaises(OSError) as ctx:
                svc.write_auth_file(str(self.auth_file), b"data")

        self.assertIn("已重试", str(ctx.exception))
        self.assertEqual(list(self.root.glob("*.tmp")), [])


class DeleteAccountTest(unittest.TestCase):
    """账号删除：DB 行 + 凭据快照 + 关联记录一起清，其他账号不受影响。"""

    def setUp(self):
        self._stack = ExitStack()
        self.addCleanup(self._stack.close)
        self._tmp = tempfile.TemporaryDirectory(prefix="wb_delete_")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.engine = create_engine("sqlite:///" + (self.root / "test.db").as_posix())
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.Session = sessionmaker(bind=self.engine)

        self.cred_a = self.root / "a1.info"
        self.cred_b = self.root / "a2.info"
        self.cred_a.write_bytes(b"cred-a")
        self.cred_b.write_bytes(b"cred-b")

        s = self.Session()
        try:
            s.add(Account(id="a1", name="测试A", credential_path=str(self.cred_a),
                          created_at=datetime.now()))
            s.add(Account(id="a2", name="保留B", credential_path=str(self.cred_b),
                          created_at=datetime.now()))
            for account_id in ("a1", "a1", "a2"):
                s.add(ChatMessage(account_id=account_id, chat_id="c", message_id="m" + account_id,
                                  sender="u", content="x", timestamp=datetime.now()))
                s.add(CheckinRecord(account_id=account_id, checkin_time=datetime.now(),
                                    points=100, status="success", task_type="daily_checkin"))
            s.commit()
        finally:
            s.close()

        # 服务里所有 get_db() 都指向临时库会话（每次调用新建，模拟真实生命周期）。
        self._stack.enter_context(
            mock.patch.object(svc, "get_db", lambda: iter([self.Session()])))

    def _count(self, model, account_id):
        s = self.Session()
        try:
            return s.scalar(select(func.count()).select_from(model).where(
                model.account_id == account_id))
        finally:
            s.close()

    def test_delete_removes_account_credential_and_related_records(self):
        result = svc.account_service.delete_account("a1")

        self.assertTrue(result["ok"])
        self.assertEqual(result["deleted_chat_messages"], 2)
        self.assertEqual(result["deleted_checkin_records"], 2)
        self.assertTrue(result["credential_removed"])
        self.assertFalse(self.cred_a.exists())

        s = self.Session()
        try:
            self.assertIsNone(s.get(Account, "a1"))
            self.assertIsNotNone(s.get(Account, "a2"))
        finally:
            s.close()

        self.assertEqual(self._count(ChatMessage, "a1"), 0)
        self.assertEqual(self._count(CheckinRecord, "a1"), 0)
        # 其他账号完好
        self.assertTrue(self.cred_b.exists())
        self.assertEqual(self._count(ChatMessage, "a2"), 1)
        self.assertEqual(self._count(CheckinRecord, "a2"), 1)

    def test_delete_missing_account_returns_not_found(self):
        result = svc.account_service.delete_account("does-not-exist")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
