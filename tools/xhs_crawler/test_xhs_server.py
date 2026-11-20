r"""xhs_crawler Web 界面（server.py）API mock 单元测试（TASK-0072）。

运行方式（在仓库根目录 D:\code\tool_box 下执行）：

    python -X utf8 -m unittest discover -s tools/xhs_crawler -t tools/xhs_crawler -p "test_*.py" -v

夜班红线对照（docs/night_ops.md §2：xhs_crawler 不真机抓取，只跑 mock/单元测试）：
1. 全部路由用 Flask app.test_client() 进程内调用：不监听真实端口、
   无真实 socket、无真实 HTTP 网络流量。
2. server.DATA_OUT 与 crawler.LOGIN_STATE 在 setUp 中统一 patch 到临时目录，
   永不指向真实 data/output 与 data/cache/xhs_state.json。
3. threading.Thread 全程 mock：api_start / api_login_qr 不会真正起后台线程；
   _run_login 测试将 server.sync_playwright 与 crawler.ensure_login 一并
   mock——浏览器层零真实调用。
4. 排除项（按任务清单，不做用例）：server:main（真监听/开浏览器）、
   index（模板渲染）、api_image（静态文件服务）。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import crawler  # noqa: E402  扁平脚本目录导入
import server  # noqa: E402

UID = "65a1b2c3000000001a01ab2c"


class ServerTestBase(unittest.TestCase):
    """公共夹具（红线固化）：DATA_OUT/LOGIN_STATE 重定向临时目录 + 状态复位。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="xhs_srv_ut_")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.out_dir = self.tmp / "xhs_output"
        self.state_file = self.tmp / "xhs_state.json"  # 红线：永不指向真实登录态
        for target, name, value in (
                (server, "DATA_OUT", self.out_dir),
                (crawler, "LOGIN_STATE", self.state_file)):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # 复位模块级共享状态，避免用例间串扰
        server._state.update(running=False, logs=[], error=None, result=None)
        server._login.update(busy=False, message="", started=0.0, timeout=0)
        self.client = server.app.test_client()


# ------------------------------------------------ 内部工具（_log / 标注 / 后台任务）


class TestLog(ServerTestBase):
    """覆盖 E：_log 环形缓冲上限与行格式。"""

    def test_ring_buffer_capped_at_max_log_lines(self):
        """超过 MAX_LOG_LINES 后只保留最近 800 条，最旧的被丢弃"""
        for i in range(server.MAX_LOG_LINES + 5):
            server._log(f"m{i}")
        self.assertEqual(len(server._state["logs"]), server.MAX_LOG_LINES)
        self.assertTrue(server._state["logs"][0].endswith("m5"))
        joined = "\n".join(server._state["logs"])
        self.assertNotIn("m0\n", joined)
        self.assertIn(f"m{server.MAX_LOG_LINES + 4}", joined)

    def test_line_format(self):
        """每行带时间戳前缀且包含原文"""
        server._log("hello")
        line = server._state["logs"][-1]
        self.assertTrue(line.startswith("["))
        self.assertIn("hello", line)


class TestAnnotateLocalImages(ServerTestBase):
    """覆盖 E：_annotate_local_images 本地图片 URL 标注。"""

    def test_annotates_sorted_jpg_urls(self):
        """有图片目录的笔记补充 /images/<run>/<nid>/<file> 列表（按文件名排序）"""
        img_dir = self.out_dir / "runA" / "images" / "n1"
        img_dir.mkdir(parents=True)
        (img_dir / "02.jpg").write_bytes(b"b")
        (img_dir / "01.jpg").write_bytes(b"a")
        notes = [{"note_id": "n1"}, {"note_id": "n2"}]
        result = server._annotate_local_images("runA", notes)
        self.assertEqual(result[0]["local_images"],
                         ["/images/runA/n1/01.jpg", "/images/runA/n1/02.jpg"])
        self.assertNotIn("local_images", result[1])

    def test_no_image_dir_leaves_note_untouched(self):
        """目录不存在：笔记不带 local_images 键"""
        result = server._annotate_local_images("missing", [{"note_id": "nX"}])
        self.assertNotIn("local_images", result[0])


