r"""annual_report_reader Web 界面（server.py）路由 mock 单元测试。

TASK-0077（夜班优化项 OP-03）。覆盖 6 条路由 + _log/_run_pipeline/
_refresh_snapshot 内部函数，共 36 例。

运行方式（仓库根目录 D:\code\tool_box 下执行）：

    python -X utf8 -m unittest discover -s tools/annual_report_reader/tests -t tools/annual_report_reader -p "test_*.py" -v

夜班红线对照（docs/night_ops.md）：
1. 全部路由用 Flask app.test_client() 进程内调用：不监听真实端口、
   无真实 socket、无真实 HTTP 网络流量。
2. 零网络零 GLM 计费：industry.load_snapshot / industry.refresh_snapshot /
   main.run_pipeline 全部 mock，analyzer / LLM 层不被触达。
3. 路径常量在 setUp 统一 mock 重定向到临时目录：server.DATA_OUT、
   memory.CONFIG_PATH、memory.INDEX_PATH，严禁读写真实 data/output/ 与
   data/input/annual_report_reader/config.json。
4. threading.Thread 全程 mock（api_start / api_industries 不真正起后台
   线程）；_run_pipeline / _refresh_snapshot 改为直接同步调用。
5. selfcheck.py 不被收集也不被导入（discover 仅匹配 test_*.py，且本文件
   不 import 它；import 即执行检查会开浏览器）。

与任务建议覆盖项的差异（按源码实际结构，逐条说明）：
- api_start 无"缺行业/公司 → 400"分支：空参默认 auto 全行业模式，
  按实际行为覆盖（空 body / 非法 JSON 均归一为 auto）。
- api_industries 无 select 抛异常分支：异常兜底在 _refresh_snapshot 内，
  单独建类覆盖。
- index 路由只做 200 冒烟（模板渲染细节不在本任务范围，与 xhs 前例一致）。

已记录未修的产品缺陷（只记录，不修）：
- api_report 路径校验用 str.startswith 前缀比对，未补路径分隔符，
  同级目录如 "output2" 会通过前缀检查（目录穿越防护偏弱）。
- api_start 对非数字 top_n（如 "abc"）int() 直接抛 ValueError → 500。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOL_DIR = HERE.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import memory  # noqa: E402
import server  # noqa: E402

SNAP = {
    "updated_at": "2026-11-20 18:00:00",
    "industries": {
        "食品饮料": {"code": "801120",
                    "stocks": [{"code": "600519", "name": "贵州茅台"}]},
        "银行": {"code": "801780",
                "stocks": [{"code": "601398", "name": "工商银行"}]},
    },
}


class ServerTestBase(unittest.TestCase):
    """公共夹具（红线固化）：路径常量重定向临时目录 + 全局状态复位。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="arr_srv_ut_")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.out_dir = self.tmp / "output"
        self.cfg_path = self.tmp / "input" / "config.json"
        self.index_path = self.out_dir / "index.json"
        for target, name, value in (
                (server, "DATA_OUT", self.out_dir),
                (memory, "CONFIG_PATH", self.cfg_path),
                (memory, "INDEX_PATH", self.index_path)):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # 复位模块级共享状态，避免用例间串扰
        server._state.update(running=False, logs=[], error=None,
                             done=0, total=0, current="")
        server._refresh.update(busy=False, error=None)
        self.client = server.app.test_client()


# ------------------------------------------------ GET /api/industries


