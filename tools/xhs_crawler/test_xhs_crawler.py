r"""xhs_crawler 纯逻辑 mock 单元测试：crawler.py + main.py（TASK-0072）。

运行方式（在仓库根目录 D:\code\tool_box 下执行，任选其一）：

    # 仅本文件
    python -X utf8 -m unittest discover -s tools/xhs_crawler -t tools/xhs_crawler -p "test_xhs_crawler.py" -v

    # 全部测试（含 test_xhs_server.py）
    python -X utf8 -m unittest discover -s tools/xhs_crawler -t tools/xhs_crawler -p "test_*.py" -v

夜班红线对照（docs/night_ops.md §2：xhs_crawler 不真机抓取，只跑 mock/单元测试）：
1. 绝不发起真实网络请求、绝不启动真实浏览器/真实 Playwright：
   浏览器层全部 mock——sync_playwright 用 MagicMock 假上下文管理器，
   ensure_login / collect_note_links / crawl_note_detail / download_note_images
   在编排层测试中按脚本 fake；Playwright page/context 用 Mock、
   SimpleNamespace 及本文件 Fake* 假对象（接口按 crawler.py 源码构造）。
2. crawler.LOGIN_STATE 在 setUp 中统一 patch 到临时目录的 xhs_state.json，
   永不指向真实 data/cache/xhs_state.json。
3. crawler.DATA_OUT 在 setUp 中统一 patch 到临时目录，不写真实 data/output。
4. crawl 编排测试统一 mock time.sleep；FakePage.wait_for_timeout 为空操作，
   全部用例瞬时完成，无任何真实等待。
5. 只读产品代码不修改；不 pip 安装；不提交 git。

分组说明（与任务清单对应）：
- A 纯函数：parse_cli_date / normalize_user_target / safe_int / parse_note_date /
  NOTE_ID_RE / safe_text / extract_image_urls
- B Cookie 导入与登录信号：cookie_string_to_state / import_cookie_login /
  _web_session_value / _page_user_signal / _new_context / _save_state /
  launch_browser / ensure_login 双信号判定 / dismiss_modal
- C 熔断编排与落日志：crawl / collect_note_links / crawl_note_detail /
  save_outputs / download_note_images
- D main.py：parse_args 默认值与 cookie 导入优先分支
"""

import csv
import io
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import crawler  # noqa: E402  扁平脚本目录导入
import main as xhs_main  # noqa: E402

UID = "65a1b2c3000000001a01ab2c"  # 24 位十六进制博主 ID
BASE = crawler.BASE


# ---------------------------------------------------------------- 假对象


class FakeClock:
    """可控 time.time()：按序列返回（末值重复），驱动 ensure_login 超时循环。"""

    def __init__(self, values):
        self._values = list(values)
        self._i = 0

    def time(self):
        val = self._values[min(self._i, len(self._values) - 1)]
        self._i += 1
        return val


class FakePage:
    """ensure_login 用假页面：evaluate 按序列返回（末值重复），reload 可计数。"""

    def __init__(self, eval_seq=()):
        self._eval_seq = list(eval_seq)
        self._eval_i = 0
        self.reload_count = 0
        self.goto = mock.Mock()
        self.keyboard = mock.Mock()
        self.wait_for_timeout = mock.Mock()

    def evaluate(self, _js):
        if not self._eval_seq:
            return False
        val = self._eval_seq[min(self._eval_i, len(self._eval_seq) - 1)]
        self._eval_i += 1
        return val

    def reload(self, **_kw):
        self.reload_count += 1


class FakeContext:
    """ensure_login 用假上下文：cookies() 按序列返回（末值重复）。"""

    def __init__(self, page, cookie_seq=()):
        self.page = page
        self._cookie_seq = list(cookie_seq)
        self._cookie_i = 0
        self.closed = False
        self.storage_state = mock.Mock()
        self.add_init_script = mock.Mock()

    def new_page(self):
        return self.page

    def cookies(self):
        if not self._cookie_seq:
            return []
        val = self._cookie_seq[min(self._cookie_i, len(self._cookie_seq) - 1)]
        self._cookie_i += 1
        return val

    def close(self):
        self.closed = True


def anon_cookie(value):
    """构造一条 web_session cookie（ensure_login 弱信号判定输入）。"""
    return {"name": "web_session", "value": value}


class FakeCards:
    """collect_note_links 用假卡片集合：nth(i).get_attribute("href") 返回预设值。"""

    def __init__(self, hrefs, fail_indexes=()):
        self.hrefs = list(hrefs)
        self.fail_indexes = set(fail_indexes)

    def count(self):
        return len(self.hrefs)

    def nth(self, i):
        card = mock.Mock()
        if i in self.fail_indexes:
            card.get_attribute.side_effect = RuntimeError("element detached")
        else:
            card.get_attribute.return_value = self.hrefs[i]
        return card


class FakeProfilePage:
    """collect_note_links 用假主页：locator(note_card) 逐批消费预设 hrefs。"""

    def __init__(self, batches, url=None):
        self.batches = list(batches)  # 每次 locator(note_card) 消费一个批次
        self.url = url or f"{BASE}/user/profile/{UID}"
        self.locator_calls = 0
        self.mouse = mock.Mock()
        self.keyboard = mock.Mock()
        self.goto = mock.Mock()
        self.wait_for_timeout = mock.Mock()
        self.wait_for_selector = mock.Mock()

    def locator(self, sel):
        if sel == crawler.SEL["close_modal"]:
            return mock.Mock()  # dismiss_modal 的关闭按钮：点击无异常即可
        batch = self.batches.pop(0) if self.batches else []
        self.locator_calls += 1
        return batch if isinstance(batch, FakeCards) else FakeCards(batch)


def make_detail_page(url, texts=None, images=()):
    """crawl_note_detail 用假 page：locator(sel).first.inner_text() 按 texts 返回。"""
    page = mock.MagicMock()
    page.url = url
    texts = dict(texts or {})

    def locator(sel):
        holder = mock.MagicMock()
        holder.first.inner_text.return_value = texts.get(sel, "")
        return holder

    page.locator.side_effect = locator
    page.eval_on_selector_all.return_value = list(images)
    return page


def make_note(note_id, d="2026-11-05", title="标题甲", content="正文内容",
              images=(), likes=3):
    """构造 crawl 编排层使用的完整 note dict。"""
    return {
        "note_id": note_id,
        "url": f"{BASE}/explore/{note_id}",
        "title": title,
        "date": d,
        "date_raw": d if d else "",
        "content": content,
        "likes": likes,
        "collects": 1,
        "comments": 2,
        "images": list(images),
    }


def make_empty_note(note_id):
    """构造风控验证页形态的空 note（crawl 空结果熔断的判定输入）。"""
    return make_note(note_id, d=None, title="(无标题)", content="", images=[])


# ---------------------------------------------------------------- 公共夹具


