#!/usr/bin/env python3
"""生成 hardware/02_afe.kicad_sch（MP2797 AFE：8S 采集与保护）。

幂等：同一输入跑两次输出逐字节相同（UUID 用 uuid.uuid5 按位号/用途派生）。
运行即覆盖生成 hardware/02_afe.kicad_sch。

    python3 hardware/gen/gen_02_afe.py

器件符号从 hardware/lib/jlc/jlc.kicad_sym 原样复制到本图 (lib_symbols ...)；
lib_id 用 jlc:<符号名>（顶层嵌入符号名 = lib_id，子单元名不带昵称），
实例带 Footprint/Datasheet/LCSC 字段（隐藏），C226/C222–C225 带 (dnp yes)。
位号一律「字母前缀 + 纯数字」：规格书 §6 原写 C219B，但尾随字母的位号 KiCad 不认
（annotator 解析不出序号），根图导网表会报 `Warning: schematic has annotation errors`，
实测确认过，故改 C226（2xx C 段里 222–225 留给 NTC DNP，226 是下一个空号）。

设计依据：design/02_afe-spec.md（Opus 按 MP2797 手册写）+ §12.1b 用户决定（2026-09-27）。
本脚本按任务书分段交付：**分段 A**（U1 48 脚 + §9 电源 + §6 高边驱动），
分段 B/C 在同一脚本里续画（J5/电芯 RC/NTC/通讯），版面分区见文件末尾注释。

沿用 04/05 页教训：坐标全落 1.27mm 栅格；每条 wire 只 2 点；竖放件字段角 (360-rot)%360；
引脚几何以库读数为准（parse_pins/pin_world）；IC 引脚引短线 + 标签；
导线不穿本体/不经过非端点引脚；引脚处 ≥2 段导线端点相接补 junction。

本页特有：U1 用 (mirror y)（手册 Fig 26/27 的画法：电芯脚朝左，J5/RC 在左，电源/驱动在右）。
KiCad 的 mirror 语义已用网表实测确认：rot=0 + (mirror y) 时 世界坐标 = (px − ix, py − iy)。
"""
from __future__ import annotations

import os
import re
import uuid

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
JLCSYM = os.path.join(HW, "lib", "jlc", "jlc.kicad_sym")
OUT = os.path.join(HW, "02_afe.kicad_sch")

PAGE_UUID = "d1c7b78c-1731-540c-8187-6dd957cc111f"   # 02 页文件自身 uuid（保持骨架现值）
ROOT_UUID = "632f74a5-cd8f-58d8-9ac1-1bfbb611d555"
SHEET_UUID = "b7551ed3-1617-5b05-94f3-5ce7ab4e2107"  # 根图里 Sheetfile "02_afe.kicad_sch" 的 sheet
PATH = f"/{ROOT_UUID}/{SHEET_UUID}"

NS = uuid.UUID("d1c7b78c1731540c81876dd957cc111f")


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def fmt(v: float) -> str:
    return f"{v:.2f}"


def esc(txt: str) -> str:
    return txt.replace("\\", "\\\\").replace('"', '\\"')


def read_symbol(name: str) -> str:
    s = open(JLCSYM, encoding="utf-8").read()
    key = f'(symbol "{name}"'
    start = s.index(key)
    i, depth = start, 0
    while True:
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    block = s[start:i + 1]
    return block.replace(f'(symbol "{name}"', f'(symbol "jlc:{name}"', 1)


def symbol_props(block: str) -> dict:
    return {m.group(1): m.group(2)
            for m in re.finditer(r'\(property "([^"]+)" "([^"]*)"', block)}


def parse_pins(block: str) -> dict:
    pins = {}
    for m in re.finditer(
        r'\(pin\s+\S+\s+\S+\s+\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\).*?'
        r'\(number\s+"([^"]+)"',
        block, re.S,
    ):
        pins[m.group(4)] = (float(m.group(1)), float(m.group(2)))
    return pins


def pin_world(px: float, py: float, rot: int, ix: float, iy: float, mirror: bool = False):
    """符号局部坐标 → 世界坐标（y 轴向下）。

    mirror=True 表示 (mirror y)（绕 y 轴镜像 = 水平翻转），先翻局部 x 再旋转。
    rot=0 的语义已用网表实测：普通符号 pin1（局部 x=−5.08）落左侧，
    (mirror y) 后落右侧，即 世界坐标 = (px − ix, py − iy)。
    """
    if mirror:
        ix = -ix
    if rot == 0:
        return (px + ix, py - iy)
    if rot == 90:
        return (px - iy, py - ix)
    if rot == 180:
        return (px - ix, py + iy)
    if rot == 270:
        return (px + iy, py + ix)
    raise ValueError(rot)


