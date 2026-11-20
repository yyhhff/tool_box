r"""service_manager 单元测试（标准库 unittest，无第三方测试框架依赖）。

运行方式（任选其一）：

1) 工具目录内：
   cd /d D:\code\tool_box\tools\service_manager
   python -m unittest test_service_manager -v

2) 仓库根目录（注意 -t 须与 -s 同目录：Python 3.11 的 discover 不支持
   namespace package，子目录 start_dir 没有 __init__.py 会报
   "Start directory is not importable"）：
   python -m unittest discover -s tools/service_manager -t tools/service_manager -p "test_*.py" -v

说明与边界（夜班章程红线对照）：
- 导入 service_manager 模块会执行其模块级 `manager = ServiceManager()`，
  在真实 data/cache/service_manager 下创建目录（已被 .gitignore 忽略，
  属预期行为，不算失败）；除此之外本测试不读写真实 data/ 内容——
  所有状态文件读写均通过 mock 掉 CACHE_DIR/LOGS_DIR 指向临时目录。
- 不启动任何真实服务进程：进程与端口一律用 mock.Mock / SimpleNamespace 假对象。
- mock 边界：_locate_process（进程定位）、psutil.net_connections（端口扫描）、
  psutil.Process 的 cmdline()/connections()（进程识别）。
- psutil 为既有依赖，测试只引用其异常类型，不安装任何包。
"""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import psutil  # noqa: E402  既有依赖
import service_manager  # noqa: E402
from service_manager import ServiceManager  # noqa: E402

XHS_PORT = ServiceManager.SERVICES["xhs_crawler"]["port"]
XHS_SCRIPT = str(ServiceManager.SERVICES["xhs_crawler"]["script"])


class ServiceManagerTestBase(unittest.TestCase):
    """公共夹具：把 CACHE_DIR/LOGS_DIR 指向临时目录，避免触碰真实 data/cache。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="svc_mgr_ut_")
        self.addCleanup(tmp.cleanup)
        self.cache_dir = Path(tmp.name) / "cache"
        self.state_file = self.cache_dir / "services.json"
        for name, value in (("CACHE_DIR", self.cache_dir),
                            ("LOGS_DIR", self.cache_dir / "logs")):
            patcher = mock.patch.object(service_manager, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_manager(self) -> ServiceManager:
        """在已 mock 的目录常量下新建实例（__init__ 会建临时目录结构）。"""
        return ServiceManager()

    def write_state_file(self, payload):
        """预先向临时 CACHE_DIR 写入一份状态文件（测试“文件存在”分支用）。"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")

    def read_persisted_state(self):
        """读取临时目录中已落盘的状态文件。"""
        return json.loads(self.state_file.read_text(encoding="utf-8"))


class TestLoadState(ServiceManagerTestBase):
    """覆盖 1：_load_state（状态文件存在正常加载 / 不存在初始化默认结构）"""

    def test_load_state_with_existing_file(self):
        """状态文件存在：按文件内容原样加载，不使用默认结构"""
        preset = {
            "xhs_crawler": {"running": True, "process": 1111, "error": "preset"},
            "annual_report_reader": {"running": False, "process": None,
                                     "error": None},
        }
        self.write_state_file(preset)
        mgr = self.make_manager()
        self.assertEqual(mgr.state, preset)
        self.assertTrue(mgr.state["xhs_crawler"]["running"])
        self.assertEqual(mgr.state["xhs_crawler"]["process"], 1111)

    def test_load_state_without_file_initializes_defaults(self):
        """状态文件不存在：为全部已配置服务初始化默认停止结构"""
        self.assertFalse(self.cache_dir.exists())
        mgr = self.make_manager()
        expected = {
            service_id: {"running": False, "process": None, "error": None}
            for service_id in ServiceManager.SERVICES
        }
        self.assertEqual(mgr.state, expected)
        # __init__ 顺带建好了目录结构（指向临时目录）
        self.assertTrue(self.cache_dir.exists())
        self.assertTrue((self.cache_dir / "logs").exists())


class TestSaveLoadRoundtrip(ServiceManagerTestBase):
    """覆盖 2：_save_state → 新实例 _load_state 往返一致"""

    def test_save_state_roundtrip_new_instance_loads_identical_state(self):
        """保存后重建实例，加载到的状态与保存前完全一致"""
        mgr1 = self.make_manager()
        mgr1.state["xhs_crawler"] = {"running": True, "process": 4321,
                                     "error": None}
        mgr1.state["annual_report_reader"]["error"] = "上次启动失败"
        mgr1._save_state()

        self.assertTrue(self.state_file.exists())
        mgr2 = self.make_manager()
        self.assertEqual(mgr2.state, mgr1.state)
        self.assertTrue(mgr2.state["xhs_crawler"]["running"])
        self.assertEqual(mgr2.state["xhs_crawler"]["process"], 4321)


