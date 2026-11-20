# -*- coding: utf-8 -*-
"""
TASK-0037 单元测试：services/task_snapshot_service.py（切号任务列表迁移）

仅使用标准库 unittest / tempfile / json / shutil(可选) / unittest.mock。
每个用例都在 tempfile.TemporaryDirectory 中隔离，把快照根目录、备份目录、
以及可能的 DB 路径 patch 到临时目录，绝不触碰真实客户端数据 / 凭据 / 仓库 DB。

契约来源：team-lead 下发的模块契约（见文件末尾各用例注释）。
"""
import copy
import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

# discover 默认只把 tests/ 放进 sys.path；这里补上应用根目录，
# 使 `import config` / `from services import task_snapshot_service` 可用。
_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

import config  # noqa: E402

# 后端按契约应提供 services/task_snapshot_service.py；兼容平铺放置的兜底。
try:
    from services import task_snapshot_service as svc  # noqa: E402
except ImportError:  # pragma: no cover - 仅兜底
    import task_snapshot_service as svc  # noqa: E402


class SnapshotServiceTestBase(unittest.TestCase):
    """公共夹具：临时目录 + 配置 patch。"""

    def setUp(self):
        self._stack = ExitStack()
        self.addCleanup(self._stack.close)

        self._tmp = tempfile.TemporaryDirectory(prefix="wb_migrate_")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.client_root = self.root / "client_data"
        self.backup_dir = self.root / "snapshot_backup"
        self.client_root.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.root / "isolated_test.db"
        self.db_url = "sqlite:///" + self.db_path.as_posix()

        # 两种导入风格都 patch：import config 的 config.X，以及
        # from config import X 后在服务模块内留下的 svc.X。
        for obj, name, value in (
            (config, "CLIENT_DATA_ROOT", self.client_root),
            (config, "SNAPSHOT_BACKUP_DIR", self.backup_dir),
            (config, "DATABASE_URL", self.db_url),
            (svc, "CLIENT_DATA_ROOT", self.client_root),
            (svc, "SNAPSHOT_BACKUP_DIR", self.backup_dir),
            (svc, "DATABASE_URL", self.db_url),
            (svc, "DB_PATH", str(self.db_path)),
        ):
            self._safe_patch(obj, name, value)

        # 若服务通过 models.DB_PATH 取库，也指向临时库，避免污染仓库 workbuddy.db。
        try:
            import models
            self._safe_patch(models, "DB_PATH", str(self.db_path))
        except Exception:
            pass

    def _safe_patch(self, obj, name, value):
        try:
            self._stack.enter_context(
                mock.patch.object(obj, name, value, create=True))
        except Exception:
            # patch 失败不应让用例 setup 崩掉；契约相关的失败由断言暴露。
            pass

    # ---------- 测试数据工厂 ----------
    @staticmethod
    def item(task_id, ts, **extra):
        """同时带 lastActivityAt / updatedAt，兼容任一比较字段的实现。"""
        data = {"id": task_id, "lastActivityAt": ts, "updatedAt": ts}
        data.update(extra)
        return data

    def write_credential(self, uid, token="SECRET_SHOULD_NOT_LEAK"):
        path = self.root / ("cred_%s.json" % uid)
        payload = {"account": {"uid": uid, "accessToken": token}}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def write_snapshot(self, uid, items, version=3, saved_at=1000):
        snapshot = {"version": version, "savedAt": saved_at, "items": items}
        path = svc.write_snapshot_atomic(uid, snapshot)
        return snapshot, path

    @staticmethod
    def read_bytes(path):
        with open(path, "rb") as fh:
            return fh.read()

    @staticmethod
    def load_json(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def files_under(directory):
        found = []
        for base, _dirs, names in os.walk(str(directory)):
            for name in names:
                found.append(os.path.join(base, name))
        return found


# ---------------------------------------------------------------------------
# 用例 1-3：read_uid_from_credential
# ---------------------------------------------------------------------------
class TestReadUidFromCredential(SnapshotServiceTestBase):

    def test_01_read_uid_from_credential_returns_uid_without_token(self):
        cred = self.write_credential("u-src")
        uid = svc.read_uid_from_credential(cred)
        self.assertEqual(uid, "u-src")
        self.assertNotIn("SECRET", str(uid))

    def test_02_read_uid_from_credential_missing_file_returns_none(self):
        self.assertIsNone(
            svc.read_uid_from_credential(str(self.root / "not_exist.json")))

    def test_03_read_uid_from_credential_bad_shape_returns_none(self):
        bad_payloads = [
            {},
            {"foo": "bar"},
            {"account": {}},
            {"account": {"name": "no-uid"}},
            "i am a json string, not an object",
            {"account": None},
        ]
        for idx, payload in enumerate(bad_payloads):
            path = self.root / ("bad_cred_%d.json" % idx)
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertIsNone(
                svc.read_uid_from_credential(str(path)),
                msg="畸形凭据应返回 None, payload=%r" % (payload,))


# ---------------------------------------------------------------------------
# 用例 4：read_snapshot
# ---------------------------------------------------------------------------
class TestReadSnapshot(SnapshotServiceTestBase):

    def test_04_read_snapshot_normal_and_missing_default(self):
        items = [self.item("t1", 100), self.item("t2", 200, title="two")]
        snapshot, _path = self.write_snapshot("u-src", items)

        got = svc.read_snapshot("u-src")
        self.assertEqual(got["version"], 3)
        self.assertIsInstance(got["savedAt"], int)
        self.assertEqual([i["id"] for i in got["items"]], ["t1", "t2"])
        self.assertEqual(got["items"], snapshot["items"])

        empty = svc.read_snapshot("uid-never-written")
        self.assertEqual(empty.get("version"), 3)
        self.assertEqual(empty.get("items"), [])
        self.assertIsInstance(empty.get("savedAt"), int)


# ---------------------------------------------------------------------------
# 用例 5-8：merge_items
# ---------------------------------------------------------------------------
class TestMergeItems(SnapshotServiceTestBase):

    def test_05_merge_items_adds_new_id_and_does_not_mutate_inputs(self):
        src = [self.item("new-1", 300, title="brand-new")]
        dst = [self.item("old-1", 100)]
        src_before = copy.deepcopy(src)
        dst_before = copy.deepcopy(dst)

        merged, stats = svc.merge_items(src, dst)

        self.assertEqual(stats["added"], 1)
        ids = [i["id"] for i in merged]
        self.assertEqual(len(ids), 2)
        self.assertIn("new-1", ids)
        self.assertIn("old-1", ids)
        self.assertEqual(src, src_before, "源任务对象不得被修改")
        self.assertEqual(dst, dst_before, "目标任务对象不得被修改")

    def test_06_merge_items_source_newer_overrides(self):
        src = [self.item("dup", 300, title="from-source")]
        dst = [self.item("dup", 100, title="from-target")]

        merged, stats = svc.merge_items(src, dst)

        self.assertEqual(stats["updated"], 1)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], "dup")
        self.assertEqual(merged[0]["lastActivityAt"], 300)
        self.assertEqual(merged[0]["title"], "from-source")

    def test_07_merge_items_target_newer_is_kept(self):
        src = [self.item("dup", 100, title="from-source")]
        dst = [self.item("dup", 300, title="from-target")]

        merged, stats = svc.merge_items(src, dst)

        self.assertEqual(stats["unchanged"], 1)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["lastActivityAt"], 300)
        self.assertEqual(merged[0]["title"], "from-target",
                         "目标较新时源不能覆盖回去")

    def test_08_merge_items_equal_timestamp_is_idempotent(self):
        src = [self.item("dup", 200, title="src")]
        dst = [self.item("dup", 200, title="dst")]
        src_before = copy.deepcopy(src)

        merged1, _ = svc.merge_items(src, dst)
        merged2, _ = svc.merge_items(src, dst)

        self.assertEqual(len(merged1), 1, "相同时间戳不应产生重复任务")
        self.assertEqual(merged1[0]["id"], "dup")
        self.assertEqual(merged2, merged1, "重复 merge 结果应一致（幂等）")
        self.assertEqual(src, src_before)


