"""service_manager - 服务管理核心逻辑"""

import json
import psutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional


# 项目根目录
ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "service_manager"
LOGS_DIR = CACHE_DIR / "logs"


class ServiceManager:
    """服务管理器"""

    # 服务配置
    SERVICES = {
        "xhs_crawler": {
            "name": "小红书博文爬取",
            "port": 5000,
            "script": ROOT / "tools" / "xhs_crawler" / "server.py",
        },
        "annual_report_reader": {
            "name": "行业龙头年报带读",
            "port": 5001,
            "script": ROOT / "tools" / "annual_report_reader" / "server.py",
        },
    }

    def __init__(self):
        """初始化服务管理器"""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(exist_ok=True)
        self._load_state()

    def _load_state(self) -> None:
        """加载服务状态"""
        state_file = CACHE_DIR / "services.json"
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        else:
            self.state = {service_id: {"running": False, "process": None, "error": None}
                          for service_id in self.SERVICES.keys()}

    def _save_state(self) -> None:
        """保存服务状态"""
        state_file = CACHE_DIR / "services.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def _clear_state(self, service_id: str, error: Optional[str] = None) -> None:
        """清理为已停止状态（停止幂等化用）"""
        self.state[service_id]["running"] = False
        self.state[service_id]["process"] = None
        self.state[service_id]["error"] = error
        self._save_state()

    def _get_service_info(self, service_id: str) -> Optional[Dict]:
        """获取服务信息"""
        return self.SERVICES.get(service_id)

    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN" and conn.laddr and conn.laddr.port == port:
                    return True
        except (psutil.AccessDenied, OSError):
            pass
        return False

    def _get_process_by_port(self, port: int) -> Optional[psutil.Process]:
        """通过端口查找进程"""
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    for conn in proc.connections(kind="inet"):
                        if conn.status == "LISTEN" and conn.laddr and conn.laddr.port == port:
                            return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"获取进程失败: {e}")
        return None

    def _get_process_by_script(self, script_path: Path) -> Optional[psutil.Process]:
        """通过脚本路径查找进程"""
        script = str(script_path)
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if "python" in proc.name().lower():
                        cmdline = proc.cmdline()
                        if any(script in (arg or "") for arg in cmdline):
                            return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"获取进程失败: {e}")
        return None

    def _is_our_service_process(self, proc: psutil.Process, service_id: str) -> bool:
        """判断进程是否属于指定服务（脚本路径匹配，端口兜底，防 PID 复用误杀）"""
        service_info = self._get_service_info(service_id)
        if not service_info:
            return False
        script = str(service_info["script"])
        # 优先：命令行路径匹配
        try:
            cmdline = proc.cmdline()
            if any(script in (arg or "") for arg in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
        # 兜底：端口匹配
        port = service_info["port"]
        try:
            for conn in proc.connections(kind="inet"):
                if conn.status == "LISTEN" and conn.laddr and conn.laddr.port == port:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
        return False

    def _locate_process(self, service_id: str) -> Optional[psutil.Process]:
        """多重兜底定位服务进程：state PID → 脚本路径 → 端口"""
        service_info = self._get_service_info(service_id)
        if not service_info:
            return None

        # 1. state 记录的 PID（二次校验，防 PID 复用误杀）
        pid = self.state.get(service_id, {}).get("process")
        if pid:
            try:
                proc = psutil.Process(pid)
                if self._is_our_service_process(proc, service_id):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # 2. 脚本路径匹配
        proc = self._get_process_by_script(service_info["script"])
        if proc:
            return proc

        # 3. 端口查找
        return self._get_process_by_port(service_info["port"])

    def _terminate_tree(self, proc: psutil.Process, timeout: int = 5) -> bool:
        """终止进程及其子进程树：先 terminate 全体，超时未退的再 kill"""
        try:
            children = proc.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            children = []
        targets = [proc] + children

        # 第一级：优雅终止（Windows 下等价于 TerminateProcess）
        for p in targets:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _, alive = psutil.wait_procs(targets, timeout=timeout)

        # 第二级：对仍存活的强制 kill
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _, still_alive = psutil.wait_procs(alive, timeout=timeout)
        return len(still_alive) == 0

    def _wait_port_free(self, port: int, timeout: float = 5.0) -> bool:
        """等待端口释放"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._is_port_in_use(port):
                return True
            time.sleep(0.3)
        return not self._is_port_in_use(port)

    def _start_service(self, service_id: str) -> bool:
        """启动服务"""
        service_info = self._get_service_info(service_id)
        if not service_info:
            return False

        script = service_info["script"]
        port = service_info["port"]

        # 状态标记为运行中时，实际校验进程是否还活着；已死则重置状态
        if self.state[service_id]["running"]:
            if self._locate_process(service_id):
                return True
            self._clear_state(service_id)

        # 端口占用兜底：若占用者是本服务进程则先清理，否则判定端口被外部占用
        if self._is_port_in_use(port):
            occupant = self._get_process_by_port(port)
            if occupant and self._is_our_service_process(occupant, service_id):
                self._terminate_tree(occupant)
                self._wait_port_free(port)
            else:
                self.state[service_id]["error"] = f"端口 {port} 被其他程序占用"
                self._save_state()
                return False

        # 启动进程
        try:
            log_file = LOGS_DIR / f"{service_id}.log"
            with open(log_file, "a", encoding="utf-8") as log:
                process = subprocess.Popen(
                    ["python", str(script)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=str(script.parent)
                )
                # 等待几秒确认进程存活（比端口判定更可靠：端口监听可能稍晚）
                time.sleep(3)
                if process.poll() is None:
                    self.state[service_id]["running"] = True
                    self.state[service_id]["process"] = process.pid
                    self.state[service_id]["error"] = None
                    self._save_state()
                    return True
                else:
                    self.state[service_id]["error"] = "进程启动后立即退出，请查看日志"
                    self._save_state()
                    return False
        except Exception as e:
            self.state[service_id]["error"] = str(e)
            self._save_state()
            return False

    def _stop_service(self, service_id: str) -> bool:
        """停止服务（幂等：进程不存在视为已停止）"""
        service_info = self._get_service_info(service_id)
        if not service_info:
            return False

        proc = self._locate_process(service_id)
        if not proc:
            # 进程已不存在：清理残留状态并返回成功
            self._clear_state(service_id)
            return True

        try:
            ok = self._terminate_tree(proc)
            if ok:
                self._clear_state(service_id)
                return True
            else:
                self._clear_state(service_id, error="进程残留，强制终止未成功")
                return False
        except Exception as e:
            self._clear_state(service_id, error=f"停止失败: {e}")
            return False

    def _restart_service(self, service_id: str) -> bool:
        """重启服务：先尽力停止（不因"本就停止"而中止），再启动"""
        self._stop_service(service_id)
        service_info = self._get_service_info(service_id)
        if service_info:
            self._wait_port_free(service_info["port"])
        return self._start_service(service_id)

    def get_status(self) -> Dict[str, Dict]:
        """获取所有服务状态"""
        status = {}
        for service_id, service_info in self.SERVICES.items():
            running = self.state[service_id]["running"]
            process_id = self.state[service_id]["process"]
            error = self.state[service_id]["error"]

            if running and not self._locate_process(service_id):
                # 状态显示运行中但进程已不存在：自动纠正
                running = False
                self._clear_state(service_id)
                process_id = None
                error = None

            status[service_id] = {
                "name": service_info["name"],
                "port": service_info["port"],
                "running": running,
                "pid": process_id if running else None,
                "error": error,
            }
        return status

    def start_service(self, service_id: str) -> Dict:
        """启动服务"""
        success = self._start_service(service_id)
        return {
            "service_id": service_id,
            "success": success,
            "message": f"服务 {service_id} {'启动成功' if success else '启动失败'}",
        }

    def stop_service(self, service_id: str) -> Dict:
        """停止服务"""
        success = self._stop_service(service_id)
        return {
            "service_id": service_id,
            "success": success,
            "message": f"服务 {service_id} {'关闭成功' if success else '关闭失败'}",
        }

    def restart_service(self, service_id: str) -> Dict:
        """重启服务"""
        success = self._restart_service(service_id)
        return {
            "service_id": service_id,
            "success": success,
            "message": f"服务 {service_id} {'重启成功' if success else '重启失败'}",
        }


# 全局实例
manager = ServiceManager()
