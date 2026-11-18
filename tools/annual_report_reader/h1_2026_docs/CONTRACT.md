# 2026 A股半年报分析台 — 数据契约与验收标准（CONTRACT）

> 版本：v1.7 ｜ 制定人：pm-architect ｜ 数据时点标注：2026-11-18
> 适用范围：本文件是 finance-data / macro-data 采集、data-engineer 生成 CSV、frontend-dev 生成单文件 HTML、qa-tester 验收的**唯一字段契约**。任何字段增删改必须先改本文件并通知 team-lead。
> 周期口径：全部数据为 **2026H1 半年度报告累计口径（2026-01-01 ~ 2026-06-30，非单季、非年化）**。

---

## 0. 全局约定

| 约定项 | 规则 |
|---|---|
| 六表六板块 | 一张 CSV 对应一个板块，一一映射（见 §2）。 |
| CSV 表头 | 用「中文表头」列作为 CSV 第一行列名（UTF-8 with BOM 保存，便于 Excel 直接打开）。 |
| 对象键 | 内嵌快照 / SDK 返回的 JS 记录对象统一用「对象键」列（camelCase 英文）。CSV ↔ 对象通过 §1 各表的中英键映射转换。 |
| 空值 | CSV 中可空字段留空字符串；JS 中用 `null`。禁止用 `0` / `-` / `N/A` 代替缺失（金额 0 与缺失语义不同）。 |
| 数字 | 金额类一律「元」为单位的纯数字（不带千分位、不带单位后缀）；比例为「%」数值（如 `12.35` 表示 12.35%，不是 0.1235）。 |
| 代码 | 股票代码统一 6 位字符串（不足左补 0），保留前导零，禁止转 number。 |
| 日期 | `YYYY-MM-DD` 字符串。 |
| 涨红跌绿 | A股习惯：正增长/上涨=红色，负增长/下跌=绿色，0=中性灰。前端所有同比、涨跌幅字段按此着色。 |
| 免责声明 | **文案以 team-lead 最终下发给 frontend-dev 的版本为准**（v1.3 裁决）；必须包含核心要素：数据来自公开资料、不构成投资建议、数据以公司公告原文为准。契约原建议文案不再作为强制项。 |

### 0.1 交付形态硬约束（frontend-dev 必须遵守）

- **单文件**：最终交付为**一个 .html 文件**，HTML / CSS / JS / 数据快照全部内联，不得引用任何外部文件。
- **禁止外部 CDN**：不得通过 `<script src>` / `<link href>` / `@import` / `fetch(CDN)` 等加载任何外部资源，**包括 ECharts 等任何图表库**。
- **图表方案**：如需条形/柱状等可视化，一律用**内联 SVG 或 CSS 条形图**实现（可复用现有 `.bar` 模式：轨道 `#e9ecf1`、填充 `var(--brand)`、高 8px、圆角 4px），不得引入图表库。
- **视觉风格沿用** `tools/annual_report_reader/templates/index.html`，强制使用其 CSS 变量与基础样式：
  - 变量：`--bg:#f5f6f8`（浅灰底）、`--card:#fff`（白卡）、`--line:#e3e6ea`（描边）、`--txt:#22262b`（主文）、`--sub:#7a828c`（次文）、`--brand:#2f6fed`（蓝主色）。
  - 字体：`"Segoe UI","Microsoft YaHei",system-ui,sans-serif`。
  - 白卡 `.card`：白底、1px `#e3e6ea` 描边、`border-radius:10px`、`padding:16px`、卡片间距 `16px`。
  - 简洁表格：全宽 `width:100%`、`border-collapse:collapse`、字号 `13px`；`th` 用 `--sub` 加粗、背景 `#fafbfc`；`tbody tr:hover` 背景 `#f0f4ff`。
  - 按钮：主色 `var(--brand)` 白字、`border:0`、`border-radius:6px`、`padding:9px 18px`；次要按钮 ghost 样式（白底描边）。
- 该风格约束与涨红跌绿不冲突：涨红跌绿仅作用于同比/涨跌数值的文案颜色，不改动整体蓝主色体系。

---

## 1. 六张 CSV 数据表定义

六张表文件名统一前缀 `h1_2026_`，存于 WorkBuddy 资料库。示例行中的值**均为占位符「待填」，不代表真实财务数字**。

### 表1 全市场正式半年报总榜

- 中文表名：**全市场2026半年报总榜**
- 文件名：`h1_2026_market.csv`
- 对应板块：①全市场正式半年报总榜

| 中文表头 | 对象键 | 类型 | 单位 | 口径/说明 | 可空 |
|---|---|---|---|---|---|
| 股票代码 | code | string | — | 6 位代码，保留前导零 | 否 |
| 股票简称 | name | string | — | 截至 2026-11-18 简称 | 否 |
| 申万一级行业 | swIndustry | string | — | 申万一级（2021版）行业名 | 是 |
| 所属产业链 | chain | string | — | 产业链标签，可多标签逗号分隔 | 是 |
| 所属环节 | link | string | — | 在本产业链中的环节 | 是 |
| 营业总收入 | revenue | number | 元 | 营收=营业总收入，2026H1 累计 | 是 |
| 营收同比 | revenueYoy | number | % | 较 2025H1 同比，正红负绿 | 是 |
| 归母净利润 | netProfit | number | 元 | 净利=归属于上市公司股东的净利润 | 是 |
| 归母净利同比 | netProfitYoy | number | % | 较 2025H1 同比，正红负绿 | 是 |
| 扣非净利润 | deductNetProfit | number | 元 | 扣非归母净利润 | 是 |
| 经营现金流净额 | ocf | number | 元 | 经营活动产生的现金流量净额 | 是 |
| 加权平均ROE | roe | number | % | 加权平均净资产收益率，半年度口径未年化，必须注明 | 是 |
| 毛利率 | grossMargin | number | % | （营业收入−营业成本）/营业收入 | 是 |
| 资产负债率 | debtToAssetRatio | number | % | 负债合计/资产总计×100；来自 NeoData 直连 financial_indicators.debt_to_assets_ratio（2026H1）；金融类同样有值（高负债为行业特征，如银行约 90%），仅在来源缺失时留空 | 是 |
| 披露日期 | discloseDate | date | — | 正式半年报披露日 | 是 |
| 数据来源 | source | string | — | Wind/iFinD/东方财富/WeStock，可多来源逗号分隔 | 否 |
| 数据时点 | asOf | date | — | 统一 2026-11-18 | 否 |