class CrawlerTestBase(unittest.TestCase):
    """公共夹具（红线固化）：LOGIN_STATE/DATA_OUT 重定向到临时目录。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="xhs_ut_")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.out_root = self.tmp / "output"
        self.state_file = self.tmp / "xhs_state.json"  # 红线：永不指向真实登录态
        for name, value in (("LOGIN_STATE", self.state_file),
                            ("DATA_OUT", self.out_root)):
            patcher = mock.patch.object(crawler, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_saved_state(self):
        """预置一个"已存在"的登录态文件（仅存在性参与判定，内容随意）。"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text('{"cookies": [], "origins": []}',
                                   encoding="utf-8")


# ================================================================ A 纯函数


class TestParseCliDate(CrawlerTestBase):
    """覆盖 A：parse_cli_date 日期解析与错误提示。"""

    def test_valid_date_parsed(self):
        """合法 YYYY-MM-DD 解析为 date 对象"""
        self.assertEqual(crawler.parse_cli_date("2026-01-02", "start"),
                         date(2026, 1, 2))

    def test_invalid_format_raises_systemexit_with_flag(self):
        """格式错误抛 SystemExit，提示含 --start 与原文"""
        with self.assertRaises(SystemExit) as ctx:
            crawler.parse_cli_date("2026/01/02", "start")
        msg = str(ctx.exception)
        self.assertIn("--start", msg)
        self.assertIn("2026/01/02", msg)

    def test_invalid_end_flag_name_reported(self):
        """what="end" 时提示 --end"""
        with self.assertRaises(SystemExit) as ctx:
            crawler.parse_cli_date("bad", "end")
        self.assertIn("--end", str(ctx.exception))

    def test_empty_and_none_return_none(self):
        """空串与 None 均返回 None（不限日期）"""
        self.assertIsNone(crawler.parse_cli_date(None, "start"))
        self.assertIsNone(crawler.parse_cli_date("", "end"))


class TestNormalizeUserTarget(CrawlerTestBase):
    """覆盖 A：博主标识归一化（TASK-0007 核心：链接含 xsec_token 原样保留）。"""

    def test_bare_id_normalized_with_surrounding_space(self):
        """纯博主 ID（含首尾空白）→ (BASE 主页 URL, ID)"""
        url, uid = crawler.normalize_user_target(f"  {UID}  ")
        self.assertEqual(uid, UID)
        self.assertEqual(url, f"{BASE}/user/profile/{UID}")

    def test_full_link_kept_verbatim_including_xsec_token(self):
        """完整主页链接原样保留（含 xsec_token 等全部参数），ID 正确提取"""
        raw = (f"https://www.xiaohongshu.com/user/profile/{UID}"
               "?xsec_token=ABCD1234&xsec_source=pc_user")
        url, uid = crawler.normalize_user_target(raw)
        self.assertEqual(url, raw)
        self.assertEqual(uid, UID)

    def test_schemeless_link_rebuilt_with_base(self):
        """无协议头链接：ID 提取后用 BASE 重建主页 URL"""
        raw = f"www.xiaohongshu.com/user/profile/{UID}"
        url, uid = crawler.normalize_user_target(raw)
        self.assertEqual(uid, UID)
        self.assertEqual(url, f"{BASE}/user/profile/{UID}")

    def test_unrecognized_target_raises_systemexit(self):
        """过短/非十六进制/纯文本均抛 SystemExit 并提示格式"""
        for bad in ("65a1", "hello", "z" * 24):
            with self.assertRaises(SystemExit) as ctx:
                crawler.normalize_user_target(bad)
            self.assertIn("无法识别博主标识", str(ctx.exception))


class TestSafeInt(CrawlerTestBase):
    """覆盖 A：safe_int 中文计数解析。"""

    def test_wan_unit_multiplied(self):
        self.assertEqual(crawler.safe_int("1.2万"), 12000)

    def test_decimal_wan(self):
        self.assertEqual(crawler.safe_int("0.5万"), 5000)

    def test_wan_with_spaces(self):
        self.assertEqual(crawler.safe_int(" 3.5万 "), 35000)

    def test_plain_digits(self):
        self.assertEqual(crawler.safe_int("128"), 128)

    def test_no_digits_returns_zero(self):
        self.assertEqual(crawler.safe_int("赞"), 0)

    def test_empty_and_none_return_zero(self):
        self.assertEqual(crawler.safe_int(""), 0)
        self.assertEqual(crawler.safe_int(None), 0)


class TestParseNoteDate(CrawlerTestBase):
    """覆盖 A：parse_note_date 各类详情页日期文案。"""

    TODAY = date(2026, 11, 20)

    def test_full_date(self):
        """完整日期直接解析"""
        self.assertEqual(crawler.parse_note_date("2026-01-15", self.TODAY),
                         date(2026, 1, 15))

    def test_edited_prefix(self):
        """'编辑于 YYYY-MM-DD' 前缀剥离后解析"""
        self.assertEqual(crawler.parse_note_date("编辑于 2026-01-15", self.TODAY),
                         date(2026, 1, 15))

    def test_today(self):
        self.assertEqual(crawler.parse_note_date("今天 08:12", self.TODAY),
                         self.TODAY)

    def test_yesterday(self):
        self.assertEqual(crawler.parse_note_date("昨天", self.TODAY),
                         self.TODAY - timedelta(days=1))

    def test_days_ago(self):
        self.assertEqual(crawler.parse_note_date("3天前", self.TODAY),
                         self.TODAY - timedelta(days=3))

    def test_days_ago_with_space(self):
        self.assertEqual(crawler.parse_note_date("12 天前", self.TODAY),
                         self.TODAY - timedelta(days=12))

    def test_month_day_past_stays_current_year(self):
        """MM-DD 早于今天：留在当前年"""
        today = date(2026, 6, 15)
        self.assertEqual(crawler.parse_note_date("01-02", today),
                         date(2026, 1, 2))

    def test_month_day_future_falls_back_to_last_year(self):
        """MM-DD 晚于今天：跨年回退到上一年"""
        today = date(2026, 6, 15)
        self.assertEqual(crawler.parse_note_date("12-31", today),
                         date(2025, 12, 31))

    def test_unparseable_returns_none(self):
        """无法识别的文案/空/None → None"""
        for text in ("随便写的", "", None):
            self.assertIsNone(crawler.parse_note_date(text, self.TODAY))


class TestNoteIdRe(CrawlerTestBase):
    """覆盖 A：NOTE_ID_RE 提取 16-32 位十六进制 note id。"""

    def test_explore_url_extracts_id(self):
        m = crawler.NOTE_ID_RE.search(f"{BASE}/explore/{UID}?xsec_token=T")
        self.assertEqual(m.group(1), UID)

    def test_search_result_url_extracts_id(self):
        m = crawler.NOTE_ID_RE.search(f"{BASE}/search_result/{UID}")
        self.assertEqual(m.group(1), UID)

    def test_min_length_16(self):
        nid = "a" * 16
        m = crawler.NOTE_ID_RE.search(f"/explore/{nid}")
        self.assertEqual(m.group(1), nid)

    def test_max_length_32(self):
        nid = "b" * 32
        m = crawler.NOTE_ID_RE.search(f"/explore/{nid}")
        self.assertEqual(m.group(1), nid)

    def test_15_chars_no_match(self):
        self.assertIsNone(crawler.NOTE_ID_RE.search("/explore/" + "a" * 15))

    def test_non_note_urls_no_match(self):
        self.assertIsNone(
            crawler.NOTE_ID_RE.search(f"{BASE}/user/profile/{UID}"))
        self.assertIsNone(crawler.NOTE_ID_RE.search("/explore/xyz!"))