class TestClearState(ServiceManagerTestBase):
    """覆盖 3：_clear_state（running/process 复位，error 正确传递并落盘）"""

    def test_clear_state_resets_running_process_and_passes_error(self):
        """传入 error 时：running/process 复位，error 原样保存到内存与文件"""
        mgr = self.make_manager()
        mgr.state["xhs_crawler"] = {"running": True, "process": 9999,
                                    "error": "old"}
        mgr._clear_state("xhs_crawler", error="停止失败: mock")

        entry = mgr.state["xhs_crawler"]
        self.assertFalse(entry["running"])
        self.assertIsNone(entry["process"])
        self.assertEqual(entry["error"], "停止失败: mock")
        persisted = self.read_persisted_state()
        self.assertEqual(persisted["xhs_crawler"], entry)

    def test_clear_state_defaults_error_to_none(self):
        """不传 error 时：error 复位为 None"""
        mgr = self.make_manager()
        mgr.state["xhs_crawler"] = {"running": True, "process": 8888,
                                    "error": "old"}
        mgr._clear_state("xhs_crawler")
        self.assertFalse(mgr.state["xhs_crawler"]["running"])
        self.assertIsNone(mgr.state["xhs_crawler"]["process"])
        self.assertIsNone(mgr.state["xhs_crawler"]["error"])


class TestGetServiceInfo(ServiceManagerTestBase):
    """覆盖 4：_get_service_info（未知 service_id 返回 None）"""

    def test_unknown_service_id_returns_none(self):
        """未知/空 service_id 均返回 None"""
        mgr = self.make_manager()
        self.assertIsNone(mgr._get_service_info("no_such_service"))
        self.assertIsNone(mgr._get_service_info(""))

    def test_known_service_id_returns_config(self):
        """已知 service_id 返回配置（端口与脚本路径）"""
        mgr = self.make_manager()
        info = mgr._get_service_info("xhs_crawler")
        self.assertIsNotNone(info)
        self.assertEqual(info["port"], XHS_PORT)
        self.assertIn("server.py", str(info["script"]))


class TestGetStatus(ServiceManagerTestBase):
    """覆盖 5：get_status 对“标记运行中但进程已消失”的状态自动纠正"""

    def test_stale_running_state_autocorrected_to_stopped(self):
        """state 标记 running=True 但 _locate_process 找不到进程：
        返回值纠正为 running=False / pid=None / error=None，且状态落盘复位"""
        mgr = self.make_manager()
        mgr.state["xhs_crawler"] = {"running": True, "process": 12345,
                                    "error": None}

        with mock.patch.object(ServiceManager, "_locate_process",
                               return_value=None):
            status = mgr.get_status()

        info = status["xhs_crawler"]
        self.assertFalse(info["running"])
        self.assertIsNone(info["pid"])
        self.assertIsNone(info["error"])
        self.assertEqual(info["port"], XHS_PORT)
        self.assertEqual(info["name"],
                         ServiceManager.SERVICES["xhs_crawler"]["name"])

        # 纠正结果已落盘
        persisted = self.read_persisted_state()
        self.assertFalse(persisted["xhs_crawler"]["running"])
        self.assertIsNone(persisted["xhs_crawler"]["process"])
        self.assertIsNone(persisted["xhs_crawler"]["error"])

        # 另一个服务仍在返回列表中且保持停止态
        self.assertIn("annual_report_reader", status)
        self.assertFalse(status["annual_report_reader"]["running"])