示例行（占位符）：
```
股票代码,股票简称,申万一级行业,所属产业链,所属环节,营业总收入,营收同比,归母净利润,归母净利同比,扣非净利润,经营现金流净额,加权平均ROE,毛利率,资产负债率,披露日期,数据来源,数据时点
待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,2026-11-18
```

### 表2 产业链环节赚钱榜

- 中文表名：**产业链环节赚钱榜**
- 文件名：`h1_2026_chain_link.csv`
- 对应板块：②产业链环节赚钱榜（选产业链自动联动环节）
- 粒度：一行 = 一个「产业链 × 环节」聚合，非单公司

| 中文表头 | 对象键 | 类型 | 单位 | 口径/说明 | 可空 |
|---|---|---|---|---|---|
| 产业链 | chain | string | — | 产业链名称 | 否 |
| 环节 | link | string | — | 环节名称 | 否 |
| 环节公司数 | companyCount | integer | 家 | 参与聚合的公司数量 | 是 |
| 环节营收合计 | revenueSum | number | 元 | 环节内公司营业总收入合计 | 是 |
| 环节营收同比 | revenueYoy | number | % | 环节合计较上年同期同比 | 是 |
| 环节归母净利合计 | netProfitSum | number | 元 | 环节内公司归母净利润合计 | 是 |
| 环节净利同比 | netProfitYoy | number | % | 环节合计较上年同期同比 | 是 |
| 环节平均ROE | roeAvg | number | % | 环节内公司 ROE 算术平均，半年度未年化需注明 | 是 |
| 环节平均毛利率 | grossMarginAvg | number | % | 环节内公司毛利率算术平均 | 是 |
| 赚钱能力排名 | profitRank | integer | — | 同一产业链内按 netProfitSum 降序排名，从 1 起 | 是 |
| 代表公司 | leadCompanies | string | — | 环节内代表公司简介，逗号分隔，仅展示用 | 是 |
| 数据来源 | source | string | — | 来源标注 | 否 |
| 数据时点 | asOf | date | — | 统一 2026-11-18 | 否 |

示例行（占位符）：
```
产业链,环节,环节公司数,环节营收合计,环节营收同比,环节归母净利合计,环节净利同比,环节平均ROE,环节平均毛利率,赚钱能力排名,代表公司,数据来源,数据时点
待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,2026-11-18
```

### 表3 双增公司榜

- 中文表名：**营收净利双增公司榜**
- 文件名：`h1_2026_double_growth.csv`
- 对应板块：③双增公司榜（营收与归母净利同比双升）
- 入榜硬条件：`revenueYoy > 0` **且** `netProfitYoy > 0`（两者必须同时为正，缺一不可；为空不入选）

| 中文表头 | 对象键 | 类型 | 单位 | 口径/说明 | 可空 |
|---|---|---|---|---|---|
| 股票代码 | code | string | — | 6 位代码 | 否 |
| 股票简称 | name | string | — | — | 否 |
| 所属产业链 | chain | string | — | — | 是 |
| 所属环节 | link | string | — | — | 是 |
| 申万一级行业 | swIndustry | string | — | — | 是 |
| 营业总收入 | revenue | number | 元 | 2026H1 累计 | 是 |
| 营收同比 | revenueYoy | number | % | **入榜条件：>0** | 否 |
| 归母净利润 | netProfit | number | 元 | — | 是 |
| 归母净利同比 | netProfitYoy | number | % | **入榜条件：>0** | 否 |
| 加权平均ROE | roe | number | % | 半年度未年化需注明 | 是 |
| 双增强度 | growthScore | number | — | 综合排序分 = revenueYoy + netProfitYoy（两项均为正） | 否 |
| 披露日期 | discloseDate | date | — | — | 是 |
| 数据来源 | source | string | — | — | 否 |
| 数据时点 | asOf | date | — | 统一 2026-11-18 | 否 |

示例行（占位符）：
```
股票代码,股票简称,所属产业链,所属环节,申万一级行业,营业总收入,营收同比,归母净利润,归母净利同比,加权平均ROE,双增强度,披露日期,数据来源,数据时点
待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,2026-11-18
```

### 表4 产业链内公司对比

- 中文表名：**产业链内公司对比**
- 文件名：`h1_2026_chain_company.csv`
- 对应板块：④产业链内公司对比
- 粒度：一行 = 一家公司，必须带 chain + link 才能参与联动对比

| 中文表头 | 对象键 | 类型 | 单位 | 口径/说明 | 可空 |
|---|---|---|---|---|---|
| 股票代码 | code | string | — | 6 位代码 | 否 |
| 股票简称 | name | string | — | — | 否 |
| 所属产业链 | chain | string | — | 联动字段；有产业链归属的个股必填。无归属的额外龙头（如仅有完整行情但未纳入本次产业链梳理的公司）留空，见下方说明 | 是 |
| 所属环节 | link | string | — | 联动字段；有产业链归属的个股必填，无归属龙头随 chain 留空 | 是 |
| 营业总收入 | revenue | number | 元 | — | 是 |
| 营收同比 | revenueYoy | number | % | 正红负绿 | 是 |
| 归母净利润 | netProfit | number | 元 | — | 是 |
| 归母净利同比 | netProfitYoy | number | % | 正红负绿 | 是 |
| 加权平均ROE | roe | number | % | 半年度未年化需注明 | 是 |
| 毛利率 | grossMargin | number | % | — | 是 |
| 环节内营收排名 | linkRevenueRank | integer | — | 同 chain+link 内按 revenue 降序 | 是 |
| 环节内净利排名 | linkProfitRank | integer | — | 同 chain+link 内按 netProfit 降序 | 是 |
| 最新价 | price | number | 元 | 行情快照最新价，对应 `quoteDate` | 是 |
| 涨跌幅 | changePercent | number | % | 对应 `quoteDate` 当日涨跌幅，正红负绿。**对象键用 camelCase，不采用 `change_percent`** | 是 |
| 主力净流入 | mainNetFlow | number | 元 | 当日主力净流入（WeStock `MainNetFlow`） | 是 |
| 5日主力净流入 | mainNetFlow5D | number | 元 | WeStock `MainNetFlow5D` | 是 |
| 20日主力净流入 | mainNetFlow20D | number | 元 | WeStock `MainNetFlow20D` | 是 |
| 行情日期 | quoteDate | date | — | 上述价格/涨跌幅/资金流对应交易日，与 `asOf`（研究整理日）区分 | 是 |
| 技术指标数值 | techIndicators | string(JSON) | — | 完整数值集存为 JSON 字符串，结构见下方；机器可读，避免拆 18 个宽列 | 是 |
| 技术面摘要 | techSignal | string | — | 客观文字摘要（如「超卖反弹初期」）；须标注来源（工具返回/计算值），禁止买卖建议用语 | 是 |
| 数据来源 | source | string | — | — | 否 |
| 数据时点 | asOf | date | — | 统一 2026-11-18 | 否 |

