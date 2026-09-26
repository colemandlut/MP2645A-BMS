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