class TestSafeText(CrawlerTestBase):
    """覆盖 A：safe_text 文本清洗与异常兜底。"""

    def test_whitespace_collapsed_and_stripped(self):
        page = mock.MagicMock()
        page.locator.return_value.first.inner_text.return_value = "  赞\n100\t "
        self.assertEqual(crawler.safe_text(page, "#t"), "赞 100")

    def test_locator_error_returns_empty(self):
        page = mock.MagicMock()
        page.locator.side_effect = RuntimeError("no such element")
        self.assertEqual(crawler.safe_text(page, "#t"), "")


class TestExtractImageUrls(CrawlerTestBase):
    """覆盖 A：extract_image_urls 仅保留 xhscdn 域并按序去重。"""

    def test_filter_and_dedup_keep_order(self):
        page = mock.MagicMock()
        page.eval_on_selector_all.return_value = [
            "https://sns-img.xhscdn.com/a.jpg",
            "https://pic.other.com/b.jpg",
            "https://sns-img.xhscdn.com/a.jpg",
        ]
        self.assertEqual(crawler.extract_image_urls(page),
                         ["https://sns-img.xhscdn.com/a.jpg"])

    def test_eval_error_returns_empty(self):
        page = mock.MagicMock()
        page.eval_on_selector_all.side_effect = RuntimeError("boom")
        self.assertEqual(crawler.extract_image_urls(page), [])


# ============================================================ B Cookie/登录


class TestCookieStringToState(CrawlerTestBase):
    """覆盖 B：cookie 头 → Playwright storage_state 合成。"""

    def test_basic_pairs_fixed_fields(self):
        """a=1; b=2 → 两条 cookie，domain/expires/sameSite 等字段固定"""
        state = crawler.cookie_string_to_state("a=1; b=2")
        self.assertEqual([c["name"] for c in state["cookies"]], ["a", "b"])
        self.assertEqual([c["value"] for c in state["cookies"]], ["1", "2"])
        for c in state["cookies"]:
            self.assertEqual(c["domain"], ".xiaohongshu.com")
            self.assertEqual(c["path"], "/")
            self.assertFalse(c["httpOnly"])
            self.assertTrue(c["secure"])
            self.assertEqual(c["sameSite"], "Lax")
        self.assertEqual(state["origins"], [])

    def test_newline_treated_as_separator(self):
        state = crawler.cookie_string_to_state("a=1\nb=2")
        self.assertEqual([c["name"] for c in state["cookies"]], ["a", "b"])

    def test_invalid_pairs_skipped(self):
        """无 '=' 与空名的片段被跳过"""
        state = crawler.cookie_string_to_state(";; =x ; ok=1")
        self.assertEqual([c["name"] for c in state["cookies"]], ["ok"])

    def test_value_may_contain_equals(self):
        state = crawler.cookie_string_to_state("a=b=c")
        self.assertEqual(state["cookies"][0]["value"], "b=c")

    def test_expires_about_180_days(self):
        now = int(crawler.time.time())
        state = crawler.cookie_string_to_state("web_session=s1")
        expires = state["cookies"][0]["expires"]
        self.assertAlmostEqual(expires, now + 180 * 24 * 3600, delta=120)


class TestImportCookieLogin(CrawlerTestBase):
    """覆盖 B：import_cookie_login 拒绝缺 web_session，成功落盘到临时登录态。"""

    def test_missing_web_session_rejected_and_no_file(self):
        """缺 web_session → (False, 提示含 web_session)，不落盘"""
        ok, msg = crawler.import_cookie_login("foo=1; bar=2")
        self.assertFalse(ok)
        self.assertIn("web_session", msg)
        self.assertFalse(self.state_file.exists())

    def test_empty_or_malformed_rejected(self):
        """无有效 cookie 对 → (False, 'cookie 内容为空或格式不对')"""
        for raw in (";;;", "", None):
            ok, msg = crawler.import_cookie_login(raw)
            self.assertFalse(ok)
            self.assertIn("cookie 内容为空或格式不对", msg)

    def test_success_writes_state_file(self):
        """含 web_session → (True, 已导入 N 个)，登录态写入临时路径"""
        ok, msg = crawler.import_cookie_login("a=1; web_session=abc123")
        self.assertTrue(ok)
        self.assertIn("已导入 2 个 cookie", msg)
        self.assertTrue(self.state_file.exists())
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        values = {c["name"]: c["value"] for c in state["cookies"]}
        self.assertEqual(values, {"a": "1", "web_session": "abc123"})


class TestWebSessionValue(CrawlerTestBase):
    """覆盖 B：_web_session_value（匿名访客也下发 web_session，取当前值）。"""

    def test_returns_current_value(self):
        ctx = SimpleNamespace(cookies=lambda: [
            {"name": "a", "value": "1"}, anon_cookie("v1")])
        self.assertEqual(crawler._web_session_value(ctx), "v1")

    def test_empty_value_skipped(self):
        ctx = SimpleNamespace(cookies=lambda: [anon_cookie("")])
        self.assertIsNone(crawler._web_session_value(ctx))

    def test_absent_returns_none(self):
        ctx = SimpleNamespace(cookies=lambda: [{"name": "a", "value": "1"}])
        self.assertIsNone(crawler._web_session_value(ctx))


class TestPageUserSignal(CrawlerTestBase):
    """覆盖 B：_page_user_signal evaluate 透传 + 异常兜底 False。"""

    def test_truthy_evaluate_passed_through(self):
        page = mock.Mock()
        page.evaluate.return_value = {"loggedIn": True}
        self.assertTrue(crawler._page_user_signal(page))

    def test_falsy_evaluate(self):
        page = mock.Mock()
        page.evaluate.return_value = False
        self.assertFalse(crawler._page_user_signal(page))

    def test_evaluate_exception_returns_false(self):
        page = mock.Mock()
        page.evaluate.side_effect = RuntimeError("page closed")
        self.assertFalse(crawler._page_user_signal(page))


