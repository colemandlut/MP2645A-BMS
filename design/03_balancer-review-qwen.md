# 子图 03_balancer 独立复核（review2 / qwen3.8-27b）

- 快照：`review/03-r1/`（03_balancer.kicad_sch md5 `9caa8c53…5d5c59`，与 `hardware/` 工作树逐字节一致，已核）
- 复核方：阿里云 qwen3.8-27b；画图方 DeepSeek、第一复核 Opus，三方不同厂商
- 独立性声明：未读画图方报告（`03_balancer-draw-report.md`、`*-draw-*.out`）、未读第一复核报告、未读生成/自检脚本注释；全部结论从快照 + 规格书 + docs + BOM + 手册 + 05 页源独立重推。
- 输入：`review/03-r1/`（sch / erc.json / netlist.xml / sch.pdf 第 4 页）、`design/03_balancer-spec.md`、`docs/03-详细设计.md` §1/2.4/4、`docs/02-BOM.csv` 均衡段、`datasheets/`（C479060、C5350990、C7394021、C191023、C15008、C163126、C18202166）、`hardware/05_mcu_comm.kicad_sch`（BAL_CLK 源）、`hardware/mp2645a-bms.kicad_pro`（网络类）、`tools/bms_calc.py`（sc_equalizer）。

## 结论汇总

> 待填（P0 / P1 / P2 计数）

## 0 前置检查（断线/死头/悬空、同网多名、GND/CELL）

> 进行中

## 1 逐节推导（k=1..8）

> 进行中

## 2 时钟链与停时钟/复位/上电/卡高状态、飞电容耐压

> 进行中

## 3 器件级核算（Vgs/Rds(on)/耐压/死区直通）

> 进行中

## 4 J6 针位与保险丝

> 进行中

## 5 网络类（BAL_3A）

> 进行中

## 6 均衡电流口径（bms_calc sc_equalizer）

> 进行中

## 7 ① 电容完备性 / ② 封装下探 / ③ 可读性（PDF 第 4 页）/ LCSC 与 BOM 一致性

> 进行中

## 覆盖清单

> 待填
