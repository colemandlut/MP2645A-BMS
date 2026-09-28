#!/usr/bin/env python3
"""生成 hardware/03_balancer.kicad_sch（开关电容主动均衡，8S LiFePO4）。

幂等：同一输入跑两次输出逐字节相同（UUID 用 uuid.uuid5 按位号/用途派生）。
运行即覆盖生成 hardware/03_balancer.kicad_sch。

    python3 hardware/gen/gen_03_balancer.py

设计依据：design/03_balancer-spec.md（含 §8.1b 用户决定 2026-09-27/28；附录 A 已作废）。
本脚本按任务书分段交付：**分段 A** 画第 1–4 节（k=1..4）全部器件 + 首级时钟输入，
**分段 B** 续画第 5–8 节（右栏，整体比左栏上移 26.67mm 以避开右下角标题栏）、
余下 4 级飞电容（C334–C337 / C344–C347）、最左栏的 J6 与 F300–F308，
版面分区见下面 LAYOUT 注释与 a_components 的说明。

沿用 02 页的通用函数（read_symbol/pin_world/发射器逐字照搬）与教训：
坐标全落 1.27mm 栅格；每条 wire 只 2 点；竖放件字段角 (360-rot)%360；
引脚几何以库读数为准（parse_pins/pin_world，**P 管 AO3415A 的引脚几何与 N 管不同**：
AO3416 G=−5.08/S,D=2.54，AO3415A G=−6.35/S,D=3.81）；IC 引脚引短线 + 标签；
导线不穿本体/不经过非端点引脚；引脚处 ≥2 段导线端点相接补 junction（本脚本自动补）。

本页特有：**不含 GND、不含任何电源符号**（§8.1b U-3：VB0 不接地，首级改交流耦合）；
局部网络名一律用具体名（VB0..VB8 / X1..X8 / IN1..IN8 / DRV1..DRV8 / GNk / GPk / CLK_R），
跨节一律用局部标签，不画长导线（§7.4）。
"""
from __future__ import annotations

import os
import re
import uuid

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
JLCSYM = os.path.join(HW, "lib", "jlc", "jlc.kicad_sym")
OUT = os.path.join(HW, "03_balancer.kicad_sch")

PAGE_UUID = "249fa7f7-2571-5b26-9553-df94514122d0"   # 03 页文件自身 uuid（保持骨架现值）
ROOT_UUID = "632f74a5-cd8f-58d8-9ac1-1bfbb611d555"
SHEET_UUID = "66cc3a14-196d-5f5c-9535-d482588cd3fc"  # 根图里 Sheetfile "03_balancer.kicad_sch" 的 sheet
PATH = f"/{ROOT_UUID}/{SHEET_UUID}"

NS = uuid.UUID("249fa7f725715b269553df94514122d0")


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
    """符号局部坐标 → 世界坐标（y 轴向下）。本页不用 mirror，保留参数与 02 页一致。"""
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
# 版面（spec §7.4：A3 420×297 分两栏、自下而上，左栏 1–4 节、右栏 5–8 节，最左栏熔丝/端子）
# 每节一个横条：① R30k 下拉 / C32k 耦合 ② U30k（74LVC1G17，本节电芯供电）+ C30k 去耦
# ③ 死区 R31k∥D30k、R32k∥D31k + GP/DRV/GN 三条竖轨 ④ 半桥 Q31k(P) 上 / Q30k(N) 下，
# 漏极相对接 Xk，源极之间挂 C31k 储能 ⑤ 最右 Xk 标签。飞电容摆在第 k 节与第 k+1 节
# 之间的右侧（两端用 Xk/X(k+1) 标签）。相邻两节之间只有两处相连：飞电容 + 1nF 耦合电容。
# ---------------------------------------------------------------------------
SEC = {1: 251.46, 2: 199.39, 3: 147.32, 4: 95.25}    # 左栏第 k 节的横条基线 y（行距 52.07）
# 右栏（第 5–8 节）：整列比左栏同序号行上移 26.67mm（=21×1.27），
# 否则第 5 节最低的 D 值字段（R+19.05+0.95）会压到右下角标题栏（y ≥ 250 @ x ≥ 295）。
# 上移后：第 8 节顶端字段 y=50.80（标题文字止于 ~51.7，横向隔 2 栏无重叠），
# 第 5 节最低 y=243.84 < 250 ✓，右栏最右墨迹 ≈385 < 410 ✓。
SEC_R = {5: 224.79, 6: 172.72, 7: 120.65, 8: 68.58}
DX = 168.91          # 右栏相对左栏的 x 偏移（133×1.27）；右栏最左墨迹 ≈221.3 > 左栏最右 ≈216.2