class TestStopServiceIdempotent(ServiceManagerTestBase):
    """覆盖 6：stop_service 幂等（进程已不存在时视为关闭成功）"""

    def test_stop_when_process_missing_returns_success(self):
        """_locate_process 返回 None：success=True，消息含“关闭成功”，状态清理"""
        mgr = self.make_manager()
        mgr.state["xhs_crawler"] = {"running": True, "process": 777,
                                    "error": None}

        with mock.patch.object(ServiceManager, "_locate_process",
                               return_value=None):
            resp = mgr.stop_service("xhs_crawler")

        self.assertEqual(resp["service_id"], "xhs_crawler")
        self.assertTrue(resp["success"])
        self.assertIn("关闭成功", resp["message"])
        # 残留状态被清理并落盘
        self.assertFalse(mgr.state["xhs_crawler"]["running"])
        self.assertIsNone(mgr.state["xhs_crawler"]["process"])
        persisted = self.read_persisted_state()
        self.assertFalse(persisted["xhs_crawler"]["running"])

    def test_stop_unknown_service_id_returns_failure(self):
        """未知 service_id：success=False，消息含“关闭失败”"""
        mgr = self.make_manager()
        resp = mgr.stop_service("ghost")
        self.assertFalse(resp["success"])
        self.assertIn("关闭失败", resp["message"])


class TestIsPortInUse(ServiceManagerTestBase):
    """覆盖 7：_is_port_in_use 的三种 psutil 场景（LISTEN 命中 / 空 / AccessDenied）"""

    def _patch_net_connections(self, return_value=None, side_effect=None):
        patcher = mock.patch("service_manager.psutil.net_connections")
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        if side_effect is not None:
            mocked.side_effect = side_effect
        else:
            mocked.return_value = return_value if return_value is not None else []
        return mocked

    def test_listen_connection_on_port_returns_true(self):
        """存在目标端口 LISTEN 连接：返回 True（其余状态/端口/无 laddr 均不干扰）"""
        mocked = self._patch_net_connections(return_value=[
            SimpleNamespace(status="ESTABLISHED",
                            laddr=SimpleNamespace(port=XHS_PORT)),
            SimpleNamespace(status="LISTEN", laddr=SimpleNamespace(port=9999)),
            SimpleNamespace(status="LISTEN",
                            laddr=SimpleNamespace(port=XHS_PORT)),
            SimpleNamespace(status="LISTEN", laddr=None),
        ])
        mgr = self.make_manager()
        self.assertTrue(mgr._is_port_in_use(XHS_PORT))
        mocked.assert_called_once_with(kind="inet")

    def test_no_connections_returns_false(self):
        """连接列表为空：返回 False"""
        self._patch_net_connections(return_value=[])
        mgr = self.make_manager()
        self.assertFalse(mgr._is_port_in_use(XHS_PORT))

    def test_access_denied_returns_false(self):
        """psutil.AccessDenied：静默吞掉并返回 False"""
        self._patch_net_connections(side_effect=psutil.AccessDenied())
        mgr = self.make_manager()
        self.assertFalse(mgr._is_port_in_use(XHS_PORT))

    def test_oserror_returns_false(self):
        """OSError：同样被吞掉返回 False（补充覆盖同一 except 分支）"""
        self._patch_net_connections(side_effect=OSError("network unavailable"))
        mgr = self.make_manager()
        self.assertFalse(mgr._is_port_in_use(XHS_PORT))


class TestIsOurServiceProcess(ServiceManagerTestBase):
    """覆盖 8：_is_our_service_process（命令行路径命中 / 端口兜底，全用假进程）"""

    @staticmethod
    def fake_proc(cmdline=None, connections=None, cmdline_error=None):
        """构造 psutil.Process 的假对象：cmdline() / connections(kind=...) 可控"""
        proc = mock.Mock()
        if cmdline_error is not None:
            proc.cmdline.side_effect = cmdline_error
        else:
            proc.cmdline.return_value = cmdline if cmdline is not None else []
        proc.connections.return_value = connections if connections is not None else []
        return proc

    @staticmethod
    def listen_conn(port):
        return SimpleNamespace(status="LISTEN", laddr=SimpleNamespace(port=port))

    def test_cmdline_path_match_returns_true(self):
        """命令行包含服务脚本路径：命中返回 True，且短路不再查端口"""
        proc = self.fake_proc(cmdline=["python", "-u", XHS_SCRIPT])
        mgr = self.make_manager()
        self.assertTrue(mgr._is_our_service_process(proc, "xhs_crawler"))
        proc.connections.assert_not_called()

    def test_port_fallback_returns_true(self):
        """命令行不含脚本路径但监听服务端口：端口兜底命中返回 True"""
        proc = self.fake_proc(cmdline=["python", "D:/elsewhere/other_server.py"],
                              connections=[self.listen_conn(XHS_PORT)])
        mgr = self.make_manager()
        self.assertTrue(mgr._is_our_service_process(proc, "xhs_crawler"))

    def test_cmdline_denied_falls_back_to_port(self):
        """cmdline() 抛 AccessDenied：降级到端口兜底仍能命中"""
        proc = self.fake_proc(cmdline_error=psutil.AccessDenied(),
                              connections=[self.listen_conn(XHS_PORT)])
        mgr = self.make_manager()
        self.assertTrue(mgr._is_our_service_process(proc, "xhs_crawler"))

    def test_no_match_returns_false(self):
        """命令行不匹配且端口也不匹配：返回 False（防 PID 复用误杀）"""
        proc = self.fake_proc(cmdline=["python", "D:/elsewhere/other_server.py"],
                              connections=[self.listen_conn(6000)])
        mgr = self.make_manager()
        self.assertFalse(mgr._is_our_service_process(proc, "xhs_crawler"))

    def test_unknown_service_id_returns_false(self):
        """未知 service_id：直接返回 False，不触碰进程对象"""
        mgr = self.make_manager()
        proc = self.fake_proc(cmdline=["python", XHS_SCRIPT])
        self.assertFalse(mgr._is_our_service_process(proc, "ghost"))
        proc.cmdline.assert_not_called()


