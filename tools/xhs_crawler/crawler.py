"""小红书博文抓取核心逻辑：CLI（main.py）与 Web（server.py）共用。

主入口 crawl(...)：
- progress(msg) 回调用于上报进度（CLI 传 print，Web 传日志收集器）
- 返回 (notes, out_dir, uid, stop_reason)；stop_reason 非空表示提前停止
  （风控/登录失效等，已抓取内容会保留并落盘）

登录三种方式：
1. 已保存登录态（data/cache/xhs_state.json）有效 → 直接使用
2. 浏览器交互登录（扫码/短信均可），确认成功后持久化
3. import_cookie_login：从浏览器复制的 cookie 字符串直接生成登录态
"""

import csv
import json
import random
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from playwright.sync_api import TimeoutError as PWTimeout
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit(
        "缺少依赖 playwright。请先执行：\n"
        "  pip install -r requirements.txt\n"
        "  playwright install chromium"
    )

# ---------------------------------------------------------------- 路径与常量

ROOT = Path(__file__).resolve().parents[2]
DATA_OUT = ROOT / "data" / "output"
LOGIN_STATE = ROOT / "data" / "cache" / "xhs_state.json"

BASE = "https://www.xiaohongshu.com"
LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]
STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
# 页面用户态检测：__INITIAL_STATE__ 里能拿到用户 id / loggedIn 才算真登录
# 注意：小红书各层值都可能是 JSON 字符串，必须逐层反序列化
USER_STATE_JS = """
() => {
  const parse = (v) => {
    if (typeof v === 'string') { try { return JSON.parse(v); } catch (e) { return null; } }
    return v;
  };
  try {
    let s = parse(window.__INITIAL_STATE__);
    if (!s || typeof s !== 'object') return false;
    let u = parse(s.user);
    if (!u || typeof u !== 'object') return false;
    if (u.loggedIn === true) return true;
    const info = parse(u.userInfo);
    const src = (info && typeof info === 'object') ? info : u;
    const id = src.userId || src.uid || src.userid;
    return !!(id && String(id).length > 0);
  } catch (e) { return false; }
}
"""

# 小红书页面结构常变：选择器集中在这里，失效时只需更新这一处
SEL = {
    "note_card": "section.note-item a[href*='/explore/'], section.note-item a[href*='/search_result/']",
    "title": "#detail-title, .note-content .title",
    "content": "#detail-desc, .note-content .desc",
    "date": "#detail-desc .date, .bottom-container .date",
    "like": ".like-wrapper .count, .engage-bar .like .count",
    "collect": ".collect-wrapper .count, .engage-bar .collect .count",
    "comment": ".chat-wrapper .count, .engage-bar .comment .count",
    "close_modal": ".close-circle, .close",
    "note_images": "div.note-image img, .media-container img, #detail-desc img",
}

NOTE_ID_RE = re.compile(r"/(?:explore|search_result)/([0-9a-f]{16,32})")
EARLY_STOP_STREAK = 15   # 连续 N 篇早于起始日期则提前结束（主页博文大致按时间倒序）
SCROLL_STALE_LIMIT = 6   # 连续 N 次滚动无新内容，认为已到底
RISK_EMPTY_STREAK = 5    # 详情连续 N 篇解析为空 → 判定风控，停止
FAIL_STREAK = 8          # 详情连续 N 次异常 → 判定风控，停止
LOGIN_TIMEOUT_DEFAULT = 600  # 交互登录最长等待（秒）

# ---------------------------------------------------------------- 异常


class LoginExpired(Exception):
    """登录状态失效，需要重新登录"""


class RiskControlDetected(Exception):
    """疑似被风控，应停止后续任务"""


# ---------------------------------------------------------------- 参数解析


def parse_cli_date(text: "str | None", what: str) -> "date | None":
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"--{what} 日期格式应为 YYYY-MM-DD，收到：{text}")