`techIndicators` JSON 结构（缺项省略或为 `null`，不填 0）：
```
{"macd":{"dif":null,"dea":null,"hist":null},
 "kdj":{"k":null,"d":null,"j":null},
 "rsi":{"6":null,"12":null,"24":null},
 "ma":{"5":null,"10":null,"20":null,"60":null,"120":null,"250":null},
 "boll":{"upper":null,"mid":null,"lower":null}}
```

示例行（占位符）：
```
股票代码,股票简称,所属产业链,所属环节,营业总收入,营收同比,归母净利润,归母净利同比,加权平均ROE,毛利率,环节内营收排名,环节内净利排名,最新价,涨跌幅,主力净流入,5日主力净流入,20日主力净流入,行情日期,技术指标数值,技术面摘要,数据来源,数据时点
待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,2026-11-18
```

- **v1.5 无归属龙头说明**：表4 允许存在 `chain`/`link` 留空的记录——即**仅有完整行情/财务但未纳入本次产业链梳理范围的额外龙头**（如贵州茅台）。这类记录是行情数据的有益补充，不删、不编造产业链归属；其可见性规则见 §2.2 第 2 条。产业链归属须有据可依，禁止为凑联动而强行归类。

### 表5 业绩预告/待披露观察区

- 中文表名：**业绩预告与待披露观察区**
- 文件名：`h1_2026_watch.csv`
- 对应板块：⑤业绩预告/待披露观察区（未披露自动观察，披露后转正入榜）
- 状态机：`待披露未预告` → `已发业绩预告` → `已披露正式半年报`（此时 `enteredOfficial=true`，可转正迁入表1）
- **v1.2/v1.3 时点裁决**：2026H1 披露已于 8/31 收官，2026-11-18 时点**不存在「待披露未预告」活样本**。板块⑤定位为**历史观察快照 + 转正归档**双视图。**允许本表无「待披露未预告」记录**，不得为凑满状态而编造。
- **字段时间语义（v1.3 定稿，macro-data 确认采用）**：
  - `discloseStatus` = **观察时点状态**（`statDate` 当日状态）。历史预告快照记录填 `已发业绩预告`，`statDate=2026-07-15`（强制预告截止日，回看约 1,692 家预告样本）。
  - `enteredOfficial` = **截至 `asOf` 的当前状态**。上述公司 8/31 前均已披露正式半年报并迁入表1，故填 `true`，**可与 `discloseStatus=已发业绩预告` 并存**。
  - `forecastType` + 预告值 = **观察时点的真实预告**，与 `enteredOfficial=true` 并存时不强制留空；仅当 `discloseStatus=已披露正式半年报`（无预告快照可留）时才留空、预告值移入 `note`。
  - `note` 统一标注「历史预告快照（截至7/15）；已转正入榜」。
  - 前端：这类记录**同时显示预告标签/增幅与「已转正入榜」标记**；板块⑤顶部固定提示「历史观察快照，统计时点 2026-07-15；H1 披露已于 8/31 收官」。
  - **v1.5 澄清（防 QA 误判）**：「11-18 时点无待披露活样本」仅指**以 11-18 为观察时点**的情形。若存在 `discloseStatus=待披露未预告` 记录且其 `statDate` 为更早的真实时点（如 `*ST萃华` 以 2026-08-31 法定披露截止日为观察时点，来源深交所公告、经 team-lead 指令收录），属**合规的历史观察快照**，不违反「禁止编造」——只要 `statDate` 与来源真实可溯即可。QA 不得以「契约说无待披露记录」为由判此类记录违规。

| 中文表头 | 对象键 | 类型 | 单位 | 口径/说明 | 可空 |
|---|---|---|---|---|---|
| 股票代码 | code | string | — | 6 位代码 | 否 |
| 股票简称 | name | string | — | — | 否 |
| 所属产业链 | chain | string | — | — | 是 |
| 所属环节 | link | string | — | — | 是 |
| 披露状态 | discloseStatus | enum | — | 三选一：已披露正式半年报 / 已发业绩预告 / 待披露未预告；语义=`statDate` 观察时点状态（当前快照可无第三类） | 否 |
| 预告类型 | forecastType | enum | — | 预增/略增/扭亏/续盈/预减/略减/首亏/续亏/不确定；仅 `discloseStatus=已发业绩预告` 时填写，可与 `enteredOfficial=true` 并存 | 是 |
| 预告净利下限 | forecastProfitMin | number | 元 | 预告归母净利区间下限 | 是 |
| 预告净利上限 | forecastProfitMax | number | 元 | 预告归母净利区间上限 | 是 |
| 预告净利同比下限 | forecastYoyMin | number | % | 区间下限，正红负绿 | 是 |
| 预告净利同比上限 | forecastYoyMax | number | % | 区间上限，正红负绿 | 是 |
| 预约披露日期 | scheduledDate | date | — | 交易所预约披露日 | 是 |
| 观察统计时点 | statDate | date | — | 该条观察记录的实际统计/快照时点（预告快照=2026-07-15）；与 `asOf`（研究整理日）区分 | 是 |
| 是否已入正式榜 | enteredOfficial | boolean | — | true=截至 `asOf` 已披露正式半年报并已迁入表1；**可与 `discloseStatus=已发业绩预告` 并存**；默认 false | 否 |
| 备注 | note | string | — | 观察说明；约值/历史预告/未获取均在此标注 | 是 |
| 数据来源 | source | string | — | — | 否 |
| 数据时点 | asOf | date | — | 统一 2026-11-18（研究整理日） | 否 |

示例行（占位符）：
```
股票代码,股票简称,所属产业链,所属环节,披露状态,预告类型,预告净利下限,预告净利上限,预告净利同比下限,预告净利同比上限,预约披露日期,观察统计时点,是否已入正式榜,备注,数据来源,数据时点
待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,2026-11-18
```

