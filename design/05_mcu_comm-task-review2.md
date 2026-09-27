# 独立复核任务书：子图 05_mcu_comm（MCU 与通讯）

你是**第二复核方 review2**（规则 00c 第 6 泳道，阿里云 qwen3.8-27b；画图方 DeepSeek、复核方 Opus 各为不同厂商）。只读不改工程文件；报告写到 `design/05_mcu_comm-review-qwen.md`（**必须落盘**）。
工作目录 `/home/user/MP2645A-BMS`，全部中文。

## 纪律
- **不要读**画图方的报告（`design/05_mcu_comm-draw-report.md`、`*-draw-*.out`）和生成脚本注释；独立重推。
- 输入：快照 `review/05-r2/`（`05_mcu_comm.kicad_sch`、`erc.json`、`netlist.xml`、`sch.pdf`，05 页在 PDF 第 6 页）、
  设计规格书 `design/05_mcu_comm-spec.md`（Opus 按手册写，**它本身也要被你质疑**：前提对不对、手册页码是否支持结论）、
  用户决定（`docs/03-详细设计.md` 第 6 节、`docs/02-BOM.csv` MCU 段：RS485 不画、调试口 J8 1×6 2.54 DNP、CAN 待机超标接受、晶振 33pF、绿灯 330Ω、删 PWR_EN、
  CAN 终端为 R55 串 JP1 跳线可选（用户 2026-09-27，本快照已画））、数据手册 `datasheets/`。
- 可以自己跑 `kicad-cli`（在 `hardware/` 下对 `mp2645a-bms.kicad_sch`，输出写 /tmp）。
- 核约束要问「串在哪、并在哪、电流走哪条路」，算最坏工况；推导链上游的前提也要核。

## 坐标约定
- **KiCad 封装与原理图坐标 y 轴向下**（y 为正 = 下方）；判断焊盘方位时先换算，否则会把上下看反。

## 必查
- ⓪ 断线/死头/悬空（ERC、网表 `unconnected-*`）；⓪b 同网多名。
- ①a 每颗 IC 按手册典型应用逐件点名：U6 CH32V203C8T6（`datasheets/C3001172_*.pdf`：电源脚、VDDA、VBAT、NRST、BOOT0、HSE）、
  U7 HGSEMI SN65HVD230M（`datasheets/C55259679*.pdf`：Rs、Vref、VCC 去耦）、U8 PESD2CAN、Y1（CL 与负载电容算式）、L2（DNP）/R56/R57。
- 48 脚逐脚：网表里每个用到的脚接对网络、未用脚有 NC 标志；外设复用关系（I2C1 PB6/7、CAN1 PA11/12、TIM1_CH1 PA8、USART1 PA9/10、SWD PA13/14）按手册复用表核。
- ① 电容完备性、② 封装下探、③ 可读性（目视 PDF 第 6 页）。
- 极性件：LED1/LED2（C84256，符号 `FC-2012HRK-620D`）、LED3（C2297）按符号引脚名与封装极性核，接反 = P0。
- 安全态：MCU 复位/高阻时 BAL_CLK、PRECHG_EN、CAN TXD、AFE_WAKE 的电平（R51/R52/R53、02 页 R_WAK）是否满足「复位即停」。
- 跨页接口：全局标签名与契约一致（`I2C_SCL I2C_SDA AFE_ALERT AFE_WAKE BAL_CLK PRECHG_EN CAN_H CAN_L +3V3 GND`），无 RS485 残留。
- LCSC 字段与 `docs/02-BOM.csv` 一致，封装与库一致。

## 输出格式
`P0 / P1 / P2` 三档，每条：位号 + 引脚/网络 + 依据（手册页码或算式）。附**覆盖清单**（逐器件、逐外围件「已核对无问题」或问题编号）。

## 时间限制（上一次 60 分钟超时、没留下报告）
- **开工第一步先建报告文件**（标题 + 空的 P0/P1/P2/覆盖清单小节），**每核完一类就把结论追加写进去**，不要等全部查完才写。
- 优先顺序：⓪/⓪b 连通 → 48 脚逐脚 → ①a IC 外围 → 极性件 → 安全态 → ① 电容 → ③ 可读性 → ② 封装。时间不够时后面的写「未核」。
