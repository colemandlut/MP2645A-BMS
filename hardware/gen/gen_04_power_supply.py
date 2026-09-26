#!/usr/bin/env python3
"""生成 hardware/04_power_supply.kicad_sch（辅助电源：LMR16006X 直降 3.3V）。

幂等：同一输入跑两次输出逐字节相同（UUID 用 uuid.uuid5 按位号/用途派生）。
运行即覆盖生成 hardware/04_power_supply.kicad_sch。

    python3 hardware/gen/gen_04_power_supply.py

器件符号从 hardware/lib/jlc/jlc.kicad_sym 复制到本图 (lib_symbols ...)；
lib_id 用 jlc:<符号名>（顶层嵌入符号名 = lib_id，带 jlc: 前缀；子单元名不带昵称），
实例加 LCSC 字段（隐藏）。只改本图，不动库/根图/其它子图。

第 2 轮变更（主代理核查）：
  * lib_id 带 jlc: 前缀，嵌入符号与库一致 → 消除 11 条 lib_symbol_issues（library ''）。
  * 引脚电气类型不再在脚本里改（库已由 fetch_jlc_parts.py 统一归一为 passive），原样复制。
  * 位号统一「前缀+数字」40 段：C_IN_E→C40(47µF/63V RV63V47M6X8)、C_BST→C41、
    C_IN1→C42、C_OUT1→C43、R_FB1→R40、R_FB2→R41；U4/F11/D7/L1 不变。
  * 删 D6（SMBJ33A，BAT+ 上 D3 已钳位 ≈53V < VIN 65V）。

注意（KiCad 10 实测）：
  * 每条 (wire ...) 只能有 2 个点；折线要拆成多段 2 点导线。
  * 坐标全部落在 1.27mm 栅格上（输出统一 :.2f，消除浮点尾巴）。
"""
from __future__ import annotations

import os
import re
import uuid

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
JLCSYM = os.path.join(HW, "lib", "jlc", "jlc.kicad_sym")
OUT = os.path.join(HW, "04_power_supply.kicad_sch")

# 本页固定 UUID（与骨架一致，幂等）
PAGE_UUID = "30cbc880-65ec-5706-9809-92789c0e1f35"
ROOT_UUID = "632f74a5-cd8f-58d8-9ac1-1bfbb611d555"
SHEET_UUID = "c20e45f9-c9d2-50e9-b477-f2356556af13"
PATH = f"/{ROOT_UUID}/{SHEET_UUID}"

# 生成 UUID 的命名空间（与本页其它元素区分，独立于骨架的 NS）
NS = uuid.UUID("7a1f2e3c-4b5d-4e6f-8a9b-0c1d2e3f4a5b")


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def fmt(v: float) -> str:
    """坐标输出：保留 2 位小数，消除浮点尾巴（所有值本就是 1.27 的整数倍）。"""
    return f"{v:.2f}"


def esc(txt: str) -> str:
    return txt.replace("\\", "\\\\").replace('"', '\\"')


def read_symbol(name: str) -> str:
    """从 jlc.kicad_sym 抽出 (symbol "name" ...) 完整块（括号配对），
    只把顶层符号名加 jlc: 前缀（子单元名不带昵称，保持与库一致）；
    引脚电气类型原样保留（库已由 fetch_jlc_parts.py 统一归一为 passive，不在这里改）。"""
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


def parse_pins(block: str) -> dict:
    """返回 {pin_number: (ix, iy)}（符号内坐标，Y 向上）。"""
    pins = {}
    for m in re.finditer(
        r'\(pin\s+\S+\s+\S+\s+\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\).*?'
        r'\(number\s+"([^"]+)"',
        block, re.S,
    ):
        pins[m.group(4)] = (float(m.group(1)), float(m.group(2)))
    return pins


