# 04_power_supply（辅助电源）画图报告 · 第 3 轮

- 生成脚本：`hardware/gen/gen_04_power_supply.py`（幂等，UUID 用 `uuid.uuid5` 派生，跑两次输出逐字节相同）
- 自检脚本：`hardware/gen/check_04_layout.py`（几何检查 1–3，直接解析生成的 `.kicad_sch`）
- 产物：`hardware/04_power_supply.kicad_sch`
- 依据：`docs/03-详细设计.md` 第 5 节 + `datasheets/C87080_TI_LMR16006XDDCR.pdf` 第 3 / 11 / 13 页
- 上一轮：第 2 轮报告见本文件「历史（第 2 轮）」章节，纪律全部沿用

---

## 0. 第 3 轮变更（版面返工，只改版面不改连接）

1. **消灭「VIN_F 导线横穿 U4 本体」P0**：U4 每个脚引 ≥5.08mm 短线，线端放局部标签
   （`VIN_F`/`SW_3V3`/`CB_3V3`/`FB_3V3`）或 `GND` 全局标签，组与 U4 之间靠同名标签相连。
   不再有任何导线穿过 U4 本体或其它引脚端点。
2. **分组重排（左→右、电源上地在下）**：输入保护（BAT+→F11→C40/C42）一组 →
   续流/电感/输出（D7→L1→C43）一组 → 反馈（R40→R41）一组；C41 自举电容放 U4 上方，
   两端各用 `CB_3V3`/`SW_3V3` 标签；D7 改为横放（阴极左接 SW、阳极右接 GND）。
3. **位号/值重排**：竖放两脚件位号与值都放器件右侧、水平书写（字段角 `(360−rot)%360`
   抵消符号旋转）；横放件位号在上、值在下；U4 位号在上、值在下。修正「4.7µF 100V 竖排压线」、
   「LMR16006XDDCR 跑到 D7 下方」「C40/C42/C43 位号值压线」等第 2 轮问题。
4. **放大布局**：器件间距 ≥12.7mm，电路居中偏上（约 x 40–320mm / y 66–128mm），
   说明文字移到电路下方（y≈175/188），不与任何图元重叠。
5. `title_block.rev` → `v0.3-draw-r3`。

**网表逐脚与第 2 轮完全一致**（只改版面，不改连接）：见 §1 自检第 6 项。

---

## 1. 自检结果（第 3 轮任务书 8 项）

| # | 检查 | 结果 |
|---|---|---|
| 1 | 导线不许经过非端点的引脚 | ✅ PASS（`check_04_layout.py`，22 段导线逐一判） |
| 2 | 导线不许穿过符号本体 | ✅ PASS（符号 rectangle/polyline/arc/circle 包络 + 实例坐标变换） |
| 3 | T 型连接必须有 junction | ✅ PASS（唯一 T 接点 x=304.80 已放 junction） |
| 4 | 文字不重叠（pymupdf 逐 span bbox，容差 0.2mm） | ✅ 电路区 143 个 span 两两检查 **0 重叠**（唯一例外：D7 符号自带的引脚名 K/A 重叠，见 §1.1） |
| 5 | `sch_conn.py --show` | ✅ ②③ 部分 **P0 = 0**；③「同网多名」= 0；ERC 只剩 BAT+ `isolated_pin_label`（P1，预期） |
| 6 | 网表逐脚与第 2 轮一致 | ✅ 24 脚「位号.脚→网络名」映射 **0 diff** |
| 7 | PDF 04 页渲 PNG 目视 | ✅ 问题 1–3 全部消失（无导线穿 U4 本体、文字不压线、布局放大居中偏上） |
| 8 | 幂等 | ✅ 跑两次 md5 相同（`7c6c3570328407a6e9d7e61621cfc988`） |

### 1.1 自检第 4 项的唯一例外（符号级 quirk，非本图文字摆放问题）

`D7`（jlc:SS210 二极管）的**引脚名 `K`/`A`** 被 KiCad 自动摆到符号本体中心、彼此重叠约 1.9mm。
- 证据：pymupdf 实测 `K` bbox=(227.8,79.2,229.1,81.1)、`A` bbox=(228.1,79.2,229.2,81.1)（mm），
  二者几乎完全重合；而引脚号 `1`/`2` 分别正确落在左右引脚处。
