# 子图 05_mcu_comm 独立复核报告（review2 / qwen3.8-max）

- 复核方：review2（阿里云 qwen3.8-max，规则 00c 第 6 泳道）
- 日期：2026-09-27（JST）
- 输入：`review/05-r1/`（05_mcu_comm.kicad_sch、erc.json、netlist.xml、sch.pdf 第 6 页）、`design/05_mcu_comm-spec.md`、`docs/03-详细设计.md` §6、`docs/02-BOM.csv`、`datasheets/`
- 纪律：未读画图方报告与生成脚本注释，独立重推。
- 状态：**进行中**（每核完一类即追加；最后更新见各节）

## P0（必须改）

（暂无——已完成类目未发现 P0）

## P1（应该改）

1. **CAN_H_X / CAN_L_X 网络类仍是 Default，未加入 CAN_DIFF**（规格书 X-3 未落实）。
   - 依据：netlist.xml `net code=3 "/MCU 与通讯/CAN_H_X" class="Default"`、`net code=4 CAN_L_X class="Default"`；而 `CAN_H`/`CAN_L` 均为 `class="CAN_DIFF"`。
   - 影响：PCB 里收发器侧（R56/R57/L2→U7.6/7）这段差分线不享受 CAN_DIFF 的差分对/120Ω 规则，规则 0c「J7→U8→L2/R56/R57→U7 直通道」在最后一段失效。
   - 改法：`tools/gen_kicad_skeleton.py` 的 CAN_DIFF 匹配名单加 `CAN_H_X`、`CAN_L_X`（或改为前缀匹配 `CAN_*`），并同步 `.kicad_pro` 后重跑 ERC。属主代理/工具泳道，跨页事项。

2. **【已知待改项，用户已定】R55 120Ω 终端未串 JP1 跳线**。
   - 现状：netlist `CAN_H: …R55.2…`、`CAN_L: R55.1…`，R55 直接并在 J7 侧终端上，无 JP1。
   - 用户 2026-09-27 决定：CAN 终端改为 R55 串 JP1 跳线可选。本快照（05-r1）未画，按任务书报为已知待改项，不计画图方差错；下一轮需验证 JP1（C492401+C100114，扩展库）落地与 BOM/上料费影响。

3. **【跨页待核】AFE_WAKE / AFE_ALERT / I2C 上拉全部依赖 02 页，02 页目前是骨架、无任何器件**。
   - 现状：netlist 中 `AFE_WAKE` 只有 U6.41 一个节点、`AFE_ALERT` 只有 U6.40、`I2C_SCL/SDA` 只有 U6.42/43；`hardware/02_afe.kicad_sch` 仅有一条文字注释含 "AFE_WAKE"（第 202 行），无 R_WAK/R_ALT/R_I2C 实体。ERC 的 4 条 isolated_pin_label 警告（I2C_SDA/I2C_SCL/AFE_WAKE/AFE_ALERT）即由此而来。
   - 安全态后果：若 02 页最终没画 R_WAK 10k 上拉到 **+3V3（本板 buck 轨，X-4）**，MCU 复位时 PB5 高阻、NSHDN 无确定电平，「AFE 不因 MCU 复位而关断」的安全态不成立。
   - 05 页本身符合规格书 §1.3（直连、不放电阻），故不算 05 页差错；列为跨页接口 P1 待核项，02 页画图后必须复查。

## P2（建议）

1. **全部符号引脚电气类型均为 passive**（netlist 所有节点 `pintype=passive`），ERC 无法做输出冲突/方向检查。jlc 库通病，非 05 页独有；建议主代理在库层面择机修 U6/U7 关键脚（输出/电源）类型。
2. **PB4 复用注意（待手册确认后定级）**：AFE_ALERT 用 PB4。若 CH32V203 复位后 PB4 默认为 NJTRST（STM32F103 兼容脚位），固件需先做 SWJ/remap 配置才能当普通 EXTI 输入用。规格书 §1.3 未提及此点。→ 见「①a IC 外围」核实结果（下文）。

---

# 分项核查明细（按任务书优先顺序）

## ⓪/⓪b 连通性（已核 ✓）