# ---------------------------------------------------------------------------
# 用例 9：write_snapshot_atomic
# ---------------------------------------------------------------------------
class TestWriteSnapshotAtomic(SnapshotServiceTestBase):

    def test_09_write_atomic_writes_content_and_creates_backup(self):
        uid = "u-backup"
        first = {"version": 3, "savedAt": 111,
                 "items": [self.item("a", 1, title="first")]}
        second = {"version": 3, "savedAt": 222,
                  "items": [self.item("b", 2, title="second")]}
        self.assertEqual(self.files_under(self.backup_dir), [],
                         "测试开始前备份目录应为空")

        path1 = svc.write_snapshot_atomic(uid, first)
        path2 = svc.write_snapshot_atomic(uid, second)

        self.assertTrue(os.path.exists(path2))
        self.assertTrue(os.path.exists(path1) or path1 == path2)
        written = self.load_json(path2)
        self.assertEqual(written["version"], 3)
        self.assertEqual(written["items"], second["items"])
        self.assertEqual(written["items"][0]["title"], "second")

        backups = self.files_under(self.backup_dir)
        self.assertTrue(backups, "备份目录里应生成备份文件")
        self.assertTrue(
            any(self.load_json(p).get("items") == first["items"]
                for p in backups),
            "备份文件应保留写回前的内容（first）")