X_R30 = 55.88        # R30k 下拉（竖放 rot 270，pin1 上=INk、pin2 下=VB(k-1)）：R301=100k、R302–R308=330k
X_C32 = 71.12        # C32k 1nF 交流耦合（横放 rot 0，pin1 左、pin2 右）
X_U30 = 96.52        # U30k SN74LVC1G17（rot 90：1 NC / 2 INA / 3 GND / 4 OUTY / 5 VCC）
X_C30 = 113.03       # C30k 100nF 去耦（竖放 rot 270）
X_R_D_D = 129.54     # R32k ＋ D31k（GP 轨 ↔ DRV 轨）
X_R_D_G = 144.78     # R31k ＋ D30k（DRV 轨 ↔ GN 轨）
X_GP, X_DRV, X_GN = 121.92, 137.16, 152.40   # 三条竖轨
X_QN, X_QP = 165.10, 171.45   # Q30k rot 0（S/D 在 x=167.64）＋ Q31k rot 180（同样落 167.64）
X_C31 = 190.50       # 每节 100µF 本地储能（竖放 rot 270）
X_FLY_L, X_FLY_R = 194.31, 201.93   # 飞电容两并联链；标签锚 191.77 / 204.47
RD_DY = 6.35         # 死区两行的高度：R 行 y=R+6.35、D 行 y=R+13.97（轨底 y=R+16.51）
STUB = 2.54          # 引脚短线的通用长度

# 跨栏那一级飞电容（第 4–5 级，spec §7.4：放右栏最下）。x 落在右栏链位上，
# y 取左栏最下一条的空档（R300 与标题栏之间）：两件都在 y=276.86，字段向上摆。
X4_L, X4_R, Y4 = 224.79, 240.03, 276.86

# 最左栏（spec §7.4）：F300–F308 一列 + J6 线束端子。
# F30k：pin1 → BALk 全局标签（向左引线，标签右对齐）、pin2 → VBk 局部标签（向右）。
# 栈自下而上 F300…F308，节距 22.86；F300 与第 1 节基线同高（251.46）。
# 说明：§7.4 希望 F30k 与 VBk 同高——两栏行高互不相同（52.07 错位 26.67），
# 无法让 9 只同时对齐，故取等节距排布；两端都是标签连接，电气等价（报告已记录）。
X_FUSE, Y_FUSE0, FUSE_PITCH = 27.94, 251.46, 22.86
X_J6, Y_J6 = 27.94, 269.24       # XDWF-C3030WV-2*5P：本体 x±3.81 / y±7.62，引脚 x±6.35


def sec_row(k: int, R: float, dx: float = 0.0):
    """spec §3.1 每节通用连接的 11 件（k，右栏 dx≠0）。"""
    # R30k 是 DRVk 的下拉/泄放电阻。第 2 轮（复核 P1-2 → 规格书 §8.1c 用户决定）：
    # R301 保持 100k（它是整套死区时序的基准），R302–R308 改 330k，让第 1 级**总是**先
    # 泄放完（第 1 级翻相 ≤133µs，其余 ≥169µs）。时钟卡高或 MCU 掉电时，八级同时异步
    # 衰减会让相邻级混相，浪涌可达 20–40A（超 AO3415A 的 IDM 15.6A）。330k 的漏电流
    # 偏移 ±0.33V < VT−,min 0.89V，不会误翻。
    r30 = (("0402WGF1003TCE", "100k 1%", "C25741") if k == 1
           else ("0402WGF3303TCE", "330k 1%", "C25778"))
    # 死区二极管（复核 P1-1 → 规格书 §8.1c）：1N5819WS → BAT54WS。1N5819WS 的结电容
    # ~110pF@4V，经 R31k/R32k 330Ω 耦合会把栅极瞬时顶过 Vth，慢开快关的死区被抹掉；
    # BAT54WS 的 CT ≤10pF、VF 0.24V@0.1mA。**脚位几何完全相同**（SOD-323，1=K/2=A，
    # 本体折线一致），所以接线一根不用动，只换符号/值/LCSC。
    return [
        (f"R30{k}", *r30, X_R30 + dx, R, 270, False),
        (f"C32{k}", "0402B102K500NT", "1nF 50V", "C1523", X_C32 + dx, R, 0, False),
        (f"U30{k}", "SN74LVC1G17DBVR", "SN74LVC1G17DBVR", "C7394021", X_U30 + dx, R, 90, False),
        (f"C30{k}", "CL05B104KO5NNNC", "100nF 16V", "C1525", X_C30 + dx, R, 270, False),
        (f"R32{k}", "0402WGF3300TCE", "330Ω 1%", "C25104", X_R_D_D + dx, R + RD_DY, 0, False),
        (f"D31{k}", "BAT54WSL9", "BAT54WS", "C22629", X_R_D_D + dx, R + 2 * RD_DY + 1.27, 0, False),
        (f"R31{k}", "0402WGF3300TCE", "330Ω 1%", "C25104", X_R_D_G + dx, R + RD_DY, 0, False),
        (f"D30{k}", "BAT54WSL9", "BAT54WS", "C22629", X_R_D_G + dx, R + 2 * RD_DY + 1.27, 0, False),
        (f"Q30{k}", "AO3416_C479060", "AO3416", "C479060", X_QN + dx, R + 6.35, 0, False),
        (f"Q31{k}", "AO3415A_C5350990", "AO3415A", "C5350990", X_QP + dx, R - 6.35, 180, False),
        (f"C31{k}", "CL31A107MQHNNNE", "100µF 6.3V", "C15008", X_C31 + dx, R, 270, False),
    ]