class TestNewContext(CrawlerTestBase):
    """覆盖 B：_new_context 默认不覆盖 UA（指纹一致对策）+ STEALTH_JS 注入。"""

    def test_default_no_ua_override_and_stealth_injected(self):
        """默认不传 user_agent；viewport/locale/timezone 固定；注入抹 webdriver 脚本"""
        browser = mock.MagicMock()
        ctx = crawler._new_context(browser)
        kwargs = browser.new_context.call_args.kwargs
        self.assertNotIn("user_agent", kwargs)
        self.assertEqual(kwargs["viewport"], {"width": 1280, "height": 860})
        self.assertEqual(kwargs["locale"], "zh-CN")
        self.assertEqual(kwargs["timezone_id"], "Asia/Shanghai")
        ctx.add_init_script.assert_called_once_with(crawler.STEALTH_JS)

    def test_explicit_ua_passed_through(self):
        browser = mock.MagicMock()
        crawler._new_context(browser, ua="Mozilla/5.0 (UT)")
        self.assertEqual(browser.new_context.call_args.kwargs["user_agent"],
                         "Mozilla/5.0 (UT)")

    def test_storage_state_passed_through(self):
        browser = mock.MagicMock()
        crawler._new_context(browser, storage_state="D:/tmp/state.json")
        self.assertEqual(browser.new_context.call_args.kwargs["storage_state"],
                         "D:/tmp/state.json")


class TestSaveState(CrawlerTestBase):
    """覆盖 B：_save_state 落盘到临时登录态路径（先建父目录）。"""

    def test_writes_to_patched_login_state(self):
        ctx = SimpleNamespace(storage_state=mock.Mock())
        crawler._save_state(ctx)
        self.assertTrue(self.state_file.parent.exists())
        ctx.storage_state.assert_called_once_with(path=str(self.state_file))


class TestLaunchBrowser(CrawlerTestBase):
    """覆盖 B：launch_browser 传入反自动化启动参数。"""

    def test_default_headless_false_with_anti_automation_args(self):
        p = mock.MagicMock()
        crawler.launch_browser(p)
        p.chromium.launch.assert_called_once_with(
            headless=False, args=crawler.LAUNCH_ARGS)

    def test_headless_flag_passed(self):
        p = mock.MagicMock()
        crawler.launch_browser(p, headless=True)
        self.assertTrue(p.chromium.launch.call_args.kwargs["headless"])


class TestDismissModal(CrawlerTestBase):
    """覆盖 B：dismiss_modal 关闭弹窗且异常全部吞掉。"""

    def test_presses_escape_and_clicks_close(self):
        page = mock.Mock()
        crawler.dismiss_modal(page)
        page.keyboard.press.assert_called_once_with("Escape")
        page.locator.return_value.first.click.assert_called_once()

    def test_all_errors_swallowed(self):
        page = mock.Mock()
        page.keyboard.press.side_effect = RuntimeError("no keyboard")
        page.locator.return_value.first.click.side_effect = \
            RuntimeError("no modal")
        crawler.dismiss_modal(page)  # 不应抛出
        page.locator.return_value.first.click.assert_called_once()


class TestEnsureLogin(CrawlerTestBase):
    """覆盖 B：ensure_login 双信号判定（TASK-0007 主战场，全 fake 无浏览器）。

    主信号 = 页面用户态（__INITIAL_STATE__）reload 后稳定；
    弱信号 = web_session 相对基线新增/变化且 reload 后稳定；
    双信号皆无 → 超时 SystemExit。
    """

    def _browser_returning(self, *contexts):
        browser = mock.MagicMock()
        browser.new_context.side_effect = list(contexts)
        return browser

    def test_saved_state_valid_reused_directly(self):
        """已保存登录态 + 页面用户态为真：直接复用上下文，不重新落盘"""
        self.make_saved_state()
        ctx = FakeContext(FakePage([True]))
        browser = self._browser_returning(ctx)
        logs = []
        result = crawler.ensure_login(browser, logs.append, timeout=5)
        self.assertIs(result, ctx)
        self.assertIn("使用已保存的登录态", "\n".join(logs))
        self.assertIn("storage_state", browser.new_context.call_args.kwargs)
        ctx.storage_state.assert_not_called()

    def test_saved_state_invalid_falls_back_to_fresh_login(self):
        """已保存登录态失效：关闭旧上下文，走全新登录并成功保存"""
        self.make_saved_state()
        ctx_saved = FakeContext(FakePage([False]))
        ctx_fresh = FakeContext(FakePage([True]), cookie_seq=[[]])
        browser = self._browser_returning(ctx_saved, ctx_fresh)
        logs = []
        result = crawler.ensure_login(browser, logs.append, timeout=5)
        self.assertIs(result, ctx_fresh)
        self.assertTrue(ctx_saved.closed)
        self.assertIn("已保存的登录态已失效", "\n".join(logs))
        self.assertIn("登录成功，状态已保存", "\n".join(logs))
        ctx_fresh.storage_state.assert_called_once_with(
            path=str(self.state_file))

    def test_main_signal_success_saves_state(self):
        """主信号：页面用户态为真 → reload 后仍为真 → 保存登录态"""
        ctx = FakeContext(FakePage([True]), cookie_seq=[[]])
        browser = self._browser_returning(ctx)
        logs = []
        result = crawler.ensure_login(browser, logs.append, timeout=5)
        self.assertIs(result, ctx)
        self.assertIn("请在打开的浏览器窗口中完成登录", "\n".join(logs))
        self.assertIn("登录成功，状态已保存", "\n".join(logs))
        ctx.storage_state.assert_called_once_with(path=str(self.state_file))

    def test_weak_signal_stable_web_session_saves_state(self):
        """弱信号：web_session 相对匿名基线变化且 reload 后稳定 → 保存"""
        ctx = FakeContext(FakePage([False]),
                          cookie_seq=[[anon_cookie("anon")],
                                      [anon_cookie("real")],
                                      [anon_cookie("real")]])
        browser = self._browser_returning(ctx)
        logs = []
        result = crawler.ensure_login(browser, logs.append, timeout=5)
        self.assertIs(result, ctx)
        self.assertIn("检测到匿名会话 cookie", "\n".join(logs))
        self.assertIn("登录成功（web_session 已更新）", "\n".join(logs))
        ctx.storage_state.assert_called_once()
        self.assertEqual(ctx.page.reload_count, 1)

    def test_weak_signal_unstable_eventually_times_out(self):
        """弱信号不稳定（reload 后回到基线值）：不保存，最终超时退出"""
        ctx = FakeContext(FakePage([False]),
                          cookie_seq=[[anon_cookie("anon")],
                                      [anon_cookie("real")],
                                      [anon_cookie("anon")]])
        browser = self._browser_returning(ctx)
        with mock.patch.object(crawler, "time",
                               FakeClock([1000, 1000, 1000, 1006])):
            with self.assertRaises(SystemExit) as exc_ctx:
                crawler.ensure_login(browser, lambda m: None, timeout=5)
        self.assertIn("等待登录超时", str(exc_ctx.exception))
        self.assertTrue(ctx.closed)
        ctx.storage_state.assert_not_called()

    def test_no_signal_times_out_and_closes_context(self):
        """双信号皆无：超时 SystemExit，上下文关闭并提示改用 Cookie 导入"""
        ctx = FakeContext(FakePage([False]))
        browser = self._browser_returning(ctx)
        logs = []
        with mock.patch.object(crawler, "time", FakeClock([1000, 1000, 1006])):
            with self.assertRaises(SystemExit) as exc_ctx:
                crawler.ensure_login(browser, logs.append, timeout=5)
        self.assertIn("等待登录超时", str(exc_ctx.exception))
        self.assertIn("请在打开的浏览器窗口中完成登录", "\n".join(logs))
        self.assertTrue(ctx.closed)
        ctx.storage_state.assert_not_called()


