# service_manager

服务管理工具，支持启动、重启、关闭项目中的 Web 服务（xhs_crawler、annual_report_reader），并提供状态查看功能。

## 用法

```bat
python server.py [--port 5002]
```

浏览器打开 http://127.0.0.1:5002 管理服务。

## 功能

- **启动服务**：启动 xhs_crawler 或 annual_report_reader
- **关闭服务**：关闭运行中的服务
- **重启服务**：关闭后重新启动（服务已停止时也可直接重启）
- **查看状态**：列出所有服务及其端口、进程状态

> **停止/重启的健壮性**：进程定位按「记录 PID → 脚本路径 → 端口」三级兜底，服务假死（进程在但端口未监听）也能找到并关闭；关闭会连带清理子进程树；进程已不存在时关闭按成功处理（`get_status` 也会自动纠正僵尸状态）；重启不再因"服务已停止"而失败。

## 输入 / 输出

- **输入**：无（通过 Web 界面选择操作）
- **输出**：
  - 服务状态记录：`data/cache/service_manager/services.json`
  - 服务日志：`data/cache/service_manager/logs/<service>.log`

## 依赖

- Python 3.10+
- Flask
- psutil