# ---------------------------------------------------------------------------
# 器件表：位号 / 符号名 / 值 / LCSC / 位置(mm) / 旋转 / DNP / 镜像
# 版面（spec §11.3）：
#   ① J5 + NTC    x 15–60   （J5：J5.1–13；NTC 探头走 J5.1–4，已画）
#   ② 电芯 RC      x 62–136  （R201–R209 y 68.58–129.54，C201–C208，D201）
#   ③ U1（镜像）    x 134–202
#   ④ 右：电源/驱动/通讯/采样
#        §9 电源    x 205–290, y 43–135
#        §6 驱动    x 300–410, y 43–105
#        §5 SRP/SRN x 305–375, y 105–150
#        §7 NTC     x 205–290, y 145–250  ← 分段 C（R216–R219 x=222.25，C222–C225 x=265.43）
#        §8 通讯    x 300–410, y 155–215  ← 分段 C（R220–R223 y=179.07，x=314.96/340.36/365.76/391.16）
# ---------------------------------------------------------------------------
COMPONENTS = [
    # ref, symbol, value, lcsc, x, y, rot, dnp, mirror
    ("U1", "MP2797DFP-0000-T", "MP2797DFP-0000-T", "C18198873", 170.18, 152.40, 0, False, True),
    # §9 电源（spec §9.1–§9.4）
    ("R212", "0603WAF200JT5E", "20Ω 1%", "C22950", 228.60, 66.04, 0, False, False),
    ("C212", "TCC0805X7R474K101FT", "470nF 100V", "C5375914", 250.19, 66.04, 90, False, False),
    ("R213", "0603WAF5100T5E", "510Ω 1%", "C23193", 228.60, 86.36, 0, False, False),
    ("C213", "TCC1206X7R105K101HT", "1µF 100V", "C282823", 250.19, 86.36, 90, False, False),
    ("Q201", "MMBT5551_C2145", "MMBT5551", "C2145", 224.79, 106.68, 0, False, False),
    ("C214", "CL10A106KP8NNNC", "10µF 10V", "C19702", 250.19, 106.68, 90, False, False),
    # §9 内部 LDO 去耦（spec §9.3，U1.26/27/22/21 各一只）
    ("C215", "CL05A105KA5NQNC", "1µF 25V", "C52923", 273.05, 63.50, 90, False, False),
    ("C216", "CL05A105KA5NQNC", "1µF 25V", "C52923", 273.05, 83.82, 90, False, False),
    ("C217", "CL05A105KA5NQNC", "1µF 25V", "C52923", 273.05, 104.14, 90, False, False),
    ("C218", "CL05B103KB5NNNC", "10nF 50V", "C15195", 273.05, 124.46, 90, False, False),
    # §6 高边驱动（spec §6.3/§6.4）
    ("R214", "0402WGF1000TCE", "100Ω 1%", "C25076", 330.20, 66.04, 0, False, False),
    ("C219", "CL21B104KCFNNNE", "100nF 100V", "C28233", 355.60, 66.04, 90, False, False),
    ("C226", "CL21B104KCFNNNE", "100nF 100V DNP", "C28233", 374.65, 66.04, 90, True, False),
    # C220 从 x=396.24 左移到 384.81：竖放件的 Value 锚点在 x+5.08 且左对齐，
    # 「100nF 100V」≈12mm 会写到 x≈413（越出 410 图框）。左移后 389.89+12 = 402 ✓。
    ("C220", "CL21B104KCFNNNE", "100nF 100V", "C28233", 384.81, 66.04, 90, False, False),
    ("R215", "0402WGF1000TCE", "100Ω 1%", "C25076", 330.20, 86.36, 0, False, False),
    ("C221", "TCC0603X7R103K101CT", "10nF 100V", "C282516", 355.60, 86.36, 90, False, False),
    # ------------------------------------------------------------------
    # §10 J5 采样端子（spec §10.2）：13 脚，1 NTC_CELL1 / 2 GND / 3 NTC_CELL2 / 4 GND
    # / 5–13 CELL0–CELL8。NTC 放低压端（abs-max 6V），故 1/3 脚紧贴 CELL0 那侧。
    # J5 脚 1–13 落在 y = 73.66 … 104.14（间距 2.54），左侧引 2.54 短线接标签。
    # ------------------------------------------------------------------
    ("J5", "XH-13A", "XH-13A 13P", "C40669", 44.45, 88.90, 0, False, False),
    # ------------------------------------------------------------------
    # §4 电芯采样 RC（spec §4）：CELLn → R20(n+1) 33Ω → VCn → U1.14…6；
    # C20(n+1) 100nF 跨 VCn↔VC(n+1)（8 只，不接地）；D201 阴极→VC0、阳极→GND。
    # 行距 7.62（行内位号/值并排一行，避免 5.08 行距时字段互相压）。
    # ------------------------------------------------------------------
    ("R201", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 68.58, 0, False, False),
    ("R202", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 76.20, 0, False, False),
    ("R203", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 83.82, 0, False, False),
    ("R204", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 91.44, 0, False, False),
    ("R205", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 99.06, 0, False, False),
    ("R206", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 106.68, 0, False, False),
    ("R207", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 114.30, 0, False, False),
    ("R208", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 121.92, 0, False, False),
    ("R209", "0805W8F330JT5E", "33Ω 1%", "C17634", 76.20, 129.54, 0, False, False),
    ("C201", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 76.20, 0, False, False),
    ("C202", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 83.82, 0, False, False),
    ("C203", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 91.44, 0, False, False),
    ("C204", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 99.06, 0, False, False),
    ("C205", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 106.68, 0, False, False),
    ("C206", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 114.30, 0, False, False),
    ("C207", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 121.92, 0, False, False),
    ("C208", "CL05B104KB54PNC", "100nF 50V", "C307331", 111.76, 129.54, 0, False, False),
    ("D201", "BZT52C3V3_C353528", "BZT52C3V3", "C353528", 133.35, 68.58, 0, False, False),
    # ------------------------------------------------------------------
    # §5 电流采样（spec §5）：开尔文取自分流器电池侧 → R210/R211 100Ω →
    # SRP_F/SRN_F → U1.15/16；C209 差模跨 SRP_F↔SRN_F，C210/C211 共模到 GND。
    # ------------------------------------------------------------------
    ("R210", "0402WGF1000TCE", "100Ω 1%", "C25076", 325.12, 127.00, 0, False, False),
    ("R211", "0402WGF1000TCE", "100Ω 1%", "C25076", 325.12, 146.05, 0, False, False),
    ("C209", "CL05B104KO5NNNC", "100nF 50V", "C1525", 350.52, 137.16, 0, False, False),
    ("C210", "CL05B104KO5NNNC", "100nF 50V", "C1525", 369.57, 127.00, 90, False, False),
    ("C211", "CL05B104KO5NNNC", "100nF 50V", "C1525", 369.57, 146.05, 90, False, False),
    # ------------------------------------------------------------------
    # §7 NTC ×4（spec §7）：每路一行「NTCB ─ R21x 10k ─ NTCx」+「NTCx ─ C22x ─ GND」。
    # 上拉一律接 NTCB（不接任何 3V3，NTC 读数与 NTCB 成比例）；C222–C225 为 DNP
    # （NTCB_DYNAMIC_ON=1，100nF 会让低温读数偏，见 spec §7.3）。
    # 行距 17.78：行内最高的文字是 C22x 顶标签（y−6.35±1.05），下一行最低是底标签
    # （y+6.35±1.05），净空 17.78−14.8 = 2.98mm。
    # ------------------------------------------------------------------
    ("R216", "0402WGF1002TCE", "10k 1%", "C25744", 222.25, 171.45, 0, False, False),
    ("R217", "0402WGF1002TCE", "10k 1%", "C25744", 222.25, 189.23, 0, False, False),
    ("R218", "0402WGF1002TCE", "10k 1%", "C25744", 222.25, 207.01, 0, False, False),
    ("R219", "0402WGF1002TCE", "10k 1%", "C25744", 222.25, 224.79, 0, False, False),
    ("C222", "0402B102K500NT", "1nF DNP", "C1523", 265.43, 171.45, 90, True, False),
    ("C223", "0402B102K500NT", "1nF DNP", "C1523", 265.43, 189.23, 90, True, False),
    ("C224", "0402B102K500NT", "1nF DNP", "C1523", 265.43, 207.01, 90, True, False),
    ("C225", "0402B102K500NT", "1nF DNP", "C1523", 265.43, 224.79, 90, True, False),
    # ------------------------------------------------------------------
    # §8 通讯与中断（spec §8）：四只电阻竖放，上端是 3.3V 域 / 中断域，下端是信号。
    # R220/R221 2.2k 上拉到 +3V3（I2C 开漏必须上拉）；R222 100k 下拉 AFE_ALERT
    # （xALERT 推挽、ALERT_POL 默认高有效，空闲低电平）；R223 10k 把 NSHDN 拉高到
    # +3V3（不是 AFE_3V3）。WDT（29）在 U1 侧已经放 NC 标志，本区不再接任何东西。
    # ------------------------------------------------------------------
    ("R220", "0402WGF2201TCE", "2.2k 1%", "C25879", 314.96, 187.96, 90, False, False),
    ("R221", "0402WGF2201TCE", "2.2k 1%", "C25879", 340.36, 187.96, 90, False, False),
    ("R222", "0402WGF1003TCE", "100k 1%", "C25741", 365.76, 187.96, 90, False, False),
    ("R223", "0402WGF1002TCE", "10k 1%", "C25744", 391.16, 187.96, 90, False, False),
]

