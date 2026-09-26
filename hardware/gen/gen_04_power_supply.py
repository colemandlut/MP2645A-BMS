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
  * 位号统一「前缀+数字」40 段；U4/F11/D7/L1 不变；删 D6（SMBJ33A）。

第 3 轮变更（版面返工，只改版面不改连接）：
  * U4 每个脚引 ≥5.08mm 短线，线端放局部标签，组与 U4 之间靠同名标签相连。
  * 分组左→右；位号/值重排（竖放件位号与值在右侧水平书写）。

第 4 轮变更（按 Opus 复核 + 用户 13:57 第 2 轮换料）：
  * P0-1：每个实例补 Footprint（jlc:…，取库符号同值）+ Datasheet（隐藏）+ LCSC（隐藏）。
  * P1-1/P1-2：F11 与 VIN_F 之间串 R42 10Ω（1206W4F100JT5E, C17903），新网络 VIN_R
    （保险丝后、串阻前）；VIN_F 浪涌/上电 I²t 被 R42+C40 的 RC 压住（替代已删 D6）。
  * 换料：U4 LCSC C87080→C54823941（值 LMR16006XDDCR (Tokmas)，600kHz）；
    F11 0466001.NRHF→JFC1206-1100FS（值 1A 63V，C136343）；
    C42 4.7µF/1210→CL31B105KCHNNNE 1µF/100V（C13832）并新增 C44 同件并联；
    第 5 轮后（主代理，用户 14:46 决定）：C42/C44 改 CCTC TCC1206X7R105K101HT（C282823），同规格 1µF/100V X7R 1206。
    C43 22µF/25V 0805→CL10A226MQ8NRNC 22µF/6.3V 0603（C59461）。
  * C42/C44 并排、紧挨 U4.VIN（串阻后高频回路就近）；图名/说明文字回图纸左上角。

第 5 轮变更（按 Opus 复核第 2 轮 P1-1/P1-2 + 取料报告 parts-r5）：
  * P1-1：R42 10Ω 普通厚膜 → FCR1206J56RP055W（56Ω 5% 熔断 1206, C153337）。
    VIN_F 短路时 ≥5W 手册保证 <30s 受控开路；F11 留作 VIN_R 短路二级保护。
  * P1-2：新增 C45 CL21B104KCFNNNE（100nF 100V, C28233, jlc:C0805）贴 U4.VIN，
    接 VIN_F–GND，排在三颗输入陶瓷中最靠 U4 的一列（C45/C42/C44 各距 25.4mm）。
  * P2-5：U4 的 Datasheet 字段覆盖为 Tokmas 件 PDF（DATASHEET_OVERRIDE）。
  * P2-6：C45.2 / C42.2 / C43.2 三处「引脚 + 两段共线导线」T 型接点补 junction。

注意（KiCad 10 实测）：
  * 每条 (wire ...) 只能有 2 个点；折线要拆成多段 2 点导线。
  * 坐标全部落在 1.27mm 栅格上（输出统一 :.2f，消除浮点尾巴），否则 ERC 报 endpoint_off_grid。
  * 同名符号（C42/C44 共用 TCC1206X7R105K101HT）在 lib_symbols 只写一次。
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


