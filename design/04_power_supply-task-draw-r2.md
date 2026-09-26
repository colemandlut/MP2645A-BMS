# 画图任务书：子图 04_power_supply，第 2 轮（接续第 1 轮）

工作目录 `/home/user/MP2645A-BMS`。先读第 1 轮任务书 `design/04_power_supply-task-draw-r1.md`（纪律全部沿用）、
你上一轮的脚本 `hardware/gen/gen_04_power_supply.py` 和报告 `design/04_power_supply-draw-report.md`。
**先备份**：`cp hardware/04_power_supply.kicad_sch /tmp/draw-backup/04_power_supply.r1.kicad_sch`，
然后**先跑一遍脚本确认幂等**（输出与现有文件逐字节相同），再动手改脚本。

## 主代理对第 1 轮的核查结论（要改的）

1. **lib_id 必须带库昵称 `jlc:`**。你报告里说写 `jlc:<名>` 会把引脚解析成 `Pad??`——根因不是库表，而是
   **本图 `(lib_symbols …)` 里嵌入的符号名必须与 lib_id 完全相同**：顶层写 `(symbol "jlc:LMR16006XDDCR" …)`，
   其下的子单元仍写 `(symbol "LMR16006XDDCR_0_1" …)`、`(symbol "LMR16006XDDCR_1_1" …)`（子单元名**不带**库昵称）。
   这就是 KiCad 自己保存的格式。现在 ERC 的 11 条 `lib_symbol_issues` 全是 "does not include the symbol library ''"——库昵称为空导致的，改对后应消失。
2. **引脚电气类型**：主代理已把工程库 `hardware/lib/jlc/jlc.kicad_sym` 的全部引脚统一改成 `passive`
   （`tools/fetch_jlc_parts.py` 里的 `normalize_pin_types`，以后重新取库也会自动做）。
   所以你**不要再在脚本里改引脚类型**，嵌入的符号从库里**原样复制**（只改顶层符号名加 `jlc:` 前缀），
   保证嵌入符号与库一致，不产生 `lib_symbol_mismatch`。
3. **位号统一成「前缀+数字」**，本页电容/电阻用 40 段，不要一半 `C40` 一半 `C_IN1`：

   | 原位号 | 新位号 |
   |---|---|
   | C_IN_E（47µF 电解） | C40 |
   | C_BST（100nF 自举） | C41 |
   | C_IN1（4.7µF/100V） | C42 |
   | C_OUT1（22µF/25V） | C43 |
   | R_FB1（33k） | R40 |
   | R_FB2（10k） | R41 |
   | U4、F11、D7、L1 | 不变（D6 删除，见第 4 条） |

   在图上的说明文字或报告里保留一张「新位号 ↔ `docs/02-BOM.csv` 旧位号」对照表（BOM 由主代理统一改）。

4. **用户 2026-09-26 12:18 的第 2 轮决定（已落 `docs/02-BOM.csv`、`docs/03-详细设计.md` 第 5 节，必须照做）**：
   - **删除 D6（SMBJ33A）**：BAT+ 上 01 页的 D3 SMDJ33A 已钳位 ≈53V < LMR16006 VIN 绝对最大 65V。本页不再有输入 TVS。
   - **C40（原 C_IN_E）换料**：JIERR RV63V47M6X8，47µF **63V** 105℃，LCSC **C48971005**，
     符号名 `RV63V47M6X8`（`jlc:RV63V47M6X8`），封装 `jlc:CAP-SMD_BD6.3-L6.6-W6.6-LS7.3-FD`。
     **重新核对这颗电解的正负极引脚号**（看符号 pin name/number 与 `jlc.pretty` 里该封装的极性丝印），写进报告。
   - 电路说明文字同步：去掉 D6，C40 标 47µF/63V。

## 验收（你自己跑到满足再交）

- `kicad-cli sch erc --format json --severity-all --output /tmp/erc04.json hardware/mp2645a-bms.kicad_sch`：
  除 `isolated_pin_label`（BAT+，01 页画好后消失）外 **0 条**；`lib_symbol_issues` 必须 0。
- `kicad-cli sch export netlist --format kicadxml --output /tmp/net04.xml hardware/mp2645a-bms.kicad_sch`：
  逐脚核对连接与第 1 轮一致（只有位号变了），**没有 `Pad??`、没有 `unconnected-*`**；每个器件的 `LCSC` 字段在网表里可见。
- `kicad-cli sch export pdf --output /tmp/sch04.pdf hardware/mp2645a-bms.kicad_sch`，用 python（pymupdf）把 04 页渲成 PNG 目视：
  无重叠、无交叉线、无越界、文字不压线。
- 脚本幂等（跑两次 md5 相同）。

## 交付
更新脚本、原理图、报告（在报告开头加「第 2 轮变更」小节）。最后一行回复 `DONE`。