PROP_OVERRIDE = {
    # U1 本体是 ±15.24 × ±54.61 的大矩形，默认的「位号在 y−5.08」会落进本体里。
    # 挪到本体上方空带（本体上沿 y=97.79，VDD 引线在 x=170.18 的 y 90.17–95.25）。
    # 对齐必须用「居中」（不写 justify 节点）：(mirror y) 会把水平 justify 一起翻转
    # ——`justify left` 实测渲染成右对齐（U1 位号锚点 154.94，PDF 里画在 152.16–154.70）。
    # 居中对镜像免疫，且 check_02 的 8a 也正是按「渲染文字中心 = 锚点」判的。
    "U1": (("U1", 154.94, 80.01, "center"), ("Value", 154.94, 85.09, "center")),
    # Q201 是 SOT-23，本体在 y 方向约 ±3.0，默认的值位置（y+2.54）会压本体下沿。
    "Q201": (("Q201", 224.79, 99.06), ("Value", 224.79, 114.30)),
    # J5（XH-13A）本体 x 43.18–48.26 / y 71.12–106.68，默认的「位号在 y−5.08」正好落进本体里。
    # 位号挪到本体上方、值挪到本体下方，居中（J5 没镜像，居中只是省得再算宽度）。
    "J5": (("J5", 44.45, 67.31, "center"), ("Value", 44.45, 110.49, "center")),
    # C209 是 100nF 的 0402，本体在 y 方向 ±2.03；默认的值位置（y+2.54，盒底 y+3.17）
    # 只离本体下沿 1.14mm，实测盒 139.065–140.335 与本体（下沿 139.19）相交 0.13mm。
    # 值再往下挪一格（y+3.81）。
    "C209": (("C209", 350.52, 132.08), ("Value", 350.52, 140.97)),
    # C226 是 DNP 件，Value 文本比 C219/C220 长（「100nF 100V DNP」≈17mm）。默认位置在
    # y+2.54 = 68.58，和 C220 左移后的 Value 同一行会撞上（379.73–396.6 vs 389.89–402）。
    # 单独把它挪到 y+9.53 = 75.57：上方 C22x 的 GND 标签 ink 到 74.2，留 0.9mm；下方 §6
    # 的说明文字已挪到 y 91.44 起，远得很。
    "C226": (("C226", 379.73, 63.50), ("Value", 379.73, 75.57)),
}

# §4 电芯 RC 阵（R201–R209 / C201–C208 / D201）：行距 7.62，若按默认「位号 y−5.08、值 y+2.54」
# 摆，字段会压到相邻行的标签上。改成位号/值**并排在同一条线上、居中**：
#   位号 (x−6.35, y−3.81)、值 (x+6.35, y−3.81) —— 离本体上沿 ≥1.1mm，离上一行标签 ≥2.5mm。
RC_ARRAY = ({f"R{n}" for n in range(201, 210)}
            | {f"C{n}" for n in range(201, 209)}
            | {"D201"})