class TestRunCrawl(ServerTestBase):
    """覆盖 E：_run_crawl 结果/错误映射与 running 复位（crawl 全 mock）。"""

    def run_it(self, crawl_mock):
        with mock.patch.object(crawler, "crawl", crawl_mock):
            server._run_crawl({"user": UID})
        return server._state

    def test_success_sets_result_and_resets_running(self):
        state = self.run_it(mock.Mock(return_value=(
            [{"note_id": "n1"}], self.out_dir / "runA", "uid1", None)))
        self.assertEqual(state["result"],
                         {"run": "runA", "uid": "uid1", "count": 1})
        self.assertIsNone(state["error"])
        self.assertFalse(state["running"])

    def test_stop_reason_becomes_error(self):
        """crawl 提前停止（stop_reason 非空）→ 写入 error，running 复位"""
        state = self.run_it(mock.Mock(return_value=(
            [], self.out_dir / "runB", "uid", "疑似被风控，停止后续任务")))
        self.assertEqual(state["error"], "疑似被风控，停止后续任务")
        self.assertFalse(state["running"])

    def test_systemexit_message_mapped(self):
        """SystemExit 带消息 → error 为该消息"""
        state = self.run_it(mock.Mock(side_effect=SystemExit("参数错误")))
        self.assertEqual(state["error"], "参数错误")
        self.assertFalse(state["running"])

    def test_empty_systemexit_fallback_message(self):
        """SystemExit 空消息 → 兜底文案 '任务异常结束'"""
        state = self.run_it(mock.Mock(side_effect=SystemExit("")))
        self.assertEqual(state["error"], "任务异常结束")
        self.assertFalse(state["running"])

    def test_generic_exception_formatted(self):
        """一般异常 → '类型: 消息' 格式"""
        state = self.run_it(mock.Mock(side_effect=ValueError("boom")))
        self.assertEqual(state["error"], "ValueError: boom")
        self.assertFalse(state["running"])


# ------------------------------------------------ 路由：抓取与状态


