# 画图任务书：子图 05_mcu_comm（MCU 与通讯），第 1 轮

你是本项目的**画图方**。工作目录 `/home/user/MP2645A-BMS`。全部中文。
画 `hardware/05_mcu_comm.kicad_sch`。**设计依据是规格书 `design/05_mcu_comm-spec.md`（Opus 按手册写的，逐条照画）**，
加上下面「用户决定」一节对规格书「待用户定」项的裁定。

## 0. 纪律（与 04 页完全相同，先读 04 页的成果作样板）

- 样板：`hardware/gen/gen_04_power_supply.py`（生成器）、`hardware/gen/check_04_layout.py`（几何自检）、
  `design/04_power_supply-task-draw-r1.md` … `-r6.md`（04 页 6 轮任务书里积累的全部规则）。**先把这些读一遍**，
  04 页踩过的坑（lib_id 带 `jlc:` 且嵌入符号顶层名 = lib_id、位号「前缀+数字」、实例必须带 Footprint/Datasheet/LCSC 字段、
  1.27mm 栅格、字段角抵消旋转、导线不穿本体/不经过非端点引脚、T 接点要 junction、IC 引脚用短线 + 标签、文字不重叠、
  换符号后引脚几何会变）**一个都不许再犯**。可以把 04 的生成器/自检里通用的部分抽成 `hardware/gen/schlib.py` 共用
  （04 的生成器改成 import 它时，**04 的输出必须逐字节不变**，用 md5 验证；做不到就别动 04，复制一份到 05）。
- **可接续**：生成逻辑写成幂等脚本 `hardware/gen/gen_05_mcu_comm.py`，自检脚本 `hardware/gen/check_05_layout.py`。
- 只改：`hardware/05_mcu_comm.kicad_sch`、`hardware/gen/` 下 05 的脚本（及可选的 schlib.py）、报告 `design/05_mcu_comm-draw-report.md`。
  **不要**改库、BOM、docs、根图、其它子图；**不要**运行 `tools/gen_kicad_skeleton.py`、git。
- 器件只用 `hardware/lib/jlc/jlc.kicad_sym` 里的嘉立创符号（原样复制，只把顶层名改成 `jlc:NAME`），不用 KiCad 官方库。
- 本页层次路径（实例 `instances` 用）：根图 uuid `632f74a5-cd8f-58d8-9ac1-1bfbb611d555`，05 页的 sheet uuid 从
  `hardware/mp2645a-bms.kicad_sch` 里 `Sheetfile "05_mcu_comm.kicad_sch"` 那个 sheet 的 `uuid` 取；05 页文件自身 uuid 保持现值。

## 1. 用户决定（2026-09-27，覆盖规格书的「待用户定」）

| 编号 | 决定 |
|---|---|
| U-1 RS485 | **不画**。接口契约删掉 `RS485_A/RS485_B`；PA2/PA3/PA4 放「无连接」标志（规格书 §1.3 已为它们保留，不挪作他用） |
| U-2 调试口 | **J8 1×6 2.54mm（C492405，DNP）**：3V3/SWDIO/SWCLK/GND/TX/RX（针序按规格书 §4.1），实例加 `DNP` 属性（`(dnp yes)`） |
| U-3 CAN 终端 | 只放 R55 120Ω（默认贴），不做跳线 |
| U-4 SW1 | 用户键（PB12） |
| U-5 CAN 待机 | 接受超标，不加断电 MOS |
| U-6 晶振电容 | **33pF C1562**（C56/C57，符号 `0402CG330J500NT`） |
| U-7 J7 针脚 | 按规格书 §3.6：1 CAN_H / 2 CAN_L / 3 GND / 4 GND |
| U-8 绿灯电阻 | **330Ω C25104**（R60，符号 `0402WGF3300TCE`） |
| U-9 PWR_EN | **删除** |
| L2 共模电感 | C95572（符号 `ACT1210-510-2P-TL00`），**DNP**；R56/R57 0Ω 旁路默认贴 |

接口契约（全局标签）：`I2C_SCL I2C_SDA AFE_ALERT AFE_WAKE BAL_CLK PRECHG_EN CAN_H CAN_L +3V3 GND`。
器件表以规格书 §6 为准（去掉 JP1、U9、D8、C60、R61–R63 这些 RS485/跳线方案件）。

## 2. 必须逐项核对并写进报告（规则 00 ①①a）

- 规格书 §7 的每颗 IC 外围件点名清单，逐件在你的网表里点名（位号 + 网络）。
- 规格书 §1.3 的 48 脚逐脚表，逐脚在网表里核对（用到的脚接对网络、未用脚放 NC 标志）。
- 规格书 §8.2 电容完备性：每个 VDD/VDDA/VBAT 脚就近去耦。
- **极性件**：LED1/LED2（C84256，符号名 `FC-2012HRK-620D`，规格书说它 1 脚是阴极）与 LED3（C2297，1 脚是阳极）按**引脚名**接，
  打开符号和 `jlc.pretty` 里的封装核对极性，写进报告。
- 差分对 CAN_H/CAN_L 顺序：J7 → U8（ESD）→ L2/R56/R57 → U7（规则 0c），网络名按规格书（含 L2 与收发器之间一段的命名）。

## 3. 版面（规则 00 ③）

按规格书 §9：从左到右 电源/时钟/复位 → MCU → CAN/调试/LED/按键；U6 每个用到的脚引短线 + 标签；
去耦电容靠近各自 VDD 脚成列排；晶振与负载电容一组；CAN 链一行从右到左或左到右连续排列，差分对两根线平行。
标题「MCU 与通讯（CH32V203C8T6 + CAN）」和一段说明文字放左上角。

## 4. 验收（自己跑到满足再交）

1. `kicad-cli sch erc --format json --severity-all --output /tmp/erc05.json hardware/mp2645a-bms.kicad_sch`：05 页 0 条；
   跨页的 `isolated_pin_label`/`global_label_dangling`（02/03 页未画导致对端不存在的全局标签，如 I2C_SCL、BAL_CLK 等）单独列出说明，不算本页问题。
2. `kicad-cli sch export netlist --format kicadxml`：05 页每个器件 Footprint/LCSC 非空，无 `Pad??`；逐脚表全部核对。
3. `python3 /tmp/pcbws/scripts/sch_conn.py hardware/mp2645a-bms.kicad_sch`：②③ 的 P0 = 0、同网多名 = 0、死头 = 0。
   （若 `/tmp/pcbws` 不存在：`mkdir -p /tmp/pcbws && cp -r /root/.claude/skills/synced/*/pcb-workflow/scripts /tmp/pcbws/`；拷不了就跳过并说明。）
4. `check_05_layout.py`：导线不穿本体、不经过非端点引脚、T 接点有 junction、文字 bbox 不重叠（pymupdf）。
5. PDF 渲 PNG（dpi≥200）自己目视。
6. 幂等（跑两次 md5 相同）；若改了 04 的生成器，04 输出 md5 不变。

## 5. 交付
脚本、原理图、报告（① 位号对照 ② 外围件点名 ③ 48 脚逐脚核对 ④ 极性核对 ⑤ 自检结果 ⑥ 建议）。最后一行回复 `DONE`。