### 表6 宏观行业对照区

- 中文表名：**宏观行业对照区**
- 文件名：`h1_2026_macro.csv`
- 对应板块：⑥宏观行业对照区

| 中文表头 | 对象键 | 类型 | 单位 | 口径/说明 | 可空 |
|---|---|---|---|---|---|
| 行业或指标名称 | name | string | — | 行业名或宏观指标名 | 否 |
| 层级 | level | enum | — | 申万一级 / 产业链 / 板块 / 宏观指标 / 指数行情 | 否 |
| 关联产业链 | chain | string | — | 用于与板块②④⑤联动；层级=宏观指标时可空 | 是 |
| 营收同比 | revenueYoy | number | % | 行业整体营收同比，正红负绿 | 是 |
| 净利同比 | netProfitYoy | number | % | 行业整体净利同比，正红负绿 | 是 |
| 平均ROE | roeAvg | number | % | 行业平均 ROE；v1.2 允许 TTM 滚动口径，具体口径由 `roeCaliber` 标注，禁止与加权平均半年度值直接比较 | 是 |
| ROE口径 | roeCaliber | enum | — | 三选一：`加权平均半年度未年化` / `TTM滚动12个月` / `待填`；行业 ROE 来自 westock-data `roeTTM` 时填 `TTM滚动12个月` | 是 |
| 景气度标签 | prosperity | enum | — | 高景气/平稳/承压/下行；v1.2 计算值分档规则见 §4.1 | 是 |
| 宏观指标值 | macroValue | number | — | 层级=宏观指标时填写（如 PMI、GDP 同比） | 是 |
| 宏观指标单位 | macroUnit | string | — | 如 %、点、亿元 | 是 |
| 对照说明 | compareNote | string | — | 行业与宏观的对照结论；口径/计算值/时点差异均在此注明 | 是 |
| 数据来源 | source | string | — | — | 否 |
| 数据时点 | asOf | date | — | 统一 2026-11-18（研究整理日） | 否 |
| 涨跌幅 | changePercent | number | % | 指数当日涨跌幅，对应 `quoteTime`，正红负绿；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |
| 换手率 | turnoverRate | number | % | 指数当日换手率；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |
| 近5日涨跌 | chg5d | number | % | 近5日区间涨跌幅；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |
| 近20日涨跌 | chg20d | number | % | 近20日区间涨跌幅；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |
| 年初至今 | chgYtd | number | % | YTD，基准 2025-12-31 收盘；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |
| 主力净流入 | mainNetFlow | number | 元 | 当日主力净流入；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |
| 散户净流入 | retailNetFlow | number | 元 | 小单净流入（散户口径）；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |
| 行情时点 | quoteTime | string | — | 行情/资金流对应时点，如「2026-11-18 09:56 盘中快照」；可空，仅 level=指数行情 时填写 | 是（仅指数行情） |

示例行（占位符）：
```
行业或指标名称,层级,关联产业链,营收同比,净利同比,平均ROE,ROE口径,景气度标签,宏观指标值,宏观指标单位,对照说明,数据来源,数据时点,涨跌幅,换手率,近5日涨跌,近20日涨跌,年初至今,主力净流入,散户净流入,行情时点
待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,待填,2026-11-18,,,,,,,,
```

---

## 2. 六大板块字段映射与交互联动规则

### 2.1 板块 ↔ 表 ↔ 字段映射总表

| 板块 | 数据表 | 主展示字段 | 筛选/联动字段 | 默认排序维度 |
|---|---|---|---|---|
| ①全市场正式半年报总榜 | h1_2026_market.csv | name, swIndustry, revenue, netProfit, roe, revenueYoy, netProfitYoy | chain, link, swIndustry, keyword | netProfit（归母净利降序） |
| ②产业链环节赚钱榜 | h1_2026_chain_link.csv | chain, link, netProfitSum, profitRank, roeAvg, revenueYoy | chain, keyword | profitRank（赚钱能力升序，即名次靠前） |
| ③双增公司榜 | h1_2026_double_growth.csv | name, revenueYoy, netProfitYoy, growthScore, roe | chain, link, swIndustry, keyword | growthScore（双增强度降序） |
| ④产业链内公司对比 | h1_2026_chain_company.csv | name, link, revenue, netProfit, roe, linkProfitRank, price, changePercent, mainNetFlow, techSignal | chain, link, keyword | linkProfitRank（环节内净利排名升序） |
| ⑤业绩预告/待披露观察区 | h1_2026_watch.csv | name, discloseStatus, forecastType, forecastYoyMax, scheduledDate, statDate | chain, link, discloseStatus, keyword | scheduledDate（预约披露日升序） |
| ⑥宏观行业对照区 | h1_2026_macro.csv | name, level, revenueYoy, netProfitYoy, roeAvg, roeCaliber, prosperity | level, chain, keyword | netProfitYoy（净利同比降序） |

**v1.6 表6 指数行情说明**：`level=指数行情` 的记录为盘中行情快照，行情/资金流时点以 `quoteTime` 为准，与 `asOf`（2026-11-18 研究整理日）、财报统计期 2026H1 三者严格区分、不可混用；`retailNetFlow` 以小单净流入近似散户口径，并在 `compareNote` 标注；原始资金流表无明细的指数（上证50、中证500）该项留空，不编造。

**v1.7 NeoData 直连回填说明**：表1 的经营现金流净额（`ocf`）与毛利率（`grossMargin`）空缺项、表4 的毛利率空缺项，由 NeoData 直连 `financial_indicators` + `cash_flow`（2026H1，截止 2026-06-30）同源同口径回填，已抽样逐位核对；资产负债率（`debtToAssetRatio`）为 v1.7 新增列，取自 NeoData `debt_to_assets_ratio`（负债合计/资产总计×100），金融类同样有值（高负债为行业特征），仅来源缺失时留空。**只填空缺、不覆盖已有值**（如贵州茅台经营现金流 70690750119.06、毛利率 89.5552，大全能源毛利率 −74.4 均保持原值）；`roe` 与 `revenueYoy` 因口径差异（表1 加权平均未年化 vs NeoData 平均口径；营业总收入 vs 营业收入）未被本次回填覆盖，保持原值。

### 2.2 联动链路：`产业链 → 环节 → 板块/类型/排序/关键词`

