#!/usr/bin/env python3
"""生成 hardware/05_mcu_comm.kicad_sch（MCU 与通讯：CH32V203C8T6 + CAN + 调试 + LED/按键）。

幂等：同一输入跑两次输出逐字节相同（UUID 用 uuid.uuid5 按位号/用途派生）。
运行即覆盖生成 hardware/05_mcu_comm.kicad_sch。

    python3 hardware/gen/gen_05_mcu_comm.py

器件符号从 hardware/lib/jlc/jlc.kicad_sym 原样复制到本图 (lib_symbols ...)；
lib_id 用 jlc:<符号名>（顶层嵌入符号名 = lib_id，子单元名不带昵称），
实例带 Footprint/Datasheet/LCSC 字段（隐藏），J8/L2 带 (dnp yes)。
只改本图，不动库/根图/其它子图。

设计依据：design/05_mcu_comm-spec.md（Opus）+ 用户 2026-09-27 决定（U-1 删 RS485、
U-2 J8 1×6 2.54 DNP、U-3 只放 R55、U-4 SW1=用户键、U-5 接受待机超标、U-6 33pF C1562、
U-7 J7 1CAN_H/2CAN_L/3GND/4GND、U-8 绿灯 330Ω、U-9 删 PWR_EN、L2 DNP + R56/R57 0Ω 旁路）。

沿用 04 页教训：坐标全落 1.27mm 栅格；每条 wire 只 2 点；竖放件字段角 (360-rot)%360；
引脚几何以库读数为准（parse_pins/pin_world）；IC 引脚引短线 + 标签；
导线不穿本体/不经过非端点引脚；引脚处 ≥2 段导线端点相接补 junction。
"""
from __future__ import annotations

import os
import re
import uuid

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
JLCSYM = os.path.join(HW, "lib", "jlc", "jlc.kicad_sym")
OUT = os.path.join(HW, "05_mcu_comm.kicad_sch")

PAGE_UUID = "ef19efef-64fc-54ca-82f9-f901118054c4"
ROOT_UUID = "632f74a5-cd8f-58d8-9ac1-1bfbb611d555"
SHEET_UUID = "0739f2da-d4a5-5124-931f-263baaef6ebe"
PATH = f"/{ROOT_UUID}/{SHEET_UUID}"

NS = uuid.UUID("c3d2e1f0-9a8b-7c6d-5e4f-3a2b1c0d9e8f")


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
    block = block.replace(f'(symbol "{name}"', f'(symbol "jlc:{name}"', 1)
    return block


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


def pin_world(px: float, py: float, rot: int, ix: float, iy: float):
    if rot == 0:
        return (px + ix, py - iy)
    if rot == 90:
        return (px - iy, py - ix)
    if rot == 180:
        return (px - ix, py + iy)
    if rot == 270:
        return (px + iy, py + ix)
    raise ValueError(rot)


# 引脚名会画在本体边缘；0402 电容/晶振/LED 本体过窄，引脚名会互相粘连或压本体。
# 这些符号把引脚名置空（脚号保留）：极性/方向由 +3V3 标签与二极管/晶振图形表达。
HIDE_PIN_NAME_SYMS = {"X322512MSB4SI", "0402CG330J500NT", "FC-2012HRK-620D", "0805G"}


def hide_pin_names(block: str) -> str:
    """把符号块内所有 (name "X" 置空（脚号保留）。KiCad 只会在引脚块里出现 (name "。"""
    return re.sub(r'(\(name\s+)"[^"]*"', r'\1""', block)