- **ERC**：`/MCU 与通讯/` 页 violations 为空（erc.json）。根图 5 条 warning 均为 isolated_pin_label：BAT+（01 页骨架侧）、I2C_SDA、I2C_SCL、AFE_WAKE、AFE_ALERT——后 4 条是 05 页跨页接口标签只接 1 脚，因 01–03 页还是骨架，属预期（已列 P1-3）。ignored_checks（single_global_label、four_way_junction 等）与既往各页一致。
- **断线/死头**：05 页所有网络节点数 ≥2（单脚全局标签除外，见上）。无悬空线段类告警。
- **NC 标志**：netlist `unconnected-*` 共 20 个 = U6 的 19 个 NC 脚（2,3,4,10,12–22,38,39,45,46）+ U7.5 Vref，kicad_sch 内 no_connect 标志 20 个一一对应（另 1 个 U4.4 SHDN 属 04 页）。全部 NC 脚都有「无连接」旗标，无裸悬空 ✓。
- **⓪b 同网多名 / 异网同名**：无。`CAN_H` 与 `CAN_H_X`、`CAN_L` 与 `CAN_L_X` 是有意分隔（中间串 L2/R56、R57），不是命名事故；GND、+3V3 全工程唯一（05 页与 04 页 +3V3 轨经 L1.2/C43.2 连通，正确同网）。
- **RS485 残留**：netlist 无任何 RS485 网络/器件，05 页 kicad_sch 无 RS485 标签 ✓（用户已定 U-1=不画）。
- **CAN_TXD 标签 ×3**：对应 U6.33、U7.1、R53.1 三个节点各自挂标签，同一网络，非冗余标注 ✓。

## 48 脚逐脚核对（已核 ✓）

以 netlist pinfunction + kicad_sch 独立重推，对照 CH32V203C8T6 LQFP48 脚位与规格书 §1.3：

| 脚 | 名称 | 实际连接（netlist） | 判定 |
|---|---|---|---|
| 1 | VBAT | +3V3，C50 100nF 就近 | ✓ |
| 2–4 | PC13/14/15 | NC+旗标 | ✓ |
| 5 | OSC_IN | HSE_IN：Y1.1 + C56 33pF→GND | ✓ |
| 6 | OSC_OUT | HSE_OUT：Y1.3 + C57 33pF→GND | ✓ |
| 7 | NRST | C58 100nF→GND，无上拉/按键（U-4 用户已定） | ✓ |
| 8 | VSSA | GND | ✓ |
| 9 | VDDA | +3V3，C51 100nF | ✓ |
| 10 | PA0 | NC（规格书：非 FT，不放 AFE_ALERT） | ✓ |
| 11 | PA1 | PRECHG_EN（全局）+ R51 100k→GND | ✓ |
| 12–14 | PA2/3/4 | NC+旗标（RS485 不画，脚位保留） | ✓ |
| 15–22 | PA5–7/PB0–2/PB10–11 | NC+旗标 | ✓ |
| 23 | VSS_1 | GND | ✓ |
| 24 | VDD_VIO_1 | +3V3，C52 100nF | ✓ |
| 25 | PB12 | KEY：SW1.1/2，SW1.3/4→GND | ✓ |
| 26 | PB13 | LED1_K→R58 1k→LED1 阴极 | ✓ |
| 27 | PB14 | LED2_K→R59 1k→LED2 阴极 | ✓ |
| 28 | PB15 | LED3_K→R60 330Ω→LED3 阴极 | ✓ |
| 29 | PA8 | BAL_CLK（全局）+ R52 100k→GND | ✓ |
| 30 | PA9 | DBG_TX→J8.5 | ✓ |
| 31 | PA10 | DBG_RX→J8.6 | ✓ |
| 32 | PA11 | CAN_RXD→U7.4(R) | ✓ |
| 33 | PA12 | CAN_TXD→U7.1(D)+R53 10k→+3V3 | ✓ |
| 34 | PA13 | SWDIO→J8.2 | ✓ |
| 35 | VSS_2 | GND | ✓ |
| 36 | VDD_2 | +3V3，C53 100nF | ✓ |
| 37 | PA14 | SWCLK→J8.3 | ✓ |
| 38/39 | PA15/PB3 | NC+旗标 | ✓ |
| 40 | PB4 | AFE_ALERT（全局，直连） | ✓（复用注意见 P2-2） |
| 41 | PB5 | AFE_WAKE（全局，直连，上拉在 02 页） | ✓（P1-3） |
| 42 | PB6 | I2C_SCL（全局，直连） | ✓ |
| 43 | PB7 | I2C_SDA（全局，直连） | ✓ |
| 44 | BOOT0 | R50 10k→GND | ✓ |
| 45/46 | PB8/PB9 | NC+旗标（PB8 按规格书留 CAN_STB 候选） | ✓ |
| 47 | VSS_3 | GND | ✓ |
| 48 | VDD_VIO_3 | +3V3，C54 100nF | ✓ |

