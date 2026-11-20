r"""service_manager Web 界面（server.py）路由 mock 单元测试（TASK-0073 / OP-01）。

运行方式（任选其一）：

1) 仓库根目录 D:\code\tool_box 下（推荐，与夜班红测命令一致）：
   python -X utf8 -m unittest discover -s tools/service_manager -t tools/service_manager -p "test_*.py" -v

2) 工具目录内：
   cd /d D:\code\tool_box\tools\service_manager
   python -m unittest test_server_api -v

夜班红线对照（docs/night_ops.md §2 / §5）：
1. 全部路由用 Flask app.test_client() 进程内调用：不启动真实服务进程、
   不监听端口、无 socket、无真实 HTTP 流量（对照红线"不启动真实服务进程/端口监听"）。
2. manager 单例的 4 个对外方法（get_status / start_service / stop_service /
   restart_service）在 setUp 中统一 mock——start/stop/restart 的真实实现
   （含 subprocess.Popen、psutil）全程零调用，对照红线"全程不调用真实实现"。
3. 目录常量重定向临时目录（对照红线"不读写真实 data/"）：
   - service_manager.CACHE_DIR / service_manager.LOGS_DIR（模块常量，防御性 patch，
     server.py 虽未引用，防止任何意外路径写真实 data/cache）；
   - manager 实例的 CACHE_DIR（server.py get_logs 的真实读取点，见下方已知缺陷）。
4. 不安装任何包（Flask 为既有依赖，3.1.3）；不修改 server.py / service_manager.py。
5. 导入 server.py 会执行模块级 app = Flask(...) 与 service_manager 模块级
   manager = ServiceManager()（在真实 data/cache/service_manager 下建目录，
   已被 .gitignore 忽略，属预期行为，不算失败）。

已知源码缺陷（书面记录，红线禁改源码，测试绕行）：
- service_manager.ServiceManager 未把模块常量 CACHE_DIR 绑定到实例/类
  （__init__ 只以模块全局方式引用，实例 dict 仅含 state），
  因此 server.py get_logs 中 `manager.CACHE_DIR` 在生产环境会抛
  AttributeError → Flask 兜底 500，即 /api/logs 现状必 500。
- 本测试用 mock.patch.object(..., create=True) 在临时目录上造出该实例属性，
  只覆盖 get_logs 的路由逻辑本身（路径拼接 / 读全文 / 缺失提示）；
  不固化"必 500"断言，避免源码修复（如 __init__ 绑 self.CACHE_DIR）后用例翻红。

响应结构假设与取舍（对照源码逐条）：
- server.py 路由无 try/except：500 均为 Flask 兜底而非源码分支，
  TestApiStatus 的异常用例验证的是该兜底行为（app.testing 保持 False，
  PROPAGATE_EXCEPTIONS 默认关闭）。
- service_id 是 URL 路径段，源码无"缺参校验"：POST /api/start（无 id）
  由 Werkzeug 路由层 404，manager 方法不被调用——按实际行为测试。
- start/stop/restart 失败时 HTTP 仍为 200（失败语义只在 JSON 内），按源码透传。
- 未知 service_id 在 server 层不校验、透传 manager；/api/logs 按文件名探测，
  不存在文件统一返回提示文案"日志文件不存在"。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import service_manager  # noqa: E402  先注入 sys.path 再导入扁平脚本目录
import server  # noqa: E402

# 与 service_manager.py 的模块常量无关：仅用作"任意存在的服务 id"样本，
# server 层不校验 id，manager 又被 mock，故取值不影响断言。
KNOWN_ID = "xhs_crawler"
UNKNOWN_ID = "ghost"


def make_result(service_id, success, verb_ok, verb_fail):
    """按 manager 对外方法的消息结构构造返回 dict（透传断言用）。"""
    return {
        "service_id": service_id,
        "success": success,
        "message": f"服务 {service_id} {verb_ok if success else verb_fail}",
    }


class ServerApiTestBase(unittest.TestCase):
    """公共夹具（红线固化）：临时目录 + manager 全方法 mock + 进程内 test_client。"""

    def setUp(self):
        # ---- 临时目录（自动清理，绝不触碰真实 data/）----
        tmp = tempfile.TemporaryDirectory(prefix="svc_srv_ut_")
        self.addCleanup(tmp.cleanup)
        self.cache_dir = Path(tmp.name) / "cache"
        self.logs_dir = self.cache_dir / "logs"

        # ---- 目录常量 patch（三层，patch 点跟着源码走）----
        # 1) 模块常量（防御性：server.py 未引用，但防意外写真实目录）
        for target, name, value in (
                (service_manager, "CACHE_DIR", self.cache_dir),
                (service_manager, "LOGS_DIR", self.logs_dir)):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # 2) manager 实例 CACHE_DIR：get_logs 的真实读取点。
        #    已知缺陷：实例上原本没有该属性，须 create=True 造出（见文件头说明）。
        patcher = mock.patch.object(service_manager.manager, "CACHE_DIR",
                                    self.cache_dir, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        # ---- manager 对外方法全 mock（红线：真实实现零调用）----
        self.m_get_status = self._patch_manager_method(
            "get_status", return_value={})
        self.m_start = self._patch_manager_method(
            "start_service",
            return_value=make_result(KNOWN_ID, True, "启动成功", "启动失败"))
        self.m_stop = self._patch_manager_method(
            "stop_service",
            return_value=make_result(KNOWN_ID, True, "关闭成功", "关闭失败"))
        self.m_restart = self._patch_manager_method(
            "restart_service",
            return_value=make_result(KNOWN_ID, True, "重启成功", "重启失败"))

        # ---- Flask 静默：替换 app.logger，异常兜底路径不向 stderr 喷日志 ----
        patcher = mock.patch.object(server.app, "logger", mock.MagicMock(),
                                    create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        # ---- 进程内客户端（无 socket）----
        self.client = server.app.test_client()

    def _patch_manager_method(self, name, return_value):
        """把 manager 单例的对外方法替换为 Mock 并登记清理（实例属性遮蔽类方法）。"""
        patcher = mock.patch.object(service_manager.manager, name,
                                    return_value=return_value)
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        return mocked

    def _write_log(self, service_id, text):
        """在临时 logs 目录下写入指定服务日志文件（logs 相关用例共用）"""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.logs_dir / f"{service_id}.log"
        log_file.write_text(text, encoding="utf-8")
        return log_file


# ------------------------------------------------ 根路由


class TestRootRoute(ServerApiTestBase):
    """覆盖 1：根路由渲染 templates/index.html（只断言 200 与关键字，不深究模板）。"""

    def test_index_returns_200_with_title_keyword(self):
        """GET / → 200，响应含模板标题“服务管理工具”"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("服务管理工具", resp.get_data(as_text=True))

    def test_index_content_type_is_html(self):
        """GET / → Content-Type 为 text/html"""
        resp = self.client.get("/")
        self.assertTrue(resp.content_type.startswith("text/html"))