def fly_stages():
    """7 级飞电容 (j, x 左链, x 右链, y)。j=1..3 在左栏两节之间，j=4 跨栏，j=5..7 在右栏。"""
    out = []
    for j in (1, 2, 3):
        out.append((j, X_FLY_L, X_FLY_R, SEC[j] - 25.40))
    out.append((4, X4_L, X4_R, Y4))
    for j in (5, 6, 7):
        out.append((j, X_FLY_L + DX, X_FLY_R + DX, SEC_R[j] - 25.40))
    return out


def fuse_rows():
    """最左栏 F300–F308 的 (k, x, y)：自下而上等节距，F300 与第 1 节基线同高。"""
    return [(k, X_FUSE, Y_FUSE0 - k * FUSE_PITCH) for k in range(9)]


def a_components():
    """全页器件表（ref, symbol, value, lcsc, x, y, rot, dnp）。

    位号按规格书 §2.3：QN1–8→Q301–Q308、QP1–8→Q311–Q318、UD1–8→U301–U308、
    CD1–8→C301–C308、RB1–8（输入下拉）→R301–R308（第 2 轮：R301 100k、R302–R308 330k）、
    R311–R318/R321–R328（330Ω 死区）、D301–D308/D311–D318（第 2 轮：BAT54WS C22629）、
    C311–C318（100µF 储能）、C321–C328（1nF 耦合）、
    CF(2k−1)/CF(2k)→C33k/C34k（飞电容，k=1..7）、R_CLK→R300、
    线束节点熔丝→F300–F308、线束端子→J6。
    """
    out = []
    for k in (1, 2, 3, 4):
        out += sec_row(k, SEC[k])
    for k in (5, 6, 7, 8):
        out += sec_row(k, SEC_R[k], DX)
    for j, xl, xr, yf in fly_stages():
        out += [
            (f"C33{j}", "CL31A107MQHNNNE", "100µF 6.3V", "C15008", xl, yf, 270, False),
            (f"C34{j}", "CL31A107MQHNNNE", "100µF 6.3V", "C15008", xr, yf, 270, False),
        ]
    for k, x, y in fuse_rows():
        out.append((f"F30{k}", "CFS12V3T3R0", "CFS12V3T3R0", "C163126", x, y, 0, False))
    out.append(("J6", "XDWF-C3030WV-2*5P", "XDWF-C3030WV-2*5P", "C18202166", X_J6, Y_J6, 0, False))
    # 首级时钟输入（§3.1 / §8.1b U-3）：BAL_CLK → R300 1k → CLK_R → C321 → IN1
    out.append(("R300", "0402WGF1001TCE", "1k 1%", "C11702", 63.50, 276.86, 0, False))
    return out


COMPONENTS = a_components()


