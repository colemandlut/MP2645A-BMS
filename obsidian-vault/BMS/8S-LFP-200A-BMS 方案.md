---
tags: [BMS, LFP, MPS, 项目]
created: 2026-09-26
repo: colemandlut/MP2645A-BMS
---
# 8S LFP 200A BMS 方案

- 需求：8S 磷酸铁锂、最大 200A、自动均衡、用 MPS 芯片
- 假设：200Ah 电芯；持续放电 200A、充电 100A；同口
- AFE：[[MPS 芯片笔记#MP2797|MP2797]]；均衡：[[MPS 芯片笔记#MP2645A|MP2645A]] ×2 级联
- 功率：高边背靠背 NMOS，每方向 8 颗 80V/1.2mΩ TOLL；200A 通路损耗约 20W，最坏 Tj≈79°C（45°C 环境）
- 分流器 100µΩ：200A→20mV/4W；SCP 800A→80mV
- 保护参数见仓库 `firmware/src/bms_config.h`
- 均衡策略见 [[LFP 均衡要点]]
- 详细文档：仓库 `docs/01-系统设计说明.md`

## 待办
- [ ] 获取 MP2645A 正式数据手册（pre-release），确认 8S 接法（C1~C5 + C4~C8 或 4 节配置）
- [ ] 确认 MP2797 高边驱动能力是否足够驱动 8 并联 MOSFET
- [ ] 确认实际电芯容量
- [ ] 编写 MP2797 寄存器驱动

## v0.2 详细设计（2026-09-26）
- 文档 `docs/03-详细设计.md`；KiCad 10 骨架 `hardware/`（`tools/gen_kicad_skeleton.py` 生成，ERC=0）
- 功率拓扑：BAT+ → F1 → DSG×8 → FET_MID(共源) → CHG×8 → PACK+；两组各 PNP 快关 + 15V 钳位【共源/共漏按 MP2797 手册定】
- 均衡线每根 5A 快熔；采样/均衡分线；GND 单点在分流器电池侧
- 电芯采样串阻：若被动均衡电流流经串阻 → 30Ω 0.1W → 0805
- 预充可选：30Ω（2×15Ω 5W），单次 4.26J，1.5s 超时保护
- MP9486A 若为非同步 buck 必须加续流肖特基（规则 00 ①a）
- 阻塞：数据手册全部被网络拦截；codex(gpt-6-astra) 不可用 → 规则 00c 画图分工待用户裁定

## v0.3（2026-09-26）均衡改为 MP2643 ×7
- 用户指令：MP2645A 买不到 → 用 MP2643（MPS 官网：1 片 ¥19.28 / 10 片 ¥17.25 / 100 片 ¥14.46，库存 3639，运费 $5/单），客供给嘉立创贴片
- 第 k 颗：PGND=BAL(k-1)、CL=BALk、CU=BAL(k+1)；7 个本地地铜岛
- 外围（手册 Table 10/9）：L 2.2µH SLO0618H2R2MTT C216189；CCU/CCL 22µF 25V 0805 C45783；C4V5 1µF；CBST 100nF（值待 MPS 确认）
- RUBC 120k → 1.78A（含容差 ≤2A）；RLBC 150k；R1/R2 = 2M/392k → VCU_LIM 7.32V
- EN/MODE：每颗 2 只光耦 EL3H7(C) C92243（共 14），输出侧由 CL 供电、100k 下拉；MCU 复位即全部停止
- 不照搬手册 Fig.7（EN 接 AFE 被动均衡开关），因我们还要用 MP2797 被动微调
- 固件：边界电荷盈亏 E_k 决定方向（>0 buck 上→下，<0 boost 下→上），相邻两颗不同时开；仿真 90mV→10mV 44 步收敛
- 均衡端子改 2×9 Micro-Fit（每节点 2 针），节点保险丝 7A 2410 C99548
- 成本（元器件，不含 PCB/SMT 费）：10 块 ≈ ¥587/块，100 块 ≈ ¥460/块；MOSFET ×16 ≈ ¥214 最大头，MP2643 ≈ ¥121
- 风险：STM32G0B1 与 4.7µF/100V 1210 嘉立创库存 0；降本候选：Tokmas MOSFET（省 ≈¥118）、CH32V203（省 ≈¥38）
- 工具：tools/jlc_api.py（嘉立创 SMT 料号接口：jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList）、tools/cost.py
