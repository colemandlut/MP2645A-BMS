---
tags: [MPS, 芯片]
updated: 2026-09-27
---
# MPS 芯片笔记

## MP2797
- 7~16 串电池监测保护 AFE，TQFP-48，部分引脚耐压 > 80V
- 双 ADC：电芯电压(16 通道)+片温+4 路 NTC；库仑计独立 ADC
- 高边 NMOS 驱动；DSG 可配置软启动（可省预充）
- OCP/SCP/OVP/UVP/温度保护；I2C 或 SPI，可选 CRC
- 内部被动均衡最大 58mA，可驱动外部均衡管
- 同族：MP2793（4~16 串）、MP2796、MP2787

## MP2645A
- 5 节双向 buck-boost 主动均衡器，单线级联，最多 8 颗（33 节 → 相邻两颗共用 1 节）
- MP2645 最大均衡电流 3.75A；A 版 2026-09 时为 pre-release
- 支持 Li-ion / LFP / 超级电容

## MP2640
- 2 节双向主动均衡器

> 来源：MPS 官网产品页、Mouser、Future Electronics 产品简介（完整手册未获取）

## 立创料号（2026-09-26，来自搜索结果，库存/嘉立创库待核）
- MP2797DFP-0000-T = C18198873
- MP2645A / MP2645：立创、LCSC 均未上架（MP2645A 2026-07-21 发布，QFN-19 4x4）→ 客供/样品
- MP9486AGN-Z = C404013，**非同步迟滞 buck，必须外加续流肖特基**（SS310 C15874），FB≈0.2V 待核
- MP2013AGQ-33-Z = C6096988（QFN-8，40V 150mA Iq 3.3µA）
- 其它：IPT012N08N5 C531199（**Qg=240nC** @VDS=50V/VGS=10V，2026-09-27 按 datasheets/C19626224_Tokmas 手册 p.3 修正，旧值 178nC 有误）；43045-1000 是弯针，立式是 43045-1012 C277725；NCP18XH103F03RB 立创标 B25/50=3380K；0402 100nF 基础料 C1525 只有 16V

## 均衡器可采购性（2026-09-26 实测，嘉立创料号搜索 API）
- MP2645A / MP2645：嘉立创只有「邮寄专用」客供占位料号（C9900296922 等），库存 0 → **买不到，只能客供**
- 用户规定：MP2645A 买不到就用 **MP2643**。但 MP2643 在嘉立创同样只有占位 C9900102770，库存 0，立创商城未搜到
- MPS 官网有 Fastly 反爬，headless 浏览器登录被拦；MP2645A 手册需登录下载（未取得）
- MP2643（手册 Rev1.1 已下载 datasheets/MP2643GR_MPS.pdf）：**2 节**相邻均衡，0.5–2A 电阻设定；QFN-26 4x4；CU 3.9–16V，CL 2.4–4.5V
  - **不是自主均衡**：EN（使能）+ MODE（低=buck 上→下，高=boost 下→上）由主机控制；逻辑参考各自的 PGND（下节电芯负极）
  - 8S 需 7 颗（每对相邻电芯一颗）→ 14 路跨电位控制信号，需电平移位/隔离
  - 外围：电感（LX-SW）、BST 电容、4V5 1µF、LOGIC 接 4V5、CU_FB 分压、LBC/UBC 电流设定电阻
- MP9486A 实为偏 LED 驱动的迟滞 buck（带 DIM，FB 均值 200mV），做 5V 电源可用但非主用途，待评估
- 嘉立创库取回：30/30 符号+封装+3D；**B13B-XH-A 封装间距是 2.54mm（错，JST XH 实为 2.50mm）**

## MP2797 画图前核定（2026-09-27 16:29 JST，Opus 规格书 design/02_afe-spec.md）
- **手册拓扑是共漏**（Fig 26 p.121、Fig 27 p.122）：CHG 管在电池侧源极朝 BAT+，DSG 管在 PACK 侧源极朝 PACK+，FET_MID = 漏极公共点；关断时 CHG 栅拉向 VTOP、DSG 栅拉向 PACKP（p.14–15）。docs/03 写的共源会让 PACK 拉低时顶开 CHG 管 → 01 页 P0，待用户定
- **WDT 不能上拉**（p.24 外部拉高复位芯片，p.48 WDT_RST_EN 默认 1）→ 悬空
- 被动均衡电流走 VC 串阻（Fig 28 p.125，情况 B）；LFP + 33Ω 典型 39mA、最坏 45mA、每只 67mW → 0805 保留（85°C 下 0603 余量 1.22 不够）；docs/03 的「58mA」是手册 4V/20Ω 的数
- SRP 接分流器电池侧（GND 单点）、SRN 接 PACK− 侧；01 页 Net-Tie 把 SRP 与 GND 在焊盘处相连
- 固件：CELL_S_CTRL 必须写 0x7（默认 0xF 会把 C9–C16 判欠压）；开 USE_COMM_CRC；单管导通硬件兜底 175A

