# 画图任务书：02_afe 第 1 轮 · 分段 C（限时 30 分钟，接续分段 B，收尾）

工作目录 `/home/user/MP2645A-BMS`。纪律与依据同 `design/02_afe-task-draw-r1a.md`，规格书 `design/02_afe-spec.md`（含 §12.1b 用户决定）。
**先读 `design/02_afe-draw-report.md` §6 给 C 的清单**，**先跑 `hardware/gen/gen_02_afe.py` 确认幂等**（md5 `d92a9e7589aff4462ca441d922095520`），再续画。
（`C219B`→`C226` 已由主代理在 BOM/规格书/docs 同步，不用再管。）

## 本段（C）要做
1. 规格书 **§7 NTC ×4**（R216–R219 等上拉/网络，C222–C225 为 **DNP**，NTC_CELL1/2 来自 J5 线束探头，NTC_FET/NTC_SHUNT 到 01 页）。
2. 规格书 **§8 通讯与中断**：I2C 上拉 R_I2C 两只（本页）、xALERT → `AFE_ALERT`（R_ALT **100k 下拉**）、NSHDN → `AFE_WAKE`（R_WAK **10k 上拉到 +3V3**）、WDT **悬空放 NC**、R222 沿用 `output` 形状等（按你 §6 清单）。
3. 规格书 §11.3 版面收尾：标题「MP2797 采集与保护」+ 一段说明文字放左上角；全页无重叠、无越界。
4. **全页验收**：`check_02_layout.py` 9 项全过（PART_EXPECT 覆盖全部器件）；ERC 本页 0 条，跨页 `isolated_pin_label` 只允许对端在 01/03 页的（逐条列明）；
   05 页的 `I2C_SCL/I2C_SDA/AFE_ALERT/AFE_WAKE` 此后应不再是单脚；网表每个器件 Footprint/LCSC 非空；规格书 §13 自检清单逐条打勾；PDF 渲 PNG 目视。
5. 报告追加「分段 C / 第 1 轮完成」：全页位号总表（新位号 ↔ BOM）、外围件点名、48 脚核对结论、自检结果、建议。

最后一行回复 `DONE`。