def symbol_props(block: str) -> dict:
    """符号块里的 property 值（Footprint / Datasheet / Reference / Value …）。"""
    return {m.group(1): m.group(2)
            for m in re.finditer(r'\(property "([^"]+)" "([^"]*)"', block)}


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
# 第 4 轮（左→右：BAT+→F11→R42→C40 输入组；U4 居中；C42/C44 紧挨 U4.VIN；
#           D7→L1→C43 输出组；R40/R41 反馈组；C41 在 U4 上方）
# 所有坐标都是 1.27mm 的整数倍（否则 ERC 报 endpoint_off_grid）。
# ---------------------------------------------------------------------------
COMPONENTS = [
    # ref, symbol, value, lcsc, x, y, rot
    ("F11", "JFC1206-1100FS",   "1A 63V",              "C136343",    86.36,  71.12,   0),   # 输入保险丝（1A 63V，引脚 ±7.62）
    ("R42", "FCR1206J56RP055W", "56Ω 5% 熔断 1206",     "C153337",   114.30,  71.12,   0),   # 熔断电阻（F11 后、VIN_F 前；≥5W 时 <30s 受控开路）
    ("C40", "RV63V47M6X8",      "47µF 63V",            "C48971005", 139.70,  76.20, 270),   # 输入电解（竖放，正极上）
    ("U4",  "LMR16006XDDCR",    "LMR16006XDDCR (Tokmas)", "C54823941", 185.42, 104.14, 0),  # 主控 buck（Tokmas 件，符号沿用 TI）
    ("C41", "CL05B104KO5NNNC",  "100nF 16V",           "C1525",     185.42,  86.36,   0),   # 自举电容（U4 上方，横放）
    ("C45", "CL21B104KCFNNNE",  "100nF 100V",          "C28233",    215.90, 107.95,  90),   # VIN 高频旁路（三颗输入陶瓷中最靠 U4.VIN，竖放）
    ("C42", "TCC1206X7R105K101HT", "1µF 100V",          "C282823",    241.30, 109.22,  90),   # 输入陶瓷 1/2（C45 旁，竖放）
    ("C44", "TCC1206X7R105K101HT", "1µF 100V",          "C282823",    266.70, 109.22,  90),   # 输入陶瓷 2/2（与 C42 并联）
    ("D7",  "SS210",            "SS210",               "C14996",    228.60,  80.01,   0),   # 续流肖特基（横放，阴极左接 SW）
    ("L1",  "SWPA5040S220MT",   "22µH",                "C68434",    254.00,  71.12,   0),   # 输出电感（横放）
    ("C43", "CL10A226MQ8NRNC",  "22µF 6.3V",           "C59461",    289.56,  76.20,  90),   # 输出电容（竖放）
    ("R40", "0402WGF3302TCE",   "33k 1%",              "C25779",    304.80,  91.44, 270),   # 反馈上电阻（竖放）
    ("R41", "0402WGF1002TCE",   "10k 1%",              "C25744",    304.80, 114.30, 270),   # 反馈下电阻（竖放）
]

# 个别器件的 Datasheet 字段覆盖（取库符号的 Datasheet 指向旧料号商品页，这里换成实际用料）
DATASHEET_OVERRIDE = {
    "U4": "https://www.lcsc.com/datasheet/C54823941.pdf",
}

