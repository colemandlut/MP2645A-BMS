# 画图任务书：子图 04_power_supply，第 4 轮（按 Opus 复核改，接续第 3 轮）

工作目录 `/home/user/MP2645A-BMS`。纪律同第 1–3 轮任务书。**先备份** `cp hardware/04_power_supply.kicad_sch /tmp/draw-backup/04_power_supply.r3.kicad_sch`，
**先跑一遍脚本确认幂等**再改。第 3 轮的版面要求与 8 项自检全部继续有效，本轮改完**全部重跑**。

复核报告：`design/04_power_supply-review-opus.md`（你可以读它的 P0/P1 条目与依据）。本轮只改下面列出的项，P2 除明确列出的外**不要改**（交用户定）。

## P0-1：器件实例缺 `Footprint` 字段（网表封装全空，PCB 放不上件）

每个器件**实例**（不是嵌入库符号）必须带完整字段：`Reference`、`Value`、`Footprint`（`jlc:<封装名>`，与库符号的 Footprint 字段相同）、
`Datasheet`（取库符号的值）、`LCSC`（隐藏）。Footprint/Datasheet/LCSC 隐藏显示。
验收：`kicad-cli sch export netlist --format kicadxml` 里每个 `<comp>` 都有非空 `<footprint>jlc:…</footprint>`，且与库符号一致。

## P1-1 / P1-2：输入串一只 10Ω 抗浪涌电阻 R42

依据（复核报告 P1-1/P1-2）：删 D6 后，800A 短路快关时 BAT+ 尖峰可能超过 LMR16006 VIN 绝对最大 65V；F11 直挂电池，上电给 C40/C42 充电的 I²t（≈0.046A²s）超过 0466001 的熔化 I²t（0.0423A²s），分断能力 50A 也远小于下游短路预期电流。
在 **F11 与 VIN_F 之间**串 R42，与 C40 组成 RC：短路电流 ≤ 5.3A、上电 I²t ≈ 0.002A²s，VIN_F 浪涌被 RC 压住。

```
BAT+ ─ F11 ─ VIN_R ─ R42 10Ω ─ VIN_F ─┬─ C40 ─┬─ C42 ─ U4.VIN（经 VIN_F 标签）
```

| 位号 | 符号名 | 值 | 封装 | LCSC |
|---|---|---|---|---|
| R42 | 1206W4F100JT5E（主代理已取库，`jlc:1206W4F100JT5E`） | 10Ω 1% 1206 | 以库符号 Footprint 字段为准 | C17903（基础库） |

新网络名 `VIN_R`（保险丝后、串阻前）。在图上说明文字里加一句：`R42 10Ω 与 C40 构成输入 RC：限上电浪涌与短路电流，替代已删的 D6`。

## 用户 2026-09-26 13:57 第 2 轮换料（已落 `docs/02-BOM.csv`，本轮必须照做）

| 位号 | 原料 | 新料（符号名 → lib_id `jlc:…`） | 值 | 封装 | LCSC 字段 |
|---|---|---|---|---|---|
| U4 | TI C87080 | **符号仍用 `LMR16006XDDCR`**（Tokmas 件在 EasyEDA 无库，沿用 TI 同名件的符号/封装，引脚已核一致） | LMR16006XDDCR (Tokmas) | 不变 | **C54823941** |
| F11 | Littelfuse 0466001.NRHF C151135 | `JFC1206-1100FS` | 1A 63V | jlc:F1206 | C136343 |
| C42 | 4.7µF/100V 1210 C381466 | `CL31B105KCHNNNE`，**改为两颗并联：C42、C44** | 1µF 100V | jlc:C1206 | C13832 |
| C43 | 22µF/25V 0805 C45783 | `CL10A226MQ8NRNC` | 22µF 6.3V | jlc:C0603 | C59461 |

- U4 的 Tokmas 件 VFB = 0.770V、fsw = 600kHz：33k/10k → 3.31V；图上说明文字里的「700kHz」改成「600kHz（Tokmas）」。
- 上面「可读性」一节里 F11 的值按新料写 `1A 63V`（JDT JFC1206-1100FS），不用再核 Littelfuse 手册。
- C44 与 C42 并排放、同样接 VIN_F–GND，紧挨 U4 的 VIN（布局时就近）。

## 可读性（复核 P2-9，属规则 00 ③，本轮一并改）

- `FB_3V3` 等标签不许直接压在引脚上，必须在短线末端（第 3 轮若已改好就确认一下）；
- U4 的值 `LMR16006XDDCR` 必须紧贴 U4，不能靠近 D7；
- F11 的值写成 `1A 63V`（额定电压依据 `datasheets/C151135_Littelfuse_0466001.NRHF.pdf`，你核一下是否确为 63V，若不是按手册写）。

## 版面小修

- 图名「辅助电源（LMR16006X 直降 3.3V）」和说明文字放回图纸左上角（第 3 轮移到了下方，标题应在上）；说明文字补上 R42 那句。

## 交付
更新脚本、原理图、报告（开头加「第 4 轮变更」+ 全部自检结果 + 新网表的「位号.脚 → 网络」全表）。最后一行回复 `DONE`。