# ---------------------------------------------------------------------------
# 器件表：位号 / 符号名 / 值 / LCSC / 位置(mm) / 旋转 / DNP
# 版面（spec §9）：左=电源/时钟/复位（去耦列 + 偏置列 + 晶振组），中=U6，
#   右=CAN 链（J7 右→U8→R55→R56/R57‖L2→U7 左）+ U7 外围 + J8 + LED + SW1。
# ---------------------------------------------------------------------------
COMPONENTS = [
    # ref, symbol, value, lcsc, x, y, rot, dnp
    ("U6", "CH32V203C8T6", "CH32V203C8T6", "C3001172", 203.20, 152.40, 0, False),
    # 左：去耦列（横放，pin1 左=+3V3，pin2 右=GND）
    ("C50", "CL05B104KO5NNNC", "100nF 16V", "C1525", 127.00, 121.92, 0, False),
    ("C51", "CL05B104KO5NNNC", "100nF 16V", "C1525", 127.00, 134.62, 0, False),
    ("C52", "CL05B104KO5NNNC", "100nF 16V", "C1525", 127.00, 147.32, 0, False),
    ("C53", "CL05B104KO5NNNC", "100nF 16V", "C1525", 127.00, 160.02, 0, False),
    ("C54", "CL05B104KO5NNNC", "100nF 16V", "C1525", 127.00, 172.72, 0, False),
    ("C55", "CL10A475KO8NNNC", "4.7µF 16V", "C19666", 127.00, 185.42, 0, False),
    # 左：偏置列（横放，pin1 左=信号，pin2 右=GND）
    ("C58", "CL05B104KO5NNNC", "100nF 16V", "C1525", 88.90, 96.52, 0, False),
    ("R50", "0402WGF1002TCE", "10k 1%", "C25744", 88.90, 109.22, 0, False),
    ("R51", "0402WGF1003TCE", "100k 1%", "C25741", 88.90, 121.92, 0, False),
    ("R52", "0402WGF1003TCE", "100k 1%", "C25741", 88.90, 134.62, 0, False),
    # 左：晶振组（C56 左、C57 右）
    ("Y1", "X322512MSB4SI", "12MHz", "C9002", 101.60, 209.55, 0, False),
    ("C56", "0402CG330J500NT", "33pF 50V", "C1562", 85.09, 212.09, 0, False),
    ("C57", "0402CG330J500NT", "33pF 50V", "C1562", 120.65, 207.01, 0, False),
    # 右：CAN 链（J7 右端 → U7 左端）
    ("J7", "ZX-XH2.54-4PZZ", "XH 4P", "C7429634", 393.70, 139.70, 0, False),
    ("U8", "PESD2CAN_C2687131", "PESD2CAN", "C2687131", 368.30, 116.84, 0, False),
    ("R55", "0603WAF1200T5E", "120Ω 1%", "C22787", 342.90, 138.43, 90, False),
    ("JP1", "PZ254V-11-02P", "终端跳线", "C492401", 347.98, 139.70, 90, False),
    ("R56", "0402WGF0000TCE", "0Ω", "C17168", 320.04, 133.35, 0, False),
    ("R57", "0402WGF0000TCE", "0Ω", "C17168", 320.04, 146.05, 0, False),
    ("L2", "ACT1210-510-2P-TL00", "51µH CMC", "C95572", 342.90, 175.26, 0, True),
    ("U7", "SN65HVD230M_TR-HG", "SN65HVD230M", "C55259679", 284.48, 143.51, 0, False),
    # 右：U7 外围（竖放列，x=274.32）
    ("R53", "0402WGF1002TCE", "10k 1%", "C25744", 274.32, 160.02, 90, False),
    ("C59", "CL05B104KO5NNNC", "100nF 16V", "C1525", 274.32, 185.42, 90, False),
    ("R54", "0402WGF0000TCE", "0Ω", "C17168", 274.32, 210.82, 90, False),
    # 右：调试 + 人机
    ("J8", "PZ254V-11-06P", "1×6 2.54mm", "C492405", 248.92, 182.88, 0, True),
    ("LED1", "FC-2012HRK-620D", "红 0805", "C84256", 312.42, 165.10, 0, False),
    ("LED2", "FC-2012HRK-620D", "红 0805", "C84256", 312.42, 177.80, 0, False),
    ("LED3", "0805G", "绿 0805", "C2297", 312.42, 190.50, 0, False),
    ("R58", "0402WGF1001TCE", "1k 1%", "C11702", 297.18, 166.37, 0, False),
    ("R59", "0402WGF1001TCE", "1k 1%", "C11702", 297.18, 179.07, 0, False),
    ("R60", "0402WGF3300TCE", "330Ω 1%", "C25104", 297.18, 191.77, 0, False),
    ("SW1", "TS-1187A-B-A-B", "按键", "C318884", 375.92, 180.34, 0, False),
]