def sec_fields(k: int, R: float, dx: float = 0.0):
    """一节 11 件的字段落位（随栏偏移 dx）；返回 {ref: (位号元组, 值元组)}。

    小件的默认「位号 y−5.08、值 y+2.54」在本页会被死区两行、飞电容簇和竖轨标签顶住，
    所以逐类给出：
      * R30k / C30k / C31k 竖放：字段摆在本体上下——C30k 的值从默认的 y=R+5.08 挪到
        y=R−3.81：R+5.08 会被 R32k 的 GPk 标签（锚 x=121.92 右对齐、墨迹伸到 117.94）
        咬住（分段 A 实测 8a/8e 各 4 条）；而 C30k 的本体是 y=R±2.54，贴到 R−2.54
        又会被第 6 项检查判「字段压本体」（实测 8 条，两栏都有）；
      * C32k 横放：字段摆在本体上下；
      * R31k/R32k 死区电阻：字段摆到 R 行上方（y=R+1.27/+3.81），D 行的本体在 y ≥ R+11.94；
      * D30k/D31k：位号在 R 行与 D 行之间的空带（R+9.53），值一律落到 D 行下方的空带
        （R+19.05）——两只二极管的值文字各 6.1mm，挤在中间会互相压（02 页同类缺陷）。
    """
    return {
        f"R30{k}": ((f"R30{k}", X_R30 + dx, R - 11.43, "center"), ("Value", X_R30 + dx, R - 13.97, "center")),
        f"C32{k}": ((f"C32{k}", X_C32 + dx, R - 3.81, "center"), ("Value", X_C32 + dx, R + 3.81, "center")),
        f"U30{k}": ((f"U30{k}", X_U30 + dx, R - 17.78, "center"), ("Value", X_U30 + dx, R + 17.78, "center")),
        # C30k：位号与值原来同在 y=R−5.08 / R−3.81 两行，模型只差 0.01mm、渲染实测
        # 纵向压 0.64mm（P2-4）。上方 VBk 标签的墨迹止于 y=R−6.89，塞不下两行，
        # 所以位号往右上让：y=R−6.35 且右移 3.81，与值**纵分**、与 VBk 标签**横分**。
        f"C30{k}": ((f"C30{k}", X_C30 + dx + 3.81, R - 6.35, "center"), ("Value", X_C30 + dx, R - 3.81, "center")),
        f"R32{k}": ((f"R32{k}", X_R_D_D + dx, R + 3.81, "center"), ("Value", X_R_D_D + dx, R + 1.27, "center")),
        f"R31{k}": ((f"R31{k}", X_R_D_G + dx, R + 3.81, "center"), ("Value", X_R_D_G + dx, R + 1.27, "center")),
        f"D31{k}": ((f"D31{k}", X_R_D_D + dx, R + 9.53, "center"), ("Value", X_R_D_D + dx, R + 19.05, "center")),
        f"D30{k}": ((f"D30{k}", X_R_D_G + dx, R + 9.53, "center"), ("Value", X_R_D_G + dx, R + 19.05, "center")),
        f"Q30{k}": ((f"Q30{k}", X_QN + dx - 3.81, R + 9.53, "right"), ("Value", X_QN + dx - 3.81, R + 12.70, "right")),
        # Q31k 是 P 管、符号转 180°。KiCad 在 rot=180 时把字段的水平对齐左右翻面
        # （实测：写 right 会渲染成「从锚点往右长」），而 center 不受翻面影响、锚点即
        # 文字中心。所以这里改用 center，锚点从 X_QP−8.89 左移到 X_QP−12.70，让文字
        # 落在 GN 竖轨（x=X_GN）与 Q31k 本体（x≥X_QP−7.37）之间的空带里。
        f"Q31{k}": ((f"Q31{k}", X_QP + dx - 12.70, R - 3.81, "center"), ("Value", X_QP + dx - 12.70, R - 6.35, "center")),
        f"C31{k}": ((f"C31{k}", X_C31 + dx + 2.54, R - 1.27, "left"), ("Value", X_C31 + dx + 2.54, R + 1.27, "left")),
    }