def _fld(t):
    """字段位置元组规范化：(名, x, y[, 对齐]) → (名, x, y, 对齐)；对齐缺省 left。"""
    return t if len(t) == 4 else (t[0], t[1], t[2], "left")


def prop_pos(ref, x, y, rot):
    if ref in PROP_OVERRIDE:
        a, b = PROP_OVERRIDE[ref]
        return _fld(a), _fld(b)
    if ref in RC_ARRAY:
        return (ref, x - 6.35, y - 3.81, "center"), ("Value", x + 6.35, y - 3.81, "center")
    if rot in (90, 270):
        return (ref, x + 5.08, y - 2.54, "left"), ("Value", x + 5.08, y + 2.54, "left")
    return (ref, x, y - 5.08, "left"), ("Value", x, y + 2.54, "left")


# 全局标签形状：契约网络按方向选，页内重复出现的电源类用 input（同页两个 output 会触发 ERC 冲突）。
# 分段 B/C 续画时，同名全局标签重复出现请沿用这里的形状。
SHAPE = {
    "BAT+": "input", "PACK+": "input", "FET_MID": "input", "GND": "input", "+3V3": "input",
    "AFE_WAKE": "input", "I2C_SCL": "input", "I2C_SDA": "input",
    "CHG_G": "output", "DSG_G": "output", "AFE_ALERT": "output",
    "CELL0": "passive", "CELL1": "passive", "CELL2": "passive", "CELL3": "passive",
    "CELL4": "passive", "CELL5": "passive", "CELL6": "passive", "CELL7": "passive",
    "CELL8": "passive", "SRP": "passive", "SRN": "passive",
    "NTC_CELL1": "passive", "NTC_CELL2": "passive",
    "NTC_FET": "passive", "NTC_SHUNT": "passive",
}

# U1 引脚 → (网络, 标签种类)。lbl=局部标签，glbl=全局标签。
U1_LEFT = [  # 镜像后原符号右侧的脚（电芯 + 3V3/DSG/PACKP/xALERT/CHG）
    ("26", "AFE_3V3", "lbl"),
    ("39", "DSG_G", "glbl"),
    ("38", "PACKP", "lbl"),
    ("28", "AFE_ALERT", "glbl"),
    ("14", "VC0", "lbl"), ("13", "VC1", "lbl"), ("12", "VC2", "lbl"), ("11", "VC3", "lbl"),
    ("10", "VC4", "lbl"), ("9", "VC5", "lbl"), ("8", "VC6", "lbl"), ("7", "VC7", "lbl"),
    ("44", "CHG_G", "glbl"),
]
# C9–C16（脚 5,4,3,2,1,48,47,46）与 C8（脚 6）并到 VC8：一条竖线 + 各脚短线（spec §1.3）
U1_VC8_PINS = ["6", "5", "4", "3", "2", "1", "48", "47", "46"]
U1_RIGHT = [  # 镜像后原符号左侧的脚（通讯/NTC/采样/电源）
    ("30", "AFE_WAKE", "glbl"),
    ("24", "REGCTRL", "lbl"),
    ("25", "REGIN", "lbl"),
    ("31", "I2C_SCL", "glbl"),
    ("32", "I2C_SDA", "glbl"),
    ("16", "SRN_F", "lbl"),
    ("15", "SRP_F", "lbl"),
    ("42", "VCP", "lbl"),
    ("43", "VMID", "lbl"),
    ("22", "AFE_VREF", "lbl"),
    ("45", "VTOP", "lbl"),
    ("20", "NTC_CELL1", "glbl"),
    ("19", "NTC_CELL2", "glbl"),
    ("18", "NTC_FET", "glbl"),
    ("17", "NTC_SHUNT", "glbl"),
    ("21", "NTCB", "lbl"),
]
# NC 8 脚（spec §1.3）：29 WDT（严禁上拉）、33 SDO、34 GPIO3、35 GPIO2、36 GPIO1、37 GPIOHV1、40 N/C、41 SBYDSG
U1_NC = ["29", "33", "34", "35", "36", "37", "40", "41"]

LEFT_STUB = 5.08    # U1 左侧引脚短线长度
RIGHT_STUB = 5.08   # U1 右侧引脚短线长度
TOP_STUB = 5.08     # VDD（顶）/ AGND（底）


def sym_origin(comp):
    return (comp[4], comp[5], comp[6], comp[8] if len(comp) > 8 else False)


def pins_of(comp):
    return parse_pins(read_symbol(comp[1]))