PROP_OVERRIDE = {
    "U6": (("U6", 203.20, 88.90), ("Value", 203.20, 200.66)),
    "U7": (("U7", 284.48, 133.35), ("Value", 284.48, 152.40)),
    "U8": (("U8", 368.30, 93.98), ("Value", 368.30, 152.40)),
    "Y1": (("Y1", 101.60, 200.66), ("Value", 101.60, 217.17)),
    "LED1": (("LED1", 312.42, 160.02), ("Value", 312.42, 170.18)),
    "LED2": (("LED2", 312.42, 172.72), ("Value", 312.42, 182.88)),
    "LED3": (("LED3", 312.42, 185.42), ("Value", 312.42, 195.58)),
    "J7": (("J7", 393.70, 133.35), ("Value", 393.70, 146.05)),
    "J8": (("J8", 248.92, 168.91), ("Value", 248.92, 193.04)),
    "L2": (("L2", 342.90, 160.02), ("Value", 342.90, 196.85)),
    "SW1": (("SW1", 375.92, 172.72), ("Value", 375.92, 187.96)),
}


def prop_pos(ref, x, y, rot):
    if ref in PROP_OVERRIDE:
        return PROP_OVERRIDE[ref]
    if rot in (90, 270):
        return ((ref, x + 5.08, y - 2.54), ("Value", x + 5.08, y + 2.54))
    return ((ref, x, y - 5.08), ("Value", x, y + 2.54))


def sym_origin(comp):
    return (comp[4], comp[5], comp[6])


def pins_of(comp):
    return parse_pins(read_symbol(comp[1]))


