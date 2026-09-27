# 画图任务书：02_afe 第 1 轮 · 分段 B（限时 30 分钟，接续分段 A）

工作目录 `/home/user/MP2645A-BMS`。纪律与依据同分段 A 任务书 `design/02_afe-task-draw-r1a.md`（全部沿用），规格书 `design/02_afe-spec.md`（含 §12.1b 用户决定）。
**先读你上一段的报告 `design/02_afe-draw-report.md`（§5 给 B/C 的清单）**，然后**先跑一遍 `hardware/gen/gen_02_afe.py` 确认幂等**（当前产物 md5 `079bbe7f6f2101937166b8b73554f160`），从脚本末尾的版面分区注释处续画。
注意：主代理已把规格书/BOM 里的 `C219B` 全部改名为 `C226`（与你分段 A 一致）。

## 本段（B）要做
1. 规格书 **§4 电芯采样 RC**（CELL0..CELL8 → VC0..VC8 的串阻 + 电容，8 只 C 按规格书；本页局部标签名严格照规格书，网络类 `*/VC?` 要能匹配上）。
2. 规格书 **§5 电流采样 SRP/SRN**（滤波 RC、`SRP_F`/`SRN_F` 等局部标签名照规格书，KELVIN 网络类要能匹配）。
3. 规格书 **§10 J5 采样端子**（C40669，针脚：1 NTC_CELL1 / 2 GND / 3 NTC_CELL2 / 4 GND / 5–13 CELL0–CELL8）。
4. 同步扩 `check_02_layout.py` 的 `PART_EXPECT` / 逐脚核对表，覆盖本段新增件。
5. 跑 ERC 与全部自检（9 项）到干净；跨页/留给 C 段的标签单脚告警列明。报告追加「分段 B 完成情况」与留给 C 的清单。

最后一行回复 `DONE`。
