# 最小绝对差交班报告

白班仍按 `README.md` 的接口录入四点、冻结、发行并接纳。夜班用中心库里一份指定的接纳件核定最小绝对差。原标读留在站库，关站后也可以签发。

## 调用

- `review.inspection.issue_minimum(center, admission_id, left, right)` 签发并返回定稿。`center` 由 `report.store.open_center_store` 打开，调用时连接在事务外。`admission_id` 沿用 V1 登记号格式。闭窗两端接受 V1 有理输入，即整数、`Fraction` 或有理文本。单点窗有效。
- `report.publish.read_minimum(center, report_id)` 按签发返回的正整数报告号领取定稿。报告号的存储布局由实现决定，调用方使用对应种类的领取入口。

两处返回的定稿具有以下属性。

| 属性 | 内容 |
| --- | --- |
| `report_id` | 正整数报告号 |
| `request` | 含 `admission_id`、`left`、`right`，端点为 `Fraction` |
| `origin` | `report.origins.ReportOrigin`，含台架、接纳号、发行号、冻结号和修订号 |
| `receipt` | `report.receipts.Receipt`，使用本报告号及该父发行的发行号 |
| `infimum` | 非负 `Fraction` 或 `review.endpoints.QuadraticRoot`，无可读点时为 `None` |
| `status` | `empty` 表示无可读点，`unattained` 表示下界无法取到，`attained` 表示下界可取到 |
| `best` | 按设点顺序排列且互不相交的区间元组。每项有 `left`、`right`、`left_closed` 和 `right_closed` 属性。端点沿用 `review.endpoints.Endpoint`，两端同值且均闭表示孤点。`empty` 和 `unattained` 均返回 `()` |

## 判定和定稿

任一原分母为零的设点不可读，即使约分后有有限极限。仅以窗内可读实数设点的绝对通道差核定下界。可取得时，`best` 的并集恰好是全部可读且达到下界的设点。若整段同为最佳，保留该段及其开闭端点。结果用精确值比较，二次实根沿用 V1 的本原多项式及根序表示。

签发使用该登记号对应的固定校准。请求、出处、精确结果和回执同次提交。SQLite 提交失败传播对应的 `sqlite3.Error`，报告和回执均无新增，可重试。勘误及中心库重开后，`read_minimum` 直接返回原号已提交的定稿。倒序窗、非法有理输入和非法编号报 `ValueError`。格式有效但未知的登记或报告号报 `KeyError`。旧阈值报告继续经原领取、导出和查点入口按原格式使用。

## 交班样例

`minimum_samples.py` 提供 V1 四点标读，以及 `open_sample_station(path)` 和 `admit_marks(source, center, marks, base_revision=None)`。后者返回 `(admission_id, issued)`。用 `MARKS` 的一组标读接纳并关闭站库，再以返回的接纳号调用新签发入口。勘误组可用 `tests.fixtures.CONSTANT[:2]` 及含洞件的 `issued.evidence.revision_id` 登记并另行接纳。

| 样例 | 甲与乙 | 闭窗 | `status` | `infimum` | `best` |
| --- | --- | --- | --- | --- | --- |
| `hole` | `(x−1)/(x−1)` 与 `x` | `[0,2]` | `unattained` | `0` | 空 |
| `hole` | 同一含洞件 | `[1,1]` | `empty` | `None` | 空 |
| 勘误件 | `1/1` 与 `x` | `[1,1]` | `attained` | `0` | `{1}` |
| `zero_tie` | `x` 与 `2/x` | `[−2,2]` | `attained` | `0` | `{−√2}`、`{√2}` |
| `positive_tie` | `x` 与 `−2/x` | `[−2,2]` | `attained` | `2√2` | `{−√2}`、`{√2}` |
| `boundary_tie` | `(x+1)/(x+1)` 与 `(x−1)/x` | `[−1,1]` | `attained` | `1` | `{1}` |
| `constant_with_hole` | 两条均为 `(x−1)/(x−1)` | `[0,2]` | `attained` | `0` | `[0,1)`、`(1,2]` |

`python3 -B minimum_samples.py` 用现有阈值报告检查样例来件，输出实际合格段、不可读点及回执。原 `tests/fixtures.py` 提供站库、中心库和 V1 延迟外键提交失败夹具，可用作验证同次提交的参考。

## 运行核验与演示

沿用 `.pointwise-runtime.json` 的 version 1 和 cli 类型。`setup` 是准备命令的 argv 列表，`verify` 和 `demo` 分别是一条 argv 命令。交付时使 `verify` 保留完整原回归，并实际核验三种状态、无理并列、失败重试和重开领取。核验失败以非零状态退出。使 `demo` 展示从指定接纳件断源签发和重开领取的实际报告。原 `python3 -B check_project.py` 和 `python3 -B demo.py` 仍可运行。