# ======================================================== C 熔断编排与落日志


class TestCollectNoteLinks(CrawlerTestBase):
    """覆盖 C：collect_note_links 链接收集（去重/截断/异常分支/风控判定）。"""

    def test_dedup_prefix_and_xsec_token_verbatim(self):
        """相对链接补 BASE、http 链接原样保留（含 xsec_token）、同 id 去重"""
        id_b = "a1b2c3d4000000001a01ab99"
        page = FakeProfilePage([[
            f"/explore/{UID}",
            f"/explore/{UID}",
            f"https://www.xiaohongshu.com/explore/{id_b}?xsec_token=TOKEN99",
        ]])
        logs = []
        result = crawler.collect_note_links(
            page, f"{BASE}/user/profile/{UID}", 10, logs.append)
        self.assertEqual(result, [
            f"{BASE}/explore/{UID}",
            f"https://www.xiaohongshu.com/explore/{id_b}?xsec_token=TOKEN99",
        ])
        self.assertIn("共收集到 2 条博文链接", "\n".join(logs))
        page.mouse.wheel.assert_called()  # 滚动加载发生过

    def test_max_notes_stops_collection(self):
        """达到 max_notes 上限即停止滚动收集（后续批次不再消费）"""
        page = FakeProfilePage([
            [f"/explore/{UID}", "/explore/b1b2c3d4000000001a01ab99"],
            ["/explore/c1b2c3d4000000001a01ab99",
             "/explore/d1b2c3d4000000001a01ab99",
             "/explore/e1b2c3d4000000001a01ab99"],
        ])
        logs = []
        result = crawler.collect_note_links(page, "url", 2, logs.append)
        self.assertEqual(len(result), 2)
        self.assertIn("达到抓取上限 max_notes=2", "\n".join(logs))
        self.assertEqual(page.locator_calls, 1)

    def test_login_redirect_raises_login_expired(self):
        """等不到卡片且页面跳到登录页 → LoginExpired"""
        page = FakeProfilePage(
            [], url=f"{BASE}/login?redirect=/user/profile/{UID}")
        page.wait_for_selector.side_effect = crawler.PWTimeout("timeout")
        with self.assertRaises(crawler.LoginExpired) as ctx:
            crawler.collect_note_links(page, "url", 10, lambda m: None)
        self.assertIn("登录", str(ctx.exception))

    def test_selector_timeout_without_login_raises_risk_control(self):
        """等不到卡片且非登录页 → RiskControlDetected（疑似风控/结构变化）"""
        page = FakeProfilePage([])
        page.wait_for_selector.side_effect = crawler.PWTimeout("timeout")
        with self.assertRaises(crawler.RiskControlDetected) as ctx:
            crawler.collect_note_links(page, "url", 10, lambda m: None)
        self.assertIn("风控", str(ctx.exception))

    def test_cards_without_valid_links_raises_risk_control(self):
        """卡片存在但解析不出任何 note id → RiskControlDetected"""
        page = FakeProfilePage([[f"/user/profile/{UID}"]])
        with self.assertRaises(crawler.RiskControlDetected) as ctx:
            crawler.collect_note_links(page, "url", 10, lambda m: None)
        self.assertIn("未解析出任何博文链接", str(ctx.exception))

    def test_multiple_batches_accumulate_then_stale_stop(self):
        """多批滚动累积链接，连续无新内容（stale 上限）后自然终止"""
        page = FakeProfilePage(
            [[f"/explore/{UID}"], ["/explore/b1b2c3d4000000001a01ab99"]])
        result = crawler.collect_note_links(page, "url", 10, lambda m: None)
        self.assertEqual(len(result), 2)

    def test_get_attribute_error_card_skipped(self):
        """单张卡片读取 href 异常：跳过该卡，其余照常收集"""
        cards = FakeCards([f"/explore/{UID}",
                           "/explore/b1b2c3d4000000001a01ab99"],
                          fail_indexes={0})
        page = FakeProfilePage([cards])
        result = crawler.collect_note_links(page, "url", 10, lambda m: None)
        self.assertEqual(result,
                         [f"{BASE}/explore/b1b2c3d4000000001a01ab99"])


class TestCrawlNoteDetail(CrawlerTestBase):
    """覆盖 C：crawl_note_detail 详情解析（字段/日期剥离/登录失效/空页形态）。"""

    def test_full_parse_with_referer_and_date_strip(self):
        """全字段解析：标题清洗、正文剥离日期文案、1.2万→12000、图片列表"""
        texts = {
            crawler.SEL["title"]: "  标题甲\n乙  ",
            crawler.SEL["date"]: "编辑于 2026-11-05",
            crawler.SEL["content"]: "编辑于 2026-11-05 正文内容",
            crawler.SEL["like"]: "1.2万",
            crawler.SEL["collect"]: "88",
            crawler.SEL["comment"]: "9",
        }
        images = ["https://sns-img.xhscdn.com/a.jpg",
                  "https://sns-img.xhscdn.com/b.jpg"]
        url = f"{BASE}/explore/{UID}?xsec_token=T1"
        page = make_detail_page(url, texts, images)
        note = crawler.crawl_note_detail(page, url, date(2026, 11, 20),
                                         referer="http://ref.example")
        self.assertEqual(note["title"], "标题甲 乙")
        self.assertEqual(note["date"], "2026-11-05")
        self.assertEqual(note["date_raw"], "编辑于 2026-11-05")
        self.assertEqual(note["content"], "正文内容")
        self.assertEqual(note["likes"], 12000)
        self.assertEqual(note["collects"], 88)
        self.assertEqual(note["comments"], 9)
        self.assertEqual(note["images"], images)
        self.assertEqual(note["note_id"], UID)
        self.assertEqual(note["url"], url)
        page.goto.assert_called_once_with(
            url, wait_until="domcontentloaded", referer="http://ref.example")

    def test_url_without_note_id_returns_none(self):
        """URL 中无 explore/search_result note id → None"""
        url = f"{BASE}/user/profile/{UID}"
        page = make_detail_page(url)
        self.assertIsNone(
            crawler.crawl_note_detail(page, url, date(2026, 11, 20)))

    def test_login_redirect_raises_login_expired(self):
        """详情页跳到登录页 → LoginExpired"""
        url = f"{BASE}/login?redirect=x"
        page = make_detail_page(url)
        with self.assertRaises(crawler.LoginExpired) as ctx:
            crawler.crawl_note_detail(page, url, date(2026, 11, 20))
        self.assertIn(url, str(ctx.exception))

    def test_all_empty_texts_returns_captcha_shape(self):
        """标题/正文/日期/图片全空 → 返回默认 dict（crawl 据此判风控验证页）"""
        url = f"{BASE}/explore/{UID}"
        page = make_detail_page(url)
        note = crawler.crawl_note_detail(page, url, date(2026, 11, 20))
        self.assertEqual(note["title"], "(无标题)")
        self.assertIsNone(note["date"])
        self.assertEqual(note["date_raw"], "")
        self.assertEqual(note["content"], "")
        self.assertEqual(note["likes"], 0)
        self.assertEqual(note["images"], [])


