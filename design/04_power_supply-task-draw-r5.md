# 画图任务书：子图 04_power_supply，第 5 轮（按 Opus 复核第 2 轮 P1 改，接续第 4 轮）

工作目录 `/home/user/MP2645A-BMS`。纪律同第 1–4 轮任务书。**先备份** `cp hardware/04_power_supply.kicad_sch /tmp/draw-backup/04_power_supply.r4.kicad_sch`，
**先跑一遍脚本确认幂等**再改。第 3、4 轮的版面要求与全部自检继续有效，本轮改完**全部重跑**。
依据：`design/04_power_supply-review-opus-r2.md`（复核）、`design/04_power_supply-parts-r5.md`（取料）。

## 1. R42 换成熔断型电阻（复核 P1-1）

| 位号 | 符号名（lib_id `jlc:…`） | 值 | 封装 | LCSC |
|---|---|---|---|---|
| R42 | `FCR1206J56RP055W` | `56Ω 5% 熔断 1206` | jlc:R1206（以库符号 Footprint 字段为准） | C153337 |

理由：VIN_F 对地短路时 10Ω 普通厚膜会先于 F11 烧开起火；56Ω 熔断电阻在 20V 时 ≥7W、手册保证 <30s 受控开路，F11 留作 VIN_R 短路的二级保护。

## 2. 新增 C45 100nF/100V 贴 U4.VIN（复核 P1-2，Tokmas 手册第 14 页）

| 位号 | 符号名 | 值 | 封装 | LCSC |
|---|---|---|---|---|
| C45 | `CL21B104KCFNNNE` | `100nF 100V` | jlc:C0805 | C28233 |

接 VIN_F–GND，放在 C42/C44 旁、**最靠近 U4 VIN 脚**的位置（原理图上排在最靠 U4 的一列），GND 标签在下方。

## 3. 小修（复核 P2，确定无争议的两条）

- U4 的 `Datasheet` 字段改为 Tokmas 件：`https://www.lcsc.com/datasheet/C54823941.pdf`（其余字段不动）。
- C42、C43 等处若存在导线 T 型接点（一段导线端点落在另一段导线中间）没有 `junction`，补上结点；你的几何自检第 3 项要能抓到这一类。

## 4. 说明文字同步
把 R42 那句改为：`R42 56Ω 熔断电阻与 C40 构成输入 RC：限上电浪涌与短路电流，VIN_F 短路时受控开路；C45 100nF/100V 贴 VIN（Tokmas 手册 p14）`。

## 交付
更新脚本、原理图、报告（开头加「第 5 轮变更」+ 全部自检结果 + 新网表「位号.脚 → 网络」全表）。最后一行回复 `DONE`。
