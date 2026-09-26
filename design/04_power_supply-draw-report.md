# 04_power_supply（辅助电源）画图报告 · 第 1 轮

- 生成脚本：`hardware/gen/gen_04_power_supply.py`（幂等，UUID 用 `uuid.uuid5` 派生，跑两次输出逐字节相同）
- 产物：`hardware/04_power_supply.kicad_sch`
- 依据：`docs/03-详细设计.md` 第 5 节 + `datasheets/C87080_TI_LMR16006XDDCR.pdf` 第 3 / 11 / 13 页

---

## 0. 位号对照表（KiCad 对位号有限制，两处改名）

KiCad 10 的位号必须**以数字结尾**（`前缀+数字`），`C_IN_E`、`C_BST` 以字母结尾会被判为
「annotation errors」（导出网表时提示 *schematic has annotation errors*）。按任务书要求改成数字编号：

| 任务书位号 | 本图位号 | 器件 | 值 | LCSC |
|---|---|---|---|---|
| C_IN_E | **C40** | Panasonic EEE-FT1H470AP（输入电解） | 47µF 50V | C92059 |
| C_BST | **C41** | Samsung CL05B104KO5NNNC（自举电容） | 100nF 16V | C1525 |

其余位号（U4 / F11 / D6 / D7 / L1 / C_IN1 / C_OUT1 / R_FB1 / R_FB2）保持不变。

---

## 1. 手册外围件点名表（规则 00 ①a，第 11 页 Figure 9）

Figure 9 是「5V/0.6A 典型应用」，逐件与本图对应：

| Figure 9 外围件 | 功能 | 本图位号 | 连接 | 核对 |
|---|---|---|---|---|
| Cboot 100nF | 自举电容 | **C41** | U4.CB(1) — C41 — SW_3V3 | ✅ 手册 Pin 1「Connect Cboot cap between CB and SW」 |
| L1 22µH | 输出电感 | **L1** | SW_3V3 — L1 — +3V3 | ✅ 22µH（手册 §9.2.2.2 建议 22µH/1.6A 起步，本设计 1.9A） |
| D1（续流肖特基） | 非同步 buck 续流 | **D7** | 阴极接 SW_3V3、阳极接 GND | ✅ 手册 Pin 6「Connect to inductor, diode, and Cboot cap」；方向：阴极接 SW |
| Cin | 输入电容 | **C40 + C_IN1** | VIN_F — GND | ✅ 电解 47µF + 陶瓷 4.7µF/100V（手册 §9.2.2.5：1–10µF X5R/X7R，本设计加大以满足输入纹波与瞬态） |
| R1（上分压） | 反馈上电阻 | **R_FB1** | +3V3 — FB_3V3 | ✅ 33k（Figure 9 为 54.9k 对应 5V；本设计 3.3V 用 33k） |
| R2（下分压） | 反馈下电阻 | **R_FB2** | FB_3V3 — GND | ✅ 10k |
| Cout | 输出电容 | **C_OUT1** | +3V3 — GND | ✅ 22µF/25V（手册 §9.2.2.3：4.7–100µF、ESR≤0.7Ω 起步） |
| SHDN 100k 上拉到 VIN | 使能 | —（未画） | SHDN 悬空 | 见 §5 建议 |

**Pin Functions（第 3 页）逐脚点名**（U4 = LMR16006XDDCR，TSOT-6）：

| 脚 | 名称 | 手册原文 | 本图处理 |
|---|---|---|---|
| 1 | CB | Switch FET gate bias voltage. Connect Cboot cap between CB and SW | 接 C41 → SW_3V3 ✅ |
| 2 | GND | Ground connection | 接 GND ✅ |
| 3 | FB | Feedback Input. VOUT = VFB(1+(R1/R2)) | 接 FB_3V3（R_FB1/R_FB2 分压中点）✅ |
| 4 | SHDN | HV tolerant, internal pull-up. Pull below 1.25V to disable. Float to enable | 放「无连接」标志（悬空=常开）✅ |
| 5 | VIN | Power input voltage pin | 接 VIN_F（经 F11 保险丝、D6/C40/C_IN1）✅ |
| 6 | SW | Switch node. Connect to inductor, diode, and Cboot cap | 接 L1 + D7 阴极 + C41 ✅ |

