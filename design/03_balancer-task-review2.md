# 独立复核任务书：子图 03_balancer（开关电容主动均衡）

你是**第二复核方 review2**（阿里云 qwen3.8-27b；画图方 DeepSeek、复核方 Opus 各为不同厂商）。报告写到 `design/03_balancer-review-qwen.md`。只读不改工程文件；报告写到本任务指定的文件（**必须落盘，开工先建报告骨架、边查边写**）。
工作目录 `/home/user/MP2645A-BMS`，全部中文。**KiCad 封装与原理图坐标 y 轴向下**（y 为正 = 下方）。

## 纪律
- **不要读**画图方报告（`design/03_balancer-draw-report.md`、`*-draw-*.out`）与生成/自检脚本注释；独立重推。
- 输入：快照 `review/03-r1/`（`03_balancer.kicad_sch`、`erc.json`、`netlist.xml`、`sch.pdf`：03 页在 PDF 第 4 页）、
  规格书 `design/03_balancer-spec.md`（**它本身也要被质疑**，含 §8.1b 用户决定：死区网络、只接 100k 下拉、首级交流耦合 VB0 不接 GND、每节 100µF 本地储能、线束保险丝暂不加=已知风险、BAL 保险丝保持 C163126 1206）、
  `docs/03-详细设计.md` 第 1、2.4、4 节、`docs/02-BOM.csv` 均衡段、手册（AO3416 C479060、AO3415A C5350990、74LVC1G17 C7394021、1N5819WS C191023、C15008、C163126、C18202166 J6 等，在 `datasheets/`）、05 页 BAL_CLK 源（`hardware/05_mcu_comm.kicad_sch`：PA8 + R52 100k 下拉）。
- 可自己跑 `kicad-cli`（在 `hardware/` 下对 `mp2645a-bms.kicad_sch`，输出写 /tmp）。
- 核约束要问「串在哪、并在哪、电流走哪条路」，算最坏工况；推导链上游前提也要核。

## 必查
- ⓪ 断线/死头/悬空；⓪b 同网多名；本页无 GND、无 CELL* 网络。
- 逐节（k=1..8）推一遍：UDk 的 VCC/GND 接哪两个节点；半桥 QN/QP 的 S/D/G；死区网络方向（慢开快关，二极管极性、谁开谁关）；输入耦合电容与 100k 下拉；飞电容 Xk–X(k+1)；本地储能与去耦跨本节。
- 时钟链：BAL_CLK → R300/C321 → 第 1 级 → 逐级耦合；**停时钟、MCU 复位（PA8 高阻 + R52）、上电、时钟卡高**时各级最终状态，飞电容最大承受电压是否 ≤ 6.3V。
- 每管 Vgs 在 2.5–3.65V 驱动下的导通电阻与电流能力；直通与死区估算；器件耐压（每管只承受一节）。
- J6（C18202166）焊盘 n ↔ BAL(n−1)、焊盘 10 空；按封装焊盘实测坐标核；F300–F308 各接对应 BAL 节点。
- 网络类：网表里 `Xk`、`VBk`、`BALk` 是否属 BAL_3A（`hardware/mp2645a-bms.kicad_pro`）。
- 均衡电流 0.16A@100mV 口径（`tools/bms_calc.py sc_equalizer`）的前提与算式。
- ① 电容完备性、② 封装下探、③ 可读性（目视 PDF 第 4 页）；LCSC 与 BOM 一致。

## 输出
`P0 / P1 / P2`，每条：位号 + 引脚/网络 + 依据（手册页码或算式）；附覆盖清单。时间不够按上面顺序，后面的写「未核」。