```
[产业链下拉 chain]
      │ onchange
      ▼
[环节下拉 link]  ← 选项 = 当前 chain 下各表 link 的去重集
      │ onchange
      ▼
[板块/类型/排序/关键词 过滤器] → 重算当前板块表格
```

**规则明细：**

1. **产业链 → 环节**：环节下拉的选项由「当前选中产业链」在所有相关表中出现的 `link` 去重生成；产业链切换时若原环节不在新选项中，自动重置为「全部环节」。
2. **环节 → 数据**：选中环节后，各板块仅显示 `row.chain === 选中产业链 && row.link === 选中环节` 的记录；「全部环节」则只按 chain 过滤。**v1.5**：`chain`/`link` 留空的无归属龙头（见表4 说明）仅在「全部产业链 + 全部环节」视图显示；一旦选中任何具体产业链/环节即被过滤掉——此为预期行为，前端不得视为缺数或报错，并可在表4 加一句「含未纳入产业链梳理的龙头，仅全部视图可见」提示。
3. **产业链/环节 → ⑥宏观对照区**：宏观表 `level` 为「产业链」的记录按 `chain` 联动过滤；`level` 为「宏观指标」的记录始终显示（作为全局对照背景）。
4. **⑤观察区状态联动**：`discloseStatus` 作为「类型」过滤器；`enteredOfficial=true` 的记录（无论 `discloseStatus` 是 `已发业绩预告` 还是 `已披露正式半年报`）前端都加「已转正入榜」标记，并提示可前往板块①查看；历史快照记录同时保留预告标签/增幅。**v1.2/v1.3**：板块⑤为历史观察快照视图，顶部须固定提示「历史观察快照，统计时点 2026-07-15；H1 披露已于 8/31 收官」；无「待披露未预告」记录时不得视为数据缺失或报错。
5. **关键词搜索**：对当前板块所有字符串字段做大小写不敏感包含匹配（code/name/chain/link/swIndustry/forecastType 等）。
6. **排序**：每个板块提供排序下拉，维度至少包含该板块「默认排序维度」+ 营收/净利/ROE/同比等核心数值字段；点击表头也可切换升降序。
7. **涨红跌绿**：所有 `Yoy` / 涨跌类字段渲染时 `>0` 加 `.up`（红）、`<0` 加 `.down`（绿）、`=0`/空加 `.flat`（灰）。
8. **全局重置**：提供「重置筛选」按钮，清空 chain/link/类型/排序/关键词并回到各板块默认排序。
9. **空态**：筛选后无数据时显示「暂无符合条件的数据（可能为占位数据或该环节未披露）」，不得显示空白表格误导。

### 2.3 各板块排序维度清单

- **板块①**：归母净利 netProfit（默认）｜营业总收入 revenue｜加权平均ROE roe｜营收同比 revenueYoy｜归母净利同比 netProfitYoy
- **板块②**：赚钱能力排名 profitRank（默认，升序）｜环节归母净利合计 netProfitSum｜环节营收同比 revenueYoy｜环节平均ROE roeAvg｜环节公司数 companyCount
- **板块③**：双增强度 growthScore（默认，降序）｜营收同比 revenueYoy｜归母净利同比 netProfitYoy｜加权平均ROE roe
- **板块④**：环节内净利排名 linkProfitRank（默认，升序）｜环节内营收排名 linkRevenueRank｜营业总收入 revenue｜归母净利润 netProfit｜加权平均ROE roe｜涨跌幅 changePercent｜主力净流入 mainNetFlow｜最新价 price
- **板块⑤**：预约披露日 scheduledDate（默认，升序）｜预告净利同比上限 forecastYoyMax｜披露状态 discloseStatus
- **板块⑥**：净利同比 netProfitYoy（默认，降序）｜营收同比 revenueYoy｜平均ROE roeAvg｜宏观指标值 macroValue

---

## 3. 双数据源策略（内嵌快照 + 资料库 SDK）

> **v1.3 裁决（frontend-dev 与 team-lead 初始指令冲突）**：`SNAPSHOT` 键名、`DB_*` 常量命名、SDK 分页签名（`page`/`rows`/`hasMore` vs `startCursor`/`results`/`nextCursor`）**以 team-lead 最终下发给 frontend-dev 的方案为准**（由他注入数据并替换 databaseId）。§3 给出的命名作为参考契约，不强制。无论采用哪套命名，以下**行为要求强制且须语义等价**：六表数据齐全；SDK 分页必须拉全（防死循环 + 安全上限）；SDK 不可用或抛错时回退内嵌快照并显示「离线快照模式」徽标；导出 CSV 为当前筛选+排序结果且带 BOM。frontend-dev 已加双向兼容层（两套键名/分页自动识别），保留该兼容层即可。

### 3.1 内嵌快照（离线兜底）

HTML 内嵌一个全局对象 `SNAPSHOT`，六个键分别对应六张表，**值为对象数组**（对象键见 §1）：

```js
const SNAPSHOT = {
  market:       [ /* h1_2026_market.csv 的记录对象，键为对象键 */ ],
  chainLink:    [ /* h1_2026_chain_link.csv */ ],
  doubleGrowth: [ /* h1_2026_double_growth.csv */ ],
  chainCompany: [ /* h1_2026_chain_company.csv */ ],
  watch:        [ /* h1_2026_watch.csv */ ],
  macro:        [ /* h1_2026_macro.csv */ ]
};
```

- 快照是**静态构建时内嵌**，内容来自 data-engineer 生成的六张 CSV（同样为占位/实测数据）。
- 快照数组允许为空 `[]`，但键必须存在。

### 3.2 资料库 SDK 按需查询

常量占位（frontend-dev 填入真实 databaseId）：

```js
const DB_MARKET       = '待填';  // h1_2026_market.csv
const DB_CHAIN_LINK   = '待填';  // h1_2026_chain_link.csv
const DB_DOUBLE_GROWTH= '待填';  // h1_2026_double_growth.csv
const DB_CHAIN_COMPANY= '待填';  // h1_2026_chain_company.csv
const DB_WATCH        = '待填';  // h1_2026_watch.csv
const DB_MACRO        = '待填';  // h1_2026_macro.csv

const DB_MAP = {
  market: DB_MARKET, chainLink: DB_CHAIN_LINK, doubleGrowth: DB_DOUBLE_GROWTH,
  chainCompany: DB_CHAIN_COMPANY, watch: DB_WATCH, macro: DB_MACRO
};
```