def gen():
    P = {}
    for c in COMPONENTS:
        for num, (ix, iy) in pins_of(c).items():
            x, y, rot = sym_origin(c)
            P[(c[0], num)] = pin_world(x, y, rot, ix, iy)

    def pt(ref, num):
        return P[(ref, num)]

    L = []
    A = L.append

    A('(kicad_sch\n')
    A('\t(version 20250610)\n')
    A('\t(generator "gen_05_mcu_comm")\n')
    A('\t(generator_version "1.0")\n')
    A(f'\t(uuid "{PAGE_UUID}")\n')
    A('\t(paper "A3")\n')
    A('\t(title_block\n')
    A('\t\t(title "MCU 与通讯")\n')
    A('\t\t(date "2026-09-27")\n')
    A('\t\t(rev "v0.3-draw-r1")\n')
    A('\t\t(company "MP2645A-BMS")\n')
    A('\t\t(comment 1 "8S LiFePO4 200A BMS · MPS MP2797 + 开关电容均衡")\n')
    A('\t)\n')

    A('\t(lib_symbols\n')
    seen = set()
    for c in COMPONENTS:
        name = c[1]
        if name in seen:
            continue
        seen.add(name)
        block = read_symbol(name)
        if name in HIDE_PIN_NAME_SYMS:
            block = hide_pin_names(block)
        A('\t' + block.replace('\n', '\n\t').rstrip('\t') + '\n')
    A('\t)\n')

    def text_item(x, y, txt, size, just="left"):
        tu = uid("txt:" + txt + ":" + fmt(x) + ":" + fmt(y))
        A(f'\t(text "{esc(txt)}"\n')
        A('\t\t(exclude_from_sim no)\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} 0)\n')
        A('\t\t(effects\n')
        A('\t\t\t(font\n')
        A(f'\t\t\t\t(size {fmt(size)} {fmt(size)})\n')
        A('\t\t\t)\n')
        A(f'\t\t\t(justify {just})\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{tu}")\n')
        A('\t)\n')

    text_item(40.64, 40.64, "MCU 与通讯（CH32V203C8T6 + CAN）", 4.0, "left top")
    text_item(40.64, 53.34,
              "CH32V203C8T6 144MHz（12MHz×12）；CAN1 PA11/12→SN65HVD230（3.3V）；I2C1 PB6/7→02 页 MP2797；",
              2.0, "left top")
    text_item(40.64, 58.42,
              "BAL_CLK=PA8(TIM1_CH1 75kHz)+R52 100k 下拉；PRECHG_EN=PA1+R51 100k 下拉；AFE_WAKE=MP2797 NSHDN(PB5 开漏，上拉 R_WAK 在 02 页)；",
              2.0, "left top")
    text_item(40.64, 63.50,
              "差分对 120Ω（规则 0c：J7→U8→L2/R56/R57→U7 直通道，顶层不换层）；JP1 插帽接入 120Ω 终端，拔帽不用；J8 DNP，下载器勿从 1 脚供电。",
              2.0, "left top")
    text_item(40.64, 68.58, "I2C 上拉 R_I2C1/2 在 02 页。", 2.0, "left top")

    def global_label(name, shape, x, y, just="left"):
        gu = uid("glbl:" + name + ":" + fmt(x) + ":" + fmt(y))
        A(f'\t(global_label "{esc(name)}"\n')
        A(f'\t\t(shape {shape})\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} 0)\n')
        A('\t\t(effects\n')
        A('\t\t\t(font\n')
        A('\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t)\n')
        A(f'\t\t\t(justify {just})\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{gu}")\n')
        A('\t)\n')

    def local_label(name, x, y, just="left"):
        lu = uid("lbl:" + name + ":" + fmt(x) + ":" + fmt(y))
        A(f'\t(label "{esc(name)}"\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} 0)\n')
        A('\t\t(effects\n')
        A('\t\t\t(font\n')
        A('\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t)\n')
        A(f'\t\t\t(justify {just})\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{lu}")\n')
        A('\t)\n')

    def wire2(x1, y1, x2, y2, key):
        wu = uid("wire:" + key)
        A('\t(wire\n')
        A('\t\t(pts\n')
        A(f'\t\t\t(xy {fmt(x1)} {fmt(y1)})\n')
        A(f'\t\t\t(xy {fmt(x2)} {fmt(y2)})\n')
        A('\t\t)\n')
        A('\t\t(stroke\n')
        A('\t\t\t(width 0)\n')
        A('\t\t\t(type default)\n')
        A('\t\t)\n')
        A(f'\t\t(uuid "{wu}")\n')
        A('\t)\n')

    def wire(pts, key):
        for i in range(len(pts) - 1):
            wire2(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], f"{key}.{i}")

    def junction(x, y):
        ju = uid("jct:" + fmt(x) + ":" + fmt(y))
        A(f'\t(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0) (uuid "{ju}"))\n')

    def no_connect(x, y, key):
        nu = uid("nc:" + key)
        A(f'\t(no_connect (at {fmt(x)} {fmt(y)}) (uuid "{nu}"))\n')

    def resolve(v):
        if isinstance(v[0], str):
            return pt(v[0], v[1])
        return (v[0], v[1])

    def wire_ref(pts, key):
        wire([resolve(p) for p in pts], key)

    # ================= U6 引脚 stub + 标签 =================
    for num, name, kind in [
        ("1", "+3V3", "glbl"), ("5", "HSE_IN", "lbl"), ("6", "HSE_OUT", "lbl"),
        ("7", "NRST", "lbl"), ("8", "GND", "glbl"), ("9", "+3V3", "glbl"),
        ("11", "PRECHG_EN", "glbl"),
    ]:
        px, py = pt("U6", num)
        wire_ref([("U6", num), (160.02, py)], f"u6_l{num}")
        if kind == "glbl":
            global_label(name, "input" if name in ("+3V3", "GND") else "output", 160.02, py, "right")
        else:
            local_label(name, 160.02, py, "right")

    for num, name, kind in [
        ("25", "KEY", "lbl"), ("26", "LED1_K", "lbl"), ("27", "LED2_K", "lbl"),
        ("28", "LED3_K", "lbl"), ("29", "BAL_CLK", "glbl"), ("30", "DBG_TX", "lbl"),
        ("31", "DBG_RX", "lbl"), ("32", "CAN_RXD", "lbl"), ("33", "CAN_TXD", "lbl"),
        ("34", "SWDIO", "lbl"), ("35", "GND", "glbl"), ("36", "+3V3", "glbl"),
    ]:
        px, py = pt("U6", num)
        wire_ref([("U6", num), (245.11, py)], f"u6_r{num}")
        if kind == "glbl":
            global_label(name, "input" if name in ("+3V3", "GND") else "output", 245.11, py, "left")
        else:
            local_label(name, 245.11, py, "left")

    for num, name, just in [("23", "GND", "right"), ("24", "+3V3", "left")]:
        px, py = pt("U6", num)
        wire_ref([("U6", num), (px, 198.12)], f"u6_b{num}")
        global_label(name, "input", px, 198.12, just)

    for num, name, kind, lx, ly, just in [
        ("37", "SWCLK", "lbl", 236.22, 114.30, "left"),
        ("40", "AFE_ALERT", "glbl", 214.63, 109.22, "left"),
        ("41", "AFE_WAKE", "glbl", 212.09, 104.14, "left"),
        ("42", "I2C_SCL", "glbl", 209.55, 99.06, "left"),
        ("43", "I2C_SDA", "glbl", 207.01, 93.98, "left"),
        ("44", "BOOT0", "lbl", 204.47, 106.68, "right"),
        ("47", "GND", "glbl", 196.85, 106.68, "right"),
        ("48", "+3V3", "glbl", 194.31, 101.60, "right"),
    ]:
        px, py = pt("U6", num)
        wire_ref([("U6", num), (lx, ly)], f"u6_t{num}")
        if kind == "glbl":
            shape = "input" if name in ("+3V3", "GND") else ("output" if name == "AFE_WAKE" else "input")
            global_label(name, shape, lx, ly, just)
        else:
            local_label(name, lx, ly, just)

    for num in ["2", "3", "4", "10", "12", "13", "14", "15", "16", "17", "18", "19",
                "20", "21", "22", "38", "39", "45", "46"]:
        no_connect(*pt("U6", num), f"u6_{num}")

    # ================= 去耦列（横放：pin1 左=+3V3、pin2 右=GND）=================
    for ref in ["C50", "C51", "C52", "C53", "C54", "C55"]:
        p1 = pt(ref, "1")
        p2 = pt(ref, "2")
        wire_ref([(ref, "1"), (p1[0] - 8.89, p1[1])], f"{ref}_p")
        global_label("+3V3", "input", p1[0] - 8.89, p1[1], "left")
        wire_ref([(ref, "2"), (p2[0] + 8.89, p2[1])], f"{ref}_g")
        global_label("GND", "input", p2[0] + 8.89, p2[1], "left")

    # ================= 偏置列（横放：pin1 左=信号、pin2 右=GND）=================
    for ref, name, kind in [("C58", "NRST", "lbl"), ("R50", "BOOT0", "lbl"),
                            ("R51", "PRECHG_EN", "glbl"), ("R52", "BAL_CLK", "glbl")]:
        p1 = pt(ref, "1")
        p2 = pt(ref, "2")
        wire_ref([(ref, "1"), (p1[0] - 10.16, p1[1])], f"{ref}_s")
        if kind == "glbl":
            global_label(name, "output", p1[0] - 10.16, p1[1], "right")
        else:
            local_label(name, p1[0] - 10.16, p1[1], "right")
        wire_ref([(ref, "2"), (p2[0] + 10.16, p2[1])], f"{ref}_g")
        global_label("GND", "input", p2[0] + 10.16, p2[1], "left")

    # ================= 晶振组（C56 左、C57 右）=================
    wire_ref([("Y1", "1"), ("C56", "2")], "y1_c56")
    wire_ref([("Y1", "1"), (pt("Y1", "1")[0], pt("Y1", "1")[1] + 7.62)], "y1_hsein")
    local_label("HSE_IN", pt("Y1", "1")[0], pt("Y1", "1")[1] + 7.62, "left")
    wire_ref([("C56", "1"), (pt("C56", "1")[0] - 7.62, pt("C56", "1")[1])], "c56_g")
    global_label("GND", "input", pt("C56", "1")[0] - 7.62, pt("C56", "1")[1], "left")
    wire_ref([("Y1", "3"), ("C57", "1")], "y1_c57")
    wire_ref([("Y1", "3"), (pt("Y1", "3")[0], pt("Y1", "3")[1] - 7.62)], "y1_hseout")
    local_label("HSE_OUT", pt("Y1", "3")[0], pt("Y1", "3")[1] - 7.62, "left")
    wire_ref([("C57", "2"), (pt("C57", "2")[0] + 7.62, pt("C57", "2")[1])], "c57_g")
    global_label("GND", "input", pt("C57", "2")[0] + 7.62, pt("C57", "2")[1], "left")
    wire_ref([("Y1", "4"), (pt("Y1", "4")[0], pt("Y1", "4")[1] - 7.62)], "y1_g4")
    global_label("GND", "input", pt("Y1", "4")[0], pt("Y1", "4")[1] - 7.62, "left")
    wire_ref([("Y1", "2"), (pt("Y1", "2")[0] + 7.62, pt("Y1", "2")[1])], "y1_g2")
    global_label("GND", "input", pt("Y1", "2")[0] + 7.62, pt("Y1", "2")[1], "left")
    junction(*pt("Y1", "1"))
    junction(*pt("Y1", "3"))

    # ================= CAN 链（差分对 CAN_H 上 y=133.35、CAN_L 下 y=146.05）=================
    for num, name in [("1", "CAN_H"), ("2", "CAN_L"), ("3", "GND"), ("4", "GND")]:
        px, py = pt("J7", num)
        wire_ref([("J7", num), (381.00, py)], f"j7_{num}")
        if name == "GND":
            global_label("GND", "input", 381.00, py, "left")
        else:
            global_label(name, "bidirectional", 381.00, py, "left")

    wire_ref([("U8", "1"), (pt("U8", "1")[0], 133.35)], "u8_h")
    wire_ref([("U8", "2"), (pt("U8", "2")[0], 146.05)], "u8_l")
    wire_ref([("U8", "3"), (pt("U8", "3")[0], pt("U8", "3")[1] - 7.62)], "u8_g")
    global_label("GND", "input", pt("U8", "3")[0], pt("U8", "3")[1] - 7.62, "right")

    wire_ref([("R55", "2"), (pt("R55", "2")[0], 133.35)], "r55_h")

    # CAN_H 总线（连接器侧，右侧）：U8.1 → R55.2 → R56.2（右 pin）
    wire([(pt("U8", "1")[0], 133.35), pt("R55", "2")], "canh_1")
    wire([pt("R55", "2"), pt("R56", "2")], "canh_2")
    # 终端跳线：R55.1 → CAN_TERM（本页网络）→ JP1.1；JP1.2 → CAN_L 总线
    wire_ref([("R55", "1"), ("JP1", "1")], "can_term")
    wire_ref([("R55", "1"), (337.82, pt("R55", "1")[1])], "can_term_lbl")
    local_label("CAN_TERM", 337.82, pt("R55", "1")[1], "right")
    wire_ref([("JP1", "2"), (pt("JP1", "2")[0], 146.05)], "jp1_l")
    # CAN_L 总线（连接器侧）：U8.2 → JP1.2 折点 → R57.2（右 pin）
    wire([(pt("U8", "2")[0], 146.05), (pt("JP1", "2")[0], 146.05)], "canl_1")
    wire([(pt("JP1", "2")[0], 146.05), pt("R57", "2")], "canl_2")
    # 收发器侧 CAN_H_X / CAN_L_X（R56.1/R57.1 左 pin → 折到 U7.7/U7.6）
    wire([pt("R56", "1"), (302.26, 133.35)], "canhx_1")
    wire([(302.26, 133.35), (302.26, pt("U7", "7")[1])], "canhx_2")
    wire([(302.26, pt("U7", "7")[1]), pt("U7", "7")], "canhx_3")
    wire([pt("R57", "1"), (302.26, 146.05)], "canlx_1")
    wire([(302.26, 146.05), (302.26, pt("U7", "6")[1])], "canlx_2")
    wire([(302.26, pt("U7", "6")[1]), pt("U7", "6")], "canlx_3")

    local_label("CAN_H_X", 304.80, 133.35, "left")
    local_label("CAN_L_X", 304.80, 146.05, "left")
    global_label("CAN_H", "bidirectional", 355.60, 133.35, "left")
    global_label("CAN_L", "bidirectional", 355.60, 146.05, "left")

    junction(*pt("R55", "2"))
    junction(*pt("R55", "1"))
    junction(pt("JP1", "2")[0], 146.05)

    # ================= U7 引脚 =================
    for num, name, kind in [("1", "CAN_TXD", "lbl"), ("2", "GND", "glbl"),
                            ("3", "+3V3", "glbl"), ("4", "CAN_RXD", "lbl")]:
        px, py = pt("U7", num)
        wire_ref([("U7", num), (266.70, py)], f"u7_l{num}")
        if kind == "glbl":
            global_label(name, "input", 266.70, py, "right")
        else:
            local_label(name, 266.70, py, "right")
    wire_ref([("U7", "8"), (pt("U7", "8")[0], pt("U7", "8")[1] - 7.62)], "u7_rs")
    local_label("CAN_RS", pt("U7", "8")[0], pt("U7", "8")[1] - 7.62, "right")
    no_connect(*pt("U7", "5"), "u7_5")

    # ================= U7 外围（R53/C59/R54 竖放列）=================
    for ref, top, bottom, tkind, bkind in [
        ("R53", "+3V3", "CAN_TXD", "glbl", "lbl"),
        ("C59", "+3V3", "GND", "glbl", "glbl"),
        ("R54", "CAN_RS", "GND", "lbl", "glbl"),
    ]:
        p2 = pt(ref, "2")
        p1 = pt(ref, "1")
        wire_ref([(ref, "2"), (p2[0], p2[1] - 2.54)], f"{ref}_p")
        if tkind == "glbl":
            global_label(top, "input", p2[0], p2[1] - 2.54, "right")
        else:
            local_label(top, p2[0], p2[1] - 2.54, "right")
        wire_ref([(ref, "1"), (p1[0], p1[1] + 2.54)], f"{ref}_g")
        if bkind == "glbl":
            global_label(bottom, "input", p1[0], p1[1] + 2.54, "right")
        else:
            local_label(bottom, p1[0], p1[1] + 2.54, "right")

    # ================= J8 调试口 =================
    for num, name, kind in [("1", "+3V3", "glbl"), ("2", "SWDIO", "lbl"), ("3", "SWCLK", "lbl"),
                            ("4", "GND", "glbl"), ("5", "DBG_TX", "lbl"), ("6", "DBG_RX", "lbl")]:
        px, py = pt("J8", num)
        wire_ref([("J8", num), (241.30, py)], f"j8_{num}")
        if kind == "glbl":
            global_label(name, "input", 241.30, py, "right")
        else:
            local_label(name, 241.30, py, "right")

    # ================= LED1–3 + R58–R60 =================
    for led, res, kn in [("LED1", "R58", "LED1_K"), ("LED2", "R59", "LED2_K"), ("LED3", "R60", "LED3_K")]:
        anode = "2" if led in ("LED1", "LED2") else "1"
        cath = "1" if led in ("LED1", "LED2") else "2"
        ax, ay = pt(led, anode)
        wire_ref([(led, anode), (ax + 7.62, ay)], f"{led}_anode")
        global_label("+3V3", "input", ax + 7.62, ay, "left")
        wire_ref([(led, cath), (res, "2")], f"{led}_cath")
        rx, ry = pt(res, "1")
        wire_ref([(res, "1"), (rx - 7.62, ry)], f"{res}_k")
        local_label(kn, rx - 7.62, ry, "left")

    # ================= SW1 =================
    wire_ref([("SW1", "1"), ("SW1", "2")], "sw1_key")
    wire_ref([("SW1", "1"), (pt("SW1", "1")[0] - 7.62, pt("SW1", "1")[1])], "sw1_keylbl")
    local_label("KEY", pt("SW1", "1")[0] - 7.62, pt("SW1", "1")[1], "left")
    wire_ref([("SW1", "3"), ("SW1", "4")], "sw1_gnd")
    wire_ref([("SW1", "3"), (pt("SW1", "3")[0] - 7.62, pt("SW1", "3")[1])], "sw1_gndlbl")
    global_label("GND", "input", pt("SW1", "3")[0] - 7.62, pt("SW1", "3")[1], "left")
    junction(*pt("SW1", "1"))
    junction(*pt("SW1", "3"))

    # ================= L2 共模电感（DNP，与 R56/R57 二选一）=================
    for num, name in [("4", "CAN_H"), ("3", "CAN_L"), ("1", "CAN_H_X"), ("2", "CAN_L_X")]:
        px, py = pt("L2", num)
        d = -5.08 if num in ("4", "1") else 5.08
        wire_ref([("L2", num), (px, py + d)], f"l2_{num}")
        if name in ("CAN_H", "CAN_L"):
            global_label(name, "bidirectional", px, py + d, "left")
        else:
            local_label(name, px, py + d, "left")
    text_item(302.26, 152.40, "L2 与 R56/R57 二选一", 1.8, "left top")

    # ================= 器件实例 =================
    for ref, sym, val, lcsc, x, y, rot, dnp in COMPONENTS:
        (rref, rx, ry), (vref, vx, vy) = prop_pos(ref, x, y, rot)
        pins = pins_of((ref, sym, val, lcsc, x, y, rot, dnp))
        props = symbol_props(read_symbol(sym))
        footprint = props.get("Footprint", "")
        datasheet = props.get("Datasheet", "")
        su = uid("sym:" + ref)
        fa = (360 - rot) % 360
        A('\t(symbol\n')
        A(f'\t\t(lib_id "jlc:{esc(sym)}")\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} {rot})\n')
        A('\t\t(unit 1)\n')
        A('\t\t(exclude_from_sim no)\n')
        A('\t\t(in_bom yes)\n')
        A('\t\t(on_board yes)\n')
        A(f'\t\t(dnp {"yes" if dnp else "no"})\n')
        A(f'\t\t(uuid "{su}")\n')
        A(f'\t\t(property "Reference" "{esc(ref)}"\n')
        A(f'\t\t\t(at {fmt(rx)} {fmt(ry)} {fa})\n')
        A('\t\t\t(effects\n')
        A('\t\t\t\t(font\n')
        A('\t\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t\t)\n')
        A('\t\t\t\t(justify left)\n')
        A('\t\t\t)\n')
        A('\t\t)\n')
        A(f'\t\t(property "Value" "{esc(val)}"\n')
        A(f'\t\t\t(at {fmt(vx)} {fmt(vy)} {fa})\n')
        A('\t\t\t(effects\n')
        A('\t\t\t\t(font\n')
        A('\t\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t\t)\n')
        A('\t\t\t\t(justify left)\n')
        A('\t\t\t)\n')
        A('\t\t)\n')
        for fname, fval in [("Footprint", footprint), ("Datasheet", datasheet), ("LCSC", lcsc)]:
            A(f'\t\t(property "{fname}" "{esc(fval)}"\n')
            A(f'\t\t\t(at {fmt(x)} {fmt(y + 7.62)} 0)\n')
            A('\t\t\t(effects\n')
            A('\t\t\t\t(font\n')
            A('\t\t\t\t\t(size 1.27 1.27)\n')
            A('\t\t\t\t)\n')
            A('\t\t\t\t(justify left)\n')
            A('\t\t\t\thide\n')
            A('\t\t\t)\n')
            A('\t\t)\n')
        for num in sorted(pins, key=lambda n: int(n)):
            pu = uid("pin:" + ref + ":" + num)
            A(f'\t\t(pin "{num}" (uuid "{pu}"))\n')
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