# ------------------------------------------------ GET /api/status


class TestApiStatus(ServerApiTestBase):
    """覆盖 2：/api/status 的正常返回与异常兜底（源码无 try/except，500 为 Flask 兜底）。"""

    def test_status_returns_mocked_payload(self):
        """manager.get_status 的返回值原样包在 {"status": ...} 中"""
        payload = {
            KNOWN_ID: {"name": "小红书博文爬取", "port": 5000,
                       "running": False, "pid": None, "error": None},
        }
        self.m_get_status.return_value = payload
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": payload})

    def test_status_calls_manager_once_without_args(self):
        """路由以无参形式调用 manager.get_status 恰好一次"""
        self.client.get("/api/status")
        self.m_get_status.assert_called_once_with()

    def test_status_manager_exception_yields_flask_500(self):
        """get_status 抛异常 → Flask 兜底 500（源码无 try/except，非源码分支，
        见文件头“响应结构假设与取舍”）"""
        self.m_get_status.side_effect = RuntimeError("状态读取爆炸")
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 500)


# ------------------------------------------------ POST /api/start/<service_id>


class TestApiStart(ServerApiTestBase):
    """覆盖 3：/api/start 的成功/失败透传、未知 id 透传与缺 id 404。"""

    def test_start_success_message_passthrough(self):
        """成功：HTTP 200，manager 返回的 dict 原样 jsonify 透传"""
        result = make_result(KNOWN_ID, True, "启动成功", "启动失败")
        self.m_start.return_value = result
        resp = self.client.post(f"/api/start/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), result)
        self.m_start.assert_called_once_with(KNOWN_ID)

    def test_start_failure_message_passthrough_http_still_200(self):
        """失败：HTTP 仍为 200，失败语义只在 JSON 内（按源码透传，不改状态码）"""
        result = make_result(KNOWN_ID, False, "启动成功", "启动失败")
        self.m_start.return_value = result
        resp = self.client.post(f"/api/start/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["success"])
        self.assertIn("启动失败", resp.get_json()["message"])

    def test_start_unknown_service_id_passthrough(self):
        """未知 service_id：server 层不校验、原样传给 manager（校验责任在 manager 层）"""
        result = make_result(UNKNOWN_ID, False, "启动成功", "启动失败")
        self.m_start.return_value = result
        resp = self.client.post(f"/api/start/{UNKNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), result)
        self.m_start.assert_called_once_with(UNKNOWN_ID)

    def test_start_without_id_404_and_manager_not_called(self):
        """缺 service_id（POST /api/start）：路由层 404，manager 不被调用"""
        resp = self.client.post("/api/start")
        self.assertEqual(resp.status_code, 404)
        self.m_start.assert_not_called()


# ------------------------------------------------ POST /api/stop/<service_id>


class TestApiStop(ServerApiTestBase):
    """覆盖 4：/api/stop 的成功/失败透传与缺 id 404。"""

    def test_stop_success_message_passthrough(self):
        """成功：HTTP 200，dict 透传，参数为 URL 中的 service_id"""
        result = make_result(KNOWN_ID, True, "关闭成功", "关闭失败")
        self.m_stop.return_value = result
        resp = self.client.post(f"/api/stop/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), result)
        self.m_stop.assert_called_once_with(KNOWN_ID)

    def test_stop_failure_message_passthrough_http_still_200(self):
        """失败：HTTP 仍为 200，JSON 内 success=False 且消息含“关闭失败”"""
        result = make_result(KNOWN_ID, False, "关闭成功", "关闭失败")
        self.m_stop.return_value = result
        resp = self.client.post(f"/api/stop/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["success"])
        self.assertIn("关闭失败", resp.get_json()["message"])

    def test_stop_without_id_404_and_manager_not_called(self):
        """缺 service_id（POST /api/stop）：路由层 404，manager 不被调用"""
        resp = self.client.post("/api/stop")
        self.assertEqual(resp.status_code, 404)
        self.m_stop.assert_not_called()


# ------------------------------------------------ POST /api/restart/<service_id>


class TestApiRestart(ServerApiTestBase):
    """覆盖 5：/api/restart 的成功/失败透传与缺 id 404。"""

    def test_restart_success_message_passthrough(self):
        """成功：HTTP 200，dict 透传"""
        result = make_result(KNOWN_ID, True, "重启成功", "重启失败")
        self.m_restart.return_value = result
        resp = self.client.post(f"/api/restart/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), result)
        self.m_restart.assert_called_once_with(KNOWN_ID)

    def test_restart_failure_message_passthrough_http_still_200(self):
        """失败：HTTP 仍为 200，JSON 内 success=False 且消息含“重启失败”"""
        result = make_result(KNOWN_ID, False, "重启成功", "重启失败")
        self.m_restart.return_value = result
        resp = self.client.post(f"/api/restart/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["success"])
        self.assertIn("重启失败", resp.get_json()["message"])

    def test_restart_without_id_404_and_manager_not_called(self):
        """缺 service_id（POST /api/restart）：路由层 404，manager 不被调用"""
        resp = self.client.post("/api/restart")
        self.assertEqual(resp.status_code, 404)
        self.m_restart.assert_not_called()


# ------------------------------------------------ GET /api/logs/<service_id>


class TestApiLogs(ServerApiTestBase):
    """覆盖 6：/api/logs 读取分支（真实读取点为 manager.CACHE_DIR，见文件头已知缺陷）。"""

    def test_logs_existing_file_returns_full_content(self):
        """日志文件存在：HTTP 200，返回 utf-8 全文（含中文与多行）"""
        content = "2026-11-21 00:00 启动服务\n第二行：中文日志内容\n"
        self._write_log(KNOWN_ID, content)
        resp = self.client.get(f"/api/logs/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"logs": content})

    def test_logs_missing_file_returns_hint(self):
        """日志文件不存在：HTTP 200，返回提示文案“日志文件不存在”（源码实际行为）"""
        resp = self.client.get(f"/api/logs/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"logs": "日志文件不存在"})

    def test_logs_unknown_service_id_returns_hint(self):
        """未知 service_id：server 层不校验，按文件名探测不到 → 同样返回提示文案"""
        resp = self.client.get(f"/api/logs/{UNKNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"logs": "日志文件不存在"})

    def test_logs_empty_file_returns_empty_string(self):
        """空日志文件：返回空字符串（区分“不存在”与“存在但为空”两个分支）"""
        self._write_log(KNOWN_ID, "")
        resp = self.client.get(f"/api/logs/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"logs": ""})


# ------------------------------------------------ 路由边界（404 / 405）


class TestRoutingEdges(ServerApiTestBase):
    """覆盖 7：方法不允许与路径缺失等路由层边界（manager 不被触发）。"""

    def test_get_on_start_endpoint_405(self):
        """GET /api/start/<id>：方法不允许 → 405，start_service 不被调用"""
        resp = self.client.get(f"/api/start/{KNOWN_ID}")
        self.assertEqual(resp.status_code, 405)
        self.m_start.assert_not_called()

    def test_post_on_status_endpoint_405(self):
        """POST /api/status：方法不允许 → 405，get_status 不被调用"""
        resp = self.client.post("/api/status")
        self.assertEqual(resp.status_code, 405)
        self.m_get_status.assert_not_called()

    def test_logs_route_never_touches_manager_methods(self):
        """/api/logs 只读 manager.CACHE_DIR 指向的文件，四个对外方法均不被调用"""
        self._write_log(KNOWN_ID, "内容")
        self.client.get(f"/api/logs/{KNOWN_ID}")
        self.client.get(f"/api/logs/{UNKNOWN_ID}")
        self.m_get_status.assert_not_called()
        self.m_start.assert_not_called()
        self.m_stop.assert_not_called()
        self.m_restart.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