class TestApiIndustries(ServerTestBase):
    """行业列表路由：正常快照 / 配置透出 / 无快照触发后台刷新。"""

    def test_list_returns_snapshot_industries_with_defaults(self):
        """有快照：行业名/代码/成分透出，top_n 与 last_run 取默认配置"""
        with mock.patch.object(server, "industry") as ind:
            ind.load_snapshot.return_value = dict(SNAP)
            resp = self.client.get("/api/industries")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["updated_at"], "2026-11-20 18:00:00")
        self.assertEqual(body["top_n"], 3)          # DEFAULT_CONFIG
        self.assertIsNone(body["last_run"])
        self.assertEqual([d["name"] for d in body["industries"]],
                         ["食品饮料", "银行"])       # dict 插入序
        fd = body["industries"][0]
        self.assertEqual(fd["code"], "801120")
        self.assertEqual(fd["stocks"][0]["code"], "600519")

    def test_list_reflects_config_top_n_and_last_run(self):
        """config.json（mock 临时路径）里的 top_n / last_run 透出到响应"""
        self.cfg_path.parent.mkdir(parents=True)
        self.cfg_path.write_text(json.dumps(
            {"top_n": 5, "last_run": {"mode": "auto"}}, ensure_ascii=False),
            encoding="utf-8")
        with mock.patch.object(server, "industry") as ind:
            ind.load_snapshot.return_value = dict(SNAP)
            resp = self.client.get("/api/industries")
        body = resp.get_json()
        self.assertEqual(body["top_n"], 5)
        self.assertEqual(body["last_run"], {"mode": "auto"})

    def test_empty_snapshot_starts_refresh_once_and_no_double_spawn(self):
        """空快照：返回 refreshing=True 并起一次刷新线程；忙期间重复请求不再起"""
        with mock.patch.object(server, "industry") as ind, \
                mock.patch.object(server, "threading") as th:
            ind.load_snapshot.return_value = {}
            resp = self.client.get("/api/industries")
            self.assertEqual(resp.status_code, 200)
            body = resp.get_json()
            self.assertFalse(body["ok"])
            self.assertTrue(body["refreshing"])
            self.assertEqual(th.Thread.call_count, 1)
            self.assertIs(th.Thread.call_args.kwargs.get("target"),
                          server._refresh_snapshot)
            self.assertTrue(server._refresh["busy"])
            # 刷新进行中：第二次请求直接返回同一快照，不再重复起线程
            resp2 = self.client.get("/api/industries")
            self.assertEqual(resp2.get_json(), body)
            self.assertEqual(th.Thread.call_count, 1)

    def test_snapshot_without_industries_key_also_refreshes(self):
        """快照缺 industries 键：视同无快照，走刷新分支"""
        with mock.patch.object(server, "industry") as ind, \
                mock.patch.object(server, "threading"):
            ind.load_snapshot.return_value = {"updated_at": "2026-11-20"}
            resp = self.client.get("/api/industries")
        self.assertFalse(resp.get_json()["ok"])
        self.assertTrue(resp.get_json()["refreshing"])


class TestRefreshSnapshot(ServerTestBase):
    """_refresh_snapshot（刷新线程体）：同步直调，industry 全 mock。"""

    def test_success_logs_ready_and_clears_busy(self):
        """抓取成功：busy 复位、error 为空、日志出现「行业快照就绪」"""
        with mock.patch.object(server, "industry") as ind:
            server._refresh["busy"] = True
            server._refresh_snapshot()
        self.assertFalse(server._refresh["busy"])
        self.assertIsNone(server._refresh["error"])
        self.assertTrue(any("行业快照就绪" in ln
                            for ln in server._state["logs"]))
        ind.refresh_snapshot.assert_called_once()
        self.assertIs(ind.refresh_snapshot.call_args.kwargs.get("progress"),
                      server._log)

    def test_failure_records_error_and_clears_busy(self):
        """抓取异常：error 记录、busy 复位、日志出现失败行"""
        with mock.patch.object(server, "industry") as ind:
            ind.refresh_snapshot.side_effect = RuntimeError("net down")
            server._refresh["busy"] = True
            server._refresh_snapshot()
        self.assertFalse(server._refresh["busy"])
        self.assertEqual(server._refresh["error"], "net down")
        self.assertTrue(any("行业快照抓取失败" in ln
                            for ln in server._state["logs"]))


# ------------------------------------------------ POST /api/start