def pin_world(px: float, py: float, rot: int, ix: float, iy: float):
    """符号内坐标 (ix, iy)（Y 向上）→ 图纸坐标（Y 向下）。已用 kicad-cli 网表实测。"""
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
# 器件表：位号 / 符号名 / 值 / LCSC / 位置(mm) / 旋转
# ---------------------------------------------------------------------------
COMPONENTS = [
    # ref, symbol, value, lcsc, x, y, rot
    ("U4",   "LMR16006XDDCR",   "LMR16006XDDCR", "C87080",   121.92, 50.80,   0),
    ("F11",  "0466001.NRHF",    "1A",            "C151135",   50.80, 50.80,   0),
    ("C40",  "RV63V47M6X8",     "47µF 63V",      "C48971005", 78.74, 55.88, 270),
    ("C42",  "FS32X475K101EGG", "4.7µF 100V",    "C381466",   91.44, 55.88,  90),
    ("C41",  "CL05B104KO5NNNC", "100nF 16V",     "C1525",    121.92, 43.18,   0),
    ("D7",   "SS210",           "SS210",         "C14996",   139.70, 53.34, 270),
    ("L1",   "SWPA5040S220MT",  "22µH",          "C68434",   157.48, 48.26,   0),
    ("C43",  "CL21A226MAQNNNE", "22µF 25V",      "C45783",   170.18, 53.34,  90),
    ("R40",  "0402WGF3302TCE",  "33k 1%",        "C25779",   177.80, 60.96,   0),
    ("R41",  "0402WGF1002TCE",  "10k 1%",        "C25744",   195.58, 60.96,   0),
]

# 位号/值文字位置（绝对坐标，justify left），避开导线与符号
PROP_POS = {
    "U4":  (("U4", 104.14, 43.18), ("Value", 127.00, 60.96)),
    "F11": (("F11", 45.72, 45.72), ("Value", 50.80, 55.88)),
    "C40": (("C40", 73.66, 45.72), ("Value", 78.74, 66.04)),
    "C42": (("C42", 86.36, 45.72), ("Value", 91.44, 66.04)),
    "C41": (("C41", 111.76, 40.64), ("Value", 121.92, 40.64)),
    "D7":  (("D7", 134.62, 55.88), ("Value", 139.70, 68.58)),
    "L1":  (("L1", 152.40, 43.18), ("Value", 157.48, 53.34)),
    "C43": (("C43", 165.10, 55.88), ("Value", 170.18, 68.58)),
    "R40": (("R40", 177.80, 58.42), ("Value", 177.80, 66.04)),
    "R41": (("R41", 195.58, 58.42), ("Value", 190.50, 66.04)),
}


def sym_origin(comp):
    return (comp[4], comp[5], comp[6])


def pins_of(comp):
    return parse_pins(read_symbol(comp[1]))