SDK 查询接口契约（frontend-dev 按此封装；若实际 SDK 签名不同，以实际为准但需保持 `loadAll` 行为）：

```js
// 约定：SDK.query({ databaseId, page, pageSize }) -> Promise<{ rows: Object[], hasMore: boolean, total?: number }>
// page 从 1 起；pageSize 默认 500。
```

**`loadAll` 分页规则：**

```js
async function loadAll(databaseId, pageSize = 500) {
  let page = 1, all = [], guard = 0;
  while (guard++ < 200) {                 // 安全上限，防死循环
    const res = await SDK.query({ databaseId, page, pageSize });
    const rows = Array.isArray(res?.rows) ? res.rows : [];
    all = all.concat(rows);
    if (!res?.hasMore || rows.length < pageSize) break;  // 无更多或末页不足则停止
    page += 1;
  }
  return all;
}
```

- 六张表各自独立调用 `loadAll`，并行发起（`Promise.all`），单表失败不影响其他表。
- 拉取到的记录对象键应与 §1「对象键」一致；若 SDK 返回中文键，需按映射表转成英文键。

### 3.3 数据源切换（SDK 不可用 → 快照）

```js
async function loadTable(key) {
  try {
    const dbId = DB_MAP[key];
    if (!dbId || dbId === '待填') throw new Error('databaseId 未配置');
    const rows = await loadAll(dbId);
    return { rows, mode: 'sdk' };
  } catch (e) {
    console.warn(`[${key}] SDK 查询失败，回退内嵌快照：`, e);
    return { rows: (SNAPSHOT[key] || []).slice(), mode: 'snapshot' };
  }
}
```

- 任一环节抛错（SDK 未注入、网络失败、databaseId 未填、返回格式异常）统一走 catch 回退快照。
- 页面顶部显示数据源徽标：`实时资料库` 或 `离线快照模式`，并对用户可见；离线模式下免责声明旁追加「当前为离线快照，数据可能非最新」。
- 六表可处于不同模式（部分 sdk、部分 snapshot），互不影响。

### 3.4 导出 CSV 逻辑

```js
function exportCSV(rows, headerMap, filename) {
  // headerMap: [{ key: 'code', label: '股票代码' }, ...]  顺序即列顺序
  const esc = v => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const lines = [
    headerMap.map(h => esc(h.label)).join(','),
    ...rows.map(r => headerMap.map(h => esc(r[h.key])).join(','))
  ];
  const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
```

- 每个板块提供「导出当前结果」按钮，导出**当前筛选+排序后**的可见行（不是全表）。
- 导出使用 §1 的中文表头（中英键映射），文件名如 `h1_2026_market.csv`。
- 必须有 BOM（`\uFEFF`）保证 Excel 中文不乱码；字段含逗号/引号/换行按 RFC4180 转义。

---

## 4. 数据口径与来源标注规范

### 4.1 口径（所有表统一遵守）

| 指标 | 统一口径 | 标注要求 |
|---|---|---|
| 报告期 | 2026H1 半年度报告，**累计口径（1–6 月）** | 表头/说明处注明「2026H1 累计，非单季、非年化」 |
| 营收 | **营业总收入**（含其他业务收入） | 不得用「营业收入」科目口径混替；如来源仅提供「营业收入」需注明差异 |
| 净利 | **归母净利润**（归属于上市公司股东的净利润） | 不得用「净利润（含少数股东损益）」替代 |
| 扣非净利 | 扣除非经常性损益后的归母净利润 | 与归母净利分列，不混用 |
| ROE | 公司级（表1/3/4）：**加权平均净资产收益率，半年度未年化**；行业级（表6）：**允许 TTM 滚动12个月**（westock-data roeTTM），须以 `roeCaliber` 标注；环节级（表2）随来源口径并注明 | 必须注明具体口径；**禁止将 TTM 与加权平均半年度值直接比较或混排** |
| 同比 | 2026H1 对比 2025H1 | 正红负绿；原文未给同比时按两期数据计算并注明「计算值」 |
| 金额单位 | 元（纯数字） | 展示层可格式化为亿元，但 CSV/对象存储必须是元；工具返回「亿元」须 ×1e8 换算后落库，data-engineer 不得二次换算 |
| 数据时点 | `asOf`=2026-11-18 为**研究整理日**；统计期为 **2026H1** | 两者须在 `compareNote`/`note` 区分；对时点敏感记录用 `statDate` 标注实际观察时点（表5预告快照=2026-07-15） |

**v1.2 口径裁决细则：**

- 表6 `roeCaliber` 取值：`加权平均半年度未年化` / `TTM滚动12个月` / `待填`；来源为 westock-data roeTTM 时填 `TTM滚动12个月`，并在 `compareNote` 注明「ROE为TTM滚动12个月、非加权平均半年度」。
- 表6 `prosperity` 为**按净利同比分档的计算值**，分档规则：`netProfitYoy>30` → 高景气；`0~30` → 平稳；`-30~0` → 承压；`<-30` → 下行。须在 `compareNote` 标注「按净利同比分档判定（计算值）」，不得冒充工具返回的原始枚举。
- **WeStock finance 字段映射（v1.3，finance-data 核验）**：`TotalOperatingRevenue`→`revenue`、`TORGrowRate`→`revenueYoy`、`NPParentCompanyOwners`→`netProfit`、`NPParentCompanyYOY`→`netProfitYoy`、`ROEWeighted`→`roe`（即加权平均口径）、`GrossIncomeRatio`→`grossMargin`、`NPDeductNonRecurringPL`→`deductNetProfit`、`NetOperateCashFlow`→`ocf`、`name`→`name`；`code` 去除 `sh/sz/bj` 市场前缀转 6 位字符串。
- **营收字段强约束（v1.3）**：营收与营收同比**必须**取 `TotalOperatingRevenue`/`TORGrowRate`（营业总收入），**禁止**误用 `OperatingRevenue`/`OperatingRevenueGrowRate_Q`（营业收入）——两套数值差异显著（如茅台 营业总收入 922.78亿/+1.30% vs 营业收入 907.03亿/−5.14%；长鑫 +873.64% vs +977.39%）。data-engineer 落库与 QA 校验均须核查此口径。
- **行情/资金/技术口径（v1.4，表4）**：`price`/`changePercent`/`mainNetFlow` 系列均为**行情快照**，必须带 `quoteDate`（交易日），与 `asOf`（研究整理日 2026-11-18）区分；缺 `quoteDate` 的行情值不得参与排序。`techIndicators` 为原始数值 JSON，缺项省略/为 `null` 不填 0；`techSignal` 为文字摘要，须在 `note` 或字段值标注来源（工具返回/计算值），**客观描述、禁止买卖建议用语**（沿用现有工具「行情视角」只陈列看多看空逻辑、不给建议的口径）。涨幅着色仍遵循涨红跌绿。
- **指数行情口径（v1.6，表6）**：`level=指数行情` 为盘中行情快照，行情/资金流对应 `quoteTime`（如 2026-11-18 09:56 盘中快照，非收盘），与 `asOf`（2026-11-18 研究整理日）、财报统计期 2026H1 三者严格区分，不得混用；`chgYtd` 基准为 2025-12-31 收盘；`retailNetFlow` 以 WeStock 小单净流入近似散户口径并在 `compareNote` 标注；原始资金流表无明细的指数（上证50、中证500）留空，不编造。
- **NeoData 直连回填口径（v1.7，表1/表4）**：空缺的 `ocf`/`grossMargin` 取 NeoData 直连 2026H1 值（报告期 2026-01-01~2026-06-30，累计口径，与统计期一致），单位为元 / % 与 §0 一致；资产负债率 `debtToAssetRatio` 为 2026H1 时点值（%）。一律只补空缺、不覆盖已有值；来源标注沿用 NeoData，ROE 与营收同比因口径差异（加权未年化 vs 平均、营业总收入 vs 营业收入）未被覆盖。