class TestApiStart(ServerTestBase):
    """启动路由：忙判定 / 线程派发 / 参数归一化 / last_run 记忆。"""

    def test_busy_returns_409_and_does_not_spawn(self):
        """已有任务运行：409 + 错误文案，不再起线程，running 保持"""
        server._state["running"] = True
        with mock.patch.object(server, "threading") as th:
            resp = self.client.post("/api/start", json={"industries": ["银行"]})
        self.assertEqual(resp.status_code, 409)
        body = resp.get_json()
        self.assertFalse(body["ok"])
        self.assertIn("已有任务在运行", body["error"])
        self.assertEqual(th.Thread.call_count, 0)
        self.assertTrue(server._state["running"])

    def test_normal_start_spawns_pipeline_thread_and_sets_running(self):
        """正常启动：running 置位、Thread 携带完整 params、日志一行、last_run 落盘"""
        with mock.patch.object(server, "threading") as th:
            resp = self.client.post("/api/start", json={
                "industries": ["食品饮料"], "top_n": 5,
                "force": True, "model": "glm-4-flash"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["ok"])
        self.assertEqual(th.Thread.call_count, 1)
        self.assertIs(th.Thread.call_args.kwargs.get("target"),
                      server._run_pipeline)
        params = th.Thread.call_args.kwargs.get("args")[0]
        self.assertEqual(params["industries"], ["食品饮料"])
        self.assertIsNone(params["stocks"])
        self.assertEqual(params["top_n"], 5)
        self.assertTrue(params["force"])
        self.assertEqual(params["model"], "glm-4-flash")
        self.assertIs(params["progress"], server._log)
        self.assertTrue(server._state["running"])
        self.assertIsNone(server._state["error"])
        self.assertEqual(len(server._state["logs"]), 1)
        self.assertIn("任务开始", server._state["logs"][0])
        cfg = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(cfg["last_run"]["mode"], "industries")
        self.assertEqual(cfg["last_run"]["industries"], ["食品饮料"])
        self.assertEqual(cfg["last_run"]["top_n"], 5)

    def test_stocks_mode_normalizes_codes(self):
        """自定义代码：.SH 后缀剥离、不足 6 位补零、空白项剔除 → mode=stocks"""
        with mock.patch.object(server, "threading") as th:
            resp = self.client.post("/api/start", json={
                "stocks": ["600519.SH", 519, "  ", ""]})
        self.assertTrue(resp.get_json()["ok"])
        params = th.Thread.call_args.kwargs.get("args")[0]
        self.assertEqual(params["stocks"], ["600519", "000519"])
        self.assertIsNone(params["industries"])
        cfg = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(cfg["last_run"]["mode"], "stocks")
        self.assertEqual(cfg["last_run"]["stocks"], ["600519", "000519"])

    def test_empty_body_falls_back_to_auto_mode(self):
        """空 body：industries/stocks/top_n/model 归一为 None → mode=auto，
        last_run 的 top_n 回落默认配置 3"""
        with mock.patch.object(server, "threading") as th:
            resp = self.client.post("/api/start", json={})
        self.assertTrue(resp.get_json()["ok"])
        params = th.Thread.call_args.kwargs.get("args")[0]
        self.assertIsNone(params["industries"])
        self.assertIsNone(params["stocks"])
        self.assertIsNone(params["top_n"])
        self.assertIsNone(params["model"])
        self.assertFalse(params["force"])
        cfg = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(cfg["last_run"]["mode"], "auto")
        self.assertEqual(cfg["last_run"]["top_n"], 3)

    def test_invalid_json_body_treated_as_empty(self):
        """非法 JSON body：silent=True 归一为空 → 仍按 auto 正常启动（与现行为一致）"""
        with mock.patch.object(server, "threading"):
            resp = self.client.post("/api/start", data="{oops",
                                    content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["ok"])

    def test_start_resets_previous_state_and_logs(self):
        """启动时清空上一轮状态：logs/done/total/error/current 全部复位"""
        server._state.update(logs=["old"], done=7, total=9,
                             error="x", current="c")
        with mock.patch.object(server, "threading"):
            resp = self.client.post("/api/start", json={"industries": ["银行"]})
        self.assertEqual(resp.status_code, 200)
        st = server._state
        self.assertTrue(st["running"])
        self.assertEqual(st["done"], 0)
        self.assertEqual(st["total"], 0)
        self.assertIsNone(st["error"])
        self.assertEqual(st["current"], "")
        self.assertEqual(len(st["logs"]), 1)

    def test_blank_model_and_zero_top_n_normalized_to_none(self):
        """model 空白串 → None；top_n=0 → None（falsy 兜底）；last_run 记 3"""
        with mock.patch.object(server, "threading") as th:
            resp = self.client.post("/api/start", json={
                "model": "  ", "top_n": 0})
        self.assertTrue(resp.get_json()["ok"])
        params = th.Thread.call_args.kwargs.get("args")[0]
        self.assertIsNone(params["model"])
        self.assertIsNone(params["top_n"])
        cfg = json.loads(self.cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(cfg["last_run"]["top_n"], 3)


# ------------------------------------------------ _run_pipeline（后台线程体）


class TestRunPipeline(ServerTestBase):
    """_run_pipeline：同步直调，main.run_pipeline 全 mock。"""

    def test_success_calls_pipeline_once_and_resets_running(self):
        """成功：run_pipeline 以原 params 调用一次，running 复位、error 为空"""
        params = {"cfg": {"top_n": 3}, "industries": ["银行"], "stocks": None,
                  "top_n": None, "force": False, "model": None,
                  "progress": server._log}
        server._state["running"] = True
        with mock.patch.object(server, "pipeline") as pl:
            server._run_pipeline(params)
        pl.run_pipeline.assert_called_once_with(**params)
        self.assertFalse(server._state["running"])
        self.assertIsNone(server._state["error"])

    def test_exception_records_error_and_resets_running(self):
        """异常：error 记录 "类型: 消息"，running 仍复位（finally 兜底）"""
        server._state["running"] = True
        with mock.patch.object(server, "pipeline") as pl:
            pl.run_pipeline.side_effect = ValueError("boom")
            server._run_pipeline({"cfg": {}})
        self.assertEqual(server._state["error"], "ValueError: boom")
        self.assertFalse(server._state["running"])


# ------------------------------------------------ _log 状态机


class TestLog(ServerTestBase):
    """_log 行解析：进度正则 / 公司计数 / 完成打勾 / 省略号 / 环形缓冲。"""

    def test_log_bracket_progress_sets_done_total(self):
        """[3/10] 前缀：done=3-1=2，total=10"""
        server._log("[3/10] 贵州茅台 分析中")
        self.assertEqual(server._state["done"], 2)
        self.assertEqual(server._state["total"], 10)

    def test_log_bracket_zero_index_clamped_to_zero(self):
        """[0/3] 异常前缀：done 按 max(0, -1) 钳到 0，不出现负数"""
        server._log("[0/3] 异常序号")
        self.assertEqual(server._state["done"], 0)
        self.assertEqual(server._state["total"], 3)

    def test_log_company_count_sets_total_only(self):
        """"共 N 家公司"：total 更新，done 不动"""
        server._log("本轮共 31 家公司，开始抓取")
        self.assertEqual(server._state["total"], 31)
        self.assertEqual(server._state["done"], 0)

    def test_log_checkmark_increments_done_and_clears_current(self):
        """✔ 行：done +1，current 清空"""
        server._state["current"] = "处理中 ..."
        server._log("✔ 600519 贵州茅台 完成")
        self.assertEqual(server._state["done"], 1)
        self.assertEqual(server._state["current"], "")

    def test_log_ellipsis_sets_current_only(self):
        """以 ... 结尾：current 记整行，done/total 不动"""
        server._log("正在下载 600519 年报 ...")
        self.assertEqual(server._state["current"], "正在下载 600519 年报 ...")
        self.assertEqual(server._state["done"], 0)
        self.assertEqual(server._state["total"], 0)

    def test_log_ring_buffer_capped_at_max_log_lines(self):
        """超过 MAX_LOG_LINES 后只保留最近 800 条，最旧的被丢弃"""
        for i in range(server.MAX_LOG_LINES + 5):
            server._log(f"m{i}")
        logs = server._state["logs"]
        self.assertEqual(len(logs), server.MAX_LOG_LINES)
        self.assertTrue(logs[0].endswith("m5"))       # 前 5 条被丢弃
        self.assertTrue(logs[-1].endswith("m804"))    # 最新一条保留


# ------------------------------------------------ GET /api/status


class TestApiStatus(ServerTestBase):
    """状态轮询路由：空闲默认值 / 状态与日志尾窗透出。"""

    def test_status_idle_defaults(self):
        """空闲：running False、done/total 0、logs 空列表"""
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertFalse(body["running"])
        self.assertIsNone(body["error"])
        self.assertEqual(body["done"], 0)
        self.assertEqual(body["total"], 0)
        self.assertEqual(body["current"], "")
        self.assertEqual(body["logs"], [])

    def test_status_reflects_state_and_last_150_logs(self):
        """运行中：done/total/error/current 原样透出，logs 只留最后 150 条"""
        server._state.update(running=True, done=4, total=10,
                             error="ValueError: boom", current="正在处理 ...")
        server._state["logs"] = [f"L{i}" for i in range(160)]
        resp = self.client.get("/api/status")
        body = resp.get_json()
        self.assertTrue(body["running"])
        self.assertEqual(body["done"], 4)
        self.assertEqual(body["total"], 10)
        self.assertEqual(body["error"], "ValueError: boom")
        self.assertEqual(body["current"], "正在处理 ...")
        self.assertEqual(len(body["logs"]), 150)
        self.assertEqual(body["logs"][0], "L10")
        self.assertEqual(body["logs"][-1], "L159")


# ------------------------------------------------ GET /api/history


class TestApiHistory(ServerTestBase):
    """历史路由：公司按年份倒序 / 行业报告按 mtime 倒序 / 空与损坏兜底。"""

    def test_companies_sorted_by_year_desc_and_fields_merged(self):
        """公司条目按 year 倒序；无 year 的条目排最后；code 与条目字段合并"""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps({
            "600519": {"year": 2024, "status": "done"},
            "000858": {"year": 2025, "status": "done"},
            "300750": {"status": "error"},        # 无 year → or 0 → 最后
        }, ensure_ascii=False), encoding="utf-8")
        resp = self.client.get("/api/history")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual([c["code"] for c in body["companies"]],
                         ["000858", "600519", "300750"])
        self.assertEqual(body["companies"][0]["year"], 2025)
        self.assertEqual(body["companies"][2]["status"], "error")

    def test_industry_reports_sorted_by_mtime_desc(self):
        """行业汇总报告按文件 mtime 倒序，path 带 industries/ 前缀"""
        ind_dir = self.out_dir / "industries"
        ind_dir.mkdir(parents=True)
        (ind_dir / "b_银行.md").write_text("b", encoding="utf-8")
        (ind_dir / "a_食品饮料.md").write_text("a", encoding="utf-8")
        os.utime(ind_dir / "b_银行.md", (1000, 1000))
        os.utime(ind_dir / "a_食品饮料.md", (2000, 2000))
        resp = self.client.get("/api/history")
        inds = resp.get_json()["industries"]
        self.assertEqual([d["name"] for d in inds],
                         ["a_食品饮料.md", "b_银行.md"])
        self.assertEqual(inds[0]["path"], "industries/a_食品饮料.md")

    def test_empty_output_returns_two_empty_lists(self):
        """无 index、无 industries 目录：companies/industries 均为空列表"""
        resp = self.client.get("/api/history")
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["companies"], [])
        self.assertEqual(body["industries"], [])

    def test_corrupted_index_falls_back_to_empty(self):
        """index.json 损坏 JSON：memory 兜底空字典，路由正常返回空列表"""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text("{oops", encoding="utf-8")
        resp = self.client.get("/api/history")
        self.assertEqual(resp.get_json()["companies"], [])


