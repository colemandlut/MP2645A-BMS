# 画图任务书：子图 02_afe（MP2797 AFE），第 1 轮 · 分段 A（共 3 段，每段限时 30 分钟）

你是**画图方**。工作目录 `/home/user/MP2645A-BMS`，全部中文。画 `hardware/02_afe.kicad_sch`。
**设计依据：规格书 `design/02_afe-spec.md`（Opus 按 MP2797 手册写，含 §12「用户决定（2026-09-27）」小节，逐条照画）。**
本任务按用户规定拆成 3 段（A/B/C），每段 30 分钟内完成并交付可运行的中间产物；下一段会接着你的脚本继续。

## 0. 纪律（与 04/05 页相同，先读样板）
- 样板：`hardware/gen/gen_05_mcu_comm.py`、`hardware/gen/check_05_layout.py`（8 项自检，含跨器件本体/字段/引脚名不相交、PDF 文字不重叠）、
  `design/05_mcu_comm-task-draw-r1.md`（纪律全文）。**先读这三个文件**，照它们的结构写 `hardware/gen/gen_02_afe.py` 与 `hardware/gen/check_02_layout.py`
  （可以 import 或复制 05 的通用函数；**不许改 04/05 的生成器与产物**）。
- 器件只用 `hardware/lib/jlc/jlc.kicad_sym` 的嘉立创符号（原样复制，只把顶层名改成 `jlc:NAME`；库已统一 passive 引脚与小器件隐藏引脚名，**不要**再改引脚名/类型）。
  实例必须带 Reference/Value/Footprint/Datasheet/LCSC 字段；DNP 件用 `(dnp yes)`。位号用规格书的 2xx 段。
- 层次路径：根图 uuid `632f74a5-cd8f-58d8-9ac1-1bfbb611d555`，02 页 sheet uuid 从 `hardware/mp2645a-bms.kicad_sch` 里 `Sheetfile "02_afe.kicad_sch"` 的 sheet 取；02 页文件自身 uuid 保持现值。
- 只改：`hardware/02_afe.kicad_sch`、`hardware/gen/gen_02_afe.py`、`hardware/gen/check_02_layout.py`、报告 `design/02_afe-draw-report.md`。不要改库/BOM/docs/根图/其它子图；不要跑 `tools/gen_kicad_skeleton.py`、git。
- KiCad 坐标 y 轴向下；所有端点落 1.27mm 栅格；IC 用到的脚引短线 + 标签；T 接点放 junction；导线不穿本体、不经过非端点引脚。

## 本段（A）要做
1. 写好生成器框架与自检脚本（从 05 移植），能生成一张 ERC 可跑的 02 页。
2. 放 **U1 MP2797**：48 脚按规格书 §1 逐脚表全部引出（用短线 + 本页标签/全局标签；未用脚放 NC 标志，按规格书对未用通道的处理）。
3. 画规格书 **§9 电源**（VTOP/REGIN 从 BAT+、外置 NPN、各电源脚去耦）与 **§6 高边驱动**（CHG/DSG/VCP/VMID/PACKP 及其外围）两部分。
4. 跑 `kicad-cli sch erc`、`check_02_layout.py`，把本段已画部分跑到干净（未画部分的标签单脚告警可以暂时存在，报告里列明）。
5. 报告 `design/02_afe-draw-report.md` 写「分段 A 完成情况」：已画哪些位号、脚本结构、剩余给 B/C 的清单。

接口全局标签（本页）：`BAT+ CELL0..CELL8 SRP SRN CHG_G DSG_G FET_MID PACK+ NTC_CELL1 NTC_CELL2 NTC_FET NTC_SHUNT I2C_SCL I2C_SDA AFE_ALERT AFE_WAKE +3V3 GND`。
最后一行回复 `DONE`。
