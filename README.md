# 双通道比值台架复检

这是模拟质控室的台架交班工具，使用 Python 3.11 标准库和两份独立的 SQLite 库。台架员从规程单和原始记录录入标读，质控员选定修订发行。夜班从中心存件判断哪些设点可用，次班凭报告号复查当时的结论和父发行。

## 一班工作

1. 用 `station.store.open_station_store(path)` 打开站库，用 `station.protocol.register_protocol(db, station, (first, second))` 注册台架和顺序固定的两条具名通道。用 `calibration.issue.initialize_issues(db)` 初始化站端发行表。重复初始化保留用户数据。
2. 用 `station.revisions.load(db, station, channel, x, numerator, denominator, base_revision=None)` 录入第一点，随后把返回的整数修订号作为 `base_revision` 传给下一次录入。勘误也是从明确指定的修订派生新修订，旧修订及其余标点保持。`read_revision` 可核账。
3. 用 `station.freeze.freeze(db, station, revision_id)` 冻结完整的四点名册。返回的 `FrozenRoster.freeze_id` 标识这份名册。缺项时拒绝冻结。
4. 用 `calibration.issue.issue(db, freeze_id)` 发行，取得 `IssuedCalibration.issue_id` 和 `.wire`。`read_issue` 按号读回存件与发送清单。原标读和冻结名册留站。
5. 用 `report.store.open_center_store(path)` 打开中心库。`exchange.admission.admit(center, station, wire)` 返回中心登记号，再关闭站库。接纳保存原交换件，校验内外身份、完整正文和正文 SHA-256。同台架同发行号且同正文的重投沿用登记，JSON 空白和字段排序可以不同。同号异文和错台件均拒绝。
6. 用 `review.inspection.review(center, admission_id, left, right, tolerance)` 签报。成功返回 `ReportSnapshot`，含整数报告号、精确分段、父发行来源和回执。窗口可为单点。报告和回执同次提交。
7. 用 `review.setpoint.point(center, report_id, x)` 查已签报告中的有理设点。`report.publish.read(center, report_id)` 领取定稿，`report.export.export_report(center, report_id)` 得到 JSON。领取、导出和查点均使用已签分段。
8. 将勘误版另行冻结和发行，再对新登记签报。重开中心库后，新旧报告及各自回执继续按原号领取。

## 数值和错误

标点、响应、设点和容差均无量纲。标点坐标只接受 0 和 1。入口的有理数可用整数、`Fraction` 或有理数文本，文本支持如 `-2`、`1/2`、`.5` 的常见写法。空标读表示缺项，录入调用拒绝空值和浮点输入。身份为非空且无首尾空白的字符串。登记号形如 `A1`，修订、冻结、发行和报告号各用所属库的正整数编号。

每通道用两点插值得到 `N(x) = n0 + (n1 - n0)x` 和 `D(x) = d0 + (d1 - d0)x`。原分母恒零时拒绝发行。任一原分母在设点为零时，该点为 `unreadable`。在共同可读域中，`|N甲/D甲 - N乙/D乙| <= tolerance` 的点为 `qualified`，其余为 `out_of_tolerance`。闭窗口内各点只属于一个分段，结果有序并保留开闭端点及孤点。导出以 `["rational", n, d]` 表示有理端点，以 `["quadratic", a, b, c, branch]` 表示本原整系数方程 `ax²+bx+c=0` 的较小根（`-1`）或较大根（`1`）。

非法输入和冲突抛出 `ValueError` 或其子类。未知修订、冻结、发行、登记或报告抛出 `KeyError` 或其子类。窗外点抛出 `ValueError`。SQLite 写入失败传播对应的 `sqlite3.Error`，调用只在成功提交后交付结果。公开写入入口使用由库初始化函数管理的连接和事务，调用时连接应处于事务外。

## 运行

平台提供 `check_project.py`，用 `python3 -B check_project.py` 运行完整正常回归。用 `python3 -B demo.py` 按样例标读在临时目录中完成一次发行、断源复检、查点、勘误对照和历史领取。样例在 `[0, 2]` 内采用容差 `1/2`，第一次交班的设点 1 不可读，勘误后该点合格。