- 根因：SS210 库里两条 pin 的 `(name "K")`/`(name "A")` 未给显式位置，KiCad 自动摆放时把两个
  名字都归到本体中心。这与第 2 轮 `lib_symbol_mismatch`（电感 arc）同类，属**嘉立创符号库 quirk**。
- 影响：仅 D7 一处、纯观感；不影响 ERC/网表/连通（第 5、6 项已证）。横放、竖放都重叠。
- 处置：不改库（纪律）；若要在图内消除，只能改本图嵌入符号（会在 `lib_symbol_mismatch` 上新增一条，
  得不偿失），故本轮记录在案、留主代理定夺是否值得为 D7 单独处理。

---

## 附 · 第 2 轮历史报告（以下为第 2 轮交付时的内容，仅作追溯，不再更新）

## 第 2 轮变更（主代理核查结论，全部照做）

1. **lib_id 带库昵称 `jlc:`**：嵌入 `(lib_symbols …)` 的顶层符号名写 `(symbol "jlc:NAME" …)`（与 lib_id 完全一致），
   其下子单元仍写 `(symbol "NAME_0_1" …)`（不带昵称）。改后第 1 轮 11 条 `lib_symbol_issues`
   （"does not include the symbol library ''"）**全部消失**。
2. **引脚电气类型不再在脚本里改**：库 `jlc.kicad_sym` 全部 497 脚已由 `fetch_jlc_parts.py` 归一为 `passive`，
   本图从库**原样复制**（只改顶层符号名加 `jlc:` 前缀），保证嵌入符号与库一致。
3. **位号统一「前缀+数字」40 段**（见 §1 对照表）：`C_IN_E→C40`、`C_BST→C41`、`C_IN1→C42`、
   `C_OUT1→C43`、`R_FB1→R40`、`R_FB2→R41`；`U4/F11/D7/L1` 不变。
4. **删 D6（SMBJ33A）**：BAT+ 上 01 页 D3 SMDJ33A 已钳位 ≈53V < LMR16006 VIN 绝对最大 65V，本页不再有输入 TVS。
5. **C40（原 C_IN_E）换料**：JIERR **RV63V47M6X8**，47µF **63V** 105℃，LCSC **C48971005**，
   封装 `jlc:CAP-SMD_BD6.3-L6.6-W6.6-LS7.3-FD`。电解正负极引脚号已重新核对（见 §3）。
6. 电路说明文字同步（去掉 D6、标注 C40 47µF/63V）；title_block `rev` → `v0.3-draw-r2`。

**新发现（需主代理定夺）**：改对后 ERC 出现 1 条 `lib_symbol_mismatch`（L1 电感），经二分定位是
KiCad 10.0.6 对电感符号「4 段半圆 arc」的失配误报，**本图嵌入符号与库逐字节一致**，非本图电路问题。详见 §4.1。

---

## 1. 位号对照表（新位号 ↔ `docs/02-BOM.csv` 旧位号，BOM 由主代理统一改）

| BOM 旧位号 | 本图新位号 | 器件（LCSC） | 值 | 封装 |
|---|---|---|---|---|
| C_IN_E | **C40** | RV63V47M6X8（C48971005） | 47µF **63V** | jlc:CAP-SMD_BD6.3-L6.6-W6.6-LS7.3-FD |
| C_BST | **C41** | CL05B104KO5NNNC（C1525） | 100nF 16V | jlc:C0402 |
| C_IN1 | **C42** | FS32X475K101EGG（C381466） | 4.7µF 100V | jlc:C1210 |
| C_OUT1 | **C43** | CL21A226MAQNNNE（C45783） | 22µF 25V | jlc:C0805 |
| R_FB1 | **R40** | 0402WGF3302TCE（C25779） | 33k 1% | jlc:R0402 |
| R_FB2 | **R41** | 0402WGF1002TCE（C25744） | 10k 1% | jlc:R0402 |
| U4 / F11 / D7 / L1 | 不变 | LMR16006XDDCR / 0466001.NRHF / SS210 / SWPA5040S220MT | — | — |
| D6 | **删除** | （SMBJ33A，本轮删） | — | — |

