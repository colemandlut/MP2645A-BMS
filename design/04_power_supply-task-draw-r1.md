# 画图任务书：子图 04_power_supply（辅助电源），第 1 轮

你是本项目的**画图方**。任务：用 KiCad 10 原理图文件格式画出 `hardware/04_power_supply.kicad_sch`。
工作目录：`/home/user/MP2645A-BMS`。全部说明、注释、报告用**中文**。

## 0. 纪律（必须遵守）

1. **可接续**：生成逻辑写成可重复运行的幂等脚本 `hardware/gen/gen_04_power_supply.py`（python3 标准库即可），
   原理图是脚本的产物，不要手工累积编辑。同一输入跑两次输出应逐字节相同（UUID 用 `uuid.uuid5` 按位号/用途派生）。
2. **开工前先备份**：`mkdir -p /tmp/draw-backup && cp hardware/04_power_supply.kicad_sch /tmp/draw-backup/04_power_supply.r0.kicad_sch`。
3. **只改这两个文件**：`hardware/04_power_supply.kicad_sch`、`hardware/gen/gen_04_power_supply.py`，外加报告
   `design/04_power_supply-draw-report.md`。不要改库、根图、其它子图、`tools/gen_kicad_skeleton.py`（**不要运行它，它会覆盖子图**）。
4. **器件只用嘉立创库**：符号从 `hardware/lib/jlc/jlc.kicad_sym` 复制到本图的 `(lib_symbols ...)`，
   `lib_id` 写成 `jlc:<符号名>`；封装字段写库里给的 `jlc:<封装名>`。**不许用 KiCad 官方库**（包括 power 库的 GND/+3V3 符号）。
   每个器件实例加字段 `LCSC`，值为立创编号（如 `C87080`），并隐藏显示。
5. **你可以直接运行 `kicad-cli`**（KiCad 10.0.6）。画完必须自己跑到 ERC 归零：
   `kicad-cli sch erc --format json --output /tmp/erc04.json hardware/mp2645a-bms.kicad_sch`（**跑根图**，只看 04 页的条目；
   其它页目前是空骨架），以及 `kicad-cli sch export netlist --format kicadxml --output /tmp/net04.xml hardware/mp2645a-bms.kicad_sch`，
   用网表逐脚核对连接；再 `kicad-cli sch export pdf --output /tmp/sch04.pdf hardware/mp2645a-bms.kicad_sch` 目视版面。
   ERC 的 `lib_symbol_issues`/`footprint_link_issues` 若出现，单独列出说明原因，不要和连通性问题混在一起。
   **禁止**运行 `tools/gen_kicad_skeleton.py`、`git` 命令，禁止改动本任务书第 3 条以外的文件。

## 1. 文件格式要点（KiCad 10，`(version 20250610)`）

- 保留现有文件头：`uuid "30cbc880-65ec-5706-9809-92789c0e1f35"`、`paper "A3"`、`title_block`（`rev` 改成 `v0.3-draw-r1`），
  删除骨架里那几条说明性 `text`（它们是占位，画完后会过时），可以保留一个简短标题文字。
- 器件实例必须带 `(instances (project "mp2645a-bms" (path "/632f74a5-cd8f-58d8-9ac1-1bfbb611d555/c20e45f9-c9d2-50e9-b477-f2356556af13" (reference "U4") (unit 1))))`，
  这是根图 → 本子图的层次路径，写错 ERC/网表会出错位号。
- 坐标用 mm，**所有引脚端点、导线端点、标签锚点都落在 1.27mm 栅格上**。注意符号内引脚坐标是 Y 向上，
  放到图纸上要 Y 取反（图纸 Y 向下），旋转/镜像时一并换算。
- 跨页网络一律用 `global_label`；本页内部网络用 `label`。T 型接点要放 `junction`。
- 导线只连到引脚端点，**不要让导线从别的引脚端点中间穿过**（会被 KiCad 认成连接）。

## 2. 接口契约（网络名以此为准）

| 网络 | 类型 | 说明 |
|---|---|---|
| `BAT+` | global_label（input） | 电池总正，29.2V 满充，TVS 钳位后最坏 ≈53V |
| `GND` | global_label | 板级地。**GND = BAT-，在 01 页分流器电池侧单点汇合（那里用 net-tie）**，本页所有回流都接 `GND`，**本页不出现 `BAT-` 标签** |
| `+3V3` | global_label（output） | 3.3V 输出，负载 < 80mA |

本页内部网络名建议：`VIN_F`（保险丝后的输入）、`SW_3V3`（开关节点）、`CB_3V3`（自举）、`FB_3V3`（反馈中点）。

## 3. 电路（依据 `docs/03-详细设计.md` 第 5 节 + `datasheets/C87080_TI_LMR16006XDDCR.pdf` 第 11 页 Figure 9）