# ------------------------------------------------ GET /api/report


class TestApiReport(ServerTestBase):
    """报告读取路由：code+year / path 两种取法与 404/500 分支。"""

    def test_report_by_code_year_success(self):
        """code+year 命中：content 为 utf-8 全文，path 为文件名"""
        d = self.out_dir / "companies" / "600519_2025"
        d.mkdir(parents=True)
        (d / "report.md").write_text("# 贵州茅台 2025 年报解读",
                                     encoding="utf-8")
        resp = self.client.get("/api/report",
                               query_string={"code": "600519", "year": 2025})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["path"], "report.md")
        self.assertEqual(body["content"], "# 贵州茅台 2025 年报解读")

    def test_report_by_code_year_missing_returns_404(self):
        """code+year 无对应报告：404 +「报告不存在」"""
        resp = self.client.get("/api/report",
                               query_string={"code": "600519", "year": 2099})
        self.assertEqual(resp.status_code, 404)
        body = resp.get_json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "报告不存在")

    def test_report_by_path_success(self):
        """path 参数命中 DATA_OUT 内文件：返回全文"""
        ind_dir = self.out_dir / "industries"
        ind_dir.mkdir(parents=True)
        (ind_dir / "银行.md").write_text("行业对比汇总", encoding="utf-8")
        resp = self.client.get("/api/report",
                               query_string={"path": "industries/银行.md"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["path"], "银行.md")
        self.assertEqual(body["content"], "行业对比汇总")

    def test_report_path_escape_blocked_returns_404(self):
        """path 越出 DATA_OUT（../ 穿越）：404 + "路径无效"，不读外部文件"""
        resp = self.client.get("/api/report",
                               query_string={"path": "../../escape.md"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()["error"], "路径无效")

    def test_report_path_inside_but_missing_returns_404(self):
        """path 在 DATA_OUT 内但文件不存在：同样 404「路径无效」"""
        resp = self.client.get("/api/report",
                               query_string={"path": "industries/nope.md"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()["error"], "路径无效")

    def test_report_invalid_utf8_returns_500(self):
        """报告存在但非 utf-8 内容：读取异常 → 500 +「读取失败」"""
        d = self.out_dir / "companies" / "000001_2025"
        d.mkdir(parents=True)
        (d / "report.md").write_bytes(b"\xff\xfe\xfa")
        resp = self.client.get("/api/report",
                               query_string={"code": "000001", "year": 2025})
        self.assertEqual(resp.status_code, 500)
        body = resp.get_json()
        self.assertFalse(body["ok"])
        self.assertIn("读取失败", body["error"])


# ------------------------------------------------ 框架边界（轻量）


class TestFrameworkEdges(ServerTestBase):
    """未知路径 405/404 与 index 冒烟。"""

    def test_unknown_path_returns_404(self):
        """不存在的 API 路径 → 404"""
        self.assertEqual(self.client.get("/api/nope").status_code, 404)

    def test_method_not_allowed_returns_405(self):
        """GET 打 POST 路由 / POST 打 GET 路由 → 405"""
        self.assertEqual(self.client.get("/api/start").status_code, 405)
        self.assertEqual(self.client.post("/api/status").status_code, 405)
        self.assertEqual(self.client.post("/api/industries").status_code, 405)

    def test_index_route_smoke_200(self):
        """GET / 渲染真实模板（静态文件，非数据）：200 且含 html 标签"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"<html", resp.data.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