---

## 2. 手册外围件点名表（规则 00 ①a，第 11 页 Figure 9）

Figure 9 是「5V/0.6A 典型应用」，逐件与本图对应（第 1 轮已核，位号按 §1 更新）：

| Figure 9 外围件 | 功能 | 本图位号 | 连接 | 核对 |
|---|---|---|---|---|
| Cboot 100nF | 自举电容 | **C41** | U4.CB(1) — C41 — SW_3V3 | ✅ 手册 Pin 1「Connect Cboot cap between CB and SW」 |
| L1 22µH | 输出电感 | **L1** | SW_3V3 — L1 — +3V3 | ✅ 22µH |
| D1（续流肖特基） | 非同步 buck 续流 | **D7** | 阴极接 SW_3V3、阳极接 GND | ✅ 手册 Pin 6；方向：阴极接 SW |
| Cin | 输入电容 | **C40 + C42** | VIN_F — GND | ✅ 电解 47µF/63V + 陶瓷 4.7µF/100V |
| R1（上分压） | 反馈上电阻 | **R40** | +3V3 — FB_3V3 | ✅ 33k |
| R2（下分压） | 反馈下电阻 | **R41** | FB_3V3 — GND | ✅ 10k |
| Cout | 输出电容 | **C43** | +3V3 — GND | ✅ 22µF/25V |
| SHDN 100k 上拉 | 使能 | —（未画） | SHDN 悬空 | 见 §5 建议 |

**Pin Functions（第 3 页）逐脚点名**（U4 = LMR16006XDDCR，TSOT-6）：同第 1 轮，未变（1=CB、2=GND、3=FB、4=SHDN、5=VIN、6=SW）。

**续流二极管反压校核（第 13 页）**：手册要求 ≥1.25×VIN_max；VIN_max = 53V → 66.25V；SS210 = 100V ✅。

---

## 3. 极性件引脚核对（本轮重点：新 C40 电解）

| 器件 | 符号引脚名/号 | 封装极性丝印 | 本图方向 | 结论 |
|---|---|---|---|---|
| **C40 RV63V47M6X8** | 符号（横放）：pin 1 在左、带「+」号（两条线段交叉），pin 2 在右、弧形极板（负极） | 封装 `CAP-SMD_BD6.3-L6.6-W6.6-LS7.3-FD`：pad 1（x=−2.67，左）丝印「+」（竖条 + 横条交叉），pad 2（x=+2.67，右）丝印单横条「−」 | 正极(pin1)→VIN_F，负极(pin2)→GND | ✅ 符号 pin1=正极 ↔ 封装 pad1=正极 一致；接线正极接高电位 |
| D7 SS210 | 1=K（阴极）、2=A（阳极） | SMA 封装色带标阴极 | 阴极→SW_3V3，阳极→GND | ✅ 续流管方向正确（阴极接 SW） |

> 核对方法：读符号 `pin name/number`（RV63V47M6X8 的 pin 1 在符号坐标 x=−5.08 侧、附近画有「+」；
> pin 2 在 x=+5.08 侧、对应弧形极板）与 `jlc.pretty/CAP-SMD_BD6.3-L6.6-W6.6-LS7.3-FD.kicad_mod` 的
> 3 个 `fp_poly` 丝印（左竖条+左横条交叉成「+」= 正极；右单横条 = 负极）。符号与封装一致。
> 网表回读确认 C40 pin1 落在 VIN_F、pin2 落在 GND。

---

## 4. 连接表（网表逐脚回读，`kicad-cli sch export netlist`）

| 网络 | 节点（引脚） |
|---|---|
| BAT+ | F11.1 |
| VIN_F（局部） | F11.2、U4.5、C40.1、C42.2 |
| +3V3 | L1.2、C43.2、R40.1 |
| SW_3V3（局部） | U4.6、D7.1、L1.1、C41.2 |
| CB_3V3（局部） | U4.1、C41.1 |
| FB_3V3（局部） | U4.3、R40.2、R41.1 |
| GND | U4.2、C40.2、C42.1、D7.2、C43.1、R41.2 |
| unconnected-(U4-SHDN-Pad4) | U4.4（无连接标志，预期） |