### 4.2 来源与标注

- 允许来源：**Wind / iFinD / 东方财富 / WeStock 工具返回**，以及**官方统计/监管机构：国家统计局 / 海关总署 / 中国人民银行 / 中国证监会 / 沪深交易所**（v1.2 扩充）；可为上述组合，在 `source` 字段用逗号分隔。宏观指标直接写官方机构名，不得冒充行情工具来源。
- 每条记录必须带 `source` 与 `asOf`；`asOf` 统一为 **2026-11-18**。
- 页面「数据来源与口径」区块固定展示：数据时点 2026-11-18、统计期 2026H1、营收=营业总收入、净利=归母净利润、公司 ROE=加权平均（半年度未年化）/行业 ROE 口径见各行标注、同比基准 2025H1、来源含官方机构。
- 来源为估算/计算值时，须在 `note` 或对照说明中标注「计算值/估算/约值」，禁止冒充公告原文。「约」值保留数值并在 `note` 标注「约值」，前端以 `≈` 展示。
- 占位数据（未采集到的真实值）一律写「待填」，不得填 0 或编造任何财务数字；**「待填」排序时沉底，不得当作 0 或零增长参与比较**。
- 行业覆盖缺口（31 个申万一级行业仅取到 17 个）与未采集的 `revenueYoy` 一律留「待填」，不得以 0 填充或解读为零增长。

### 4.3 合规

- 页面固定免责声明（见 §0），非投资建议。
- 涨红跌绿遵循 A 股习惯，不做反向着色。

---

## 5. 验收清单（qa-tester 逐条勾选）

**数据契约**
- [ ] 1. 六张 CSV 文件齐全，文件名与 §1 完全一致。
- [ ] 2. 每张 CSV 表头与 §1「中文表头」顺序、用词完全一致。
- [ ] 3. 所有「待填」占位行不含任何伪造财务数字。
- [ ] 4. 股票代码均为 6 位字符串，前导零未丢失。
- [ ] 5. 金额字段单位为元、无千分位、无单位后缀；比例字段为百分数数值。
- [ ] 6. 可空字段缺失留空/`null`，未用 0/`-`/`N/A` 冒充。
- [ ] 7. 表3 所有行满足 `revenueYoy>0` 且 `netProfitYoy>0`，`growthScore=两者之和`。
- [ ] 8. 表5 `enteredOfficial=true` 的记录均已同步进表1，状态流转正确。

**字段映射与联动**
- [ ] 9. 六大板块均按 §2.1 映射正确的数据表与默认排序。
- [ ] 10. 产业链下拉选项来自各表 `chain` 去重；环节下拉随产业链联动更新并可重置为「全部环节」。
- [ ] 11. 选中环节后各板块按 `chain + link` 过滤正确；宏观区「宏观指标」层级始终显示。
- [ ] 12. 关键词搜索对字符串字段大小写不敏感匹配，结果正确。
- [ ] 13. 每个板块排序下拉至少含默认维度 + 营收/净利/ROE/同比核心字段，点击表头可切升降序。
- [ ] 14. 筛选无结果时显示友好空态，非空白表格。

**双数据源**
- [ ] 15. HTML 内嵌 `SNAPSHOT` 对象，六个键齐全且值为数组。
- [ ] 16. `DB_MARKET` 等六个 databaseId 常量存在（可为占位 `'待填'`）。
- [ ] 17. `loadAll` 正确分页：`page` 从 1 起、`hasMore=false` 或末页不足时终止、有 200 页安全上限。
- [ ] 18. SDK 抛错/未配置/databaseId 为占位时，正确回退快照并显示「离线快照模式」徽标；六表模式互不影响。

**导出与合规**
- [ ] 19. 导出 CSV 导出当前筛选+排序结果，含 BOM、中文表头、逗号/引号正确转义，Excel 打开中文不乱码。
- [ ] 20. 同比/涨跌字段涨红跌绿；免责声明与「非投资建议」在每页可见；数据来源区块标注时点 2026-11-18 及 ROE 未年化口径。

**交付形态与视觉（硬约束）**
- [ ] 21. 最终 HTML 为单文件，HTML/CSS/JS/数据快照全部内联，无任何外部文件引用。
- [ ] 22. 无任何外部 CDN（含 ECharts 等图表库）；图表用内联 SVG 或 CSS 条形图实现。
- [ ] 23. 视觉风格沿用现有模板：浅底 `#f5f6f8`、白卡 `#fff`+10px 圆角、蓝主色 `#2f6fed`、简洁表格，CSS 变量与 §0.1 一致。

