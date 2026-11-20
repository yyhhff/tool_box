"""
客户端任务快照迁移服务

职责：切号（activate）成功后，把"客户端当前登录账号"的侧边栏任务列表
（sidebar-list-snapshot.json）按 id 去重合并到目标账号，并回写客户端
workbuddy.db 中 sessions.user_id，使会话归属与目标账号一致。

安全约定：
- 凭据文件只白名单读取 account.uid（及 name/id），绝不读取/打印 token、
  accessToken、refreshToken、envelope、$wbEncrypted 等敏感字段的值。
- 迁移只搬运任务条目（不含任何凭据内容），JSON 对象原样保留。
- 写文件前先备份到 SNAPSHOT_BACKUP_DIR/<时间戳>/，写 .tmp 再 os.replace 原子替换。
- 任何异常都返回 ok=False，不向上抛导致 API 500；绝不修改源账号数据。
"""
import json
import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from config import CLIENT_DATA_ROOT, CREDENTIAL_DIR, SNAPSHOT_BACKUP_DIR

logger = logging.getLogger("task_snapshot_service")
logger.addHandler(logging.NullHandler())

SNAPSHOT_FILENAME = "sidebar-list-snapshot.json"
DB_FILENAME = "workbuddy.db"


def _empty_snapshot():
    """返回一个独立的新鲜空快照（避免共享可变默认值）。"""
    return {"version": 3, "savedAt": 0, "items": []}


