"""xhs_crawler CLI 入口（核心逻辑在 crawler.py，Web 界面见 server.py）

用法示例：
    python main.py 65a1b2c3000000001a01ab2c --start 2026-01-01 --end 2026-11-16
    python main.py "https://www.xiaohongshu.com/user/profile/65a1..." --start 2026-06-01 --download-images
    python main.py --cookie "a1=...; web_session=..." 65a1b2c3... --start 2026-01-01
"""

import argparse
from pathlib import Path

from crawler import LOGIN_TIMEOUT_DEFAULT, crawl, import_cookie_login


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="xhs_crawler：爬取指定博主、指定时间范围内的小红书博文（个人存档用途）")
    ap.add_argument("user", help="博主用户 ID，或主页完整链接（浏览器打开博主主页后复制地址栏）")
    ap.add_argument("--start", help="起始日期 YYYY-MM-DD（含），缺省不限")
    ap.add_argument("--end", help="结束日期 YYYY-MM-DD（含），缺省为今天")
    ap.add_argument("--download-images", action="store_true",
                    help="同时下载博文图片到输出目录 images/")
    ap.add_argument("--max-notes", type=int, default=500,
                    help="最多抓取的博文详情数（安全上限），默认 500")
    ap.add_argument("--min-delay", type=float, default=3.0,
                    help="详情页之间最小间隔（秒），默认 3.0")
    ap.add_argument("--max-delay", type=float, default=6.0,
                    help="详情页之间最大间隔（秒），默认 6.0")
    ap.add_argument("--login-timeout", type=int, default=LOGIN_TIMEOUT_DEFAULT,
                    help=f"浏览器扫码登录最长等待秒数，默认 {LOGIN_TIMEOUT_DEFAULT}")
    ap.add_argument("--cookie", help="从浏览器复制的 cookie 字符串（含 web_session），导入后免扫码")
    ap.add_argument("--cookie-file", help="cookie 所在的文本文件路径（一行即可）")
    ap.add_argument("--ua", help="自定义 User-Agent（默认用浏览器自带，指纹一致更不易被识别）")
    ap.add_argument("--headless", action="store_true",
                    help="无头模式（更易被风控识别，不建议使用）")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    if args.cookie or args.cookie_file:
        raw = args.cookie or Path(args.cookie_file).read_text(encoding="utf-8")
        ok, msg = import_cookie_login(raw)
        print(msg)
        if not ok:
            return

    notes, out_dir, _uid, stop_reason = crawl(
        user=args.user, start=args.start, end=args.end,
        download_images=args.download_images, max_notes=args.max_notes,
        min_delay=args.min_delay, max_delay=args.max_delay,
        headless=args.headless, ua=args.ua,
        login_timeout=args.login_timeout, progress=print)

    print()
    if stop_reason:
        print(f"!! 提前停止：{stop_reason}")
    print(f"完成：时间范围内共 {len(notes)} 篇")
    print(f"结果目录：{out_dir}")
    print("  - notes.json  全量数据")
    print("  - notes.csv   表格汇总（Excel 可直接打开）")
    print("  - notes.md    可读归档")
    print("  - run.log     本次运行日志")


if __name__ == "__main__":
    main()