class TestLoadStateFaultTolerance(ServiceManagerTestBase):
    """覆盖 9：_load_state 容错（JSON 损坏备份重建 / 顶层非对象兜底 / 缺服务键补默认）"""

    def _expected_default_state(self):
        """全部已配置服务的默认停止结构（与 _load_state 重建结果对照）"""
        return {service_id: {"running": False, "process": None, "error": None}
                for service_id in ServiceManager.SERVICES}

    def _corrupt_backups(self):
        """列出临时 CACHE_DIR 下的损坏备份文件"""
        return list(self.cache_dir.glob("services.json.corrupt-*.bak"))

    def test_corrupt_json_backed_up_then_rebuilt(self):
        """JSON 损坏：不抛异常，重建默认状态，原文件重命名为 .bak 且内容为损坏原文"""
        corrupt_text = '{"xhs_crawler": {"running": True,'  # 截断即损坏
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(corrupt_text, encoding="utf-8")

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            mgr = self.make_manager()  # 不应抛 JSONDecodeError

        expected = self._expected_default_state()
        self.assertEqual(mgr.state, expected)
        # 中文警示已打印
        self.assertIn("状态文件损坏", fake_out.getvalue())
        self.assertIn("已重建默认状态", fake_out.getvalue())
        # 原文件已被重命名移走：备份文件存在且内容为损坏原文，
        # 当前 services.json 内容为重建的默认结构（而非损坏原文）
        backups = self._corrupt_backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), corrupt_text)
        # 重建后的默认状态已落盘
        self.assertEqual(self.read_persisted_state(), expected)

    def test_top_level_non_dict_treated_as_corrupt(self):
        """JSON 合法但顶层不是对象（如列表）：同样按损坏处理，备份后重建默认状态"""
        original_text = '["not", "a", "dict"]'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(original_text, encoding="utf-8")

        with mock.patch("sys.stdout", new=io.StringIO()):
            mgr = self.make_manager()  # 不应抛 AttributeError

        expected = self._expected_default_state()
        self.assertEqual(mgr.state, expected)
        backups = self._corrupt_backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")),
                         ["not", "a", "dict"])
        self.assertEqual(self.read_persisted_state(), expected)

    def test_missing_service_key_filled_with_default(self):
        """JSON 正常但缺一个服务键：缺失键补默认结构，已有键数据原样保留并落盘"""
        preset = {"xhs_crawler": {"running": True, "process": 2222,
                                  "error": "自定义值须保留"}}
        self.write_state_file(preset)

        mgr = self.make_manager()

        # 已有键数据不变（running=True 的自定义值保留）
        self.assertEqual(mgr.state["xhs_crawler"],
                         {"running": True, "process": 2222, "error": "自定义值须保留"})
        # 缺失键补默认结构
        self.assertEqual(mgr.state["annual_report_reader"],
                         {"running": False, "process": None, "error": None})
        # 补键后落盘：文件含全部已配置服务键
        persisted = self.read_persisted_state()
        self.assertEqual(set(persisted), set(ServiceManager.SERVICES))
        self.assertEqual(persisted["xhs_crawler"],
                         {"running": True, "process": 2222, "error": "自定义值须保留"})
        self.assertEqual(persisted["annual_report_reader"],
                         {"running": False, "process": None, "error": None})


if __name__ == "__main__":
    unittest.main(verbosity=2)
