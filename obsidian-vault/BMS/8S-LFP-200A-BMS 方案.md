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