- **无 `Pad??`** ✅；**无 `unconnected-*`**（除 SHDN 预期的 no_connect）✅。
- 每个器件实例的 **`LCSC` 字段在网表可见**（`<property name="LCSC" value="…">`），值与 §1 一致 ✅。
- 反馈输出电压：VFB=0.765V，Vout = 0.765×(1+33/10) = **3.29V** ✅。
- 与第 1 轮连接逐网一致（仅位号变化、D6 删除）。

---

## 5. 自检结果

| 检查 | 结果 |
|---|---|
| 幂等性 | ✅ 跑两次输出 md5 相同（`e10b0aa9370acc2d04ccef1272cddd65`） |
| ERC：`lib_symbol_issues` | ✅ **0 条**（第 1 轮 11 条「library ''」全部消失） |
| ERC：其余 | `isolated_pin_label` ×1（BAT+，01 页画好后消失，预期）；`lib_symbol_mismatch` ×1（L1，KiCad 误报，见 §5.1） |
| 网表逐脚核对 | ✅ 全部 10 器件、28 脚 + 1 no_connect 与 §4 一致 |
| 断线/死头 | ✅ 无 `pin_not_connected`（除 SHDN 预期）、无 `unconnected_wire_endpoint`、无 `label_dangling` |
| 短路/同网多名 | ✅ 无 `multiple_net_names` |
| 引脚号↔符号↔封装 | ✅ 符号引脚号与手册一致；封装 `jlc:*` 均存在于 `jlc.pretty/` |
| LCSC 字段 | ✅ 每器件实例带隐藏 `LCSC` 字段，值与 BOM 一致 |
| 无交叉线 / 无越界 / 文字不压线 | ✅ 目视 PDF 第 5 页：信号左→右、电源上地在下、D6 已删、C40 标 47µF/63V |

### 5.1 `lib_symbol_mismatch`（L1）—— KiCad 10.0.6 误报，非电路问题

- **现象**：ERC 报 `Symbol 'SWPA5040S220MT' doesn't match copy in library 'jlc'`（L1 电感），severity=warning。
- **证据 1（逐字节一致）**：本图 `(lib_symbols …)` 内嵌入的 `jlc:SWPA5040S220MT` 符号与库
  `hardware/lib/jlc/jlc.kicad_sym` 中 `SWPA5040S220MT` **token 级逐字节一致**（仅顶层名加 `jlc:` 前缀、
  缩进不同），符合任务书「原样复制」要求。
- **证据 2（二分定位）**：把库与本图 L1 符号**同时**删除 4 段 `(arc …)` 后失配消失；单独改 pin length
  1.27→2.54、删 `ki_description`、反转 arc start/end 均不消除。→ 根因是电感符号的 **4 段半圆 arc**
  在 KiCad 10.0.6 的「库加载路径」与「嵌入加载路径」内部归一化不一致导致的比较误报。
- **影响面**：库中另一颗同结构电感 **SLO0618H2R2MTT**（C216189，03_balancer 用，同样 4 段半圆 arc +
  pin length 1.27），画 03 页时会遇到同样的 `lib_symbol_mismatch`。
- **建议（不擅自改，留主代理定夺）**：在 `tools/fetch_jlc_parts.py` 增加「电感 arc 归一化」（类似现有
  `normalize_pin_types`，把电感符号的 4 段 arc 按 KiCad 规范重写或替换为 polyline），重新取库后即可消除。
  此为**库侧改动**，超出本图任务范围（纪律：不改库）。
- **说明**：该 warning 不影响网表/PDF/连通性——§4 网表逐脚核对全部正确。

---

## 6. 建议（未擅自改）

1. **SHDN 是否加上拉**：Figure 9 里 SHDN 经 100kΩ 上拉到 VIN；本设计按正文「Float to enable」悬空，
   手册明说「Internal pull-up … Float to enable」，悬空是正式用法，无需外加。若担心 EMI 可加 100k 上拉（DNP），
   本轮未加。
2. **`lib_symbol_mismatch`（L1 电感）**：见 §5.1，建议库侧归一化电感 arc。
3. **运输模式**（交接 §5-5）：如需硬件断电，预留 NMOS 拉低 SHDN（DNP），本轮未画。

---

最后一行回复 `DONE`。