# ---------------------------------------------------------------------------
# 用例 10-11：migrate_tasks 完整链路 + 串号隔离
# ---------------------------------------------------------------------------
class TestMigrateTasks(SnapshotServiceTestBase):

    def test_10_migrate_tasks_full_chain(self):
        src_uid, dst_uid = "u-src", "u-dst"
        cred = self.write_credential(src_uid)
        src_items = [
            self.item("t1", 300, title="src-t1"),
            self.item("t2", 400, title="src-t2"),
        ]
        _src_snap, src_path = self.write_snapshot(src_uid, src_items)
        dst_items = [self.item("t1", 100, title="old-t1")]
        _dst_snap, dst_path = self.write_snapshot(dst_uid, dst_items)

        src_before = self.read_bytes(src_path)
        dst_before = self.read_bytes(dst_path)

        result = svc.migrate_tasks(cred, dst_uid)

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("ok"), msg="迁移失败: %r" % result.get("error"))
        self.assertEqual(result.get("source_uid"), src_uid)
        self.assertEqual(result.get("target_uid"), dst_uid)
        self.assertIsInstance(result.get("stats"), dict)

        final = svc.read_snapshot(dst_uid)
        final_map = {i["id"]: i for i in final["items"]}
        self.assertEqual(set(final_map), {"t1", "t2"},
                         "目标最终应恰好包含 2 条任务")
        self.assertEqual(final_map["t1"]["lastActivityAt"], 300,
                         "重复 id 应取源较新快照")
        self.assertEqual(final_map["t1"]["title"], "src-t1")
        self.assertEqual(final_map["t2"]["lastActivityAt"], 400)

        self.assertEqual(self.read_bytes(src_path), src_before,
                         "源快照文件不应被迁移改动")
        self.assertNotEqual(self.read_bytes(dst_path), dst_before,
                            "目标快照文件应被更新")

    def test_11_migrate_does_not_touch_unrelated_uid(self):
        src_uid, dst_uid, other_uid = "u-src", "u-dst", "u-other"
        cred = self.write_credential(src_uid)
        self.write_snapshot(src_uid, [self.item("t1", 300)])
        self.write_snapshot(dst_uid, [self.item("old", 100)])
        _other_snap, other_path = self.write_snapshot(
            other_uid, [self.item("keep", 999, title="stranger")])
        other_before = self.read_bytes(other_path)

        result = svc.migrate_tasks(cred, dst_uid)

        self.assertTrue(result.get("ok"), msg="迁移失败: %r" % result.get("error"))
        self.assertEqual(self.read_bytes(other_path), other_before,
                         "不参与迁移的 uid 快照文件必须逐字节不变")


# ---------------------------------------------------------------------------
# 用例 12：dry_run 只读预演
# ---------------------------------------------------------------------------
class TestDryRun(SnapshotServiceTestBase):

    def test_12_dry_run_does_not_modify_any_snapshot_file(self):
        src_uid, dst_uid = "u-src", "u-dst"
        cred = self.write_credential(src_uid)
        _src_snap, src_path = self.write_snapshot(
            src_uid, [self.item("t1", 300), self.item("t2", 400)])
        _dst_snap, dst_path = self.write_snapshot(dst_uid, [self.item("t1", 100)])

        before = {p: self.read_bytes(p) for p in (src_path, dst_path)}
        backups_before = set(self.files_under(self.backup_dir))

        plan = svc.dry_run(cred, dst_uid)

        self.assertIsInstance(plan, dict)
        # 契约要求计划含 will_add / will_update / final_count 之类字段。
        # 兼容两种落点：字段平铺在顶层，或后端嵌套在 result["plan"] 下；
        # 终值键兼容 final_count / target_final_count（形状分歧已在报告中标注）。
        plan_fields = plan.get("plan") if isinstance(plan.get("plan"), dict) else plan
        self.assertTrue(
            {"will_add", "will_update"}.issubset(set(plan_fields)),
            msg="dry_run 计划缺少字段: %r" % (plan_fields,))
        final_keys = [k for k in ("final_count", "target_final_count")
                      if k in plan_fields]
        self.assertTrue(final_keys,
                        msg="dry_run 计划缺少最终条数字段: %r" % (plan_fields,))
        self.assertEqual(plan_fields["will_add"], 1)
        self.assertEqual(plan_fields["will_update"], 1)
        self.assertEqual(plan_fields[final_keys[0]], 2)
        self.assertTrue(plan.get("ok", True), msg="dry_run 应成功: %r" % plan)

        after = {p: self.read_bytes(p) for p in (src_path, dst_path)}
        self.assertEqual(after, before, "dry_run 不得改动任何快照文件（字节级）")
        self.assertEqual(set(self.files_under(self.backup_dir)), backups_before,
                         "dry_run 不得产生备份文件")


# ---------------------------------------------------------------------------
# 用例 13：源凭据缺失
# ---------------------------------------------------------------------------
class TestMigrateFailure(SnapshotServiceTestBase):

    def test_13_migrate_missing_credential_returns_false_and_keeps_target(self):
        dst_uid = "u-dst"
        _snap, dst_path = self.write_snapshot(dst_uid, [self.item("keep", 100)])
        before = self.read_bytes(dst_path)

        result = svc.migrate_tasks(str(self.root / "missing_cred.json"), dst_uid)

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("ok"), "源凭据不存在时应 ok=False")
        self.assertIn("error", result)
        self.assertEqual(self.read_bytes(dst_path), before,
                         "失败迁移不得改动目标快照文件")


if __name__ == "__main__":
    unittest.main(verbosity=2)
