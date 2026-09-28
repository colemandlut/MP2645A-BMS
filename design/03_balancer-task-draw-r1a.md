# 画图任务书：子图 03_balancer（开关电容主动均衡），第 1 轮 · 分段 A（共 3 段，每段限时 30 分钟）

你是**画图方**。工作目录 `/home/user/MP2645A-BMS`，全部中文。画 `hardware/03_balancer.kicad_sch`。
**设计依据：规格书 `design/03_balancer-spec.md`（含 §8.1b 用户决定，附录 A 已作废），逐条照画。**

## 0. 纪律（与 02/04/05 页相同，先读样板）
- 样板：`hardware/gen/gen_02_afe.py` 与 `hardware/gen/check_02_layout.py`（13 项自检：几何、跨器件不相交、PDF 原始文字 span 不重叠、网表逐脚核对规格书、标签压引脚/叠标签/字段离位/越框），
  以及 `design/02_afe-task-draw-r1a.md`（纪律全文）。**先读这三个文件**，照它们写 `hardware/gen/gen_03_balancer.py` 与 `hardware/gen/check_03_layout.py`
  （可复制 02 的通用函数；**不许改 02/04/05 的生成器与产物**）。
- 器件只用 `hardware/lib/jlc/jlc.kicad_sym` 的符号（原样复制，顶层名改 `jlc:NAME`）；实例带 Reference/Value/Footprint/Datasheet/LCSC；位号用规格书的 3xx 段（纯数字结尾）。
- 层次路径：根图 uuid `632f74a5-cd8f-58d8-9ac1-1bfbb611d555`，03 页 sheet uuid 从 `hardware/mp2645a-bms.kicad_sch` 里 `Sheetfile "03_balancer.kicad_sch"` 的 sheet 取；03 页文件自身 uuid 保持现值。
- 只改：`hardware/03_balancer.kicad_sch`、`hardware/gen/gen_03_balancer.py`、`hardware/gen/check_03_layout.py`、报告 `design/03_balancer-draw-report.md`（以及知识库写回）。不改库/BOM/docs/根图/其它子图；不跑 `tools/gen_kicad_skeleton.py`、git。
- KiCad 坐标 y 轴向下；端点落 1.27mm 栅格；导线不穿本体、不经过非端点引脚；T 接点放 junction；局部网络名严格照规格书（`VBk`、`Xk`、`DRVk`、`GNk`、`GPk`、`INk`、`CLK_R` 等），网络类要能匹配 `/开关电容主动均衡/X?`、`/开关电容主动均衡/VB?`。
- 接口全局标签：`BAL0..BAL8`、`BAL_CLK`（**本页不用 GND**）。

## 本段（A）要做
1. 生成器框架与自检脚本（从 02 移植，网表逐脚核对表按规格书 §3.2 的 60 个网络写）。
2. 画**第 1–4 节**（k=1..4）的全部器件：半桥 QN/QP、U30k、去耦 C30k、储能 C31k、耦合 C32k、下拉 R30k、死区 R31k/R32k + D30k/D31k、飞电容（k=1..3 的 C33k/C34k，以及跨到第 4 节的一级），以及首级时钟输入（R300、C321、`CLK_R`）。
   版面按规格书 §7 的建议（A3 分两栏，自下而上）预留第 5–8 节位置。
3. 跑 ERC 与自检到已画部分干净；未画部分的标签单脚告警列明。报告写「分段 A 完成情况」与留给 B/C 的清单。

最后一行回复 `DONE`。
