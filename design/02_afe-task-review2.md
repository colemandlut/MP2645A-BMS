# 独立复核任务书：子图 02_afe（MP2797 AFE）

你是**第二复核方 review2**（阿里云 qwen3.8-27b；画图方 DeepSeek、复核方 Opus 各为不同厂商）。报告写到 `design/02_afe-review-qwen.md`。只读不改工程文件；报告写到本任务指定的文件（**必须落盘，开工先建报告骨架、边查边写**）。
工作目录 `/home/user/MP2645A-BMS`，全部中文。**KiCad 封装与原理图坐标 y 轴向下**（y 为正 = 下方）。

## 纪律
- **不要读**画图方报告（`design/02_afe-draw-report.md`、`*-draw-*.out`）与生成/自检脚本注释；独立重推。
- 输入：快照 `review/02-r1/`（`02_afe.kicad_sch`、`erc.json`、`netlist.xml`、`sch.pdf`：02 页在 PDF 第 3 页）、
  规格书 `design/02_afe-spec.md`（**它本身也要被质疑**，含 §12.1b 用户决定）、`docs/03-详细设计.md` 第 1–3 节、`docs/02-BOM.csv` AFE 段、
  手册 `datasheets/C18198873_MPS_MP2797DFP-0000-T.pdf`（Figure 26/27/28、Table 18/22、引脚表、电气特性）及其它器件手册。
- 可自己跑 `kicad-cli`（在 `hardware/` 下对 `mp2645a-bms.kicad_sch`，输出写 /tmp）。
- 核约束要问「串在哪、并在哪、电流走哪条路」，算最坏工况（电压应力、功耗、降额）；推导链上游前提也要核。

## 必查
- ⓪ 断线/死头/悬空；⓪b 同网多名。
- MP2797 48 脚逐脚：网表网络与手册引脚功能一致；未用 VC/NTC/GPIO 通道按手册处理；WDT 悬空；xALERT 下拉；NSHDN 上拉到本板 +3V3。
- ①a 按 Figure 27 / Table 18 逐件点名外围件（VTOP/REGIN 从 BAT+、外置 NPN、REGIN/VREF/CREG/VCP/VMID/PACKP、SRP/SRN 滤波、NTC 上拉、电芯 RC）。
- 电芯采样 RC：被动均衡电流路径（Figure 28）、串阻功耗与封装；CELL 线与均衡线（03 页 BAL*）分开、本页无 BAL* 网络。
- 高压耐压：接 BAT+/VTOP/PACKP/VMID/VCP 的每颗器件耐压与降额；HV_SIG 网络。
- 极性件（D201、Q201 NPN、电解/钽若有）引脚与封装核对。
- J5 针脚（1 NTC_CELL1/2 GND/3 NTC_CELL2/4 GND/5–13 CELL0–8）与封装实测 2.50mm。
- 跨页接口：`BAT+ CELL0..8 SRP SRN CHG_G DSG_G FET_MID PACK+ NTC_* I2C_* AFE_ALERT AFE_WAKE +3V3 GND`；与 05 页连接（I2C/ALERT/WAKE 现在应多脚）；01 页未画（6 条单脚告警预期）。
- ① 电容完备性、② 封装下探、③ 可读性（目视 PDF 第 3 页）。LCSC 与 BOM 一致，DNP 件标注正确。

## 输出
`P0 / P1 / P2`，每条：位号 + 引脚/网络 + 依据（手册页码或算式）；附覆盖清单。时间不够时按上面顺序，后面的写「未核」。