## MP2797 02 页第二复核核定（2026-09-27 19:18 JST，独立重推，报告 design/02_afe-review-qwen.md）
- **3V3（脚 26）是输出脚**：p.6 原文 "3.3V voltage output to drive external peripherals. Bypass 3V3 with an external 1µF capacitor"；p.32 意图是 "powers an external MCU"。本设计 AFE_3V3 空载（只挂 C215），MCU 用 04 页 +3V3 —— 合规但偏离意图
- **引脚表跨 p.6–7 两页**：22 VREF / 31 SCL/SCK / 32 SDA/SDI / 33 SDO / 34 GPIO3/nCS 五行在 p.7（只搜 p.6 会漏）
- **绝限（p.7）**：VTOP −0.3…+86V；CHG/DSG/VCP to AGND −0.3…+100V；GPIOHV1 −0.3…+86V；NSHDN −0.3…+9V
- **Table 23（p.127）完整结论**：C13–C16/C46–48 未用电芯通道并到最高实际通道（8S→C8）；WDT/SDO/GPIO1–3/nCS/GPIOHV1/SBYDSG/N-C 全 Float（SBYDSG 原文 "Float this pin if it is not used."）；GPIO1–3/nCS 悬空时寄存器置 20kΩ 内部上拉模式；DSG 不用→Float、PACKP 不用→接 VTOP、VMID 不用→接 VTOP
- **Table 22（p.127）**：CVCP 按 ΣCiss 分 47/68/100nF 三档，100nF 为最大行（6 管并联 Tokmas Ciss 87nF 正好落最大行 → C219 100nF 合规）
- **REGIN 工作电流手册全文无规格**（p.8 仅关断 1µA / 安全模式 23µA）→ 设计的 5mA 是估算值，**样板必须实测**，>5mA 换 BCX56（C24280 已入 BOM）
- **NSHDN（脚 30）**：内部 5MΩ 下拉、VNSHDN_FALL 1V / RISE 2.65V、tDGL 8/4ms → **悬空=永久关断，必须外上拉**；10k→3.3V 分压 3.29V > 2.65V ✓；MCU 开漏 <0.4V < 1V ✓；拉高后等 ≥5ms 才允许 I2C 访问
- **Fig 27 有 D_BATT**（BAT+ 侧钳位稳压管）但 Table 18 必备件清单无对应行——设计缺此件，风险由 01 页 D3 SMDJ33A（钳位 53V）+ F11 覆盖（VTOP 绝限 86V）
- **电芯编号约定**：cell k = 自 BAT− 端起第 k 节（cell 1 邻 BAT−、cell 8 邻 PACK+）；VC0 = cell 1 负极抽头 ≈0V，**不直连 GND 网络**（经 R201 33Ω + D201 3.3V 稳压，保留线束监测与误接保护）
- **FET_MID 关断态 ≈ BAT+−0.5V**（CHG 组体二极管源极朝 BAT+ 钳位）→ VMID≈28.7V、VCP≈43.4V 静态；瞬态（TVS 钳位 53V）各脚均低于绝限
- **15V zener（DZ1/DZ2 MM3Z15）< Table 18 "Recommended 16V"**：对 Tokmas VGS 绝限 ±20V 留 25% 余量，偏保守合规
- **P1 待裁决**：BOM C226 注 "Qg 等效 144nF 超 Table 22" 与规格书 "ΣCiss 87nF" 矛盾；144nF 出处未能在手册静态参数重现（Qg/10V=24nF≠144nF）→ 样板实测 VCP 跌落，不达标贴 C226（→200nF）
- **XH-13A C40669 = 2.50mm 正确**（13 焊盘 x=−15.00…+15.00 实测）；B13B-XH-A C158025 = 2.54mm 错 —— 02 页 J5 已确认选对
- **均衡 45mA 推导**：3.65V/(2×33Ω+Ron)，Ron 取 p.13 最小 15Ω；每只 33Ω 67mW，0805 85°C 降额后 1.5× 余量