def a_prop_override():
    """字段落位（全部显式给，避免默认位置压本体/压邻件——02 页的实测教训）。"""
    d = {}
    for k in (1, 2, 3, 4):
        d.update(sec_fields(k, SEC[k]))
    for k in (5, 6, 7, 8):
        d.update(sec_fields(k, SEC_R[k], DX))
    # 飞电容：位号/值摆在链的外侧（左链左、右链右），左链右对齐、右链左对齐，
    # 让文字往两边长。分段 A 把 C34j 的字段错锚在 C33j 的 x 上（离自己本体 9.1mm、
    # 离 C33j 只有 4.2mm），第 12 项检查报了 6 条——这里改成锚在右链自己的 x 上。
    for j, xl, xr, yf in fly_stages():
        if j == 4:
            # 跨栏那一级在页面最下方（y=276.86），字段往下会蹭到图框（y ≥ 287），
            # 所以两件的字段都往上摆（上排导线在 yf−3.81，字段墨迹止于 yf−5.4）。
            d[f"C33{j}"] = ((f"C33{j}", xl - 2.54, yf - 6.35, "right"),
                            ("Value", xl - 2.54, yf - 8.89, "right"))
            d[f"C34{j}"] = ((f"C34{j}", xr + 2.54, yf - 6.35, "left"),
                            ("Value", xr + 2.54, yf - 8.89, "left"))
            continue
        d[f"C33{j}"] = ((f"C33{j}", xl - 2.54, yf - 6.35, "right"),
                        ("Value", xl - 2.54, yf - 8.89, "right"))
        d[f"C34{j}"] = ((f"C34{j}", xr + 2.54, yf + 6.35, "left"),
                        ("Value", xr + 2.54, yf + 8.89, "left"))
    # 熔丝：位号在本体上方、值在下方（两侧都是标签引线，横向留不出空带）。
    for k, x, y in fuse_rows():
        d[f"F30{k}"] = ((f"F30{k}", x, y - 3.81, "center"), ("Value", x, y + 3.81, "center"))
    # J6：字段摆在本体下方（右侧是 BAL1/3/5/7 的标签墨迹，塞不进去）。
    d["J6"] = (("J6", X_J6, Y_J6 + 9.53, "center"), ("Value", X_J6, Y_J6 + 12.07, "center"))
    d["R300"] = (("R300", 63.50, 274.32, "center"), ("Value", 63.50, 279.40, "center"))
    return d


PROP_OVERRIDE = a_prop_override()


def _fld(t):
    """字段位置元组规范化：(名, x, y[, 对齐]) → (名, x, y, 对齐)；对齐缺省 left。"""
    return t if len(t) == 4 else (t[0], t[1], t[2], "left")


def prop_pos(ref, x, y, rot):
    if ref in PROP_OVERRIDE:
        a, b = PROP_OVERRIDE[ref]
        return _fld(a), _fld(b)
    if rot in (90, 270):
        return (ref, x + 5.08, y - 2.54, "left"), ("Value", x + 5.08, y + 2.54, "left")
    return (ref, x, y - 5.08, "left"), ("Value", x, y + 2.54, "left")


# 全局标签形状：BAL_CLK 是输入（05 页 PA8 驱动）；BAL0..BAL8 是板端均衡节点，两头
# （最左栏的熔丝与 J6）都挂被动形状——本页这两处互为同网络的两个端子，不构成驱动关系。
SHAPE = {"BAL_CLK": "input", **{f"BAL{i}": "passive" for i in range(9)}}


def net_vb_below(k: int) -> str:
    """规格书 §3.1 记法 VB(k−1) → 具体名 VB0..VB7。"""
    return f"VB{k - 1}"


def net_in(k: int) -> str:
    return f"IN{k}"


def sym_origin(comp):
    return (comp[4], comp[5], comp[6], comp[7])


def pins_of(comp):
    return parse_pins(read_symbol(comp[1]))