def normalize_user_target(raw: str) -> "tuple[str, str]":
    """接受用户 ID 或主页链接，返回 (用于访问的主页 URL, 用户 ID)。

    链接形式时原样保留（含 xsec_token 等参数）——小红书很多场景
    缺 token 会直接给空页/要求登录。"""
    raw = raw.strip()
    m = re.search(r"user/profile/([0-9a-f]{16,32})", raw)
    if m:
        uid = m.group(1)
        url = raw if raw.lower().startswith("http") else f"{BASE}/user/profile/{uid}"
    elif re.fullmatch(r"[0-9a-f]{16,32}", raw):
        uid = raw
        url = f"{BASE}/user/profile/{uid}"
    else:
        raise SystemExit(
            f"无法识别博主标识：{raw}\n"
            "请传入主页链接（建议用浏览器地址栏复制的完整链接，含 xsec_token），"
            "或链接中 user/profile/ 后面的用户 ID"
        )
    return url, uid

# ---------------------------------------------------------------- 登录


def _web_session_value(context) -> "str | None":
    """web_session 的当前值。匿名访客也会被下发一个，不能只看存在性。"""
    for c in context.cookies():
        if c["name"] == "web_session" and c.get("value"):
            return c["value"]
    return None


def _page_user_signal(page) -> bool:
    try:
        return bool(page.evaluate(USER_STATE_JS))
    except Exception:
        return False


def _new_context(browser, ua: "str | None" = None,
                 storage_state: "str | None" = None):
    """新建浏览器上下文：默认不覆盖 UA（保持与真实浏览器版本一致），
    注入脚本抹除 navigator.webdriver 标记。"""
    kwargs = dict(viewport={"width": 1280, "height": 860},
                  locale="zh-CN", timezone_id="Asia/Shanghai")
    if ua:
        kwargs["user_agent"] = ua
    if storage_state:
        kwargs["storage_state"] = storage_state
    context = browser.new_context(**kwargs)
    context.add_init_script(STEALTH_JS)
    return context


def _save_state(context) -> None:
    LOGIN_STATE.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(LOGIN_STATE))


def cookie_string_to_state(cookie_str: str) -> dict:
    """把 'a=1; b=2' 形式的 cookie 头合成为 Playwright storage_state。"""
    cookies = []
    for pair in (cookie_str or "").replace("\n", ";").split(";"):
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        name, value = name.strip(), value.strip()
        if not name:
            continue
        cookies.append({
            "name": name, "value": value,
            "domain": ".xiaohongshu.com", "path": "/",
            "expires": int(time.time()) + 180 * 24 * 3600,
            "httpOnly": False, "secure": True, "sameSite": "Lax",
        })
    return {"cookies": cookies, "origins": []}


def import_cookie_login(cookie_str: str) -> "tuple[bool, str]":
    """从浏览器 DevTools 复制的 cookie 字符串生成登录态文件。"""
    state = cookie_string_to_state(cookie_str)
    names = {c["name"] for c in state["cookies"]}
    if not names:
        return False, "cookie 内容为空或格式不对，应为 a=1; b=2 形式"
    if "web_session" not in names:
        return False, "cookie 中缺少 web_session（登录凭证），请确认复制的是已登录浏览器的 cookie"
    LOGIN_STATE.parent.mkdir(parents=True, exist_ok=True)
    LOGIN_STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return True, f"已导入 {len(names)} 个 cookie 并保存登录态（下次抓取时验证）"


def launch_browser(p, headless: bool = False):
    return p.chromium.launch(headless=headless, args=LAUNCH_ARGS)