# 位号/值文字位置（绝对坐标，justify left）。
# 竖放件：位号与值都在器件右侧、水平书写（位号在上、值在下）；
# 横放件：位号在上、值在下；U4：位号在本体上方、值在本体下方。
PROP_POS = {
    "F11": (("F11", 86.36, 66.04), ("Value", 86.36, 73.66)),
    "R42": (("R42", 114.30, 66.04), ("Value", 114.30, 73.66)),
    "C40": (("C40", 144.78, 73.66), ("Value", 144.78, 78.74)),
    "U4":  (("U4", 185.42, 96.52), ("Value", 185.42, 113.03)),
    "C41": (("C41", 185.42, 81.28), ("Value", 185.42, 88.90)),
    "C45": (("C45", 220.98, 105.41), ("Value", 220.98, 110.49)),
    "C42": (("C42", 246.38, 106.68), ("Value", 246.38, 111.76)),
    "C44": (("C44", 271.78, 106.68), ("Value", 271.78, 111.76)),
    "D7":  (("D7", 228.60, 76.20), ("Value", 228.60, 83.82)),
    "L1":  (("L1", 254.00, 68.58), ("Value", 254.00, 73.66)),
    "C43": (("C43", 294.64, 73.66), ("Value", 294.64, 78.74)),
    "R40": (("R40", 309.88, 88.90), ("Value", 309.88, 93.98)),
    "R41": (("R41", 309.88, 111.76), ("Value", 309.88, 116.84)),
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
    A('\t\t(rev "v0.3-draw-r5")\n')
    A('\t\t(company "MP2645A-BMS")\n')
    A('\t\t(comment 1 "8S LiFePO4 200A BMS · MPS MP2797 + 开关电容均衡")\n')
    A('\t)\n')

    # lib_symbols：复制符号（同名符号只写一次；C42/C44 共用 TCC1206X7R105K101HT）
    A('\t(lib_symbols\n')
    seen = set()
    for c in COMPONENTS:
        name = c[1]
        if name in seen:
            continue
        seen.add(name)
        block = read_symbol(name)
        A('\t' + block.replace('\n', '\n\t').rstrip('\t') + '\n')
    A('\t)\n')

    # 图名 + 说明文字（回图纸左上角）
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

    text_item(40.64, 20.32, "辅助电源（LMR16006X 直降 3.3V）", 4.0, "left top")
    text_item(40.64, 33.02,
              "LMR16006X 600kHz（Tokmas）非同步 buck；D7 续流必需；SHDN 悬空=常开；输入 C40 47µF/63V + C42/C44 2×1µF/100V",
              2.0, "left top")
    text_item(40.64, 38.10,
              "R42 56Ω 熔断电阻与 C40 构成输入 RC：限上电浪涌与短路电流，VIN_F 短路时受控开路；C45 100nF/100V 贴 VIN（Tokmas 手册 p14）",
              2.0, "left top")

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

    global_label("BAT+", "input", 40.64, 71.12, "left")
    global_label("+3V3", "output", 320.04, 71.12, "left")

    # GND 全局标签（每个接地器件下方一条；U4.GND 用右侧 justify 避开 stub 导线）
    for x, y, j in [(139.70, 96.52, "left"), (165.10, 104.14, "right"),
                    (215.90, 121.92, "left"), (241.30, 121.92, "left"),
                    (266.70, 121.92, "left"),
                    (233.68, 96.52, "left"), (289.56, 96.52, "left"),
                    (304.80, 128.27, "left")]:
        global_label("GND", "input", x, y, j)

    # 局部标签（组内 rail 标签 + U4/C41 脚标签）
    for name, x, y, j in [
        ("VIN_R", 101.60, 71.12, "left"),    # 输入组：F11→R42（保险丝后、串阻前）
        ("VIN_F", 128.27, 71.12, "left"),    # 输入组 rail（R42→C40）
        ("VIN_F", 200.66, 104.14, "left"),   # U4.VIN stub
        ("SW_3V3", 238.76, 71.12, "left"),   # 续流/电感组 rail
        ("SW_3V3", 200.66, 101.60, "left"),  # U4.SW stub
        ("SW_3V3", 190.50, 86.36, "left"),   # C41.pin2
        ("CB_3V3", 165.10, 101.60, "right"), # U4.CB stub
        ("CB_3V3", 180.34, 86.36, "right"),  # C41.pin1
        ("FB_3V3", 165.10, 106.68, "right"), # U4.FB stub
        ("FB_3V3", 304.80, 101.60, "right"), # 反馈组 rail（R40/R41 之间）
    ]:
        local_label(name, x, y, j)

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

    # 输入段（BAT+ → F11 → VIN_R → R42 → VIN_F → C40）
    wire([(40.64, 71.12), pt("F11", "1")], "bat_f11")
    wire([pt("F11", "2"), pt("R42", "1")], "f11_r42")
    wire([pt("R42", "2"), pt("C40", "1")], "r42_c40")
    wire([pt("C40", "2"), (139.70, 96.52)], "c40_gnd")
    # U4 引脚 stub（左 CB/GND/FB，右 SW/VIN）
    wire([pt("U4", "1"), (165.10, 101.60)], "u4_cb")
    wire([pt("U4", "2"), (165.10, 104.14)], "u4_gnd")
    wire([pt("U4", "3"), (165.10, 106.68)], "u4_fb")
    wire([pt("U4", "6"), (200.66, 101.60)], "u4_sw")
    wire([pt("U4", "5"), (200.66, 104.14)], "u4_vin")
    # VIN_F rail → C45/C42/C44（C45 最靠 U4.VIN，串阻后高频回路就近）
    wire([(200.66, 104.14), pt("C45", "2")], "vinf_c45")
    wire([pt("C45", "2"), pt("C42", "2")], "vinf_c42")
    wire([pt("C42", "2"), pt("C44", "2")], "vinf_c44")
    wire([pt("C45", "1"), (215.90, 121.92)], "c45_gnd")
    wire([pt("C42", "1"), (241.30, 121.92)], "c42_gnd")
    wire([pt("C44", "1"), (266.70, 121.92)], "c44_gnd")
    # 续流/电感组（SW_3V3 rail；D7 横放：阴极引到上方 rail，阳极引到下方 GND）
    wire([pt("D7", "1"), (223.52, 71.12)], "d7_cathode")
    wire([(223.52, 71.12), (238.76, 71.12)], "sw_rail1")
    wire([(238.76, 71.12), pt("L1", "1")], "sw_rail2")
    wire([pt("D7", "2"), (233.68, 96.52)], "d7_gnd")
    # 输出组（+3V3 rail → C43 → 输出标签；tap 到反馈）
    wire([pt("L1", "2"), pt("C43", "2")], "out_l1_c43")
    wire([pt("C43", "2"), (304.80, 71.12)], "out_c43_tap")
    wire([(304.80, 71.12), (320.04, 71.12)], "out_label")
    wire([(304.80, 71.12), pt("R40", "1")], "tap_r40")
    # 反馈组（R40 → FB_3V3 → R41 → GND）
    wire([pt("R40", "2"), pt("R41", "1")], "fb_div")
    wire([pt("R41", "2"), (304.80, 128.27)], "r41_gnd")
    wire([pt("C43", "1"), (289.56, 96.52)], "c43_gnd")

    # 结点（T 型接点：+3V3 rail 在 x=304.80 分出一路向下到 R40；
    # C45.2 / C42.2 / C43.2 三处「引脚 + 两段共线导线」三方相接，补 junction 圆点）
    def junction(x, y):
        ju = uid("jct:" + fmt(x) + ":" + fmt(y))
        A(f'\t(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0) (uuid "{ju}"))\n')

    junction(304.80, 71.12)     # +3V3 rail 三线 T（wire-wire-wire）
    junction(215.90, 104.14)    # C45.2（VIN_F rail 引脚 T）
    junction(241.30, 104.14)    # C42.2（VIN_F rail 引脚 T）
    junction(289.56, 71.12)     # C43.2（+3V3 rail 引脚 T）

    # 无连接标志（SHDN 悬空 = 常开）
    sx, sy = pt("U4", "4")
    nu = uid("nc:u4:4")
    A(f'\t(no_connect (at {fmt(sx)} {fmt(sy)}) (uuid "{nu}"))\n')

    # 器件实例（含 Footprint/Datasheet 字段，取库符号同值；LCSC 隐藏）
    for ref, sym, val, lcsc, x, y, rot in COMPONENTS:
        (rref, rx, ry), (vref, vx, vy) = PROP_POS[ref]
        pins = pins_of((ref, sym, val, lcsc, x, y, rot))
        props = symbol_props(read_symbol(sym))
        footprint = props.get("Footprint", "")
        datasheet = DATASHEET_OVERRIDE.get(ref, props.get("Datasheet", ""))
        su = uid("sym:" + ref)
        # 字段文字角：KiCad 里字段角是相对符号的，绝对角 = 符号旋转 + 字段角。
        # 竖放件要让位号/值水平书写，字段角取 (360 - rot) % 360 抵消符号旋转。
        fa = (360 - rot) % 360
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
        # Footprint / Datasheet / LCSC 三字段：隐藏
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
    print(f"已生成: {os.path.abspath(OUT)}（{len(out)} 字节）")


if __name__ == "__main__":
    main()