def pw(comp, num):
    x, y, rot = sym_origin(comp)
    ix, iy = pins_of(comp)[num]
    return pin_world(x, y, rot, ix, iy)


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------
def gen():
    P = {}  # P[(ref, num)] = (x, y) 图纸坐标
    for c in COMPONENTS:
        for num, (ix, iy) in pins_of(c).items():
            x, y, rot = sym_origin(c)
            P[(c[0], num)] = pin_world(x, y, rot, ix, iy)

    def pt(ref, num):
        return P[(ref, num)]

    L = []
    A = L.append

    # 文件头
    A('(kicad_sch\n')
    A('\t(version 20250610)\n')
    A('\t(generator "gen_04_power_supply")\n')
    A('\t(generator_version "1.0")\n')
    A(f'\t(uuid "{PAGE_UUID}")\n')
    A('\t(paper "A3")\n')
    A('\t(title_block\n')
    A('\t\t(title "辅助电源")\n')
    A('\t\t(date "2026-09-26")\n')
    A('\t\t(rev "v0.3-draw-r2")\n')
    A('\t\t(company "MP2645A-BMS")\n')
    A('\t\t(comment 1 "8S LiFePO4 200A BMS · MPS MP2797 + 开关电容均衡")\n')
    A('\t)\n')

    # lib_symbols：复制 11 个符号
    A('\t(lib_symbols\n')
    for c in COMPONENTS:
        block = read_symbol(c[1])
        A('\t' + block.replace('\n', '\n\t').rstrip('\t') + '\n')
    A('\t)\n')

    # 说明文字
    def text_item(x, y, txt, size, just="left"):
        tu = uid("txt:" + txt)
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

    text_item(20, 20, "辅助电源（LMR16006X 直降 3.3V）", 4.0, "left top")
    text_item(20, 32, "LMR16006X 700kHz 非同步 buck；D7 续流必需；SHDN 悬空=常开；输入 C40 47µF/63V；L1 下方全层禁铜（规则 2d）", 2.0, "left top")

    # 全局标签
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

    global_label("BAT+", "input", 25.40, 50.80, "left")
    global_label("+3V3", "output", 203.20, 48.26, "left")

    # GND 全局标签（多个同名）
    for x, y in [(78.74, 63.50), (91.44, 63.50), (104.14, 55.88),
                 (139.70, 63.50), (170.18, 63.50), (200.66, 66.04)]:
        global_label("GND", "input", x, y, "left")

    # 局部标签
    local_label("VIN_F", 60.96, 50.80, "left")
    local_label("SW_3V3", 144.78, 48.26, "left")
    local_label("CB_3V3", 111.76, 45.72, "right")
    local_label("FB_3V3", 185.42, 63.50, "left")
    local_label("FB_3V3", 111.76, 53.34, "right")

    # 导线：每条 (wire) 只含 2 个点；折线拆成多段
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

    wire([(25.40, 50.80), pt("F11", "1")], "bat_f11")
    wire([pt("F11", "2"), pt("U4", "5")], "vinf_rail")
    wire([pt("U4", "1"), (111.76, 43.18), pt("C41", "1")], "cb_bst")
    wire([pt("C41", "2"), (132.08, 43.18), pt("U4", "6")], "bst_sw")
    wire([pt("U4", "6"), pt("L1", "1")], "sw_rail")
    wire([pt("L1", "2"), (203.20, 48.26)], "out_rail")
    wire([pt("R40", "1"), (172.72, 48.26)], "fb1_rail")
    wire([pt("R40", "2"), pt("R41", "1")], "fb_node")
    wire([(185.42, 60.96), (185.42, 63.50)], "fb_stub")
    wire([pt("R41", "2"), (200.66, 66.04)], "fb2_gnd")
    wire([pt("C40", "2"), (78.74, 63.50)], "cine_gnd")
    wire([pt("C42", "1"), (91.44, 63.50)], "cin1_gnd")
    wire([pt("U4", "2"), (104.14, 50.80), (104.14, 55.88)], "u4_gnd")
    wire([pt("D7", "2"), (139.70, 63.50)], "d7_gnd")
    wire([pt("C43", "1"), (170.18, 63.50)], "cout1_gnd")

    # 结点（T 型接点）
    def junction(x, y):
        ju = uid("jct:" + fmt(x) + ":" + fmt(y))
        A(f'\t(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0) (uuid "{ju}"))\n')

    for x, y in [(78.74, 50.80), (91.44, 50.80), (132.08, 48.26),
                 (139.70, 48.26), (170.18, 48.26), (172.72, 48.26), (185.42, 60.96)]:
        junction(x, y)

    # 无连接标志（SHDN 悬空 = 常开）
    sx, sy = pt("U4", "4")
    nu = uid("nc:u4:4")
    A(f'\t(no_connect (at {fmt(sx)} {fmt(sy)}) (uuid "{nu}"))\n')

    # 器件实例
    for ref, sym, val, lcsc, x, y, rot in COMPONENTS:
        (rref, rx, ry), (vref, vx, vy) = PROP_POS[ref]
        pins = pins_of((ref, sym, val, lcsc, x, y, rot))
        su = uid("sym:" + ref)
        A('\t(symbol\n')
        A(f'\t\t(lib_id "jlc:{esc(sym)}")\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} {rot})\n')
        A('\t\t(unit 1)\n')
        A('\t\t(exclude_from_sim no)\n')
        A('\t\t(in_bom yes)\n')
        A('\t\t(on_board yes)\n')
        A('\t\t(dnp no)\n')
        A(f'\t\t(uuid "{su}")\n')
        A(f'\t\t(property "Reference" "{esc(ref)}"\n')
        A(f'\t\t\t(at {fmt(rx)} {fmt(ry)} 0)\n')
        A('\t\t\t(effects\n')
        A('\t\t\t\t(font\n')
        A('\t\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t\t)\n')
        A('\t\t\t\t(justify left)\n')
        A('\t\t\t)\n')
        A('\t\t)\n')
        A(f'\t\t(property "Value" "{esc(val)}"\n')
        A(f'\t\t\t(at {fmt(vx)} {fmt(vy)} 0)\n')
        A('\t\t\t(effects\n')
        A('\t\t\t\t(font\n')
        A('\t\t\t\t\t(size 1.27 1.27)\n')
        A('\t\t\t\t)\n')
        A('\t\t\t\t(justify left)\n')
        A('\t\t\t)\n')
        A('\t\t)\n')
        A(f'\t\t(property "LCSC" "{esc(lcsc)}"\n')
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
    print(f"已生成: {os.path.abspath(OUT)}（{len(out)} 字节）")


if __name__ == "__main__":
    main()
