# 画图任务书：03_balancer 第 2 轮（按 Opus 复核改，限时 30 分钟）

工作目录 `/home/user/MP2645A-BMS`。纪律同 `design/03_balancer-task-draw-r1a.md`。依据：`design/03_balancer-review-opus.md`（可读）与规格书 §8.1c。
**先跑 `hardware/gen/gen_03_balancer.py` 确认幂等**（md5 `9caa8c53fcb304c45472574c5d2f5c59`）再改。

## 要改
1. **P1-1 换料**：D301–D308、D311–D318 由 `jlc:1N5819WS`（C191023）换成 **`jlc:BAT54WSL9`（C22629，值 `BAT54WS`）**，同封装 SOD-323。
   ⚠ 换符号 = 引脚几何可能变（规则 00 ⓪）：从库里读新符号的引脚坐标重新连线，**核对 K/A 方向与原设计一致**（死区「慢开快关」的二极管方向不能变）。
2. **P1-2 换料**：R302–R308 由 100k（C25741）换成 **330k（`jlc:0402WGF3303TCE`，C25778，值 `330k 1%`）**；**R301 保持 100k**。
3. **P2-4 可读性**：C30k 的位号与标签/数值重叠 → 挪开；P 管（Q311–Q318）文字倒置 → 字段角抵消旋转使文字正向；标题栏 rev/date 更新为 `v0.3-draw-r2` / 当天日期。
4. 自检：逐脚核对表与值/LCSC 期望同步更新；新增「二极管 K/A 方向核对」（按规格书 §3.2 网络）。

## 验收
全部自检通过；ERC 本页 0 条；网表与第 1 轮相比**连接 0 差异**（只有 D30x/D31x、R302–R308 的值/LCSC/符号变化）；幂等；PDF 目视。
跑 `python3 -m unittest discover -s tests` 与 `make -C firmware test`。报告加「第 2 轮变更」。最后一行回复 `DONE`。
