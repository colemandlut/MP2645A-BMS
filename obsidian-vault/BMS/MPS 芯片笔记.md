---
tags: [MPS, 芯片]
updated: 2026-09-26
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