def _new_backup_dir():
    """创建带时间戳的备份子目录并返回 Path。"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = Path(SNAPSHOT_BACKUP_DIR) / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def read_uid_from_credential(credential_path):
    """白名单读取凭据文件里的 account.uid。

    只读 uid（以及 name/id），绝不读取 token/envelope 等敏感字段的值。
    文件不存在、JSON 非法、结构不符时返回 None，且不会打印任何文件内容。
    """
    if not credential_path:
        return None
    try:
        with open(credential_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    account = data.get("account")
    if isinstance(account, dict):
        uid = account.get("uid")
        if isinstance(uid, str) and uid:
            return uid
    # 兜底：仅当列表里恰好有一个 uid 时才认为无歧义
    # （当前登录账号由 account.uid 指定，此分支只为兼容老格式）
    for key in ("accounts", "allAccounts"):
        accounts = data.get(key)
        if not isinstance(accounts, list):
            continue
        uids = [it.get("uid") for it in accounts
                if isinstance(it, dict) and isinstance(it.get("uid"), str) and it.get("uid")]
        if len(uids) == 1:
            return uids[0]
    return None


def find_credential_by_uid(uid):
    """在凭据快照目录里找 account.uid == uid 的 .info 路径；找不到返回 None。"""
    if not uid:
        return None
    try:
        for path in sorted(Path(CREDENTIAL_DIR).glob("*.info")):
            if read_uid_from_credential(str(path)) == uid:
                return str(path)
    except OSError:
        return None
    return None


def read_snapshot(uid):
    """读取 <CLIENT_DATA_ROOT>/<uid>/sidebar-list-snapshot.json。

    文件不存在或格式非法时返回空快照 {"version":3,"savedAt":0,"items":[]}。
    """
    path = Path(CLIENT_DATA_ROOT) / str(uid) / SNAPSHOT_FILENAME
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, TypeError):
        return _empty_snapshot()
    if not isinstance(data, dict):
        return _empty_snapshot()
    items = data.get("items")
    data["items"] = [it for it in items if isinstance(it, dict)] if isinstance(items, list) else []
    return data


def write_snapshot_atomic(uid, snapshot):
    """备份原文件后原子写入目标快照，返回写入路径 Path。

    先备份到 SNAPSHOT_BACKUP_DIR/<时间戳>/，再写同目录 .tmp 并 fsync，
    最后 os.replace 原子替换，避免写一半被客户端读到。
    """
    target = Path(CLIENT_DATA_ROOT) / str(uid) / SNAPSHOT_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(str(target), str(_new_backup_dir() / SNAPSHOT_FILENAME))
    tmp = Path(str(target) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp), str(target))
    return target


def _freshness(item):
    """用 lastActivityAt / updatedAt 中较大的毫秒值作为任务新鲜度。"""
    def num(v):
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0
    return max(num(item.get("lastActivityAt")), num(item.get("updatedAt")))


def merge_items(src_items, dst_items):
    """按 id 去重合并任务；同 id 保留更新（lastActivityAt/updatedAt 更大）的一份。

    不修改入参，返回 (merged_items, stats)。
    stats: added / updated / unchanged / total_src / total_dst_before / total_merged。
    """
    stats = {
        "added": 0,
        "updated": 0,
        "unchanged": 0,
        "total_src": len(src_items) if isinstance(src_items, list) else 0,
        "total_dst_before": len(dst_items) if isinstance(dst_items, list) else 0,
        "total_merged": 0,
    }
    merged = []
    by_id = {}

    dst_list = dst_items if isinstance(dst_items, list) else []
    for item in dst_list:
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        item_id = copied.get("id")
        if isinstance(item_id, str) and item_id:
            by_id[item_id] = copied
        merged.append(copied)

    src_list = src_items if isinstance(src_items, list) else []
    for item in src_list:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            logger.warning("跳过无 id 的客户端任务条目")
            continue
        copied = dict(item)
        existing = by_id.get(item_id)
        if existing is None:
            by_id[item_id] = copied
            merged.append(copied)
            stats["added"] += 1
        elif _freshness(copied) > _freshness(existing):
            # 以最新快照为准：就地替换目标列表里同 id 的项，保持原顺序
            index = next((i for i, m in enumerate(merged)
                          if isinstance(m.get("id"), str) and m["id"] == item_id), None)
            if index is None:
                merged.append(copied)
            else:
                merged[index] = copied
            by_id[item_id] = copied
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1

    stats["total_merged"] = len(merged)
    return merged, stats


def _backup_db_sidecars(db_path, backup_dir):
    """备份 workbuddy.db 及其 -wal / -shm 伴随文件（若存在）。"""
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            shutil.copy2(str(p), str(backup_dir / p.name))


def copy_sessions_user_id(src_uid, dst_uid, task_ids):
    """把客户端 workbuddy.db 的 sessions.user_id 从 src_uid 改为 dst_uid。

    仅更新 id 在 task_ids 中的记录（UPDATE ... WHERE 防串号）。
    写前备份 db（含 -wal/-shm）。db 被占用（OperationalError）时记日志返回 0，
    不抛给调用方导致整个迁移失败。返回实际更新行数。
    """
    db_path = Path(CLIENT_DATA_ROOT) / DB_FILENAME
    ids = [tid for tid in (task_ids or []) if isinstance(tid, str) and tid]
    if not db_path.exists() or not ids or not src_uid or not dst_uid:
        return 0
    try:
        _backup_db_sidecars(db_path, _new_backup_dir())
        conn = sqlite3.connect(str(db_path), timeout=5)
        try:
            updated = 0
            batch = 500  # 规避 SQLite 默认 999 个绑定变量上限
            for i in range(0, len(ids), batch):
                chunk = ids[i:i + batch]
                placeholders = ",".join("?" for _ in chunk)
                sql = "UPDATE sessions SET user_id = ? WHERE user_id = ? AND id IN (%s)" % placeholders
                cur = conn.execute(sql, [dst_uid, src_uid] + chunk)
                updated += max(cur.rowcount, 0)
            conn.commit()
            return updated
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        logger.warning("sessions 迁移跳过（db 被占用或表结构异常）：%s", e)
        return 0
    except sqlite3.Error as e:
        logger.warning("sessions 迁移失败：%s", e)
        return 0


def migrate_tasks(source_credential_path, target_uid):
    """编排切号任务迁移：读源 uid -> 合并 -> 原子写目标 -> 回写 sessions。

    任何异常都返回 {"ok": False, ..., "error": ...}，不向上抛导致 API 500。
    """
    result = {
        "ok": False,
        "source_uid": None,
        "target_uid": target_uid,
        "stats": {},
        "error": None,
    }
    try:
        src_uid = read_uid_from_credential(source_credential_path)
        result["source_uid"] = src_uid
        if not src_uid:
            result["error"] = "SOURCE_UID_NOT_FOUND"
            logger.warning("源凭据未读到 uid，跳过任务迁移：%s", source_credential_path)
            return result
        if not isinstance(target_uid, str) or not target_uid:
            result["error"] = "TARGET_UID_INVALID"
            return result
        if src_uid == target_uid:
            result["error"] = "SAME_ACCOUNT"
            logger.info("源账号与目标账号相同，跳过任务迁移：%s", src_uid)
            return result

        src_snap = read_snapshot(src_uid)
        dst_snap = read_snapshot(target_uid)
        merged, stats = merge_items(src_snap.get("items", []), dst_snap.get("items", []))

        out_snap = dict(dst_snap)
        out_snap["items"] = merged
        out_snap["savedAt"] = int(time.time() * 1000)

        original_dst = json.loads(json.dumps(dst_snap))  # 回滚点：目标快照迁移前状态
        write_snapshot_atomic(target_uid, out_snap)
        try:
            task_ids = [it["id"] for it in merged
                        if isinstance(it.get("id"), str) and it["id"]]
            stats["sessions_updated"] = copy_sessions_user_id(src_uid, target_uid, task_ids)
        except Exception:
            # 兜底回滚目标快照（copy_sessions 内部已吞掉 db 异常，此处仅防意外）
            write_snapshot_atomic(target_uid, original_dst)
            raise

        result["stats"] = stats
        result["ok"] = True
        logger.info("任务迁移完成：源=%s 目标=%s 统计=%s", src_uid, target_uid, stats)
        return result
    except Exception as e:
        result["error"] = str(e)
        logger.exception("任务迁移失败：%s", e)
        return result


def dry_run(source_credential_path, target_uid):
    """不写任何文件，返回计划：将新增 N 条、更新 M 条、目标最终 K 条。"""
    result = {
        "ok": False,
        "source_uid": None,
        "target_uid": target_uid,
        "stats": {},
        "plan": None,
        "error": None,
    }
    try:
        src_uid = read_uid_from_credential(source_credential_path)
        result["source_uid"] = src_uid
        if not src_uid:
            result["error"] = "SOURCE_UID_NOT_FOUND"
            return result
        src_snap = read_snapshot(src_uid)
        dst_snap = read_snapshot(target_uid)
        merged, stats = merge_items(src_snap.get("items", []), dst_snap.get("items", []))
        result["stats"] = stats
        plan = {
            "will_add": stats["added"],
            "will_update": stats["updated"],
            "unchanged": stats["unchanged"],
            "target_final_count": len(merged),
        }
        result["plan"] = plan
        # 顶层同时暴露契约字段，兼容调用方扁平读取（保留 plan 嵌套无害）
        result["will_add"] = plan["will_add"]
        result["will_update"] = plan["will_update"]
        result["final_count"] = len(merged)
        result["ok"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