def gen():
    P = {}
    for c in COMPONENTS:
        x, y, rot, mir = sym_origin(c)
        for num, (ix, iy) in pins_of(c).items():
            P[(c[0], num)] = pin_world(x, y, rot, ix, iy, mir)

    def pt(ref, num):
        return P[(ref, num)]

    L = []
    A = L.append

    A('(kicad_sch\n')
    A('\t(version 20250610)\n')
    A('\t(generator "gen_02_afe")\n')
    A('\t(generator_version "1.0")\n')
    A(f'\t(uuid "{PAGE_UUID}")\n')
    A('\t(paper "A3")\n')
    A('\t(title_block\n')
    A('\t\t(title "MP2797 采集与保护")\n')
    A('\t\t(date "2026-09-27")\n')
    A('\t\t(rev "v0.3-draw-r1")\n')
    A('\t\t(company "MP2645A-BMS")\n')
    A('\t\t(comment 1 "8S LiFePO4 200A BMS · MPS MP2797 AFE · 第 1 轮完成（分段 A+B+C）：U1 + §4 电芯 RC + §5 采样 + §6 驱动 + §7 NTC + §8 通讯 + §9 电源 + §10 J5")\n')
    A('\t)\n')

    A('\t(lib_symbols\n')
    seen = set()
    for c in COMPONENTS:
        if c[1] in seen:
            continue
        seen.add(c[1])
        A('\t' + read_symbol(c[1]).replace('\n', '\n\t').rstrip('\t') + '\n')
    A('\t)\n')

    def text_item(x, y, txt, size, just="left top"):
        A(f'\t(text "{esc(txt)}"\n')
        A('\t\t(exclude_from_sim no)\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} 0)\n')
        A('\t\t(effects\n')
        A('\t\t\t(font\n')
        A(f'\t\t\t\t(size {fmt(size)} {fmt(size)})\n')
        A('\t\t\t)\n')
        A(f'\t\t\t(justify {just})\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{uid("txt:" + txt + ":" + fmt(x) + ":" + fmt(y))}")\n')
        A('\t)\n')

    def global_label(name, shape, x, y, just):
        A(f'\t(global_label "{esc(name)}"\n')
        A(f'\t\t(shape {shape})\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} 0)\n')
        A('\t\t(effects\n')
        A('\t\t\t(font\n')
        A('\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t)\n')
        A(f'\t\t\t(justify {just})\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{uid("glbl:" + name + ":" + fmt(x) + ":" + fmt(y))}")\n')
        A('\t)\n')

    def local_label(name, x, y, just):
        A(f'\t(label "{esc(name)}"\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} 0)\n')
        A('\t\t(effects\n')
        A('\t\t\t(font\n')
        A('\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t)\n')
        A(f'\t\t\t(justify {just})\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{uid("lbl:" + name + ":" + fmt(x) + ":" + fmt(y))}")\n')
        A('\t)\n')

    def put_label(name, kind, x, y, just):
        if kind == "glbl":
            global_label(name, SHAPE.get(name, "input"), x, y, just)
        else:
            local_label(name, x, y, just)

    def wire2(x1, y1, x2, y2, key):
        A('\t(wire\n')
        A('\t\t(pts\n')
        A(f'\t\t\t(xy {fmt(x1)} {fmt(y1)})\n')
        A(f'\t\t\t(xy {fmt(x2)} {fmt(y2)})\n')
        A('\t\t)\n')
        A('\t\t(stroke\n')
        A('\t\t\t(width 0)\n')
        A('\t\t\t(type default)\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{uid("wire:" + key)}")\n')
        A('\t)\n')

    def wire(pts, key):
        for i in range(len(pts) - 1):
            wire2(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], f"{key}.{i}")

    def junction(x, y):
        A(f'\t(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0)'
          f' (uuid "{uid("jct:" + fmt(x) + ":" + fmt(y))}"))\n')

    def no_connect(x, y, key):
        A(f'\t(no_connect (at {fmt(x)} {fmt(y)}) (uuid "{uid("nc:" + key)}"))\n')

    def resolve(v):
        return pt(v[0], v[1]) if isinstance(v[0], str) else (v[0], v[1])

    def wire_ref(pts, key):
        wire([resolve(p) for p in pts], key)

    # =====================================================================
    # 标题与说明（左上空带；x ≤ 155，避让 U1 本体上沿 y=97.79 与右半页）
    # =====================================================================
    text_item(20.32, 16.51,
              "02 AFE：MP2797 采集与保护（8S，C9–C16 并到 C8；WDT 悬空；xALERT 高有效 100k 下拉）",
              3.5, "left top")
    text_item(20.32, 25.40,
              "U1 = MP2797DFP-0000-T（C18198873，TQFP-48）。本页 U1 全部引脚以「短线 + 标签」引出；"
              "未用脚放 NC 标志（29 WDT / 33 SDO / 34–37 GPIO / 40 N/C / 41 SBYDSG）。", 2.0)
    text_item(20.32, 30.48,
              "C9–C16（脚 5,4,3,2,1,48,47,46）用一条竖线并在 C8（脚 6）的 VC8 上，不串电阻、不加电容（Table 23「directly connect」）。",
              2.0)
    text_item(20.32, 35.56,
              "AFE_3V3 只接 C215，不与板上 +3V3 相连；NTC 四路上拉（R216–R219）都接 NTCB，不接任何 3V3。", 2.0)
    text_item(20.32, 40.64,
              "第 1 轮已画完（分段 A+B+C）：U1 + §9 电源 + §6 驱动 + §4 电芯 RC + §5 采样 + §10 J5 + §7 NTC + §8 通讯；"
              "全页 53 器件、164 个网表节点。", 2.0)

    # =====================================================================
    # U1 引脚 stub + 标签
    # =====================================================================
    for num, name, kind in U1_LEFT:
        px, py = pt("U1", num)
        lx = px - LEFT_STUB
        wire_ref([("U1", num), (lx, py)], f"u1_l{num}")
        put_label(name, kind, lx, py, "right")

    for num, name, kind in U1_RIGHT:
        px, py = pt("U1", num)
        lx = px + RIGHT_STUB
        wire_ref([("U1", num), (lx, py)], f"u1_r{num}")
        put_label(name, kind, lx, py, "left")

    # C9–C16 并到 C8：一条竖线（VC8 母线），各脚短线接上去
    bus_x = pt("U1", "6")[0] - LEFT_STUB
    bus_ys = [pt("U1", n)[1] for n in U1_VC8_PINS]
    for num in U1_VC8_PINS:
        px, py = pt("U1", num)
        wire_ref([("U1", num), (bus_x, py)], f"u1_vc8_{num}")
    wire([(bus_x, min(bus_ys)), (bus_x, max(bus_ys))], "u1_vc8_bus")
    local_label("VC8", bus_x, min(bus_ys), "right")
    for y in sorted(bus_ys)[1:-1]:      # 中间 7 个 T 接点要 junction，两端是拐角
        junction(bus_x, y)

    # VDD（脚 27，顶）/ AGND（脚 23，底）
    px, py = pt("U1", "27")
    wire_ref([("U1", "27"), (px, py - TOP_STUB)], "u1_vdd")
    local_label("AFE_VDD", px, py - TOP_STUB, "right")
    px, py = pt("U1", "23")
    wire_ref([("U1", "23"), (px, py + TOP_STUB)], "u1_agnd")
    global_label("GND", SHAPE["GND"], px, py + TOP_STUB, "right")

    for num in U1_NC:
        no_connect(*pt("U1", num), f"u1_{num}")

    # =====================================================================
    # §9 电源（spec §9.1–§9.4）
    # =====================================================================
    text_item(210.82, 43.18, "§9 电源：BAT+ 供电（U-1）", 2.4, "left top")
    # §9 的说明文字只能放在 y 45.72–53.34 这**一条窄带**里，而且每行 ≤ 89mm（写到 x≈300 为止）：
    #   * 往下 y≥54.7 是 C215–C218 那一列「标签 + 字段」的地盘（标签右端 272.82、字段左端 278.11），
    #     横向一伸过去就压字；
    #   * 往右 x≥304.72 是 §6 的说明（锚在同一批 y 上，原稿 §9 第 2 行写到 312.7，
    #     与 §6 第 2 行横向压了 7.9mm —— 这是分段 A 就带进来的缺陷，
    #     旧的 8e 因为「同一行会合并成一段」看不见它，改成比原始 span 之后才报出来）。
    # 宽度用标定过的笔画字体步进估算（窄 0.9507×size、宽 1.3120×size，见 obsidian-vault 自检要点）。
    text_item(210.82, 45.72,
              "U1.45 VTOP ← R212 20Ω ← BAT+；C212 470nF/100V 到 GND。", 1.8)
    text_item(210.82, 48.26,
              "U1.25 REGIN ← Q201(MMBT5551) 发射极（C214 10µF/10V）；", 1.8)
    text_item(210.82, 50.80,
              "Q201 基极 = REGCTRL、集电极 = REG_C；", 1.8)
    # 第 4 行必须收在 x<265 之前：x 265.02–272.82 是 AFE_3V3 标签的文字（锚点 273.05 右对齐），
    # 它的 y 是 54.70–56.61，和第 4 行的 52.83–55.73 纵向压了 1.03mm（高 dpi 裁图肉眼可见
    # 「3V3」正好夹在「到」与「BAT+」之间）。改短后收在 264.1（估宽）→ 实测约 262.7，留 2.3mm。
    text_item(210.82, 53.34,
              "C213 1µF、R213 510Ω：REG_C→BAT+。", 1.8)

    def hpart(ref, left, right, lk="lbl", rk="lbl", stub=5.08):
        """横放两脚件（rot=0）：pin1 在左，pin2 在右，各引短线 + 标签。"""
        p1, p2 = pt(ref, "1"), pt(ref, "2")
        wire_ref([(ref, "1"), (p1[0] - stub, p1[1])], f"{ref}_sl")
        put_label(left, lk, p1[0] - stub, p1[1], "right")
        wire_ref([(ref, "2"), (p2[0] + stub, p2[1])], f"{ref}_sr")
        put_label(right, rk, p2[0] + stub, p2[1], "left")

    def vpart(ref, top, bottom, tk="lbl", bk="lbl", stub=2.54):
        """竖放两脚件（rot=90）：pin2 在上、pin1 在下（库符号几何决定），各引短线 + 标签。"""
        p2, p1 = pt(ref, "2"), pt(ref, "1")
        wire_ref([(ref, "2"), (p2[0], p2[1] - stub)], f"{ref}_st")
        put_label(top, tk, p2[0], p2[1] - stub, "right")
        wire_ref([(ref, "1"), (p1[0], p1[1] + stub)], f"{ref}_sb")
        put_label(bottom, bk, p1[0], p1[1] + stub, "right")

    hpart("R212", "BAT+", "VTOP", "glbl", "lbl")
    vpart("C212", "VTOP", "GND", "lbl", "glbl")
    hpart("R213", "BAT+", "REG_C", "glbl", "lbl")
    vpart("C213", "REG_C", "GND", "lbl", "glbl")

    # Q201：B(1) 左、C(3) 右上、E(2) 右下
    for num, name, kind, dx in [("1", "REGCTRL", "lbl", -5.08),
                                ("3", "REG_C", "lbl", 5.08),
                                ("2", "REGIN", "lbl", 5.08)]:
        px, py = pt("Q201", num)
        wire_ref([("Q201", num), (px + dx, py)], f"q201_{num}")
        put_label(name, kind, px + dx, py, "right" if dx < 0 else "left")
    vpart("C214", "REGIN", "GND", "lbl", "glbl")

    # 内部 LDO 去耦：U1.26 / U1.27 / U1.22 / U1.21（spec §9.3/§9.4）
    vpart("C215", "AFE_3V3", "GND", "lbl", "glbl")
    vpart("C216", "AFE_VDD", "GND", "lbl", "glbl")
    vpart("C217", "AFE_VREF", "GND", "lbl", "glbl")
    vpart("C218", "NTCB", "GND", "lbl", "glbl")

    # =====================================================================
    # §6 高边驱动（spec §6.3/§6.4）
    # =====================================================================
    text_item(304.80, 43.18, "§6 高边驱动（CHG/DSG/VCP/VMID/PACKP）", 2.4, "left top")
    text_item(304.80, 48.26,
              "U1.43 VMID ← R214 100Ω ← FET_MID，C220 100nF/100V 到 GND。", 1.8)
    text_item(304.80, 53.34,
              "U1.38 PACKP ← R215 100Ω ← PACK+，C221 10nF/100V 到 GND", 1.8)
    text_item(304.80, 55.88, "（Table 18「不得增减」）。", 1.8)
    # 本区可用宽只有 101mm（x 304.80 → 406），长句必须拆；原两行长句渲染到 x≈420（越框）。
    # 拆成 4 行放在 y 91.44–99.06：上方 C221（y 86.36）的字段线在 88.9 附近，
    # 下方 §5 表头（y 105.41，size 2.4）的字顶从 105.0 起，两头都留 ≥2.5mm。
    text_item(304.80, 91.44, "U1.42 VCP ↔ VMID 跨接 C219 100nF/100V；", 1.8)
    text_item(304.80, 93.98, "C226 为扩展焊盘（DNP，样板实测 VCP 跌落后再定）。", 1.8)
    text_item(304.80, 96.52, "U1.44 CHG、U1.39 DSG 本页不串件，", 1.8)
    text_item(304.80, 99.06, "R_DRV/DZ/PNP 快关在 01 页。", 1.8)

    hpart("R214", "FET_MID", "VMID", "glbl", "lbl")
    vpart("C219", "VCP", "VMID", "lbl", "lbl")
    vpart("C226", "VCP", "VMID", "lbl", "lbl")
    vpart("C220", "VMID", "GND", "lbl", "glbl")
    hpart("R215", "PACK+", "PACKP", "glbl", "lbl")
    vpart("C221", "PACKP", "GND", "lbl", "glbl")

    # =====================================================================
    # §10 J5 采样端子（spec §10.2）
    # =====================================================================
    text_item(15.24, 45.72, "§10 J5 采样端子", 2.4, "left top")
    # §10 的说明也要压到 46mm 以内（写到 x≈60）：右边 x≥63.36 是 §4 的表头/说明，
    # 原稿第 2 行「1 NTC_CELL1 / 2 GND / 3 NTC_CELL2 / 4 GND」一路写到 x=74，
    # 和 §4 的表头「§4 电芯采样 RC（9 串）」（y 50.24–53.78）压在了一起 —— 同样是分段 A 带进来的。
    text_item(15.24, 48.26, "C40669 XH 2.50mm 13P 立式；", 1.6)
    text_item(15.24, 50.80, "1/3 = NTC_CELL1/2，2/4 = GND；", 1.6)
    text_item(15.24, 53.34, "5–13 = CELL0…CELL8；", 1.6)
    text_item(15.24, 55.88, "NTC 放低压端，线束短路", 1.6)
    text_item(15.24, 58.42, "不会把 29V 灌进 NTC 脚。", 1.6)

    # 13 个脚一律「引脚 → 2.54 短线 → 全局标签」，标签朝左，与 ①区左边界对齐。
    J5_NETS = ["NTC_CELL1", "GND", "NTC_CELL2", "GND"] + [f"CELL{i}" for i in range(9)]
    for i, name in enumerate(J5_NETS, start=1):
        px, py = pt("J5", str(i))
        wire_ref([("J5", str(i)), (px - 2.54, py)], f"j5_{i}")
        put_label(name, "glbl", px - 2.54, py, "right")

    # =====================================================================
    # §4 电芯采样 RC（spec §4.1–§4.4）
    # =====================================================================
    # 文字块的落位是被「字段线」顶住倒推出来的：这些注释一行能排到 x≈194，若第三行锚点 ≥61.6，
    # 渲染出的字底（锚点+2.4）就到 64.0，正好压上第 0 行 R201/D201 的字段线（63.9–65.8，实测重叠 0.1mm）。
    text_item(63.50, 50.80, "§4 电芯采样 RC（9 串）", 2.4, "left top")
    text_item(63.50, 55.25,
              "J5.5–13 CELL0–CELL8 → R201–R209 33Ω 1% → VC0–VC8 → U1.14/13/12/11/10/9/8/7/6。", 1.8)
    text_item(63.50, 57.79,
              "C201–C208 100nF/50V 跨相邻两个 VC（8 只，不接地）；C0 只挂 D201 稳压（阴极→VC0、阳极→GND）。", 1.8)
    text_item(63.50, 60.33,
              "均衡电流走串阻：33Ω 时典型 39mA、最坏 45mA，0805 耗散余量 1.5 倍；本页不出现任何 BAL* 标签。", 1.8)

    for n in range(9):
        hpart(f"R20{n + 1}", f"CELL{n}", f"VC{n}", "glbl", "lbl")
    for n in range(8):
        hpart(f"C20{n + 1}", f"VC{n}", f"VC{n + 1}", "lbl", "lbl")
    hpart("D201", "VC0", "GND", "lbl", "glbl")

    # =====================================================================
    # §5 电流采样 SRP/SRN（spec §5）
    # =====================================================================
    text_item(304.80, 105.41, "§5 电流采样（SRP/SRN 开尔文）", 2.4, "left top")
    text_item(304.80, 109.22, "SRP/SRN 取自分流器电池侧（01 页），", 1.8)
    text_item(304.80, 111.76, "经 R210/R211 100Ω → SRP_F/SRN_F → U1.15/U1.16；", 1.8)
    text_item(304.80, 114.30, "C209 100nF 跨 SRP_F↔SRN_F（差模）；", 1.8)
    text_item(304.80, 116.84, "C210/C211 各 100nF 到 GND（共模）。", 1.8)

    hpart("R210", "SRP", "SRP_F", "glbl", "lbl")
    hpart("R211", "SRN", "SRN_F", "glbl", "lbl")
    hpart("C209", "SRP_F", "SRN_F", "lbl", "lbl")
    vpart("C210", "SRP_F", "GND", "lbl", "glbl")
    vpart("C211", "SRN_F", "GND", "lbl", "glbl")

    # =====================================================================
    # §7 NTC ×4（spec §7）
    # =====================================================================
    # 说明文字只写到 x≈300 为止（右边 x>305 是 §5 的地盘，R211 的值文字在 y≈147.8–149.7，
    # 第一版一行写太长（163mm）被 8d 抓到相交，这里拆成 4 行短句。
    text_item(207.01, 145.42, "§7 NTC ×4（电芯 2 路 + FET / 分流器）", 2.4, "left top")
    text_item(207.01, 149.86,
              "R216–R219 = 10k 1% 上拉到 NTCB（不是 3V3）；C222–C225 = 1nF 为 DNP。", 1.8)
    text_item(207.01, 152.40,
              "（NTCB_DYNAMIC_ON=1；装了会让低温读数偏低）", 1.8)
    text_item(207.01, 154.94,
              "NTC_CELL1/2 走 J5.1/2 与 J5.3/4 的线束探头；", 1.8)
    text_item(207.01, 157.48,
              "NTC_FET → 01 页 RT3；NTC_SHUNT → 01 页 RT4。", 1.8)

    # 四行间距 17.78（不是 15.24）：行内最高是 C22x 顶标签 ink 到 y−7.4，下一行最低是位号
    # 字段 ink 从 y−6.4 起，净空约 3.0mm；首行还要给上面的说明文字留出 ~4mm。
    for r, c, net, yy in (("R216", "C222", "NTC_CELL1", 171.45),
                          ("R217", "C223", "NTC_CELL2", 189.23),
                          ("R218", "C224", "NTC_FET",   207.01),
                          ("R219", "C225", "NTC_SHUNT", 224.79)):
        hpart(r, "NTCB", net, "lbl", "glbl")
        vpart(c, net, "GND", "glbl", "glbl")

    # =====================================================================
    # §8 通讯与中断（spec §8）
    # =====================================================================
    text_item(304.80, 155.58, "§8 通讯与中断（I2C / xALERT / NSHDN）", 2.4, "left top")
    text_item(304.80, 160.66, "R220/R221 = 2.2k 1% 上拉到 +3V3（I2C 开漏必需）；", 1.8)
    text_item(304.80, 163.20, "R222 = 100k 1% 把 AFE_ALERT 下拉到 GND（xALERT 推挽、", 1.8)
    text_item(304.80, 165.74, "ALERT_POL 默认高有效，空闲低电平）；", 1.8)
    text_item(304.80, 168.28, "R223 = 10k 1% 把 AFE_WAKE 上拉到 +3V3（不是 AFE_3V3）。", 1.8)
    text_item(304.80, 170.82, "WDT（U1.29）悬空，已在 U1 侧放 NC 标志。", 1.8)

    vpart("R220", "+3V3", "I2C_SCL", "glbl", "glbl")
    vpart("R221", "+3V3", "I2C_SDA", "glbl", "glbl")
    vpart("R222", "AFE_ALERT", "GND", "glbl", "glbl")
    vpart("R223", "+3V3", "AFE_WAKE", "glbl", "glbl")

    # =====================================================================
    # 器件实例
    # =====================================================================
    def field(name, val, fx, fy, fa, fj="left", hide=False):
        """写一条 property。fj=="center" 时按 KiCad 惯例不写 justify 节点。"""
        A(f'\t\t(property "{name}" "{esc(val)}"\n')
        A(f'\t\t\t(at {fmt(fx)} {fmt(fy)} {fa})\n')
        A('\t\t\t(effects\n')
        A('\t\t\t\t(font\n')
        A('\t\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t\t)\n')
        if fj != "center":
            A(f'\t\t\t\t(justify {fj})\n')
        if hide:
            A('\t\t\t\thide\n')
        A('\t\t\t)\n')
        A('\t\t)\n')

    for c in COMPONENTS:
        ref, sym, val, lcsc, x, y, rot, dnp = c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7]
        mir = c[8] if len(c) > 8 else False
        (rref, rx, ry, rj), (vref, vx, vy, vj) = prop_pos(ref, x, y, rot)
        pins = pins_of(c)
        props = symbol_props(read_symbol(sym))
        fa = (360 - rot) % 360
        A('\t(symbol\n')
        A(f'\t\t(lib_id "jlc:{esc(sym)}")\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} {rot})\n')
        if mir:
            A('\t\t(mirror y)\n')
        A('\t\t(unit 1)\n')
        A('\t\t(exclude_from_sim no)\n')
        A('\t\t(in_bom yes)\n')
        A('\t\t(on_board yes)\n')
        A(f'\t\t(dnp {"yes" if dnp else "no"})\n')
        A(f'\t\t(uuid "{uid("sym:" + ref)}")\n')
        field("Reference", ref, rx, ry, fa, rj)
        field("Value", val, vx, vy, fa, vj)
        for fname, fval in [("Footprint", props.get("Footprint", "")),
                            ("Datasheet", props.get("Datasheet", "")),
                            ("LCSC", lcsc)]:
            field(fname, fval, x, y + 7.62, 0, "left", hide=True)
        for num in sorted(pins, key=lambda n: int(n)):
            A(f'\t\t(pin "{num}" (uuid "{uid("pin:" + ref + ":" + num)}"))\n')
        A('\t\t(instances\n')
        A('\t\t\t(project "mp2645a-bms"\n')
        A(f'\t\t\t\t(path "{PATH}"\n')
        A(f'\t\t\t\t\t(reference "{esc(ref)}")\n')
        A('\t\t\t\t\t(unit 1)\n')
        A('\t\t\t\t)\n')
        A('\t\t\t)\n')
        A('\t\t)\n')
        A('\t)\n')

    A('\t(embedded_fonts no)\n')
    A(')\n')
    return "".join(L)


def main():
    out = gen()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"已生成: {os.path.abspath(OUT)}（{len(out.encode('utf-8'))} 字节）")


if __name__ == "__main__":
    main()