**v1.2 口径裁决（macro-data 冲突）**
- [ ] 24. 表6 增 `roeCaliber` 列，行业 ROE（westock-data roeTTM）填 `TTM滚动12个月` 且 `compareNote` 注明；表1/3/4 仍为加权平均半年度，未在前端跨口径混排。
- [ ] 25. `source` 允许国家统计局/海关总署/央行等官方机构；宏观指标 `source` 如实填官方机构名，未冒充行情工具来源。
- [ ] 26. 表5 增 `statDate` 列，历史预告快照填 2026-07-15；页面顶部标注「历史观察快照」时点提示；无「待披露未预告」活样本不被当作缺数或报错。
- [ ] 27. 已披露记录 `forecastType` 留空、预告值移 `note`；未采字段（14 个行业、`revenueYoy`、`scheduledDate`、`chain/link`）填「待填」而非 0；「约」值在 `note` 标注。
- [ ] 28. 亿元→元换算仅一次（采集方已 ×1e8）；`prosperity` 按净利同比分档规则生成并标注「计算值」；「待填」排序沉底。

**v1.3 口径与命名裁决（finance-data / frontend-dev 反馈）**
- [ ] 29. 表1/3/4 营收/营收同比取 WeStock `TotalOperatingRevenue`/`TORGrowRate`，未误用 `OperatingRevenue`/`OperatingRevenueGrowRate_Q`；`roe` 取 `ROEWeighted`；`code` 已去 `sh/sz/bj` 前缀为 6 位。
- [ ] 30. 表5 历史预告快照记录 `discloseStatus=已发业绩预告` + `statDate=2026-07-15` + `enteredOfficial=true` 三者并存，`forecastType`/预告值保留，`note` 标注「历史预告快照（截至7/15）；已转正入榜」，前端同时显示预告标记与「已转正入榜」标记。
- [ ] 31. `SNAPSHOT`/`DB_*`/SDK 分页命名以 team-lead 最终裁决为准（兼容层保留），但六表齐全、分页拉全、失败回退快照+离线徽标、CSV 带 BOM 等行为与 §3 语义等价；免责声明采用 team-lead 指定文案。

**v1.4 表4 行情字段（frontend-dev 变更请求）**
- [ ] 32. 表4 含 8 个新字段：`price`、`changePercent`（camelCase，非 `change_percent`）、`mainNetFlow`/`mainNetFlow5D`/`mainNetFlow20D`、`quoteDate`、`techIndicators`（JSON 字符串，结构见 §1 表4）、`techSignal`；行情值带 `quoteDate`，缺失显示「—」不报错。
- [ ] 33. `techIndicators` 缺项为 `null` 不填 0；`techSignal` 为客观摘要且标注来源、无买卖建议用语；前端主别名切到契约正式键并保留兼容别名。

**v1.5 表4 无归属龙头（data-engineer 落库反馈）**
- [ ] 34. 表4 `chain`/`link` 放宽为可空：无产业链归属的额外龙头（如贵州茅台）留空、不编造归属；前端仅在「全部产业链+全部环节」视图显示此类记录，具体筛选下被过滤属预期、不报错；JSON 六键命名以 team-lead 裁决为准（market/chain/growth/compare/watch/macro 与契约别名双向兼容）。
- [ ] 35. 表5 `待披露未预告` 记录若 `statDate` 为真实历史时点（如 *ST萃华 2026-08-31、来源深交所公告、team-lead 指令收录）属合规历史快照，不按「11-18 无活样本」判违规；`statDate` 与来源须真实可溯。

**v1.6 表6 指数行情增强（P1，data-engineer 落库）**
- [ ] 36. 表6 指数行情行 `changePercent`/`turnoverRate`/`chg5d`/`chg20d`/`chgYtd`/`mainNetFlow`/`retailNetFlow`/`quoteTime` 8 字段齐全，7 大指数数值可溯源至 WeStock 工具返回（DATA_MACRO.md §4.3–4.5）。
- [ ] 37. 盘中快照时点 `quoteTime` 已标注并与 `asOf`/统计期 2026H1 区分；上证50/中证500 无资金流明细的 `mainNetFlow`/`retailNetFlow` 留空不编造，散户口径以小单净流入近似并标注。

**v1.7 NeoData 直连回填（data-engineer 落库）**
- [ ] 38. 表1 含新增资产负债率列（`debtToAssetRatio`），CSV 表头为 17 列（资产负债率插在毛利率后、披露日期前）；值取自 NeoData 直连 `debt_to_assets_ratio`（2026H1），金融类同样有值、仅来源缺失时留空、不填 0；SNAPSHOT 与资料库 market 表同步含该字段。
- [ ] 39. 表1/表4 空缺的经营现金流净额、毛利率由 NeoData 直连 2026-H1 同源同口径回填（已抽样逐位核对），已有值未被覆盖（茅台现金流 70690750119.06、毛利率 89.5552 保持原值；大全能源毛利率 −74.4 未被 −74.4242 覆盖）；SNAPSHOT/资料库与 CSV 逐字段一致，`roe`/`revenueYoy` 因口径差异保持原值。

---

> 变更记录：v1.0 初始锁定契约（pm-architect，2026-11-18）；v1.1 补充单文件/无 CDN/视觉风格硬约束（team-lead 要求）；v1.2 针对 macro-data 五处口径冲突裁决（ROE TTM 放宽+标注、来源白名单扩官方机构、表5 历史快照+statDate、金额单位单次换算、行业缺口填待填）；v1.3 定稿表5 状态字段时间语义、补 WeStock 字段映射与营收字段强约束、数据层命名/免责声明权威归 team-lead（finance-data / frontend-dev 反馈）；v1.4 应 frontend-dev 变更请求增补表4 行情/资金/技术字段（price/changePercent/mainNetFlow 系列/quoteDate/techIndicators JSON/techSignal）；v1.5 放宽表4 chain/link 为可空以容纳无产业链归属的额外龙头、澄清表5 真实历史时点待披露记录合规（data-engineer 落库反馈），验收扩至 35 条，pm-architect 更新；v1.6 表6 扩 8 字段（涨跌幅/换手率/近5日涨跌/近20日涨跌/年初至今/主力净流入/散户净流入/行情时点）容纳指数行情增强，落库 7 大指数真实盘中快照数据，level 枚举新增「指数行情」，验收扩至 37 条（pm-architect/总指挥，2026-11-18）；v1.7 表1新增资产负债率列（debtToAssetRatio，取自 NeoData 直连 2026H1 financial_indicators.debt_to_assets_ratio），经营现金流净额与毛利率空缺项由 NeoData 直连同源同口径回填（只填空缺、不覆盖已有值），ROE/营收同比因口径差异保持原值，SNAPSHOT 与资料库 market 表同步，验收扩至 39 条（data-engineer，2026-11-18）。