class TestSaveOutputs(CrawlerTestBase):
    """覆盖 C：save_outputs notes.json/csv/md 三件套落盘。"""

    def test_two_notes_roundtrip_with_csv_truncation(self):
        """三件套字段齐全；csv 内容摘要截断到 100 字；md 含图片行与互动行"""
        out_dir = self.tmp / "so"
        out_dir.mkdir()
        n1 = make_note("id1", d="2026-11-05", content="正" * 150,
                       images=["a", "b"], likes=3)
        n2 = make_note("id2", d="2026-11-01", title="标题乙")
        crawler.save_outputs([n1, n2], "uidX", date(2026, 11, 1),
                             date(2026, 11, 30), out_dir)

        meta = json.loads((out_dir / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["blogger"], "uidX")
        self.assertEqual(meta["range"], ["2026-11-01", "2026-11-30"])
        self.assertEqual(meta["count"], 2)
        self.assertEqual(len(meta["notes"]), 2)

        with open(out_dir / "notes.csv", newline="",
                  encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0], ["序号", "日期", "标题", "内容摘要",
                                   "点赞", "收藏", "评论", "链接"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][1], "2026-11-05")
        self.assertEqual(rows[1][3], "正" * 100)  # 摘要截断

        md = (out_dir / "notes.md").read_text(encoding="utf-8")
        self.assertIn("# 小红书博文归档 - uidX", md)
        self.assertIn("共 2 篇", md)
        self.assertIn("## 1. 标题甲（2026-11-05）", md)
        self.assertIn("图片 x2（链接见 notes.json）", md)
        self.assertIn("赞 3 · 藏 1 · 评 2", md)
        self.assertIn(f"[原文]({n1['url']})", md)

    def test_empty_notes_still_writes_files(self):
        """空结果也写出三件套：count=0、csv 仅表头"""
        out_dir = self.tmp / "so_empty"
        out_dir.mkdir()
        crawler.save_outputs([], "uidX", date(2026, 11, 1),
                             date(2026, 11, 30), out_dir)
        meta = json.loads((out_dir / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["count"], 0)
        with open(out_dir / "notes.csv", newline="",
                  encoding="utf-8-sig") as f:
            self.assertEqual(len(list(csv.reader(f))), 1)
        self.assertIn("共 0 篇",
                      (out_dir / "notes.md").read_text(encoding="utf-8"))

    def test_none_date_rendered_as_unknown(self):
        """日期 None → csv '未知'、md '日期未知'；空正文 → '(无正文)'"""
        out_dir = self.tmp / "so_none"
        out_dir.mkdir()
        note = make_note("idX", d=None, content="")
        crawler.save_outputs([note], "uidX", date(2026, 11, 1),
                             date(2026, 11, 30), out_dir)
        with open(out_dir / "notes.csv", newline="",
                  encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[1][1], "未知")
        md = (out_dir / "notes.md").read_text(encoding="utf-8")
        self.assertIn("（日期未知）", md)
        self.assertIn("(无正文)", md)


class TestDownloadNoteImages(CrawlerTestBase):
    """覆盖 C：download_note_images 续传/成败计数（response 按 resp.ok / resp.body() 构造）。"""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(crawler.time, "sleep")  # 红线：无真实等待
        patcher.start()
        self.addCleanup(patcher.stop)

    def _context(self, get_mock):
        return SimpleNamespace(request=SimpleNamespace(get=get_mock))

    def _ok_resp(self):
        resp = mock.Mock()
        resp.ok = True
        resp.body.return_value = b"jpg-bytes"
        return resp

    def test_success_downloads_all_and_counts(self):
        out_dir = self.tmp / "dl"
        out_dir.mkdir()
        note = make_note("id1", images=["u1", "u2"])
        get = mock.Mock(return_value=self._ok_resp())
        logs = []
        crawler.download_note_images(self._context(get), [note], out_dir,
                                     logs.append)
        self.assertEqual(logs[-1],
                         "图片下载完成：成功 2，失败 0（待下载 2 张）")
        img_dir = out_dir / "images" / "id1"
        self.assertEqual((img_dir / "01.jpg").read_bytes(), b"jpg-bytes")
        self.assertEqual((img_dir / "02.jpg").read_bytes(), b"jpg-bytes")
        self.assertEqual(get.call_args_list[0].kwargs["headers"]["Referer"],
                         f"{BASE}/")

    def test_existing_file_skipped_resume(self):
        """已存在的 01.jpg 跳过（续传），只下载缺失的 02.jpg"""
        out_dir = self.tmp / "dl_resume"
        img_dir = out_dir / "images" / "id1"
        img_dir.mkdir(parents=True)
        (img_dir / "01.jpg").write_bytes(b"old")
        note = make_note("id1", images=["u1", "u2"])
        get = mock.Mock(return_value=self._ok_resp())
        logs = []
        crawler.download_note_images(self._context(get), [note], out_dir,
                                     logs.append)
        self.assertEqual((img_dir / "01.jpg").read_bytes(), b"old")
        self.assertEqual((img_dir / "02.jpg").read_bytes(), b"jpg-bytes")
        self.assertEqual(logs[-1],
                         "图片下载完成：成功 1，失败 0（待下载 1 张）")

    def test_not_ok_response_counted_as_fail(self):
        """resp.ok=False → 计失败，不写文件"""
        out_dir = self.tmp / "dl_fail"
        out_dir.mkdir()
        note = make_note("id1", images=["u1", "u2"])
        bad = mock.Mock()
        bad.ok = False
        get = mock.Mock(return_value=bad)
        logs = []
        crawler.download_note_images(self._context(get), [note], out_dir,
                                     logs.append)
        self.assertEqual(logs[-1],
                         "图片下载完成：成功 0，失败 2（待下载 2 张）")
        self.assertFalse((out_dir / "images" / "id1" / "01.jpg").exists())

    def test_request_exception_counted_as_fail(self):
        """get 抛异常 → 计失败，不中断整体下载"""
        out_dir = self.tmp / "dl_exc"
        out_dir.mkdir()
        note = make_note("id1", images=["u1", "u2"])
        get = mock.Mock(side_effect=RuntimeError("network down"))
        logs = []
        crawler.download_note_images(self._context(get), [note], out_dir,
                                     logs.append)
        self.assertEqual(logs[-1],
                         "图片下载完成：成功 0，失败 2（待下载 2 张）")


class TestCrawl(CrawlerTestBase):
    """覆盖 C：crawl 主入口编排——熔断、部分保留、落日志、排序、下载分支。

    浏览器层全 fake（红线）：sync_playwright / ensure_login / collect /
    crawl_note_detail / download_note_images 均按脚本替换，time.sleep 置零。
    """

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(crawler.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_crawl(self, links=(), details=(), collect_error=None,
                  **crawl_kwargs):
        """编排层统一夹具：返回 (结果, logs, browser, ctx)。

        details 列表元素为 note dict 或 Exception 实例，按调用次序弹出。
        """
        browser = mock.MagicMock()
        p_obj = mock.MagicMock()
        p_obj.chromium.launch.return_value = browser
        pw = mock.MagicMock()
        pw.return_value.__enter__.return_value = p_obj
        seq = list(details)

        def fake_detail(_page, _url, _today, referer=None):
            if not seq:
                return None
            item = seq.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        ctx = mock.MagicMock()
        collect = mock.Mock(return_value=list(links))
        if collect_error is not None:
            collect.side_effect = collect_error
        ensure = mock.Mock(return_value=ctx)
        for name, value in (("sync_playwright", pw),
                            ("ensure_login", ensure),
                            ("collect_note_links", collect),
                            ("crawl_note_detail",
                             mock.Mock(side_effect=fake_detail))):
            patcher = mock.patch.object(crawler, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self._last_p = p_obj
        self._last_ensure = ensure

        logs = []
        result = crawler.crawl(user=crawl_kwargs.pop("user", UID),
                               progress=logs.append, **crawl_kwargs)
        return result, logs, browser, ctx

    def out_dir_of(self, start="2000-01-01", end=None):
        end = end or date.today().isoformat()
        return crawler.DATA_OUT / "xhs_crawler" / f"{UID}_{start}_{end}"

    def read_run_log(self, out_dir):
        return (Path(out_dir) / "run.log").read_text(encoding="utf-8")

    def test_happy_path_sorted_and_saved(self):
        """正常完成：范围内笔记按日期倒序、三件套落盘、浏览器关闭、参数透传"""
        links = [f"{BASE}/explore/{UID}"] * 3
        details = [make_note(UID, d="2026-11-03"),
                   make_note("b1b2c3d4000000001a01ab99", d="2026-11-05"),
                   make_note("c1b2c3d4000000001a01ab99", d="2026-11-04")]
        result, logs, browser, _ctx = self.run_crawl(links=links,
                                                     details=details)
        notes, out_dir, uid, stop_reason = result
        self.assertIsNone(stop_reason)
        self.assertEqual(uid, UID)
        self.assertEqual([n["date"] for n in notes],
                         ["2026-11-05", "2026-11-04", "2026-11-03"])
        self.assertEqual(out_dir, self.out_dir_of())
        meta = json.loads((out_dir / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["count"], 3)
        self.assertIn("完成：时间范围内共 3 篇", self.read_run_log(out_dir))
        browser.close.assert_called_once()
        # 启动参数与登录参数透传
        self.assertEqual(
            self._last_p.chromium.launch.call_args.kwargs["args"],
            crawler.LAUNCH_ARGS)
        self.assertEqual(self._last_ensure.call_args.kwargs["timeout"],
                         crawler.LOGIN_TIMEOUT_DEFAULT)
        self.assertIsNone(self._last_ensure.call_args.kwargs["ua"])

    def test_risk_empty_streak_stops_with_partial_notes(self):
        """空结果连续达到 RISK_EMPTY_STREAK → 停止且含风控文案，部分结果保留落盘"""
        details = [make_note(UID, d="2026-11-05"),
                   make_empty_note("b1b2c3d4000000001a01ab99"),
                   make_empty_note("c1b2c3d4000000001a01ab99")]
        links = [f"{BASE}/explore/{i}" for i in range(5)]
        with mock.patch.object(crawler, "RISK_EMPTY_STREAK", 2):
            result, _logs, _b, _c = self.run_crawl(links=links,
                                                   details=details)
        notes, out_dir, _uid, stop_reason = result
        self.assertIn("疑似被风控", stop_reason)
        self.assertIn("停止后续任务", stop_reason)
        self.assertEqual(len(notes), 1)  # 命中风控前的有效笔记保留
        meta = json.loads((out_dir / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["count"], 1)
        self.assertIn("任务提前停止", self.read_run_log(out_dir))

    def test_fail_streak_stops(self):
        """异常连续达到 FAIL_STREAK → 停止且含风控文案（notes.json 仍写出空结果）"""
        details = [ValueError("网络错"), ValueError("网络错")]
        links = [f"{BASE}/explore/{i}" for i in range(3)]
        with mock.patch.object(crawler, "FAIL_STREAK", 2):
            result, _logs, _b, _c = self.run_crawl(links=links,
                                                   details=details)
        notes, out_dir, _uid, stop_reason = result
        self.assertIn("连续 2 篇抓取异常", stop_reason)
        self.assertIn("风控", stop_reason)
        self.assertEqual(notes, [])
        self.assertTrue((out_dir / "notes.json").exists())

    def test_older_than_start_streak_stops_early_without_reason(self):
        """连续早于起始日期达到 EARLY_STOP_STREAK → 提前结束，stop_reason 为空"""
        details = [make_note(UID, d="2026-11-05"),
                   make_note("b1b2c3d4000000001a01ab99", d="2026-10-20"),
                   make_note("c1b2c3d4000000001a01ab99", d="2026-10-01")]
        links = [f"{BASE}/explore/{i}" for i in range(4)]
        with mock.patch.object(crawler, "EARLY_STOP_STREAK", 2):
            result, _logs, _b, _c = self.run_crawl(
                links=links, details=details,
                start="2026-11-01", end="2026-11-30")
        notes, out_dir, _uid, stop_reason = result
        self.assertIsNone(stop_reason)
        self.assertEqual(len(notes), 1)
        self.assertIn("连续多篇早于起始日期，提前结束抓取",
                      self.read_run_log(out_dir))

    def test_login_expired_stops_and_keeps_partial(self):
        """LoginExpired 即停：stop_reason 提示重新登录，部分结果保留落盘"""
        details = [make_note(UID, d="2026-11-05"),
                   crawler.LoginExpired("登录态失效")]
        links = [f"{BASE}/explore/{i}" for i in range(3)]
        result, _logs, _b, _c = self.run_crawl(links=links, details=details)
        notes, out_dir, _uid, stop_reason = result
        self.assertIn("登录态已失效", stop_reason)
        meta = json.loads((out_dir / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["count"], 1)

    def test_collect_error_logged_then_reraised(self):
        """collect_note_links 抛风控异常：run.log 记录任务终止后原样抛出"""
        with self.assertRaises(crawler.RiskControlDetected):
            self.run_crawl(links=[f"{BASE}/explore/{UID}"], details=[],
                           collect_error=crawler.RiskControlDetected("主页被风控"))
        out_dir = self.out_dir_of()
        self.assertIn("任务终止（RiskControlDetected）",
                      self.read_run_log(out_dir))
        self.assertFalse((out_dir / "notes.json").exists())

    def test_time_range_filter_none_date_kept_and_sorted(self):
        """时间过滤：范围外剔除、无法解析日期保留并排最后、倒序正确"""
        details = [
            make_note("b1b2c3d4000000001a01ab99", d="2026-11-02"),
            make_note("c1b2c3d4000000001a01ab99", d="2026-11-10"),
            make_note("d1b2c3d4000000001a01ab99", d=None),          # 保留
            make_note("e1b2c3d4000000001a01ab99", d="2026-12-05"),  # 范围外
            make_note("f1b2c3d4000000001a01ab99", d="2026-10-01"),  # 早于起始 1 篇
        ]
        links = [f"{BASE}/explore/{i}" for i in range(5)]
        result, _logs, _b, _c = self.run_crawl(
            links=links, details=details,
            start="2026-11-01", end="2026-11-30")
        notes, out_dir, _uid, stop_reason = result
        self.assertIsNone(stop_reason)
        self.assertEqual([n["date"] for n in notes],
                         ["2026-11-10", "2026-11-02", None])
        self.assertIn("日期未能解析", self.read_run_log(out_dir))

    def test_download_images_flag_invokes_downloader(self):
        """download_images=True 且有笔记 → 调用 download_note_images（假 context）"""
        details = [make_note(UID, d="2026-11-05", images=["u1"])]
        links = [f"{BASE}/explore/{UID}"]
        with mock.patch.object(crawler, "download_note_images") as dl:
            result, _logs, _b, ctx = self.run_crawl(
                links=links, details=details, download_images=True)
        notes, out_dir, _uid, stop_reason = result
        self.assertIsNone(stop_reason)
        dl.assert_called_once()
        self.assertIs(dl.call_args.args[0], ctx)
        self.assertEqual(dl.call_args.args[1], notes)
        self.assertEqual(dl.call_args.args[2], out_dir)


# ================================================================ D main.py


class TestMain(CrawlerTestBase):
    """覆盖 D：main.py 参数默认值与 cookie 导入优先分支（crawl 全程 mock）。"""

    def parse(self, argv):
        with mock.patch.object(sys, "argv", argv):
            return xhs_main.parse_args()

    def run_main(self, argv, import_result=None, crawl_result=None):
        """跑 main()：patch cookie 导入与 crawl，返回 (stdout, 两个 Mock)。"""
        crawl_result = crawl_result or ([], Path("D:/out/x"), "uidX", None)
        with mock.patch.object(sys, "argv", argv), \
                mock.patch("sys.stdout", new=io.StringIO()) as fake_out, \
                mock.patch.object(xhs_main, "import_cookie_login",
                                  return_value=import_result) as m_imp, \
                mock.patch.object(xhs_main, "crawl",
                                  return_value=crawl_result) as m_crawl:
            xhs_main.main()
        return fake_out.getvalue(), m_imp, m_crawl

    def test_parse_args_defaults(self):
        """默认值：max_notes=500、delay 3/6、login_timeout=600、各开关关闭"""
        args = self.parse(["main.py", UID])
        self.assertEqual(args.user, UID)
        self.assertEqual(args.max_notes, 500)
        self.assertEqual(args.min_delay, 3.0)
        self.assertEqual(args.max_delay, 6.0)
        self.assertEqual(args.login_timeout, crawler.LOGIN_TIMEOUT_DEFAULT)
        self.assertIsNone(args.start)
        self.assertIsNone(args.end)
        self.assertFalse(args.download_images)
        self.assertFalse(args.headless)
        self.assertIsNone(args.ua)
        self.assertIsNone(args.cookie)
        self.assertIsNone(args.cookie_file)

    def test_parse_args_explicit_values(self):
        """显式参数全部正确解析（含链接形式博主标识）"""
        args = self.parse([
            "main.py", f"{BASE}/user/profile/{UID}?xsec_token=T",
            "--start", "2026-01-01", "--end", "2026-02-01",
            "--max-notes", "10", "--min-delay", "1.5", "--max-delay", "2.5",
            "--download-images", "--headless", "--ua", "Mozilla/5.0 UT",
            "--cookie", "web_session=x",
        ])
        self.assertEqual(args.max_notes, 10)
        self.assertEqual(args.min_delay, 1.5)
        self.assertEqual(args.max_delay, 2.5)
        self.assertTrue(args.download_images)
        self.assertTrue(args.headless)
        self.assertEqual(args.ua, "Mozilla/5.0 UT")
        self.assertEqual(args.cookie, "web_session=x")
        self.assertEqual(args.start, "2026-01-01")
        self.assertEqual(args.end, "2026-02-01")

    def test_cookie_import_failure_skips_crawl(self):
        """cookie 导入失败：打印原因后直接 return，不进入抓取"""
        out, _m_imp, m_crawl = self.run_main(
            ["main.py", UID, "--cookie", "foo=1"],
            import_result=(False, "cookie 中缺少 web_session"))
        m_crawl.assert_not_called()
        self.assertIn("cookie 中缺少 web_session", out)

    def test_cookie_import_success_proceeds_to_crawl(self):
        """cookie 导入成功：继续调用 crawl 并透传默认参数"""
        out, _m_imp, m_crawl = self.run_main(
            ["main.py", UID, "--cookie", "web_session=x"],
            import_result=(True, "已导入 1 个 cookie"))
        m_crawl.assert_called_once()
        kwargs = m_crawl.call_args.kwargs
        self.assertEqual(kwargs["user"], UID)
        self.assertEqual(kwargs["max_notes"], 500)
        self.assertEqual(kwargs["login_timeout"], crawler.LOGIN_TIMEOUT_DEFAULT)
        self.assertIs(kwargs["progress"], print)
        self.assertIn("完成：时间范围内共 0 篇", out)

    def test_cookie_file_content_forwarded(self):
        """--cookie-file：文件内容原样转发给 import_cookie_login"""
        cf = self.tmp / "cookies.txt"
        cf.write_text("a=1; web_session=abc\n", encoding="utf-8")
        out, m_imp, m_crawl = self.run_main(
            ["main.py", UID, "--cookie-file", str(cf)],
            import_result=(True, "ok"))
        m_imp.assert_called_once_with("a=1; web_session=abc\n")
        m_crawl.assert_called_once()

    def test_stop_reason_reported(self):
        """stop_reason 非空 → 输出 '!! 提前停止' 与原因"""
        out, _m_imp, _m_crawl = self.run_main(
            ["main.py", UID],
            crawl_result=([], Path("D:/out"), "uidX", "疑似被风控，停止后续任务"))
        self.assertIn("!! 提前停止", out)
        self.assertIn("疑似被风控", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
