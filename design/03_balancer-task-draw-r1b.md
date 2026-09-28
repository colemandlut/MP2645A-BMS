# 画图任务书：03_balancer 第 1 轮 · 分段 B（限时 30 分钟，接续分段 A）

工作目录 `/home/user/MP2645A-BMS`。纪律与依据同 `design/03_balancer-task-draw-r1a.md`，规格书 `design/03_balancer-spec.md`（§8.1b 用户决定）。
**先读 `design/03_balancer-draw-report.md` 给 B 的清单，先跑 `hardware/gen/gen_03_balancer.py` 确认幂等**，从脚本末尾续画。

## 本段（B）要做
1. 画**第 5–8 节**（k=5..8）全部器件与剩余飞电容（C33k/C34k 到 k=7）。
2. 画 **J6**（C18202166，按规格书 §4：焊盘 n 接 BAL(n−1)，焊盘 10 空放 NC）与 **F300–F308**（F30k 接 BALk）。
3. 同步扩自检的逐脚核对表；ERC 与自检跑到干净；报告追加「分段 B 完成情况」。

最后一行回复 `DONE`。
