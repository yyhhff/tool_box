# -*- coding: utf-8 -*-
"""h1_2026 分析台自检启动脚本。

自检项：HTML 结构闭合、JS 语法(node --check)、内嵌 SNAPSHOT 六表完整性、
P2-2 图表函数、CRLF 行尾、CSV(BOM/行数) 与 JSON 快照一致性。
全部通过后自动用默认浏览器打开页面；任一失败则退出码 1，不打开。

用法:
    python selfcheck.py              # 自检 + 通过后打开页面
    python selfcheck.py --check-only # 仅自检, 不打开(适合 CI/定时巡检)
"""
import json
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
HTML = BASE / "h1_2026.html"
OUT = BASE.parent.parent / "data" / "output" / "h1_2026"
CSV = OUT / "h1_2026_market.csv"
JSONF = OUT / "SNAPSHOT_DATA.json"

fails = []

def check(name, cond, detail=""):
    ok = bool(cond)
    if not ok:
        fails.append(name)
    print(("PASS  " if ok else "FAIL  ") + name + (("  :: " + str(detail)) if (detail and not ok) else ""))

# 1. 文件存在
check("HTML 文件存在", HTML.exists(), HTML)

text = HTML.read_text(encoding="utf-8") if HTML.exists() else ""

# 2. 结构闭合（各恰好 1 个 + 尾部 init();）
for tag in ("<script>", "</script>", "</body>", "</html>"):
    check("结构 %s 恰好 1 个" % tag, text.count(tag) == 1, "count=%d" % text.count(tag))
check("尾部 init(); 收口", re.search(r"init\(\);\s*</script>", text) is not None)

# 3. JS 语法（提取 <script> 段交给 node --check）
script = re.search(r"<script>\r?\n(.*)\r?\n</script>", text, re.S)
if script:
    tmp = BASE / ".selfcheck_tmp.js"
    tmp.write_text(script.group(1), encoding="utf-8", newline="")
    r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
    check("JS 语法 node --check", r.returncode == 0, (r.stderr or "").strip()[:200])
    tmp.unlink(missing_ok=True)
else:
    check("提取 <script> 段", False)

# 4. 内嵌 SNAPSHOT 六表
try:
    i = text.index("var SNAPSHOT = ")
    line = text[i:text.index("\n", i)]
    snap = json.loads(line[len("var SNAPSHOT = "):].rstrip().rstrip(";"))
    keys = ["market", "chain", "growth", "compare", "watch", "macro"]
    check("SNAPSHOT 六键齐全", all(k in snap for k in keys),
          "missing=" + str([k for k in keys if k not in snap]))
    check("SNAPSHOT 六表均非空", all(isinstance(snap.get(k), list) and snap[k] for k in keys),
          str({k: len(snap.get(k, [])) for k in keys}))
    codes = [str(r.get("code")) for r in snap.get("market", [])]
    check("market code 无重复", len(codes) == len(set(codes)),
          "total=%d uniq=%d" % (len(codes), len(set(codes))))
except (ValueError, json.JSONDecodeError) as e:
    snap = {}
    check("解析内嵌 SNAPSHOT", False, e)

# 5. P2-2 图表函数
for fn in ("svgDivergingBars", "renderLinkProfitChart", "renderIndexYTDChart",
           "techMiniSvg", "mountChart", "injectMicroCharts"):
    check("图表函数 %s 存在" % fn, ("function %s(" % fn) in text)

# 6. CRLF 行尾（契约硬约束）
raw = HTML.read_bytes() if HTML.exists() else b""
lone = raw.count(b"\n") - raw.count(b"\r\n")
check("CRLF 无孤立 LF", lone == 0, "lone_LF=%d" % lone)

# 7. CSV：存在 + BOM + 行数与 SNAPSHOT market 一致
check("market CSV 存在", CSV.exists(), CSV)
if CSV.exists() and snap.get("market"):
    cb = CSV.read_bytes()
    check("CSV 带 UTF-8 BOM", cb[:3] == b"\xef\xbb\xbf")
    n_csv = len([l for l in cb.decode("utf-8-sig").splitlines() if l.strip()]) - 1
    check("CSV 数据行数 = SNAPSHOT market (%d)" % len(snap["market"]),
          n_csv == len(snap["market"]), "csv=%d snap=%d" % (n_csv, len(snap["market"])))

# 8. JSON 快照文件：存在 + market 行数与内嵌一致
check("SNAPSHOT_DATA.json 存在", JSONF.exists(), JSONF)
if JSONF.exists() and snap.get("market"):
    try:
        jd = json.loads(JSONF.read_text(encoding="utf-8"))
        check("JSON market 行数 = 内嵌 SNAPSHOT",
              len(jd.get("market", [])) == len(snap["market"]),
              "json=%d html=%d" % (len(jd.get("market", [])), len(snap["market"])))
    except json.JSONDecodeError as e:
        check("解析 SNAPSHOT_DATA.json", False, e)

print("\n===== 完成：%d 项失败 =====" % len(fails))

if fails:
    print("自检未通过，不启动页面。失败项：")
    for f in fails:
        print("  - " + f)
    sys.exit(1)

if "--check-only" in sys.argv:
    print("--check-only：跳过启动。")
else:
    print("自检通过，正在打开页面：%s" % HTML)
    webbrowser.open(HTML.as_uri())