```
BAT+ ─F11─ VIN_F ─┬─ D6 SMBJ33A 阴极（阳极→GND）
                  ├─ C_IN_E 47µF/50V 电解 +（−→GND）
                  ├─ C_IN1 4.7µF/100V（→GND），紧靠 U4.VIN
                  └─ U4.VIN(5)
U4.CB(1) ─ C_BST 100nF ─ SW_3V3
U4.SW(6) ─ SW_3V3 ─┬─ D7 SS210 阴极（阳极→GND）   ← 非同步 buck 续流管，必需
                   └─ L1 22µH ─ +3V3
+3V3 ─ R_FB1 33k ─ FB_3V3 ─ R_FB2 10k ─ GND；U4.FB(3) 接 FB_3V3
+3V3 ─ C_OUT1 22µF/25V ─ GND
U4.GND(2) → GND；U4.SHDN(4)：悬空=常开（手册：内部上拉，Float to enable）→ 放「无连接」标志
```

**手册核对任务（规则 00 ①a，必须做并写进报告）**：打开 `datasheets/C87080_TI_LMR16006XDDCR.pdf`，
把第 3 页 Pin Functions 每一脚、第 11 页 Figure 9 的每一个外围件，逐个在你的图里点名（位号 + 连接）。
Figure 9 里 SHDN 经 100kΩ 上拉到 VIN——本设计按正文「Float to enable」悬空；你若认为应加上拉，写进报告的「建议」里，**不要擅自加**。
续流二极管反压要求（手册第 13 页 Schottky Diode Selection：≥1.25×VIN_max）也请核一遍写进报告。

## 4. 器件表（全部来自 `hardware/lib/jlc/jlc.kicad_sym`，符号名 / 封装 / LCSC 已核）

| 位号 | 符号名（lib_id = jlc:…） | 值 | 封装 | LCSC |
|---|---|---|---|---|
| U4 | LMR16006XDDCR | LMR16006XDDCR | jlc:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR | C87080 |
| D7 | SS210 | SS210 | jlc:SMA_L4.3-W2.6-LS5.2-RD | C14996 |
| L1 | SWPA5040S220MT | 22µH | jlc:IND-SMD_L5.0-W5.0 | C68434 |
| C_BST | CL05B104KO5NNNC | 100nF 16V | jlc:C0402 | C1525 |
| R_FB1 | 0402WGF3302TCE | 33k 1% | jlc:R0402 | C25779 |
| R_FB2 | 0402WGF1002TCE | 10k 1% | jlc:R0402 | C25744 |
| F11 | 0466001.NRHF | 1A | jlc:F1206 | C151135 |
| D6 | SMBJ33A-C78419 | SMBJ33A | jlc:SMB_L4.6-W3.6-LS5.3-RD | C78419 |
| C_IN_E | EEE-FT1H470AP | 47µF 50V | jlc:CAP-SMD_BD6.3-L6.6-W6.6-FD | C92059 |
| C_IN1 | FS32X475K101EGG | 4.7µF 100V | jlc:C1210 | C381466 |
| C_OUT1 | CL21A226MAQNNNE | 22µF 25V | jlc:C0805 | C45783 |

KiCad 位号不能带下划线以外的奇怪字符，上面的位号可以直接用；若你发现 KiCad 对位号有限制，改成
`C40..` 这类数字编号并在报告里给出对照表。

**极性件逐一核对符号引脚名/编号与方向**：D6、D7 的阴极/阳极是哪个引脚号（看符号里 pin name/number，
再对照手册封装图），电解电容 C_IN_E 的正极是哪个引脚——写进报告。接反是 P0。

## 5. 版面（规则 00 ③ 可读性）

- 信号从左到右：BAT+ 入口（左）→ 保险丝 → 输入保护/电容 → U4 → 电感/续流 → 反馈与输出电容 → +3V3（右）。
- 电源在上、地在下；GND 用 `global_label` 放在每个接地器件的下方短线末端（可多个同名 GND 标签）。
- 无交叉线、无重叠、不越出 A3 图框；位号/值文字不压线不压符号。
- 在图上加一段简短说明文字：`LMR16006X 700kHz 非同步 buck；D7 续流必需；SHDN 悬空=常开；L1 下方全层禁铜（规则 2d）`。

## 6. 交付

1. `hardware/gen/gen_04_power_supply.py`（幂等，运行即覆盖生成 `hardware/04_power_supply.kicad_sch`）。
2. 生成好的 `hardware/04_power_supply.kicad_sch`。
3. `design/04_power_supply-draw-report.md`：① 手册外围件点名表；② 每个器件每个引脚 → 网络的连接表；
   ③ 极性件引脚核对；④ 你的自检结果；⑤ 建议（不擅自改的）。

最后一行回复 `DONE`。