def ensure_login(browser, log, timeout: int = LOGIN_TIMEOUT_DEFAULT,
                 ua: "str | None" = None):
    """确保已登录：优先用已保存登录态；失效或不存在则等待用户在浏览器中
    以任意方式（扫码/短信）登录，确认后持久化。

    防匿名误判：页面用户态（__INITIAL_STATE__）为主信号；web_session
    只认"相对基线新增/变化且 reload 后稳定"的值——匿名访客也会被下发
    web_session，仅凭存在性判定必误判。
    """
    if LOGIN_STATE.exists():
        context = _new_context(browser, ua, storage_state=str(LOGIN_STATE))
        page = context.new_page()
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        if _page_user_signal(page):
            log("使用已保存的登录态")
            return context
        log("已保存的登录态已失效，需要重新登录")
        context.close()

    context = _new_context(browser, ua)
    page = context.new_page()
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    log(f"请在打开的浏览器窗口中完成登录（扫码/短信均可），最长等待 {timeout} 秒...")
    # 匿名访客也会被下发 web_session：记录基线值，只认"后来新增或变化"的值
    baseline = _web_session_value(context)
    if baseline:
        log("检测到匿名会话 cookie（不算已登录），等待真实登录...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        page.wait_for_timeout(2000)
        # 主信号：页面用户态
        if _page_user_signal(page):
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            if _page_user_signal(page):
                _save_state(context)
                log("登录成功，状态已保存")
                return context
            continue
        # 弱信号兜底：web_session 相对基线新增或被替换（扫码登录会覆盖匿名值），
        # 且 reload 后值稳定——仅"存在"不算数
        cur = _web_session_value(context)
        if cur and cur != baseline:
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            after = _web_session_value(context)
            if _page_user_signal(page) or (after == cur and cur != baseline):
                _save_state(context)
                log("登录成功（web_session 已更新），状态已保存")
                return context
    context.close()
    raise SystemExit(f"等待登录超时（{timeout} 秒）。可重新运行，或改用 Cookie 导入登录")

# ---------------------------------------------------------------- 主页链接收集


def dismiss_modal(page) -> None:
    """关闭可能弹出的登录/引导弹窗"""
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    try:
        page.locator(SEL["close_modal"]).first.click(timeout=1200)
    except Exception:
        pass


def collect_note_links(page, profile_url: str, max_notes: int,
                       log) -> "list[str]":
    log(f"打开博主主页并滚动收集博文链接（上限 {max_notes}）...")
    page.goto(profile_url, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    dismiss_modal(page)
    try:
        page.wait_for_selector(SEL["note_card"], timeout=12000)
    except PWTimeout:
        if "login" in page.url:
            raise LoginExpired("博主主页跳转到登录页，登录态已失效")
        raise RiskControlDetected(
            "博主主页没有加载出任何博文卡片：疑似被风控限流，"
            "或页面结构变化（需更新 crawler.py 顶部 SEL），或该博主无博文")

    links: "dict[str, str]" = {}

    def harvest() -> int:
        cards = page.locator(SEL["note_card"])
        for i in range(cards.count()):
            try:
                href = cards.nth(i).get_attribute("href", timeout=2000) or ""
            except Exception:
                continue
            m = NOTE_ID_RE.search(href)
            if not m or m.group(1) in links:
                continue
            full = href if href.startswith("http") else BASE + href
            links[m.group(1)] = full
        return cards.count()

    prev, stale = -1, 0
    while True:
        count = harvest()
        if len(links) >= max_notes:
            log(f"达到抓取上限 max_notes={max_notes}，停止收集")
            break
        if count == prev:
            stale += 1
            if stale >= SCROLL_STALE_LIMIT:
                break
        else:
            stale = 0
        prev = count
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(random.randint(1500, 2500))

    if not links:
        raise RiskControlDetected(
            "主页卡片存在但未解析出任何博文链接：页面结构可能变化（需更新 SEL），或被风控")
    log(f"共收集到 {len(links)} 条博文链接")
    return list(links.values())

# ---------------------------------------------------------------- 详情抓取


def safe_text(page, selector: str) -> str:
    try:
        text = page.locator(selector).first.inner_text(timeout=3000)
    except Exception:
        return ""
    return re.sub(r"\s+", " ", text or "").strip()


def safe_int(text: str) -> int:
    m = re.search(r"([\d.]+)\s*万", text or "")
    if m:
        return int(float(m.group(1)) * 10000)
    digits = re.sub(r"\D", "", text or "")
    return int(digits) if digits else 0


def parse_note_date(text: str, today: date) -> "date | None":
    """解析详情页日期文本：'编辑于 2026-01-15' / '今天 08:12' / '3天前' / '01-02'"""
    t = (text or "").replace("编辑于", "").strip()
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if "今天" in t:
        return today
    if "昨天" in t:
        return today - timedelta(days=1)
    m = re.search(r"(\d+)\s*天前", t)
    if m:
        return today - timedelta(days=int(m.group(1)))
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", t)
    if m:
        d = date(today.year, int(m.group(1)), int(m.group(2)))
        return date(today.year - 1, d.month, d.day) if d > today else d
    return None


def extract_image_urls(page) -> "list[str]":
    try:
        srcs = page.eval_on_selector_all(
            SEL["note_images"], "els => els.map(e => e.src).filter(Boolean)")
    except Exception:
        srcs = []
    out: "list[str]" = []
    for u in srcs:
        if "xhscdn.com" in u and u not in out:
            out.append(u)
    return out


def crawl_note_detail(page, url: str, today: date,
                      referer: "str | None" = None) -> "dict | None":
    page.goto(url, wait_until="domcontentloaded", referer=referer)
    page.wait_for_timeout(random.randint(3000, 5000))
    dismiss_modal(page)
    if "login" in page.url:
        raise LoginExpired(url)

    title = safe_text(page, SEL["title"]) or "(无标题)"
    date_raw = safe_text(page, SEL["date"])
    content = safe_text(page, SEL["content"])
    if date_raw and date_raw in content:
        content = content.replace(date_raw, "").strip()
    note_date = parse_note_date(date_raw, today)

    m = NOTE_ID_RE.search(url)
    if not m:
        return None
    return {
        "note_id": m.group(1),
        "url": url,
        "title": title,
        "date": note_date.isoformat() if note_date else None,
        "date_raw": date_raw,
        "content": content,
        "likes": safe_int(safe_text(page, SEL["like"])),
        "collects": safe_int(safe_text(page, SEL["collect"])),
        "comments": safe_int(safe_text(page, SEL["comment"])),
        "images": extract_image_urls(page),
    }

# ---------------------------------------------------------------- 输出


def save_outputs(notes: "list[dict]", uid: str, start: date, end: date,
                 out_dir: Path) -> None:
    meta = {
        "blogger": uid,
        "range": [start.isoformat(), end.isoformat()],
        "count": len(notes),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes": notes,
    }
    (out_dir / "notes.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(out_dir / "notes.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["序号", "日期", "标题", "内容摘要", "点赞", "收藏", "评论", "链接"])
        for i, n in enumerate(notes, 1):
            w.writerow([i, n["date"] or "未知", n["title"],
                        n["content"][:100], n["likes"], n["collects"],
                        n["comments"], n["url"]])

    lines = [
        f"# 小红书博文归档 - {uid}", "",
        f"- 时间范围：{start} ~ {end}（含两端）",
        f"- 共 {len(notes)} 篇",
        f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M}", "",
    ]
    for i, n in enumerate(notes, 1):
        lines += [
            f"## {i}. {n['title']}（{n['date'] or '日期未知'}）", "",
            n["content"] or "(无正文)", "",
        ]
        if n["images"]:
            lines.append(f"图片 x{len(n['images'])}（链接见 notes.json）")
        lines += [
            f"赞 {n['likes']} · 藏 {n['collects']} · 评 {n['comments']} · "
            f"[原文]({n['url']})", "", "---", "",
        ]
    (out_dir / "notes.md").write_text("\n".join(lines), encoding="utf-8")


def download_note_images(context, notes: "list[dict]", out_dir: Path,
                         log) -> None:
    total = ok = fail = 0
    for n in notes:
        img_dir = out_dir / "images" / n["note_id"]
        img_dir.mkdir(parents=True, exist_ok=True)
        for idx, u in enumerate(n["images"], 1):
            path = img_dir / f"{idx:02d}.jpg"
            if path.exists():
                continue
            total += 1
            try:
                resp = context.request.get(u, headers={"Referer": f"{BASE}/"})
                if resp.ok:
                    path.write_bytes(resp.body())
                    ok += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
            time.sleep(random.uniform(0.5, 1.0))
    log(f"图片下载完成：成功 {ok}，失败 {fail}（待下载 {total} 张）")

# ---------------------------------------------------------------- 主入口


def crawl(user: str, start: "str | None" = None, end: "str | None" = None,
          download_images: bool = False, max_notes: int = 500,
          min_delay: float = 3.0, max_delay: float = 6.0,
          headless: bool = False, ua: "str | None" = None,
          login_timeout: int = LOGIN_TIMEOUT_DEFAULT,
          progress=None) -> "tuple[list[dict], Path, str, str | None]":
    """抓取指定博主在时间范围内的博文。

    返回 (notes, out_dir, uid, stop_reason)；stop_reason 非空表示因风控/
    登录失效等提前停止，此时 notes 为已抓到的部分内容（已落盘）。
    检测到风控立即停止后续任务，绝不带病硬跑。
    """
    out_log = progress if progress else (lambda msg: None)

    profile_url, uid = normalize_user_target(user)
    today = date.today()
    d_start = parse_cli_date(start, "start") or date(2000, 1, 1)
    d_end = parse_cli_date(end, "end") or today
    if d_start > d_end:
        raise SystemExit(f"起始日期({d_start}) 不能晚于 结束日期({d_end})")

    out_dir = DATA_OUT / "xhs_crawler" / f"{uid}_{d_start}_{d_end}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 日志同步落盘（tee），服务重启/终端关闭后仍可排查
    log_file = open(out_dir / "run.log", "a", encoding="utf-8")

    def log(msg: str) -> None:
        log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        log_file.flush()
        out_log(msg)

    stop_reason: "str | None" = None
    notes: "list[dict]" = []
    log(f"==== 任务开始：博主={uid} 范围=[{d_start}, {d_end}] "
        f"下载图片={download_images} 上限={max_notes} ====")
    try:
        with sync_playwright() as p:
            browser = launch_browser(p, headless=headless)
            try:
                context = ensure_login(browser, log, timeout=login_timeout, ua=ua)
                page = context.new_page()
                # RiskControlDetected / LoginExpired 在此处抛出则没有任何产出
                links = collect_note_links(page, profile_url, max_notes, log)

                empty_streak = fail_streak = older_streak = 0
                for i, link in enumerate(links, 1):
                    log(f"[{i}/{len(links)}] 抓取详情 {link[:90]}")
                    try:
                        note = crawl_note_detail(page, link, today,
                                                 referer=profile_url)
                    except LoginExpired:
                        stop_reason = ("登录态已失效：请在登录管理中重新扫码或"
                                       "导入 Cookie；已抓取内容已保留")
                        break
                    except Exception as exc:
                        fail_streak += 1
                        log(f"  抓取失败（连续 {fail_streak}）：{exc}")
                        if fail_streak >= FAIL_STREAK:
                            stop_reason = (f"连续 {fail_streak} 篇抓取异常，"
                                           "疑似被风控，停止后续任务（已抓取内容已保留）")
                            break
                        continue
                    fail_streak = 0
                    if note is None:
                        continue

                    # 疑似风控验证页：标题/正文/日期/图片全空
                    if (note["title"] == "(无标题)" and not note["content"]
                            and not note["date_raw"] and not note["images"]):
                        empty_streak += 1
                        log(f"  详情解析为空（连续 {empty_streak}），疑似风控验证页")
                        if empty_streak >= RISK_EMPTY_STREAK:
                            stop_reason = (f"连续 {empty_streak} 篇详情解析为空，"
                                           "疑似被风控，停止后续任务（已抓取内容已保留）")
                            break
                        continue
                    empty_streak = 0

                    if note["date"] is None:
                        log("  日期未能解析，保留待人工核对")
                        notes.append(note)
                        older_streak = 0
                        continue

                    nd = date.fromisoformat(note["date"])
                    if d_start <= nd <= d_end:
                        notes.append(note)
                        log(f"  命中范围 {note['date']}：{note['title'][:30]}")
                    if nd < d_start:
                        older_streak += 1
                        if older_streak >= EARLY_STOP_STREAK:
                            log("连续多篇早于起始日期，提前结束抓取")
                            break
                    else:
                        older_streak = 0
                    time.sleep(random.uniform(min_delay, max_delay))

                notes.sort(key=lambda n: n["date"] or "0000-00-00", reverse=True)
                if download_images and notes:
                    download_note_images(context, notes, out_dir, log)
            finally:
                browser.close()

        save_outputs(notes, uid, d_start, d_end, out_dir)
        if stop_reason:
            log(f"任务提前停止：{stop_reason}")
        else:
            log(f"完成：时间范围内共 {len(notes)} 篇")
        return notes, out_dir, uid, stop_reason
    except BaseException as exc:
        # 异常终止也要留下日志（风控/登录失效/超时），不能只抛给上层
        log(f"任务终止（{type(exc).__name__}）：{exc}")
        raise
    finally:
        log_file.close()