- 统计：电源/地 9 + 时钟/复位/启动 4 + 已用 GPIO 16（NC 19）= 48，账目闭合 ✓。
- **复用关系**：I2C1=PB6/7（42/43 脚）、CAN1=PA11/12（32/33 脚）、TIM1_CH1=PA8（29 脚）、USART1=PA9/10（30/31 脚）、SWD=PA13/14（34/37 脚），全部落在 CH32V203 默认复用脚位，无需 remap（PB4 待手册确认，见 ①a）。
- **J8 针序**：1=+3V3、2=SWDIO、3=SWCLK、4=GND、5=DBG_TX、6=DBG_RX，`(dnp yes)` ✓ 与规格书 §4.1 及用户决定一致。

## 安全态（05 页部分已核 ✓，跨页部分见 P1-3）

复位/高阻时各执行器入口电平（独立重推算式）：

| 信号 | 电阻 | 复位态电平 | 核算 |
|---|---|---|---|
| BAL_CLK（PA8，FT 脚漏电 ≤3µA） | R52 100k 下拉 | 低 → 均衡停 | 并上 03 页 1M（尚未画）后 ≈91k，3µA×91k=0.27V，低于 LVC1G17 类缓冲 VT−（约 0.6V 量级）✓ |
| PRECHG_EN（PA1，漏电 ≤1µA） | R51 100k 下拉 | 低 → 预充断 | 1µA×100k=0.1V ✓ |
| CAN_TXD（PA12） | R53 10k 上拉 | 高 → 总线隐性 | ✓（HVD 手册 D 脚弱偏置需外加 1k–10k，待手册原文复核，见 ①a） |
| AFE_WAKE（PB5） | 本页无电阻 | 依赖 02 页 R_WAK | **当前无确定电平**（P1-3）；固件侧 PB5 必须开漏（规格书 X-5③） |
| LED1–3 | 灌电流接法 | 高阻 → 灭 | ✓ |
| KEY（PB12） | 内部上拉 | 输入，无执行器语义 | ✓ |

「复位即停」三项（均衡时钟、预充、CAN 隐性）在 05 页范围内成立 ✓。

## LCSC 字段与规格书 §6 器件表一致性（已核 ✓）

32 个器件实例逐一比对（Value/LCSC/封装/DNP）：U6 C3001172、U7 C55259679、U8 C2687131、Y1 C9002、L2 C95572(dnp yes)、J7 C7429634、J8 C492405(dnp yes)、SW1 C318884、LED1/2 C84256、LED3 C2297、C50–C54/C58/C59 C1525、C55 C19666、C56/C57 C1562、R50/R53 C25744、R51/R52 C25741、R54/R56/R57 C17168、R55 C22787(0603)、R58/R59 C11702、R60 C25104 —— **全部与规格书一致，无错料号、无漏 DNP** ✓。
（`docs/02-BOM.csv` 的一致性另见「字段/BOM」节。）

## ①a IC 外围（进行中）

（待写：CH32 电源/NRST/BOOT0/HSE、HVD Rs/Vref/VCC 去耦、PESD2CAN 引脚、Y1 CL、L2/R56/R57——手册逐项点名）

## 极性件（待核）

## ① 电容完备性（待核）

## ③ 可读性（待核，PDF 第 6 页目视）

## ② 封装下探（待核）

## 字段/BOM 一致性（待核 docs/02-BOM.csv）

## 覆盖清单（随进度更新）

| 器件 | 状态 |
|---|---|
| U6 CH32V203C8T6 | 48 脚连接已核对无问题（复用/PB4 细节待 ①a） |
| U7 SN65HVD230M | 连接已核（8 脚全对）；Vref NC、Rs 0Ω 依据待手册 |
| U8 PESD2CAN | 连接已核（1=H,2=L,3=GND）；引脚定义待手册 |
| Y1 12MHz | 连接已核（1/3 晶振、2/4 GND）；CL/脚位待手册 |
| L2（DNP）/R56/R57 | 连接已核（1–4 串 H、2–3 串 L、0Ω 并联旁路）；绕组定义待手册 |
| J7/J8/SW1 | 连接已核 ✓；SW1 内部通断待手册 |
| LED1/2/3、R58–R60 | 连接已核 ✓；实物极性待手册（接反=P0） |
| C50–C59、R50–R57 | 连接/值/料号已核 ✓；容值依据待 ① |
| 跨页接口 | 见 P1-3 |