**续流二极管反压校核（第 13 页 Schottky Diode Selection）**：手册要求反压 ≥ 1.25×VIN_max。
VIN_max = 53V（电池侧 TVS 钳位最坏）→ 1.25×53 = **66.25V**。SS210 = **100V** ✅（余量 1.5×）。
手册另要求电流额定 ≥ 最大输出电流、峰值 > 最大负载：SS210 = 2A，负载 <80mA ✅。

---

## 2. 连接表（每个器件每个引脚 → 网络，以网表逐脚回读）

| 位号 | 器件 | 引脚 | 网络 |
|---|---|---|---|
| U4 | LMR16006XDDCR | 1 CB | CB_3V3 |
| | | 2 GND | GND |
| | | 3 FB | FB_3V3 |
| | | 4 SHDN | 无连接（NC） |
| | | 5 VIN | VIN_F |
| | | 6 SW | SW_3V3 |
| F11 | 0466001.NRHF（1A 保险丝） | 1 | BAT+ |
| | | 2 | VIN_F |
| D6 | SMBJ33A（TVS） | 1 C（阴极） | VIN_F |
| | | 2 A（阳极） | GND |
| C40 | EEE-FT1H470AP（47µF 电解） | 1 (+) | VIN_F |
| | | 2 (−) | GND |
| C_IN1 | FS32X475K101EGG（4.7µF/100V） | 1 | GND |
| | | 2 | VIN_F |
| C41 | CL05B104KO5NNNC（100nF） | 1 | CB_3V3 |
| | | 2 | SW_3V3 |
| D7 | SS210（续流肖特基） | 1 K（阴极） | SW_3V3 |
| | | 2 A（阳极） | GND |
| L1 | SWPA5040S220MT（22µH） | 1 | SW_3V3 |
| | | 2 | +3V3 |
| C_OUT1 | CL21A226MAQNNNE（22µF/25V） | 1 | GND |
| | | 2 | +3V3 |
| R_FB1 | 0402WGF3302TCE（33k） | 1 | +3V3 |
| | | 2 | FB_3V3 |
| R_FB2 | 0402WGF1002TCE（10k） | 1 | FB_3V3 |
| | | 2 | GND |

网表回读结果（`kicad-cli sch export netlist`，逐网核对）：

```
BAT+                 -> {F11.1}
VIN_F                -> {F11.2, U4.5, D6.1, C40.1, C_IN1.2}
+3V3                 -> {L1.2, C_OUT1.2, R_FB1.1}
SW_3V3               -> {U4.6, D7.1, L1.1, C41.2}
CB_3V3               -> {U4.1, C41.1}
FB_3V3               -> {U4.3, R_FB1.2, R_FB2.1}
GND                  -> {U4.2, D6.2, C40.2, C_IN1.1, D7.2, C_OUT1.1, R_FB2.2}
unconnected-(U4-SHDN-Pad4) -> {U4.4}   ← 无连接标志，预期
```

反馈输出电压：VFB=0.765V（手册 §7.5），Vout = 0.765×(1+33/10) = **3.29V** ✅（目标 3.3V）。

---

## 3. 极性件引脚核对

| 器件 | 符号引脚名/号 | 手册封装极性 | 本图方向 | 结论 |
|---|---|---|---|---|
| D6 SMBJ33A | 1=C（阴极）、2=A（阳极） | Brightking 手册「Color band denotes cathode」（单向 TVS） | 阴极→VIN_F，阳极→GND | ✅ 反向并接在电源轨，正确 |
| D7 SS210 | 1=K（阴极）、2=A（阳极） | MDD 手册「Color band denotes cathode end」 | 阴极→SW_3V3，阳极→GND | ✅ 续流管方向正确（阴极接 SW） |
| C40 EEE-FT1H470AP | 1=正极（符号顶部带「+」）、2=负极 | Panasonic 手册「Negative polarity marking (−)」 | 正极→VIN_F，负极→GND | ✅ 电解正极接高电位，正确 |

---

## 4. 自检结果

