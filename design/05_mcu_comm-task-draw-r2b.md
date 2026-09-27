# 画图任务书：05_mcu_comm 第 2 轮·接续（前任跑满 1 小时超时，没写报告）

工作目录 `/home/user/MP2645A-BMS`。原任务书：`design/05_mcu_comm-task-draw-r2.md`（逐条核对哪些已落实）；纪律同 `design/05_mcu_comm-task-draw-r1.md`。

## 前任状态（主代理核查，git 提交「05 页第 2 轮中间产物」）
- `hardware/gen/gen_05_mcu_comm.py` 已改：JP1（C492401）+ 本页网络 `CAN_TERM` 已加，网表核对正确（CAN_TERM = {JP1.1, R55.1}，R55.2 → CAN_H，JP1.2 → CAN_L）。
- `hardware/gen/check_05_layout.py` 新增了第 [6] 类检查（字段压本体），现在只剩 2 条：
  `[6] J7 字段「Reference」…压在本体上`、`[6] J7 字段「Value」…压在本体上`。
- ERC：本页 0 条（根图 5 条跨页 isolated_pin_label，01/02 页未画，正常）。
- 报告 `design/05_mcu_comm-draw-report.md` 还没加「第 2 轮变更」。

## 要做
1. **先跑一遍脚本确认幂等**（md5 应为 `6cfdbb5726dccee353b7a168a773d39b`）。
2. 修 J7 的 Reference/Value 位置（挪到本体外，别压线/别压其它文字）。
3. 对照原任务书第 1 节逐条确认已落实（P1-3 a/b/c 三处重叠、P2 可读性小项、L2 Value 去掉「(DNP)」等），没做的补上。
4. 原任务书第 2 节验收全部重跑，写报告（「第 2 轮变更」+ 自检结果 + 与第 1 轮网表的差异，差异应只有 JP1/CAN_TERM/R55 的连接）。
5. 抓紧：一次改完、一次验收，不要反复重排版面。最后一行回复 `DONE`。