class TestApiStart(ServerTestBase):
    """覆盖 E：api_start 校验/互斥/起线程（线程全程 mock，不真起任务）。"""

    def test_empty_user_400(self):
        """user 缺失 → 400"""
        resp = self.client.post("/api/start", json={})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("请填写博主", resp.get_json()["error"])

    def test_blank_user_400(self):
        """user 全空白 → 400"""
        resp = self.client.post("/api/start", json={"user": "   "})
        self.assertEqual(resp.status_code, 400)

    def test_busy_running_409(self):
        """已有抓取任务在运行 → 409"""
        server._state["running"] = True
        resp = self.client.post("/api/start", json={"user": UID})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("已有任务在运行", resp.get_json()["error"])

    def test_login_busy_409(self):
        """登录进行中 → 409"""
        server._login["busy"] = True
        resp = self.client.post("/api/start", json={"user": UID})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("登录进行中", resp.get_json()["error"])

    def test_start_spawns_patched_thread(self):
        """合法请求 → 标记 running、以 _run_crawl 起线程（Mock），参数透传"""
        with mock.patch.object(server.threading, "Thread") as m_thread:
            resp = self.client.post(
                "/api/start",
                json={"user": UID, "max_notes": 10, "start": "2026-01-01"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["ok"])
        self.assertTrue(server._state["running"])
        kwargs = m_thread.call_args.kwargs
        self.assertIs(kwargs["target"], server._run_crawl)
        self.assertTrue(kwargs["daemon"])
        params = kwargs["args"][0]
        self.assertEqual(params["user"], UID)
        self.assertEqual(params["max_notes"], 10)
        self.assertEqual(params["start"], "2026-01-01")
        self.assertIsNone(params["end"])
        self.assertFalse(params["download_images"])
        m_thread.return_value.start.assert_called_once()


class TestApiStatus(ServerTestBase):
    """覆盖 E：api_status 返回运行态与日志切片。"""

    def test_status_reflects_state_and_logs(self):
        server._log("第一条")
        server._log("第二条")
        server._state["running"] = True
        data = self.client.get("/api/status").get_json()
        self.assertTrue(data["running"])
        self.assertEqual(data["log_total"], 2)
        self.assertEqual(len(data["logs"]), 2)
        self.assertIn("第二条", data["logs"][-1])


# ------------------------------------------------ 路由：登录


class TestApiLoginCookie(ServerTestBase):
    """覆盖 E：api_login_cookie 校验/互斥/真实导入落盘到临时登录态。"""

    def test_empty_cookie_400(self):
        resp = self.client.post("/api/login_cookie", json={"cookie": "  "})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("请粘贴 cookie", resp.get_json()["error"])

    def test_success_imports_and_persists_state(self):
        """合法 cookie（含 web_session）→ 导入成功且写入临时登录态文件"""
        resp = self.client.post("/api/login_cookie",
                                json={"cookie": "a=1; web_session=abc123"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("已导入 2 个 cookie", data["message"])
        self.assertTrue(self.state_file.exists())
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        values = {c["name"]: c["value"] for c in state["cookies"]}
        self.assertEqual(values, {"a": "1", "web_session": "abc123"})
        self.assertIn("已导入", server._login["message"])

    def test_missing_web_session_reports_error(self):
        """缺 web_session → ok=False 且不落盘"""
        resp = self.client.post("/api/login_cookie", json={"cookie": "foo=1"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("web_session", data["error"])
        self.assertFalse(self.state_file.exists())

    def test_busy_409(self):
        """抓取任务进行中 → 409"""
        server._state["running"] = True
        resp = self.client.post("/api/login_cookie",
                                json={"cookie": "web_session=x"})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("任务/登录进行中", resp.get_json()["error"])


class TestApiLoginStatus(ServerTestBase):
    """覆盖 E：api_login_status 的 has_state 与登录剩余时间。"""

    def test_has_state_false_without_file(self):
        """登录态文件不存在 → has_state=False"""
        data = self.client.get("/api/login_status").get_json()
        self.assertFalse(data["has_state"])
        self.assertFalse(data["busy"])

    def test_has_state_true_with_file(self):
        """登录态文件存在（临时目录）→ has_state=True"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text("{}", encoding="utf-8")
        data = self.client.get("/api/login_status").get_json()
        self.assertTrue(data["has_state"])

    def test_busy_remaining_time(self):
        """登录进行中 → busy=True 且 remaining 在 (0, timeout] 内"""
        server._login.update(busy=True, started=server.time.time() - 10,
                             timeout=600, message="正在打开浏览器...")
        data = self.client.get("/api/login_status").get_json()
        self.assertTrue(data["busy"])
        self.assertGreater(data["remaining"], 0)
        self.assertLessEqual(data["remaining"], 600)
        self.assertEqual(data["message"], "正在打开浏览器...")


class TestApiLoginQr(ServerTestBase):
    """覆盖 E：api_login_qr 互斥校验与线程 mock。"""

    def test_running_409(self):
        """抓取任务进行中 → 409"""
        server._state["running"] = True
        resp = self.client.post("/api/login_qr")
        self.assertEqual(resp.status_code, 409)
        self.assertIn("抓取任务进行中", resp.get_json()["error"])

    def test_login_busy_409(self):
        """登录已在进行中 → 409"""
        server._login["busy"] = True
        resp = self.client.post("/api/login_qr")
        self.assertEqual(resp.status_code, 409)
        self.assertIn("登录已在进行中", resp.get_json()["error"])

    def test_success_marks_busy_with_patched_thread(self):
        """空闲时请求 → ok=True、标记 busy、以 _run_login 起线程（Mock）"""
        with mock.patch.object(server.threading, "Thread") as m_thread:
            resp = self.client.post("/api/login_qr")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["ok"])
        self.assertTrue(server._login["busy"])
        self.assertEqual(server._login["message"], "正在打开浏览器...")
        kwargs = m_thread.call_args.kwargs
        self.assertIs(kwargs["target"], server._run_login)
        self.assertEqual(kwargs["args"], (crawler.LOGIN_TIMEOUT_DEFAULT,))
        m_thread.return_value.start.assert_called_once()


class TestRunLogin(ServerTestBase):
    """覆盖 E：_run_login 消息回填（浏览器层全 mock：假 sync_playwright +
    假 ensure_login，绝不触碰真实 Playwright）。"""

    def _patch_pw(self):
        p_obj = mock.MagicMock()
        browser = mock.MagicMock()
        p_obj.chromium.launch.return_value = browser
        pw = mock.MagicMock()
        pw.return_value.__enter__.return_value = p_obj
        patcher = mock.patch.object(server, "sync_playwright", pw)
        patcher.start()
        self.addCleanup(patcher.stop)
        return p_obj, browser

    def test_login_success_message(self):
        """登录成功 → busy=False、message='登录成功'、浏览器关闭"""
        p_obj, browser = self._patch_pw()
        with mock.patch.object(crawler, "ensure_login") as m_ensure:
            server._run_login(600)
        self.assertFalse(server._login["busy"])
        self.assertEqual(server._login["message"], "登录成功")
        m_ensure.assert_called_once()
        self.assertEqual(m_ensure.call_args.kwargs["timeout"], 600)
        p_obj.chromium.launch.assert_called_once_with(
            headless=False, args=crawler.LAUNCH_ARGS)
        browser.close.assert_called_once()

    def test_systemexit_reported(self):
        """超时 SystemExit → message='登录失败：...'、busy 复位"""
        self._patch_pw()
        with mock.patch.object(
                crawler, "ensure_login",
                side_effect=SystemExit("等待登录超时（600 秒）")):
            server._run_login(600)
        self.assertFalse(server._login["busy"])
        self.assertEqual(server._login["message"],
                         "登录失败：等待登录超时（600 秒）")

    def test_generic_exception_reported(self):
        """一般异常 → message 含异常类型与消息"""
        self._patch_pw()
        with mock.patch.object(crawler, "ensure_login",
                               side_effect=ValueError("boom")):
            server._run_login(600)
        self.assertFalse(server._login["busy"])
        self.assertEqual(server._login["message"], "登录失败：ValueError: boom")


# ------------------------------------------------ 路由：结果与历史


class TestApiResults(ServerTestBase):
    """覆盖 E：api_results 的 404/500/正常分支。"""

    def _write_run(self, name, text):
        run_dir = self.out_dir / name
        run_dir.mkdir(parents=True)
        (run_dir / "notes.json").write_text(text, encoding="utf-8")
        return run_dir

    def test_missing_run_404(self):
        """无 run 参数且无上次结果 → 404"""
        resp = self.client.get("/api/results")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("没有可展示的结果", resp.get_json()["error"])

    def test_explicit_missing_run_404(self):
        """run 指向不存在的目录 → 404"""
        resp = self.client.get("/api/results?run=nope")
        self.assertEqual(resp.status_code, 404)

    def test_valid_run_returns_meta_and_notes(self):
        """正常结果 → meta（不含 notes）+ 笔记列表 + 本地图片标注"""
        run_dir = self._write_run("runA", json.dumps({
            "blogger": "uid1", "range": ["2026-11-01", "2026-11-30"],
            "count": 2, "generated_at": "t",
            "notes": [{"note_id": "n1", "title": "t1"},
                      {"note_id": "n2", "title": "t2"}],
        }, ensure_ascii=False))
        img_dir = run_dir / "images" / "n1"
        img_dir.mkdir(parents=True)
        (img_dir / "01.jpg").write_bytes(b"x")
        data = self.client.get("/api/results?run=runA").get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["run"], "runA")
        self.assertEqual(data["meta"]["blogger"], "uid1")
        self.assertNotIn("notes", data["meta"])
        self.assertEqual(data["notes"][0]["local_images"],
                         ["/images/runA/n1/01.jpg"])
        self.assertNotIn("local_images", data["notes"][1])

    def test_corrupt_json_500(self):
        """notes.json 损坏 → 500 与读取失败提示"""
        self._write_run("runB", "not-json{")
        resp = self.client.get("/api/results?run=runB")
        self.assertEqual(resp.status_code, 500)
        self.assertIn("结果文件读取失败", resp.get_json()["error"])


class TestApiHistory(ServerTestBase):
    """覆盖 E：api_history 按 mtime 倒序、无结果/坏文件跳过。"""

    def test_history_sorted_and_filtered(self):
        """新目录在前；坏 JSON 目录与散文件被跳过"""
        old = self.out_dir / "r1"
        new = self.out_dir / "r2"
        bad = self.out_dir / "bad"
        for d in (old, new, bad):
            d.mkdir(parents=True)
        (old / "notes.json").write_text('{"count": 3, "range": ["a", "b"]}',
                                        encoding="utf-8")
        (new / "notes.json").write_text(
            '{"count": 5, "range": [], "generated_at": "g2"}',
            encoding="utf-8")
        (bad / "notes.json").write_text("{corrupt", encoding="utf-8")
        (self.out_dir / "loose.txt").write_text("x", encoding="utf-8")
        now = server.time.time()
        os.utime(old, (now - 1000, now - 1000))
        os.utime(new, (now, now))

        data = self.client.get("/api/history").get_json()
        self.assertTrue(data["ok"])
        self.assertEqual([i["run"] for i in data["items"]], ["r2", "r1"])
        self.assertEqual(data["items"][0]["count"], 5)
        self.assertEqual(data["items"][0]["generated_at"], "g2")
        self.assertEqual(data["items"][1]["count"], 3)
        self.assertEqual(data["items"][1]["range"], ["a", "b"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