def gen():
    P = {}
    for c in COMPONENTS:
        x, y, rot, _dnp = sym_origin(c)
        for num, (ix, iy) in pins_of(c).items():
            P[(c[0], num)] = pin_world(x, y, rot, ix, iy)

    def pt(ref, num):
        return P[(ref, num)]

    L = []
    A = L.append

    A('(kicad_sch\n')
    A('\t(version 20250610)\n')
    A('\t(generator "gen_03_balancer")\n')
    A('\t(generator_version "1.0")\n')
    A(f'\t(uuid "{PAGE_UUID}")\n')
    A('\t(paper "A3")\n')
    A('\t(title_block\n')
    A('\t\t(title "开关电容主动均衡")\n')
    # 第 2 轮（复核 P2-4）：日期/版次随换料同步更新
    A('\t\t(date "2026-09-28")\n')
    A('\t\t(rev "v0.3-draw-r2")\n')
    A('\t\t(company "MP2645A-BMS")\n')
    A('\t\t(comment 1 "8S LiFePO4 200A BMS · MPS MP2797 + 开关电容均衡")\n')
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

    WIRES = []          # 已发射的导线（自动补 junction 用）
    JUNCTIONS = set()   # 显式 junction

    def wire2(x1, y1, x2, y2, key):
        WIRES.append(((x1, y1), (x2, y2)))
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
        JUNCTIONS.add((round(x, 4), round(y, 4)))

    def no_connect(x, y, key=None):
        key = key or f"{fmt(x)}:{fmt(y)}"
        A(f'\t(no_connect (at {fmt(x)} {fmt(y)}) (uuid "{uid("nc:" + key)}"))\n')

    def resolve(v):
        return pt(v[0], v[1]) if isinstance(v[0], str) else (v[0], v[1])

    def wire_ref(pts, key):
        wire([resolve(p) for p in pts], key)

    def pin_label(ref, num, dx, dy, net, just, kind="lbl"):
        """引脚 → 短线 → 标签（dx/dy 是短线相对引脚端点的位移）。"""
        px, py = pt(ref, num)
        wire_ref([(ref, num), (px + dx, py + dy)], f"{ref}_{num}")
        put_label(net, kind, px + dx, py + dy, just)

    # =====================================================================
    # 标题与说明（左上角空带 y ≤ 55：左栏第 8 只熔丝 F308 的字段底 y≈64.1，
    #   右栏第 8 节顶端字段 y≈50.8 但横向隔 ≥2 栏；本块止于 y≈54.3 故全页无重叠）
    # =====================================================================
    text_item(20.32, 15.24, "开关电容主动均衡（8 级半桥 + 飞电容，75kHz）", 3.5)
    text_item(20.32, 24.13,
              "内容：8 个互补半桥 QN/QP（AO3416/AO3415A）+ 8 个 74LVC1G17（本节电芯供电）"
              "+ 7 级飞电容 2×100µF；每节 C31k 100µF 本地储能。", 2.0)
    text_item(20.32, 29.21,
              "全级交流耦合：BAL_CLK 经 1nF（C321–C328）逐级耦合，首级亦然（VB0 不接地）；"
              "均衡节点经 3A 熔丝到 BAL0–BAL8；本页无 GND、无电源符号。", 2.0)
    text_item(20.32, 34.29,
              "死区：R31k/R32k 330Ω ∥ D30k/D31k BAT54WS（慢开快关，CT≤10pF）防上下管直通；"
              "停时钟/复位：R301 100k、R302–R308 330k 下拉，第 1 级先泄放完避免混相。", 2.0)
    text_item(20.32, 40.64, "接口网络（跨页用全局标签，名称以本清单为准）：", 2.4)
    text_item(25.40, 46.99, "· BAL0..BAL8（均衡节点，经 F300–F308）；· BAL_CLK（时钟输入）", 1.8)
    text_item(25.40, 52.07,
              "已知风险：F300–F308 保护不了线束段，线束电芯端保险丝未加（用户决定的已知风险）；"
              "U301–U308.1 = NC；J6.10 = NC。", 1.8)

    # =====================================================================
    # 第 1–8 节（spec §3.1 每节通用连接 / §3.2 逐节展开）
    #   左栏 k=1..4（dx=0）在下半页；右栏 k=5..8（dx=DX）是同一套画法整体平移
    # =====================================================================
    def draw_section(k, R, dx):
        vbk, vbb = f"VB{k}", net_vb_below(k)     # C30k/C31k 上端 VBk、下端 VB(k-1)
        inn, drvk, gnk, gpk, xk = net_in(k), f"DRV{k}", f"GN{k}", f"GP{k}", f"X{k}"
        xr30, xc32, xu30, xc30 = X_R30 + dx, X_C32 + dx, X_U30 + dx, X_C30 + dx
        xrdd, xrdg = X_R_D_D + dx, X_R_D_G + dx
        xgp, xdrv, xgn = X_GP + dx, X_DRV + dx, X_GN + dx
        xc31 = X_C31 + dx

        # --- R30k 100k 下拉：上端 INk、下端 VB(k-1) ---
        pin_label(f"R30{k}", "1", 0, -STUB, inn, "right")
        pin_label(f"R30{k}", "2", 0, +STUB, vbb, "right")

        # --- C32k 1nF：左端 k=1 接 CLK_R、k≥2 接 DRV(k-1)；右端 INk ---
        pin_label(f"C32{k}", "1", -STUB, 0, "CLK_R" if k == 1 else f"DRV{k - 1}", "right")
        pin_label(f"C32{k}", "2", +STUB, 0, inn, "left")

        # --- U30k SN74LVC1G17（rot 90 后：1/2/3 在下方、4/5 在上方）---
        no_connect(*pt(f"U30{k}", "1"))
        pin_label(f"U30{k}", "2", 0, +STUB, inn, "right")     # INA
        pin_label(f"U30{k}", "3", 0, +STUB, vbb, "left")      # GND ← 本节的低电位
        pin_label(f"U30{k}", "4", 0, -STUB, drvk, "right")    # OUTY
        pin_label(f"U30{k}", "5", 0, -STUB, vbk, "left")      # VCC ← 本节电芯

        # --- C30k 100nF 去耦：上端 VBk、下端 VB(k-1) ---
        pin_label(f"C30{k}", "1", 0, -STUB, vbk, "right")
        pin_label(f"C30{k}", "2", 0, +STUB, vbb, "right")

        # --- 死区网络：R31k∥D30k 在 DRV↔GN，R32k∥D31k 在 GP↔DRV；三条竖轨汇总 ---
        # R 行（y=R+6.35）
        for ref, xl, xr, nl, nr in ((f"R32{k}", xgp, xdrv, gpk, drvk),
                                    (f"R31{k}", xdrv, xgn, drvk, gnk)):
            px1, py1 = pt(ref, "1")
            wire_ref([(ref, "1"), (xl, py1)], f"{ref}_l")
            put_label(nl, "lbl", xl, py1, "right")
            px2, py2 = pt(ref, "2")
            wire_ref([(ref, "2"), (xr, py2)], f"{ref}_r")
        # D 行（y=R+13.97）：D31k 阴极→GP、阳极→DRV；D30k 阴极→DRV、阳极→GN
        for ref, xl, xr, nl, nr in ((f"D31{k}", xgp, xdrv, gpk, drvk),
                                    (f"D30{k}", xdrv, xgn, drvk, gnk)):
            px1, py1 = pt(ref, "1")
            wire_ref([(ref, "1"), (xl, py1)], f"{ref}_l")
            px2, py2 = pt(ref, "2")
            wire_ref([(ref, "2"), (xr, py2)], f"{ref}_r")
        # 三条竖轨（y=R+6.35 → R+16.51），轨底挂标签
        for x, net, just in ((xgp, gpk, "right"), (xdrv, drvk, "right"), (xgn, gnk, "left")):
            wire([(x, R + RD_DY), (x, R + 2 * RD_DY + 3.81)], f"{net}_rail")
            put_label(net, "lbl", x, R + 2 * RD_DY + 3.81, just)

        # --- 半桥：Q31k(P) 在上、Q30k(N) 在下，漏极相对接 Xk ---
        pin_label(f"Q30{k}", "1", -2.54, 0, gnk, "right")     # 栅极 → GNk
        pin_label(f"Q31{k}", "1", +2.54, 0, gpk, "left")      # 栅极 → GPk
        wire_ref([(f"Q30{k}", "3"), (f"Q31{k}", "3")], f"hb{k}_drain")
        dx_, _ = pt(f"Q30{k}", "3")          # 两管漏极同 x，连线中点即树条基线 R
        wire_ref([(dx_, R), (dx_ + 5.08, R)], f"hb{k}_x")
        put_label(xk, "lbl", dx_ + 5.08, R, "left")
        junction(dx_, R)                     # 导线端点落在漏极连线的内部 → T 接点
        # 源极 → C31k（上端 VBk、下端 VB(k-1)）；拐角处挂标签
        sx, sy = pt(f"Q31{k}", "2")
        wire_ref([(f"Q31{k}", "2"), (xc31, sy), (xc31, R - 3.81)], f"hb{k}_sp")
        put_label(vbk, "lbl", xc31, sy, "left")
        nx, ny = pt(f"Q30{k}", "2")
        wire_ref([(f"Q30{k}", "2"), (xc31, ny), (xc31, R + 3.81)], f"hb{k}_sn")
        put_label(vbb, "lbl", xc31, ny, "left")

    for k in (1, 2, 3, 4):
        draw_section(k, SEC[k], 0.0)
    for k in (5, 6, 7, 8):
        draw_section(k, SEC_R[k], DX)

    # =====================================================================
    # 飞电容（第 j 级：C33j/C34j 并成一组，把 Xj 与 X(j+1) 连起来）
    #   j=1..3 左栏两节之间、j=4 跨栏那一级（放右栏最下）、j=5..7 右栏两节之间
    # =====================================================================
    for j, xl, xr, yf in fly_stages():
        xj, xj1 = f"X{j}", f"X{j + 1}"
        # 上排 = Xj：左端引标签、两链上端并在一条线上
        wire2(xl - 2.54, yf - 3.81, xl, yf - 3.81, f"fly{j}_t0")
        wire2(xl, yf - 3.81, xr, yf - 3.81, f"fly{j}_t1")
        put_label(xj, "lbl", xl - 2.54, yf - 3.81, "right")
        junction(xl, yf - 3.81)
        # 下排 = X(j+1)：右端引标签
        wire2(xl, yf + 3.81, xr, yf + 3.81, f"fly{j}_b0")
        wire2(xr, yf + 3.81, xr + 2.54, yf + 3.81, f"fly{j}_b1")
        put_label(xj1, "lbl", xr + 2.54, yf + 3.81, "left")
        junction(xr, yf + 3.81)

    # =====================================================================
    # 最左栏（spec §7.4）：F300–F308 熔丝列 + J6 线束端子
    #   F30k：pin1 → BALk（全局标签，向左引线、右对齐）、pin2 → VBk（局部标签，向右）
    #   J6 （§4）：焊盘 n → BAL(n−1)，左列 1/3/5/7/9、右列 2/4/6/8；焊盘 10 空放 NC
    # =====================================================================
    for k, x, y in fuse_rows():
        pin_label(f"F30{k}", "1", -STUB, 0, f"BAL{k}", "right", "glbl")
        pin_label(f"F30{k}", "2", +STUB, 0, f"VB{k}", "left")
    for n in range(1, 10):
        left = n % 2 == 1
        pin_label("J6", str(n), -STUB if left else +STUB, 0, f"BAL{n - 1}",
                  "right" if left else "left", "glbl")
    no_connect(*pt("J6", "10"))

    # =====================================================================
    # 首级时钟输入（§3.1：R300.1 = BAL_CLK 全局、R300.2 = CLK_R）
    # =====================================================================
    pin_label("R300", "1", -STUB, 0, "BAL_CLK", "right", "glbl")
    pin_label("R300", "2", +STUB, 0, "CLK_R", "left")

    # =====================================================================
    # junction：T 接点（导线端点落在另一段导线内部）＋ 引脚处 ≥2 段导线端点相接
    # =====================================================================
    def on_seg_strict(p, a, b):
        ax, ay = a
        bx, by = b
        px, py = p
        if abs(ax - bx) < 1e-3:
            if abs(px - ax) > 1e-3:
                return False
            lo, hi = min(ay, by), max(ay, by)
            return lo + 1e-3 < py < hi - 1e-3
        if abs(ay - by) < 1e-3:
            if abs(py - ay) > 1e-3:
                return False
            lo, hi = min(ax, bx), max(ax, bx)
            return lo + 1e-3 < px < hi - 1e-3
        return False

    for i, (a, b) in enumerate(WIRES):
        for ep in (a, b):
            for j2, (c, d) in enumerate(WIRES):
                if i != j2 and on_seg_strict(ep, c, d):
                    JUNCTIONS.add((round(ep[0], 4), round(ep[1], 4)))
    for (ref, num), q in P.items():
        n = sum(1 for (a, b) in WIRES
                if (abs(a[0] - q[0]) < 1e-3 and abs(a[1] - q[1]) < 1e-3)
                or (abs(b[0] - q[0]) < 1e-3 and abs(b[1] - q[1]) < 1e-3))
        if n >= 2:
            JUNCTIONS.add((round(q[0], 4), round(q[1], 4)))
    for x, y in sorted(JUNCTIONS, key=lambda p: (p[1], p[0])):
        A(f'\t(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0)'
          f' (uuid "{uid("jct:" + fmt(x) + ":" + fmt(y))}"))\n')

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
        ref, sym, val, lcsc, x, y, rot, dnp = c
        (rref, rx, ry, rj), (vref, vx, vy, vj) = prop_pos(ref, x, y, rot)
        pins = pins_of(c)
        props = symbol_props(read_symbol(sym))
        fa = (360 - rot) % 360
        if rot == 180:
            # 符号转 180° 时 KiCad 的变换 y1==0，字段的绘制角**原样**取存储角（只有符号转
            # 90/270 才把水平↔竖直对调，见 SCH_FIELD::GetDrawRotation）。所以原来写的 180
            # 会画成正倒的文字（P2-4：Q311–Q318 的位号/值全倒着）。存 0 才是正的。
            fa = 0
        A('\t(symbol\n')
        A(f'\t\t(lib_id "jlc:{esc(sym)}")\n')
        A(f'\t\t(at {fmt(x)} {fmt(y)} {rot})\n')
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