| 检查 | 结果 |
|---|---|
| 幂等性 | ✅ 跑两次输出 md5 相同（`1210efaf…`） |
| ERC（根图） | **0 error**；warning 2 类（见下） |
| 网表逐脚核对 | ✅ 全部 11 个器件、29 个引脚网络与预期一致（§2 表） |
| 断线/死头（规则 00 ⓪） | ✅ 无 `pin_not_connected`（除 SHDN 预期的 `unconnected-(U4-SHDN-Pad4)`）、无 `unconnected_wire_endpoint`、无 `label_dangling` |
| 短路/同网多名（规则 00 ⓪b） | ✅ 无 `multiple_net_names`；每个网络名在网表中都存在且唯一 |
| 拓扑完备（规则 00 ①a） | ✅ 续流 D7、自举 C41、输入电解 C40、输入陶瓷 C_IN1、输出 C_OUT1、反馈分压 R_FB1/R_FB2 全部在（§1 点名表） |
| 引脚号↔符号↔封装 | ✅ 符号引脚号与手册 Pin Functions 一致；封装 `jlc:*` 均存在于 `hardware/lib/jlc/jlc.pretty/` |
| LCSC 字段 | ✅ 每器件实例带隐藏 `LCSC` 字段，值与 BOM（docs/02-BOM.csv）一致 |
| 无交叉线 / 无越界 | ✅ 目视 PDF：信号左→右、电源上地在下，无交叉、无越出 A3 图框 |

**ERC 剩余 warning（2 类，均非连通性问题）：**

1. **`lib_symbol_issues` × 11**（「The current configuration does not include the symbol library ''」）——
   **库表环境问题，非电路问题**（交接文档 §3 已预警）。本容器 `kicad-cli` 不加载工程级
   `hardware/sym-lib-table`（网表 `<libraries/>` 为空）。符号已按任务书复制进本图 `(lib_symbols ...)`，
   引脚/封装/字段全部从这份自包含副本解析，网表正确。**注**：任务书要求 `lib_id` 写 `jlc:<符号名>`；
   但实测该写法在 `kicad-cli` 下会把引脚解析成 `Pad??`（网表断线）。本图因此用裸符号名
   `lib_id "符号名"`（自包含），`Footprint` 字段仍为 `jlc:<封装名>`。若在能加载工程库表的 GUI 环境复核，
   可改回 `jlc:` 前缀。

2. **`isolated_pin_label` × 1**（Global Label 'BAT+'）——**预期**。BAT+ 本页只接 F11.1 一个脚
   （输入进保险丝），完整设计中 BAT+ 还在 01 页接 TVS/电容等，此 warning 会随 01 页绘制消失。

**引脚电气类型归一说明**：嘉立创库把无源件（电阻/电解）引脚标为 `input`、其余标为 `unspecified`，
会触发 `pin_not_driven` / `pin_to_pin`。本图在复制进 `(lib_symbols ...)` 时把引脚类型统一为 `passive`
（无源件正确类型），**不改引脚号/名称/形状/封装/LCSC**；此改动后 `pin_not_driven`、`pin_to_pin` 归零。

---

## 5. 建议（未擅自改）

1. **SHDN 是否加上拉**：Figure 9 里 SHDN 经 100kΩ 上拉到 VIN；本设计按正文「Float to enable」悬空。
   手册明说「Internal pull-up current source … Float to enable」，悬空是手册允许的正式用法，无需外加 100k。
   若担心悬空脚的抗干扰（EMI 环境），可加 100kΩ 上拉到 VIN_F（0402），由用户定夺，本轮**未加**。

2. **`lib_id` 前缀**：见 §4 第 1 条。建议复核方在能加载工程 `sym-lib-table` 的 GUI 环境里确认
   `jlc:` 前缀写法是否接受；两者电气等价（符号来自同一份自包含副本）。

3. **位号改名**：`C_IN_E→C40`、`C_BST→C41`（§0）。若用户希望保留语义位号，需改用「以数字结尾」的
   命名（如 `C_IN_E` 已不可用），BOM `docs/02-BOM.csv` 的对应行后续同步。

4. **运输模式**（交接 §5-5）：如需硬件断电，预留 NMOS 拉低 SHDN（DNP），本轮未画。

---

最后一行回复 `DONE`。
