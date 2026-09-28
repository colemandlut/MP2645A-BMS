#!/usr/bin/env python3
"""自检脚本：对 hardware/03_balancer.kicad_sch 做几何检查 1–8 + 网表检查 9（结构照搬 check_02_layout.py）。

    python3 hardware/gen/check_03_layout.py

环境变量 `BAL_HW` 可把「硬件目录」换掉（默认 hardware/）。负例验证用：把整棵硬件目录
复制到别处、人为制造缺陷，再 `BAL_HW=/tmp/neg/hardware python3 check_03_layout.py` 跑一遍，
确认检查真的会报出来（这是 obsidian-vault 的规矩：新检查不做负例验证就可能是空跑）。

与 02 页的差异有四处：
  a) 本页**不用** mirror（规格书只给了 N/P 两种管的 rot0/rot180 摆法）；pin_world /
     pin_dir_world 的 mirror 分支照抄保留，load() 仍从实例的 `(mirror y)` 读，
     只是本页实例都不带 mirror，等价于 mirror=False。
  b) 网表核对表按规格书 §3 的逐节展开写（§3.1 模板 + §3.2 的 60 个网络），不再有 U1。
  c) 分段 A 只画第 1–4 节 + 飞电容 1–3 级 + R300，所以 §3.2 里属于第 5–8 节的
     位号（U305–U308 等）在图纸上还不存在——9c 对它们**只列缺件清单，不算失败**。
  d) 本页无 GND、无电源符号（§3.2 末条），所以 9g 反过来查：网表里不许出现
     GND/+3V3/+5V 之类的电源网络。

直接解析生成的 .kicad_sch（不是 gen 脚本的数据），做八件事：
  1. 导线不许经过非端点的引脚端点；
  2. 导线不许穿过符号本体（rectangle/polyline/arc/circle 包络 + 实例坐标变换）；
  3. T 型连接必须有 junction（导线端点落在另一段导线内部、或引脚处多段导线相接）；
  4. 标签/全局标签/说明文字不许压在导线上；
  5. 同一符号的引脚名文字盒不许互相粘连；
  6. 可见字段（Reference/Value）不许压在自己的本体上；
  7. 不同符号的「本体 + 可见字段 + 引脚名」图元盒两两不许相交（第 3 轮新增，
     第 2 轮就是因为缺这一项，R55 的位号被 JP1 本体压住没人发现）；
  8. 用 kicad-cli 导出 PDF、pymupdf 读渲染文字，复核字段文字真的画在预测位置、
     且不同符号的字段文字互不相交、字段文字不落在别的符号本体上（第 3 轮新增，
     补第 1 轮任务书 §4.4 的「文字 bbox 不重叠（pymupdf）」）。
  9. 以**根图**为准导出网表，逐脚核对已画的每个端子对规格书 §3.1/§3.2 的预期网络
     （分段 A 新增）。检查 1–8 全是「我自己算的几何 vs 我自己算的几何」，对符号变换
     不敏感——02 页实测把 pin_world 的 mirror 分支屏蔽掉，1–8 依旧全 PASS；
     检查 9 量的是 KiCad 自己连出来的网，才真正兜得住「接错网」。9 里还带
     9b（NC 真悬空）/9c（外围件端子，未画件列缺件清单）/9d（DNP 标志）/9f（位号合法性）/
     9g（本页不许出现电源网络）/9h（DNP 值里写明）/9i（Footprint 与 LCSC 齐备）/
     9j（网络→脚集合反查）/9l（本页网络全集）/9m（网络类）/9n（本页 ERC=0）/
     9o（8 节同构）/9p（值·LCSC·库符号：第 2 轮换料表 + 对 docs/02-BOM.csv 逐件核）/
     9q（二极管 K/A 方向：库符号图形 + §3.2 网络，第 2 轮新增）几小项。
 10. 标签/说明文字的**墨迹盒**不许压到器件本体图元上（第 2 轮新增）；
 11. 两段标签/说明文字不许叠在一起（用「横向重叠率 + 锚Δx」区分「真叠」与
     「同列上下紧排」，第 2 轮新增）；
 12. 可见字段不许离自己的器件比离别人的器件还远（第 2 轮新增）；
 13. 两段说明文字不许互相压住（第 2 轮新增，生成域，比渲染域的 8e 早一步）。

检查 10–13 用的是**墨迹**几何（见 ink_bbox 的标定说明），1–7 用的是 text_width 的
「字符前进宽度」近似（相对量够用，判「压没压上」不够）。

全部通过 → exit 0；任何一条失败 → 打印 FAIL 并 exit 1。检查 8 需要 kicad-cli + pymupdf，
检查 9 需要 kicad-cli + 根图，缺工具时各自打印 SKIP。
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HW = os.environ.get("BAL_HW") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCH = os.path.join(HW, "03_balancer.kicad_sch")
ROOT_SCH = os.path.join(HW, "mp2645a-bms.kicad_sch")
# 检查 9p 的外部口径：docs/02-BOM.csv 是本页器件值的**另一份独立记录**（贴片厂吃的那份）。
# 用 BAL_HW 指向快照时（负例验证）BOM 通常不存在，9p 的 BOM 那一半自动降级成 SKIP。
BOM = os.environ.get("BAL_BOM") or os.path.join(os.path.dirname(os.path.abspath(HW)), "docs", "02-BOM.csv")

EPS = 1e-3

# 图纸尺寸（A3，见生成器的 `(paper "A3")`）与文字可用区留边。留边就是**实测的图框线**：
# 从 PDF 的矢量图元里量出来是 x 10.0→410.0、y 10.0→287.0（原来拍脑袋写 8.0，比图框宽
# 2mm，会把「刚压线」漏过去）。图元盒另有检查 3/4 兜着，这里只管文字。
PAGE_W, PAGE_H = 420.0, 297.0
PAGE_MARGIN = 10.0
# 图框标题栏：KiCad 自己管的文字（页号、版本、我们的 comment 行）按图框模板定位，实测
# 最后一行的右边界到 x≈418.9 —— **越过了 410 的边框线**。那不是生成器摆的，也不是
# 「画出去被裁掉」，单独开一个豁免区。区域取右下角，生成器的内容区不会伸到这里
# （全页最右的内容是 x≈402 的字段文字，y < 200）。
TITLE_BLOCK = (295.0, 250.0, 420.0, 297.0)


# ---------------------------------------------------------------------------
# S-表达式解析（够用即可）
# ---------------------------------------------------------------------------
def tokenize(s: str):
    toks, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            toks.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            while j < n:
                if s[j] == "\\":
                    j += 2
                elif s[j] == '"':
                    break
                else:
                    j += 1
            toks.append(s[i:j + 1])
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in "()":
                j += 1
            toks.append(s[i:j])
            i = j
    return toks


def parse(toks):
    i = 0

    def _p():
        nonlocal i
        if toks[i] != "(":
            v = toks[i]
            i += 1
            return v
        i += 1
        node = []
        while toks[i] != ")":
            node.append(_p())
        i += 1
        return node

    return _p()


def unq(s):
    if isinstance(s, str) and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def child(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def children(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


# ---------------------------------------------------------------------------
# 提取图元
# ---------------------------------------------------------------------------
def pin_world(px, py, rot, ix, iy, mirror=False):
    """符号局部坐标 → 世界坐标。mirror=True 表示实例带 `(mirror y)`（先翻局部 x 再旋转）。"""
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
# 文字几何（近似）：为「标签文字 vs 导线 / 引脚名 vs 引脚名 / 字段 vs 本体」检查服务
# ---------------------------------------------------------------------------
def font_size(eff):
    """effects → (高, 宽)，默认 1.27。"""
    h = w = 1.27
    if eff:
        f = child(eff, "font")
        if f:
            s = child(f, "size")
            if s and len(s) >= 3:
                h, w = float(s[1]), float(s[2])
    return h, w


def justify(eff):
    """effects → (水平, 垂直) 对齐。

    KiCad 文件格式里不写 justify 节点就表示**居中对齐**（所以 KiCad 写左对齐时一定会显式写
    `(justify left)`）。第 3 轮 JP1 的位号改成居中后就是这个样子 —— 渲染实测「JP1」画在
    363.91–367.36（中心 365.64，锚点 365.76），证实默认确实是水平居中，不是左对齐。
    生成脚本里的标签/说明文字都显式写 justify，走不到这个默认值。
    """
    hj, vj = "center", "center"
    if eff:
        j = child(eff, "justify")
        if j and len(j) >= 2:
            parts = unq(j[1]).split()
            if parts and parts[0] in ("left", "right", "center"):
                hj = parts[0]
            if len(parts) > 1 and parts[1] in ("top", "bottom"):
                vj = parts[1]
    return hj, vj


def text_width(txt, h):
    """近似文字宽度：CJK 按全角（≈h），其余按 0.6h。"""
    w = 0.0
    for ch in txt:
        w += h if ord(ch) > 0x2E80 else 0.6 * h
    return w


def text_bbox(x, y, txt, h, hj, vj):
    """水平文字（有效角度 0/180）的近似包围盒；锚点 (x, y)。"""
    tw = text_width(txt, h)
    if hj == "right":
        x0, x1 = x - tw, x
    elif hj == "center":
        x0, x1 = x - tw / 2, x + tw / 2
    else:
        x0, x1 = x, x + tw
    if vj == "top":
        y0, y1 = y, y + h
    elif vj == "bottom":
        y0, y1 = y - h, y
    else:
        y0, y1 = y - h / 2, y + h / 2
    return (x0, y0, x1, y1)


def vtext_bbox(x, y, txt, h):
    """竖排文字（有效角度 90/270）的近似包围盒：宽 = 字高 h，高 = 文字宽度。
    本页的字段都写成 fa=(360-rot)%360，有效角度恒为 0，这个分支跑不到；
    留着是为了「角度不是 0 就静默跳过」这种漏检不再发生。"""
    tw = text_width(txt, h)
    return (x - h / 2, y - tw / 2, x + h / 2, y + tw / 2)


# --- 墨迹几何（第 2 轮新增，检查 10–13 用）----------------------------------
# 检查 1–7 拿 text_width（0.6h/字）比「压没压上」是不够的：那是**字符前进宽度**，比真实
# 墨迹小约一半（实测 1.8 号的「SRN_F」墨迹 5.87mm，text_width 只给 3.81mm），拿同一把
# 偏小的尺子量两边时近距缺陷会被整片漏掉。下面两个函数是**渲染实测标定**出来的：
#   * 墨迹宽 = CJK 1.50h/字、其余 0.92h/字（1.27 号拉丁实测 0.92h/字）；
#   * 纵向锚点：`(justify … top)` 的墨迹 = y−0.25h … y+1.25h（§9 标题锚 43.18、渲染实测
#     42.62–46.16；§10 说明锚 48.26、实测 47.77–50.16），bottom 对称；居中（标签/字段）
#     实测 ≈ y±0.75h（另有 ~0.2mm 系统偏移，见下面 GLBL_PAD 的说明）。
# 已知误差：全局标签的文字画在图形框**里面**、离锚点还有一段框长，实测比「右对齐到锚点」
# 的模型再往左 ~2.0mm（C221 的 GND：模型 351.8–355.3，渲染 355.15–359.02 的实测是
# 355.15 起）。所以全局标签的墨迹盒横向额外放宽 GLBL_PAD —— 宁可把缺陷报出来。
INK_CJK, INK_LATIN = 1.50, 0.92
GLBL_PAD = 2.0


def ink_width(txt, h):
    """墨迹宽度。"""
    return sum(INK_CJK * h if ord(c) > 0x2E80 else INK_LATIN * h for c in txt)


def ink_bbox(x, y, txt, h, hj, vj="center", pad=0.0):
    """水平文字的墨迹盒（锚点 (x, y)）。"""
    tw = ink_width(txt, h)
    if hj == "right":
        x0, x1 = x - tw, x
    elif hj == "center":
        x0, x1 = x - tw / 2, x + tw / 2
    else:
        x0, x1 = x, x + tw
    if vj == "top":
        y0, y1 = y - 0.25 * h, y + 1.25 * h
    elif vj == "bottom":
        y0, y1 = y - 1.25 * h, y + 0.25 * h
    else:
        y0, y1 = y - 0.75 * h, y + 0.75 * h
    return (x0 - pad, y0, x1 + pad, y1)


def box_gap(a, b):
    """两盒的边到边距离（相交 = 0）。字段归属检查要比「离谁更近」，用 2D 间距。"""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def pin_dir_world(inst_rot, pin_rot, mirror=False):
    """引脚方向（尖端→本体）在世界坐标下的单位向量。"""
    dx = {0: 1, 90: 0, 180: -1, 270: 0}[pin_rot % 360]
    dy = {0: 0, 90: 1, 180: 0, 270: -1}[pin_rot % 360]
    if mirror:
        dx = -dx  # (mirror y)：局部 x 取反（与 pin_world 一致）
    wx, wy = dx, -dy  # 符号局部 y 向上 → 世界 y 向下
    if inst_rot == 90:
        wx, wy = -wy, wx
    elif inst_rot == 180:
        wx, wy = -wx, -wy
    elif inst_rot == 270:
        wx, wy = wy, -wx
    return wx, wy


def pin_name_bbox(bx, by, wx, wy, tw, h):
    """引脚名以本体端 (bx, by) 为锚、沿 (wx, wy) 向本体内延伸。
    水平引脚名=横排文字；顶/底引脚名=竖排文字（KiCad 实际按竖排渲染）。"""
    if wx > 0:
        x0, x1 = bx, bx + tw
        y0, y1 = by - h / 2, by + h / 2
    elif wx < 0:
        x0, x1 = bx - tw, bx
        y0, y1 = by - h / 2, by + h / 2
    elif wy > 0:  # 顶边引脚（向下指）：竖排名字向下延伸
        x0, x1 = bx - h / 2, bx + h / 2
        y0, y1 = by, by + tw
    else:  # wy < 0：底边引脚（向上指）：竖排名字向上延伸
        x0, x1 = bx - h / 2, bx + h / 2
        y0, y1 = by - tw, by
    return (x0, y0, x1, y1)


def bbox_overlap(b1, b2, eps=EPS):
    return not (b1[2] < b2[0] - eps or b2[2] < b1[0] - eps or
                b1[3] < b2[1] - eps or b2[3] < b1[1] - eps)


def bbox_overlap_xy(b1, b2, xeps, yeps):
    """两个轴分别给容差（bbox_overlap 两轴共用一个 eps）。eps 为负 = 允许的重叠量。

    pymupdf 的 span bbox **不是墨迹**：它含字体的上/下伸部。同一段文字块里相邻两行
    （行距 2.54、字号 1.8）的 bbox 会互相压 0.36mm；size 2.4 的表头压到下一行 size 1.8
    的正文字上更是压 0.93mm。所以「说明文字之间」的比对**纵向必须放宽到 ~1.2mm**，
    否则整页的说明文字会自己告自己；横向没这个问题，保持严格。
    """
    return not (b1[2] < b2[0] - xeps or b2[2] < b1[0] - xeps or
                b1[3] < b2[1] - yeps or b2[3] < b1[1] - yeps)


def load():
    txt = open(SCH, encoding="utf-8").read()
    root = parse(tokenize(txt))

    # --- 嵌入库符号：符号名 → {pin_number: (ix, iy)}，符号名 → 本体点列表 ---
    lib_pins = {}
    lib_pinmeta = {}
    lib_body = {}
    libs = child(root, "lib_symbols")
    for sym in children(libs, "symbol"):
        topname = unq(sym[1]) if len(sym) > 1 else None  # "jlc:NAME"
        pins = {}
        pinmeta = {}
        bodypts = []
        for sub in sym:
            if not (isinstance(sub, list) and sub and sub[0] == "symbol"):
                continue
            for el in sub:
                if not isinstance(el, list):
                    continue
                if el[0] == "pin":
                    at = child(el, "at")
                    num = child(el, "number")
                    if at and num:
                        ix, iy, _rot = float(at[1]), float(at[2]), float(at[3])
                        pins[unq(num[1])] = (ix, iy)
                        nm = child(el, "name")
                        ln = child(el, "length")
                        pinmeta[unq(num[1])] = {
                            "name": unq(nm[1]) if nm else "",
                            "ix": ix, "iy": iy, "rot": _rot,
                            "len": float(ln[1]) if ln else 2.54,
                        }
                elif el[0] == "rectangle":
                    st, en = child(el, "start"), child(el, "end")
                    bodypts += [(float(st[1]), float(st[2])), (float(st[1]), float(en[2])),
                                (float(en[1]), float(st[2])), (float(en[1]), float(en[2]))]
                elif el[0] == "polyline":
                    # 注意：xy 是 (pts ...) 的子节点，不是 polyline 的直接子节点。
                    # 第 2 轮这里漏了 pts 一层，导致只有 polyline 的符号（0402 电容/电阻、
                    # LED、Y1、L2）本体盒恒为 None，检查 2/6 对它们等于没跑。
                    pts_node = child(el, "pts")
                    for xy in (children(pts_node, "xy") if pts_node else []):
                        bodypts.append((float(xy[1]), float(xy[2])))
                elif el[0] == "arc":
                    for k in ("start", "mid", "end"):
                        p = child(el, k)
                        if p:
                            bodypts.append((float(p[1]), float(p[2])))
                elif el[0] == "circle":
                    c = child(el, "center")
                    r = child(el, "radius")
                    if c and r:
                        cx, cy, rr = float(c[1]), float(c[2]), float(r[1])
                        bodypts += [(cx - rr, cy), (cx + rr, cy), (cx, cy - rr), (cx, cy + rr)]
        lib_pins[topname] = pins
        lib_pinmeta[topname] = pinmeta
        lib_body[topname] = bodypts

    # --- 实例：位号 → (lib_id, x, y, rot, [pin numbers])；可见字段（Reference/Value）文字盒 ---
    instances = {}
    prop_texts = {}  # ref → [(x0, y0, x1, y1, propname)]
    for sym in children(root, "symbol"):
        lib_id = child(sym, "lib_id")
        at = child(sym, "at")
        if not (lib_id and at):
            continue
        ref = None
        insts = child(sym, "instances")
        if insts:
            for p in insts:
                if isinstance(p, list) and p and p[0] == "project":
                    for q in p:
                        if isinstance(q, list) and q and q[0] == "path":
                            r = child(q, "reference")
                            if r:
                                ref = unq(r[1])
        if not ref:
            # 兜底：用 symbol 自身没有 reference 时跳过
            continue
        nums = [unq(p[1]) for p in children(sym, "pin")]
        mir = child(sym, "mirror")
        mirror = bool(mir) and "y" in [unq(v) for v in mir[1:]]
        instances[ref] = (unq(lib_id[1]), float(at[1]), float(at[2]), float(at[3]),
                          nums, mirror)
        for prop in children(sym, "property"):
            pname = unq(prop[1]) if len(prop) > 1 else ""
            if pname not in ("Reference", "Value"):
                continue
            pval = unq(prop[2]) if len(prop) > 2 else ""
            pat = child(prop, "at")
            peff = child(prop, "effects")
            if pat and pval:
                # 有效角度 = 字段存储角度 + 符号实例旋转（KiCad 就是这么渲染的）：
                # 符号 rot=90 的字段存 270°，实际画出来是水平的（pymupdf dir=(1,0) 实测）。
                # 第 2 轮这里写的是「存储角度 % 360 == 0 才查」，把 R55/JP1 这些 rot=90 符号的
                # 字段全跳过了 —— 结果 P1 的重叠正好落在漏检区里。
                ang = float(pat[3]) if len(pat) > 3 else 0.0
                eff = int(round(ang + float(at[3]))) % 360
                h, _ = font_size(peff)
                hj, vj = justify(peff)
                if eff in (0, 180):
                    box = text_bbox(float(pat[1]), float(pat[2]), pval, h, hj, vj)
                else:
                    box = vtext_bbox(float(pat[1]), float(pat[2]), pval, h)
                # 后 4 项给检查 8 用：锚点、水平对齐、文字内容（宽度估算偏小，见 text_width）；
                # 末项字高给检查 12 的墨迹盒用（检查 10–13 一律按墨迹量，见 ink_bbox）。
                prop_texts.setdefault(ref, []).append(
                    (*box, pname, float(pat[1]), float(pat[2]), hj, pval, h))

    # --- 导线 ---
    wires = []
    for w in children(root, "wire"):
        pts = child(w, "pts")
        xys = children(pts, "xy")
        if len(xys) == 2:
            wires.append(((float(xys[0][1]), float(xys[0][2])),
                          (float(xys[1][1]), float(xys[1][2]))))

    # --- 结点 ---
    junctions = set()
    for j in children(root, "junction"):
        at = child(j, "at")
        if at:
            junctions.add((round(float(at[1]), 4), round(float(at[2]), 4)))

    # --- 引脚世界坐标 ---
    pin_world_pos = {}  # (ref, num) -> (x, y)
    for ref, (lib, x, y, rot, nums, mir) in instances.items():
        lp = lib_pins.get(lib, {})
        for num in nums:
            if num in lp:
                ix, iy = lp[num]
                pin_world_pos[(ref, num)] = pin_world(x, y, rot, ix, iy, mir)

    # --- 本体世界包围盒 ---
    body_boxes = {}  # ref -> (xmin, ymin, xmax, ymax)
    for ref, (lib, x, y, rot, nums, mir) in instances.items():
        pts = lib_body.get(lib, [])
        if not pts:
            body_boxes[ref] = None
            continue
        ws = [pin_world(x, y, rot, ix, iy, mir) for (ix, iy) in pts]
        xs = [p[0] for p in ws]
        ys = [p[1] for p in ws]
        body_boxes[ref] = (min(xs), min(ys), max(xs), max(ys))

    # --- 标签/全局标签/说明文字：文字盒 + 锚点 + 字高/对齐（后三项给检查 10/11/13 的墨迹盒）---
    labels = []  # (x0, y0, x1, y1, ax, ay, txt, kind, h, hj, vj)
    for kind, key in [("label", "label"), ("global_label", "global_label")]:
        for node in children(root, key):
            at = child(node, "at")
            eff = child(node, "effects")
            txt = unq(node[1]) if len(node) > 1 else ""
            if at and txt:
                h, _ = font_size(eff)
                hj, vj = justify(eff)
                labels.append((*text_bbox(float(at[1]), float(at[2]), txt, h, hj, vj),
                               float(at[1]), float(at[2]), txt, kind, h, hj, vj))
    for node in children(root, "text"):
        at = child(node, "at")
        eff = child(node, "effects")
        txt = unq(node[1]) if len(node) > 1 else ""
        if at and txt:
            h, _ = font_size(eff)
            hj, vj = justify(eff)
            labels.append((*text_bbox(float(at[1]), float(at[2]), txt, h, hj, vj),
                           float(at[1]), float(at[2]), txt, "text", h, hj, vj))

    # --- 引脚名世界文字盒（非空引脚名，近似本体端位置）---
    pin_name_boxes = {}  # ref → [(x0, y0, x1, y1, num)]
    for ref, (lib, x, y, rot, nums, mir) in instances.items():
        meta = lib_pinmeta.get(lib, {})
        for num in nums:
            m = meta.get(num)
            if not m or not m["name"]:
                continue
            tip = pin_world(x, y, rot, m["ix"], m["iy"], mir)
            wx, wy = pin_dir_world(rot, m["rot"], mir)
            bx = tip[0] + m["len"] * wx
            by = tip[1] + m["len"] * wy
            tw = text_width(m["name"], 1.27)
            pin_name_boxes.setdefault(ref, []).append(
                (*pin_name_bbox(bx, by, wx, wy, tw, 1.27), num))

    return wires, junctions, pin_world_pos, body_boxes, instances, labels, prop_texts, pin_name_boxes


# ---------------------------------------------------------------------------
# 几何工具
# ---------------------------------------------------------------------------
def on_segment(p, a, b, inclusive=False):
    """p 是否在轴对齐线段 ab 上（默认严格内部）。"""
    ax, ay = a
    bx, by = b
    px, py = p
    if abs(ax - bx) < EPS:  # 竖直
        if abs(px - ax) > EPS:
            return False
        lo, hi = min(ay, by), max(ay, by)
        return lo - EPS <= py <= hi + EPS and ((not inclusive) and (py > lo + EPS) and (py < hi - EPS)) if not inclusive else True
    if abs(ay - by) < EPS:  # 水平
        if abs(py - ay) > EPS:
            return False
        lo, hi = min(ax, bx), max(ax, bx)
        if inclusive:
            return lo - EPS <= px <= hi + EPS
        return lo + EPS < px < hi - EPS
    # 斜线：投影参数
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    if inclusive:
        ok = -EPS <= t <= 1 + EPS
    else:
        ok = EPS < t < 1 - EPS
    if not ok:
        return False
    qx, qy = ax + t * dx, ay + t * dy
    return abs(qx - px) < EPS and abs(qy - py) < EPS


def seg_bbox_intersect(a, b, box):
    """轴对齐线段与轴对齐 box 是否相交。"""
    xmin, ymin, xmax, ymax = box
    ax, ay = a
    bx, by = b
    # 线段包围盒
    sx0, sx1 = min(ax, bx), max(ax, bx)
    sy0, sy1 = min(ay, by), max(ay, by)
    if sx1 < xmin - EPS or sx0 > xmax + EPS or sy1 < ymin - EPS or sy0 > ymax + EPS:
        return False
    # 水平/竖直直接判
    if abs(ay - by) < EPS:
        return ymin - EPS <= ay <= ymax + EPS and sx0 <= xmax + EPS and sx1 >= xmin - EPS
    if abs(ax - bx) < EPS:
        return xmin - EPS <= ax <= xmax + EPS and sy0 <= ymax + EPS and sy1 >= ymin - EPS
    # 斜线：对 box 四边做相交（简单化，用中点采样 + 端点）
    pts = [(ax, ay), (bx, by), ((ax + bx) / 2, (ay + by) / 2)]
    for px, py in pts:
        if xmin - EPS <= px <= xmax + EPS and ymin - EPS <= py <= ymax + EPS:
            return True
    return False


# ---------------------------------------------------------------------------
# 检查 8：渲染复核（kicad-cli 导出 PDF + pymupdf 读真实文字盒）
# ---------------------------------------------------------------------------
MM = 72.0 / 25.4  # PDF 用户单位(pt) → mm


def rendered_runs(page):
    """页面上的文字 span → 去重 → 合并成「文字串」，返回 [(x0, y0, x1, y1, text)]（mm）。

    两件必须做的事（都是第 2 轮踩过的）：
      * 去重：同一段文字在 PDF 里会成对出现（实测 R55/JP1 那一带的块 174≡299、175≡300…），
        不去重会把「文字自己和自己重叠」当成重叠报出来；
      * 合并：KiCad 会把一个字段拆成多个 span（实测 C50 的「100nF 16V」= 「100nF」+「 」+「16V」），
        不合并就认不出一个字段是一段文字。
    """
    seen, spans = set(), []
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            for sp in line.get("spans", []):
                txt = sp["text"]
                if not txt.strip():
                    continue
                b = tuple(round(v / MM, 3) for v in sp["bbox"])
                if (b, txt) in seen:
                    continue
                seen.add((b, txt))
                spans.append((b, txt))
    runs = []
    for _ in range(3):  # 多跑两遍，让「合并后才挨上」的串也并起来
        merged = []
        for b, txt in spans:
            for r in merged:
                same_line = (min(b[3], r[3]) - max(b[1], r[1])
                             > 0.5 * min(b[3] - b[1], r[3] - r[1]))
                if same_line and b[0] <= r[2] + 1.6 and b[2] >= r[0] - 1.6:
                    r[0], r[1] = min(r[0], b[0]), min(r[1], b[1])
                    r[2], r[3] = max(r[2], b[2]), max(r[3], b[3])
                    r[4] += txt
                    break
            else:
                merged.append([b[0], b[1], b[2], b[3], txt])
        runs = merged
        spans = [(tuple(r[:4]), r[4]) for r in runs]
    return [tuple(r) for r in runs]


def rendered_spans(page):
    """去重后的**原始 span**（不做合并），返回 [(bbox, text)]。

    为什么重叠判定不能用合并后的 `runs`：合并规则是「同一行、水平间隙 ≤1.6mm 就并」，
    而**互相压着的**两段文字水平间隙是**负的**，一定满足 ≤1.6mm，于是必然被并成一段
    —— 8e 于是什么都看不见。分段 C 就是这么漏掉的：§9 的说明（x 210.82–312.7）和
    §6 的说明（x 304.72–400.9）锚在同一 y=48.26 上、横向压了 7.9mm，而检查全 PASS。
    合并只对「认领字段」有意义（KiCad 会把一个字段拆成多个 span），重叠判定必须用原始 span。
    """
    seen, spans = set(), []
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            for sp in line.get("spans", []):
                txt = sp["text"]
                if not txt.strip():
                    continue
                b = tuple(round(v / MM, 3) for v in sp["bbox"])
                if (b, txt) in seen:
                    continue
                seen.add((b, txt))
                spans.append((b, txt))
    return spans


def rendered_field_check(prop_texts, body_boxes, sch_path):
    """检查 8 本体：把每个可见字段「认领」到它附近真实渲染出来的文字串上，然后
      a) 认领不到（2mm 内没有文字，或文字不在锚点该在的那一侧）→ 字段没画在该画的地方；
      b) 两个不同器件的字段文字串相交 → 文字叠在一起；
      c) 某字段的文字串压到别的器件的本体上 → 正文提到的 P1 那一类问题。
    返回 (fails, 说明行)。PDF 导不出来时返回 None 表示跳过。
    """
    if not shutil.which("kicad-cli"):
        return None
    try:
        import fitz  # pymupdf
    except ImportError:
        return None
    tmp = tempfile.mkdtemp(prefix="chk05_")
    pdf = os.path.join(tmp, "05.pdf")
    r = subprocess.run(["kicad-cli", "sch", "export", "pdf", "--output", pdf, sch_path],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(pdf):
        return None
    doc = fitz.open(pdf)
    runs = rendered_runs(doc[0])
    spans = rendered_spans(doc[0])
    doc.close()

    fails, claimed = [], []
    for ref in sorted(prop_texts):
        for b in prop_texts[ref]:
            x0, y0, x1, y1, pname, ax, ay, hj, val = b[:9]
            best, berr = None, None
            for i, r in enumerate(runs):
                if abs((r[1] + r[3]) / 2 - ay) > 1.0:  # 垂直方向必须对准（字高实测 2.09mm）
                    continue
                if hj == "right":
                    dx = abs(r[2] - ax)
                elif hj == "center":
                    dx = abs((r[0] + r[2]) / 2 - ax)
                else:
                    dx = abs(r[0] - ax)
                if berr is None or dx < berr:
                    best, berr = i, dx
            if best is None or berr > 1.5:
                fails.append(f"[8a] {ref} 字段「{pname}」锚点 ({ax}, {ay}) 附近"
                             f"{'2mm 内无渲染文字' if best is None else f'最近文字横向差 {berr:.2f}mm'}"
                             f"（预测「{val}」）")
                continue
            claimed.append((ref, pname, best, b))

    def inside(box, outer, tol):
        return (box[0] >= outer[0] - tol and box[1] >= outer[1] - tol
                and box[2] <= outer[2] + tol and box[3] <= outer[3] + tol)

    for i in range(len(claimed)):
        for j in range(i + 1, len(claimed)):
            ri, rj = runs[claimed[i][2]], runs[claimed[j][2]]
            if claimed[i][0] != claimed[j][0] and bbox_overlap(ri[:4], rj[:4], eps=-0.15):
                fails.append(f"[8b] {claimed[i][0]} 字段「{claimed[i][1]}」渲染文字「{ri[4]}」{ri[:4]} "
                             f"与 {claimed[j][0]} 字段「{claimed[j][1]}」渲染文字「{rj[4]}」{rj[:4]} 相交")
    claimed_idx = {c[2] for c in claimed}
    for ref, pname, idx, b in claimed:
        run = runs[idx]
        for oref, obox in body_boxes.items():
            if oref == ref or obox is None:
                continue
            if bbox_overlap(run[:4], obox, eps=-0.15):
                fails.append(f"[8c] {ref} 字段「{pname}」渲染文字「{run[4]}」{run[:4]} "
                             f"压在 {oref} 本体 {obox} 上")
        # d) 字段文字压到任何一段「不属于本符号」的其它文字上（标签、别人的引脚名/脚号、图框文字…）。
        #    本符号本体范围内的文字（库自带、画在本体内的引脚名/脚号）豁免 —— 那是符号库 quirk。
        #    第 3 轮就是靠这一条抓到 C57 的数值压住 Y1.2 的 GND 全局标签（8a/8c 都看不见它）。
        own = body_boxes.get(ref)
        for i, r in enumerate(runs):
            if i in claimed_idx:
                continue
            if own and inside(r[:4], own, 0.5):
                continue
            if bbox_overlap(run[:4], r[:4], eps=-0.15):
                fails.append(f"[8d] {ref} 字段「{pname}」渲染文字「{run[4]}」{run[:4]} "
                             f"与另一段渲染文字「{r[4]}」{r[:4]} 相交")
    # e) 说明文字 / 标签文字之间也不许相交。8a–8d 全都拿「字段」当左操作数，两段说明文字
    #    互相压住是看不见的。分段 C 第一版就是这么漏的：§8 两行说明一路顶到 x>420mm，
    #    既越出纸面、又压到 §7 的文字，而 8a–8d + 检查 1–7 全部 PASS。
    #    这里把「既不属于任何字段、也不在任何符号本体内」的文字两两比一遍。
    #    判据不是「纵向重叠多少 mm」，而是**纵向重叠 / 较矮那个 span 的高度**（实测标定）：
    #      * 真缺陷：§9 第 4 行（高 2.90）压住 AFE_3V3 标签（高 1.91）→ 1.026/1.91 = **0.54**；
    #      * 假重叠（同一段文字块相邻两行，字体上下伸部相互穿过）：
    #        标题（2.4 号，高 3.55）压正文（1.8 号，高 2.90）→ 0.948/2.90 = 0.33；
    #        J5 位号字段（高 3.55）压说明「C40669…」→ 0.929/2.39 = 0.39。
    #    真/假之间是 0.39 → 0.54，取阈值 **0.45**。曾试过「用左端是否对齐来分档」，不行：
    #    同一行文字会被拆成多个 span（「§9 电源：…」的首 span 在 210.68、次 span 在 216.85），
    #    左端并不相等，会把标题↔正文误判成真重叠。
    #    **用原始 span 而不是合并后的 runs**（见 rendered_spans 的注释）：合并会把互相压着
    #    的两段文字并成一段，8e 就永远看不见这一类缺陷了。
    #    **用原始 span 而不是合并后的 runs**（见 rendered_spans 的注释）：合并会把互相压着
    #    的两段文字并成一段，8e 就永远看不见这一类缺陷了。
    claimed_boxes = [runs[c[2]][:4] for c in claimed]
    def _in_any(box, boxes):
        return any(inside(box, bb, 0.5) for bb in boxes)
    free = [(i, b, t) for i, (b, t) in enumerate(spans)
            if not _in_any(b, claimed_boxes)
            and not _in_any(b, [bb for bb in body_boxes.values() if bb])]
    for a in range(len(free)):
        for b in range(a + 1, len(free)):
            ba, bb2 = free[a][1], free[b][1]
            ox = min(ba[2], bb2[2]) - max(ba[0], bb2[0])
            oy = min(ba[3], bb2[3]) - max(ba[1], bb2[1])
            hmin = min(ba[3] - ba[1], bb2[3] - bb2[1])
            if ox > -0.15 and hmin > 0 and oy / hmin > 0.45:
                fails.append(f"[8e] 说明/标签文字「{free[a][2]}」{free[a][1]} "
                             f"与「{free[b][2]}」{free[b][1]} 相交"
                             f"（纵向重叠 {oy:.3f}mm = 较矮 span 的 {oy / hmin:.0%}）")
    # f) 文字不许越出页面可用区。几何检查 3/4 只量导线与图元盒，说明文字是 text 图元，
    #    越界后照样 PASS；出图后要靠肉眼才看得见「写出去被裁掉」。
    #    分段 C 第一版就是靠这条抓到 10 段越框文字，其中 §9/§5/§6 三处是分段 A/B 留下的。
    for r in runs:
        x0, y0, x1, y1 = r[:4]
        if (x0 >= TITLE_BLOCK[0] and y0 >= TITLE_BLOCK[1]
                and x1 <= TITLE_BLOCK[2] and y1 <= TITLE_BLOCK[3]):
            # 图框标题栏，KiCad 按模板摆的（见 TITLE_BLOCK）。**但豁免只对「本来就画在
            # 图框里」的文字生效**：标题栏矩形一直开到 x=420，而可用的边框线在 410。第 2 轮
            # 的 comment 1（生成器写的说明行）长到 x=418.94，正好落在豁免矩形里 —— 8f 于是
            # 一声不响，而它其实是「写出去会被裁掉」（复核 P1-3a）。这里要求被豁免的 span
            # 自己也在可用区里；越出的照样报。
            if (x0 >= PAGE_MARGIN and y0 >= PAGE_MARGIN
                    and x1 <= PAGE_W - PAGE_MARGIN and y1 <= PAGE_H - PAGE_MARGIN):
                continue
        if (x0 < PAGE_MARGIN or y0 < PAGE_MARGIN
                or x1 > PAGE_W - PAGE_MARGIN or y1 > PAGE_H - PAGE_MARGIN):
            fails.append(f"[8f] 文字「{r[4]}」{r[:4]} 越出页面可用区"
                         f"（{PAGE_MARGIN}–{PAGE_W - PAGE_MARGIN} × {PAGE_MARGIN}–{PAGE_H - PAGE_MARGIN} mm）")
    return fails, (f"PDF 文字串 {len(runs)} 段（去重+合并后），字段认领 "
                   f"{len(claimed)}/{sum(len(v) for v in prop_texts.values())} 个，"
                   f"自由文字两两比对 {len(free)} 段（原始 span）")


# ---------------------------------------------------------------------------
# 检查 10–13：墨迹盒版面归属（第 2 轮新增）
# ---------------------------------------------------------------------------
# 第 1 轮的检查 1–8 里，b/c/d 三类一条都抓不到（复核 P1-3 的 b/c/d 就是这么漏的）：
# 检查 4 只比「标签 vs 导线」，检查 6/7 比的是「字段 vs 本体」且用偏小的 text_width，
# 8d/8e 只在**渲染域**抓「字段压别人」「文字压文字」，而 P1-3b 的段落重叠、P1-3d 的
# 「标签压引脚 / 标签叠标签」在几何域和渲染域都没人看。阈值全部按第 2 轮改前/改后两棵树
# （`AFE_HW=/tmp/afe-r1-hardware` vs `hardware`）实测标定，注释里给出两侧的实测值。
# 03 页照抄同一组阈值（同一套生成器几何、同一个 A3 图框），不重新标定。
INK_BODY_TOL = 0.15       # 标签/文字墨迹与本体图元的相交容差（留一点描边重叠量）
STACK_GAP = 1.0           # 叠标签：墨迹纵向间隙小于它；再配横向重叠率
STACK_XRATIO = 0.40       # 叠标签：墨迹横向重叠 ≥ 较窄那个的 40%
STACK_DX = 1.0            # 叠标签：锚点横向必须错开 ≥ 1.0mm，同 x 的上下两行不算「叠」
TT_GAP = 0.5              # 说明文字互压：墨迹纵向间隙小于它
TT_DX = 2.0               # 说明文字互压：锚点横向错开 ≥ 2.0mm 才比
FIELD_MARGIN = 0.5        # 字段归属：离别人比离自己近 0.5mm 以上才算
FIELD_MIN_OWN = 2.0       # 字段归属：离自己本体 2mm 以内的一律不查（贴着的字段必然安全）


def ink_layout_check(labels, prop_texts, body_boxes):
    """检查 10–13。返回 (fails, note)。"""
    fails = []

    def ink_of(item):
        _x0, _y0, _x1, _y1, ax, ay, txt, kind, h, hj, vj = item
        pad = GLBL_PAD if kind == "global_label" else 0.0
        return ink_bbox(ax, ay, txt, h, hj, vj, pad)

    # 10. 标签/说明文字的墨迹不许压到器件本体图元上。第 2 轮复核 P1-3d「C213 的 GND 标签
    #     压在引脚上」就是这一类：R1 的 GND 标签墨迹 (251.76,87.95–255.27,89.85) 与 C213
    #     本体 (247.65,84.33–252.73,88.39) 相交 0.97×0.44mm，渲染出来「GND」那段文字真的
    #     压在电容极板上（实测墨迹 x 重叠 2.99mm）；改后 C213 竖放、标签离开本体，不再触发。
    #     这一条同时抓住 C221 的 GND（同一处布局，R1/R2 都有）—— 复核只点了 C213，C221 是
    #     同病，第 2 轮一并修（下移一个栅格）。
    for it in labels:
        box = ink_of(it)
        for ref, bb in body_boxes.items():
            if bb is None:
                continue
            ox = min(box[2], bb[2]) - max(box[0], bb[0])
            oy = min(box[3], bb[3]) - max(box[1], bb[1])
            if ox > INK_BODY_TOL and oy > INK_BODY_TOL:
                fails.append(
                    f"[10] {it[7]}「{it[6]}」墨迹 ({box[0]:.2f},{box[1]:.2f}–{box[2]:.2f},{box[3]:.2f}) "
                    f"压在 {ref} 本体 {bb} 上（重叠 {ox:.2f} × {oy:.2f} mm，锚点 ({it[4]},{it[5]})）")

    # 11. 两段标签/说明文字不许叠在一起（复核 P1-3d：两个 REG_C 标签叠放、SRN_F 与 GND 挤在
    #     一起）。**间隙单独用分不出来**：R1 的 REG_C 对间隙 +0.64、SRN_F 对 −0.63，而改后
    #     合法的 PACKP/PACKP 对（两根 100Ω 引到同一个网，KiCad 要求两处都标）间隙也是 +0.64。
    #     能分开的是**横向错开量**：REG_C 那对锚Δx 6.35、墨迹横向重叠 91%（两段文字几乎完全
    #     上下重合），PACKP 那对锚Δx 10.16、横向只重叠 26%（看得清是两个名字）；同列上下紧排
    #     （VC0/VC1 这类，锚Δx=0）也放行。三个条件一起用，R1 报 2 条、R2 报 0 条。
    #     **只比标签 vs 标签**：标签与说明文字之间不能比纵向（全局标签的文字画在图形框里，
    #     模型纵向误差实测 0.2–1.2mm —— 例如 (360.68,88.90) 的 GND 与 §6 说明首行模型间隙
    #     +0.24mm，PDF 实测 +0.86mm），涉及说明文字的重叠交给检查 13（它只比文字 vs 文字）。
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            A, B = labels[i], labels[j]
            if A[7] == "text" or B[7] == "text":
                continue
            ba, bc = ink_of(A), ink_of(B)
            wmin = min(ba[2] - ba[0], bc[2] - bc[0])
            if wmin <= 0:
                continue
            ox = min(ba[2], bc[2]) - max(ba[0], bc[0])
            gap = max(bc[1] - ba[3], ba[1] - bc[3])
            if (ox / wmin >= STACK_XRATIO and gap < STACK_GAP
                    and abs(A[4] - B[4]) >= STACK_DX):
                fails.append(
                    f"[11] {A[7]}「{A[6]}」({A[4]:.2f},{A[5]:.2f}) 与 {B[7]}「{B[6]}」"
                    f"({B[4]:.2f},{B[5]:.2f}) 叠在一起：墨迹纵向间隙 {gap:.2f}mm、"
                    f"横向重叠 {ox / wmin:.0%}（较窄那个）、锚Δx {abs(A[4] - B[4]):.2f}mm")

    # 12. 可见字段离自己的器件太远、反而离别人的器件更近（复核 P1-3c：C226 的位号与
    #     「100nF 100V DNP」被摆在 C220 正下方，读图会把 C220 看成 DNP）。量 2D 边到边间距：
    #     R1 的 C226 位号到 C220 本体 0.64 / 到自己 3.12（Δ=−2.48），值到 C220 本体 7.62 /
    #     到自己 8.21（Δ=−0.59）；改后位号居中到自己轴上（Δ=+5.49），值也居中（Δ≈0）。
    #     留 0.5mm 余量是因为同排等距的两个器件（R206/R207、C205/C206）会出现 Δ≈0 的**平局**
    #     —— 那是排版对称，不是缺陷。
    for ref in sorted(prop_texts):
        own = body_boxes.get(ref)
        if own is None:
            continue
        for b in prop_texts[ref]:
            fbox = ink_bbox(b[5], b[6], b[8], b[9], b[7], "center")
            d_own = box_gap(fbox, own)
            if d_own <= FIELD_MIN_OWN:
                continue
            near = min(((box_gap(fbox, bb), r) for r, bb in body_boxes.items()
                        if bb is not None and r != ref), default=None)
            if near and near[0] < d_own - FIELD_MARGIN:
                fails.append(
                    f"[12] {ref} 字段「{b[4]}」{b[8]!r} 锚点 ({b[5]:.2f},{b[6]:.2f}) "
                    f"离自己本体 {d_own:.2f}mm，却离 {near[1]} 本体只有 {near[0]:.2f}mm")

    # 13. 两段说明文字不许互相压住（复核 P1-3b：画图过程文字压在 §9 标题上）。渲染域的 8e
    #     要出图后才看得见，这里在生成域先量一遍。只比「说明文字 vs 说明文字」：涉及**标签**
    #     的纵向量不准（全局标签的文字画在图形框里，模型与渲染的系统偏差 0.2–1.2mm，实测
    #     有一对模型 −0.84mm 而渲染 +0.18mm），涉及标签的交给 11（用的是相对量）。
    #     要求锚Δx ≥ 2mm：同一段说明里上下两行是分开的 text 图元、锚点同 x，不该互告。
    #     R1 的过程文字（锚 20.32,40.64）与 §9 标题（锚 190.50,43.18）墨迹纵向压 0.60mm；
    #     R2 里锚Δx ≥ 2mm 的说明文字对最小间隙 +2.57mm。
    texts = [it for it in labels if it[7] == "text"]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            A, B = texts[i], texts[j]
            if abs(A[4] - B[4]) < TT_DX:
                continue
            ba, bc = ink_of(A), ink_of(B)
            if min(ba[2], bc[2]) - max(ba[0], bc[0]) <= 0:   # 横向不重叠的不算「压」
                continue
            gap = max(bc[1] - ba[3], ba[1] - bc[3])
            if gap < TT_GAP:
                fails.append(
                    f"[13] 说明文字「{A[6]}」({A[4]:.2f},{A[5]:.2f}) 与「{B[6]}」"
                    f"({B[4]:.2f},{B[5]:.2f}) 墨迹纵向间隙 {gap:.2f}mm（锚Δx {abs(A[4] - B[4]):.2f}mm）")
    return fails, (f"标签/文字墨迹 {len(labels)} 处（其中说明文字 {len(texts)} 处）、"
                   f"字段 {sum(len(v) for v in prop_texts.values())} 个，与 {len(body_boxes)} 个本体盒比对；"
                   f"检查 10/11/12/13")


# ---------------------------------------------------------------------------
# 检查 9：网表逐脚核对（规格书 §3.1 / §3.2 / §4）
# ---------------------------------------------------------------------------
# 规格书 §3.1「每节通用连接」的模板——k 展开成位号。键是脚号，值是本页网络名
# （去页前缀）；None = 悬空放 NC 标志（U30k.1）。
def _section(k: int):
    prev = f"VB{k - 1}"
    return {
        f"R30{k}": {"1": f"IN{k}", "2": prev},
        f"C30{k}": {"1": f"VB{k}", "2": prev},
        f"C31{k}": {"1": f"VB{k}", "2": prev},
        # 首级（k = 1）是交流耦合 CLK_R（§8.1b U-3B），k ≥ 2 接上一级的驱动输出。
        f"C32{k}": {"1": "CLK_R" if k == 1 else f"DRV{k - 1}", "2": f"IN{k}"},
        f"U30{k}": {"1": None, "2": f"IN{k}", "3": prev, "4": f"DRV{k}", "5": f"VB{k}"},
        f"R31{k}": {"1": f"DRV{k}", "2": f"GN{k}"},
        f"R32{k}": {"1": f"DRV{k}", "2": f"GP{k}"},
        # 二极管极性不可对调：D30k 的 K 接 DRVk、D31k 的 K 接 GPk（§3.1 末条）。
        f"D30{k}": {"1": f"DRV{k}", "2": f"GN{k}"},
        f"D31{k}": {"1": f"GP{k}", "2": f"DRV{k}"},
        f"Q30{k}": {"1": f"GN{k}", "2": prev, "3": f"X{k}"},
        f"Q31{k}": {"1": f"GP{k}", "2": f"VB{k}", "3": f"X{k}"},
    }


# 全页端子表（§3.1 模板 + §3.2 的 60 个网络）＝ 8 节 ×27 + 飞电容 14×2 + R300 2
# + F300–F308 9×2 + J6 10 = **274 个编号引脚**（与 §3.2 末尾的核对数一致）。
# 分段 A 只画了其中一部分，9c 对「图纸上没有的位号」只列缺件清单、不算失败。
PART_EXPECT = {
    **{ref: pins for k in range(1, 9) for ref, pins in _section(k).items()},
    # 飞电容 C33j/C34j 跨 Xj ↔ X(j+1)，j = 1..7（每级 2×100µF）。
    **{f"C33{j}": {"1": f"X{j}", "2": f"X{j + 1}"} for j in range(1, 8)},
    **{f"C34{j}": {"1": f"X{j}", "2": f"X{j + 1}"} for j in range(1, 8)},
    # 首级时钟输入（§3.1 末）：BAL_CLK 是全局标签，05 页 PA8 驱动。
    "R300": {"1": "BAL_CLK", "2": "CLK_R"},
    # 熔丝 F30k：BALk（板端全局）↔ VBk，k = 0..8。
    **{f"F30{k}": {"1": f"BAL{k}", "2": f"VB{k}"} for k in range(0, 9)},
    # J6 线束端子（§4）：焊盘 n 接 BAL(n−1)（n = 1..9），焊盘 10 无连接标志。
    "J6": {**{str(n): f"BAL{n - 1}" for n in range(1, 10)}, "10": None},
}

# 本页没有任何 DNP 件（§2.2 器件表里没有备位）。留空元组，将来要加备位时写在这里。
DNP_REFS = ()

# 值/LCSC/库符号期望表（检查 9p）：ref → (库符号名, 值, 立创编号)。
# **为什么单开一张表**：9c/9j 只核「哪只脚接哪个网」——一只参数不对但**脚位兼容**的件能
# 全过（0402 电阻换阻值、SOD-323 换同封装肖特基，网络一根不动），9i 又只查 ST LCSC 的
# *格式*。第 2 轮换料（P1-1 肖特基结电容、P1-2 输入下拉分级）恰恰是靠参数起作用的，
# 所以把这些件抄成一张独立于生成器的表：值和料号写错一格就报出来。
# 来源：`design/03_balancer-spec.md` §8.1c（用户 2026-09-28 决定）+ `docs/02-BOM.csv`。
# 全页其余器件的值由 9p 的 BOM 那一半兜（对 docs/02-BOM.csv 逐件核）。
PART_VALUE_EXPECT = {
    # R301 保持 100k：它是整套死区时序的基准，停时钟时最先泄放完。
    **{f"R30{k}": (("0402WGF1003TCE", "100k 1%", "C25741") if k == 1
                   else ("0402WGF3303TCE", "330k 1%", "C25778")) for k in range(1, 9)},
    # 1N5819WS（CT≈110pF）→ BAT54WS（CT≤10pF），否则栅极被结电容顶过阈值、死区失效。
    **{f"D3{k}{j}": ("BAT54WSL9", "BAT54WS", "C22629") for k in (0, 1) for j in range(1, 9)},
}


def expand_refs(field: str):
    """BOM 的位号栏 → 位号列表：`R301`、`R302-R308`、`R311-R318 R321-R328`、`D301-D308 D311-D318`。"""
    out = []
    for tok in re.split(r"[\s,、]+", field.strip()):
        if not tok:
            continue
        m = re.fullmatch(r"([A-Za-z]+)(\d+)-([A-Za-z]*)(\d+)", tok)
        if m:
            p1, n1, p2, n2 = m.group(1), int(m.group(2)), m.group(3) or m.group(1), int(m.group(4))
            if p1 == p2:
                out += [f"{p1}{n}" for n in range(n1, n2 + 1)]
                continue
        out.append(tok)
    return out


def diode_polarity_geometry(sch_path):
    """从原理图的 lib_symbols 里量二极管符号的**极性几何**（检查 9q 用）。

    返回 {符号名: {"axis", "base", "apex", "cathode_lo", "cathode_hi", "pin": {num: 坐标}}}：
      · axis：判断极性的轴（x 或 y，取三角有两个不同取值的那根）；
      · base/apex：三角底边与顶点在该轴上的坐标（顶点＝阴极侧）；
      · cathode_lo/hi：非三角折线（阴极横杠＋肖特基钩，或矩形）在该轴上的范围。
    判据只用到「顶点在哪一侧」——嘉立创符号的脚名都是 passive，K/A 只能从图形上认。
    """
    root = parse(tokenize(open(sch_path, encoding="utf-8").read()))
    out = {}
    for sym in children(child(root, "lib_symbols"), "symbol"):
        name = unq(sym[1])
        pins, polys = {}, []
        for sub in children(sym, "symbol"):
            for el in sub:
                if not isinstance(el, list):
                    continue
                if el[0] == "pin":
                    at, num = child(el, "at"), child(el, "number")
                    if at and num:
                        pins[unq(num[1])] = (float(at[1]), float(at[2]))
                elif el[0] in ("polyline", "rectangle"):
                    if el[0] == "rectangle":
                        st, en = child(el, "start"), child(el, "end")
                        pts = [(float(st[1]), float(st[2])), (float(st[1]), float(en[2])),
                               (float(en[1]), float(en[2])), (float(en[1]), float(st[2]))]
                    else:
                        ptsn = child(el, "pts")
                        pts = [(float(xy[1]), float(xy[2]))
                               for xy in (children(ptsn, "xy") if ptsn else [])]
                    if len(pts) >= 2:
                        polys.append(pts)
        tri_i = None
        for i, pts in enumerate(polys):
            if len(pts) >= 4 and pts[0] == pts[-1] and len(set(pts[:-1])) == 3:
                tri_i = i               # 闭合且只有 3 个不同顶点 = 二极管三角
                break
        if tri_i is None or len(pins) < 2:
            continue
        tri = polys[tri_i][:-1]
        for axis in (0, 1):
            vals = [p[axis] for p in tri]
            uniq = sorted(set(vals))
            if len(uniq) != 2:
                continue
            base = uniq[0] if vals.count(uniq[0]) == 2 else uniq[1]
            apex = uniq[1] if base == uniq[0] else uniq[0]
            marks = [p[axis] for i, pts in enumerate(polys) if i != tri_i for p in pts]
            if not marks:
                break
            out[name] = {"axis": "xy"[axis], "base": base, "apex": apex,
                         "cathode_lo": min(marks), "cathode_hi": max(marks),
                         "pin": pins}
            break
    return out

# 本页不许出现的电源网络（§3.2 末条：电源符号 0 个，VBk 全部用局部标签）。
POWER_NETS = ("GND", "GNDA", "GNDD", "+3V3", "+5V", "+12V", "VBUS", "VCC")


def netbase(name: str):
    """网表网络名 → 本页网络名。`unconnected-…` 归一成 None（NC 脚）。"""
    if name.startswith("unconnected-"):
        return None
    return name.rsplit("/", 1)[-1]


def netlist_pin_check(sch_path, root_sch):
    """以根图导出网表，逐脚核对本页已画器件的端子（规格书 §3.1/§3.2）。返回 (fails, note) 或 None。"""
    if not shutil.which("kicad-cli") or not os.path.exists(root_sch):
        return None
    with tempfile.TemporaryDirectory() as td:
        xml = os.path.join(td, "net.xml")
        r = subprocess.run(["kicad-cli", "sch", "export", "netlist",
                            "--format", "kicadxml", "-o", xml, root_sch],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(xml):
            return [f"[9] 网表导出失败：{r.stderr.strip()[:200]}"], "导出失败"
        root = ET.parse(xml).getroot()

    nodes = {}   # ref → {pin: 本页网络名}
    for net in root.iter("net"):
        nm = netbase(net.get("name"))
        for n in net.findall("node"):
            nodes.setdefault(n.get("ref"), {})[n.get("pin")] = nm

    fails = []
    # 图纸上已实例化的位号（顶层实例在文件里缩进一个 tab：`\n\t(symbol\n`）。按这个切块，
    # 避免正则跨行匹配写歪（02 页第一版就写歪过，报了个假 FAIL）。9c 用它区分
    # 「已画但接错」与「这一段还没画」——分段 A 只画了第 1–4 节。
    body = open(sch_path, encoding="utf-8").read()
    starts = [m.start() for m in re.finditer(r"\n\t\(symbol\n", body)]
    blocks = [body[s:e] for s, e in zip(starts, starts[1:] + [len(body)])]
    refs_here = []
    for b in blocks:
        m = re.search(r'"Reference" "([^"]+)"', b)
        if m:
            refs_here.append(m.group(1))
    # 9b：NC 脚必须真悬空（每个 unconnected- 网只有一个节点）
    for net in root.iter("net"):
        nm = net.get("name")
        if nm.startswith("unconnected-") and len(net.findall("node")) != 1:
            fails.append(f"[9b] NC 网络 {nm} 挂了 {len(net.findall('node'))} 个节点，不是真悬空")
    # 9c：逐脚核对规格书 §3.1/§3.2 的端子表。图纸上没有的位号只进缺件清单、不算失败
    #     ——但**已画**的位号少一个脚、多一个脚、接错网，都要报出来。
    n_pins, n_checked, missing = 0, 0, []
    swapped = []

    def swapped_ok(ref, want, got):
        """R/C/F 两脚件的 1、2 脚正好对调时算通过。

        规格书 §3.1 末条：「两脚无极性件（R、C、F）1、2 脚对调都可以……**二极管的极性
        不可对调**」。所以只对 R/C/F 且都是两脚、且两脚网络正好互换时放行；网络集合
        不对（接错网/少脚）依旧报 FAIL，二极管（1 = K）依旧严格。
        """
        if not ref.startswith(("R", "C", "F")) or len(want) != 2 or len(got) != 2:
            return False
        return got.get("1") == want["2"] and got.get("2") == want["1"]

    for ref, want in sorted(PART_EXPECT.items()):
        n_pins += len(want)
        if ref not in refs_here:
            missing.append(ref)
            continue
        n_checked += len(want)
        got = nodes.get(ref, {})
        if all(got.get(p) == n for p, n in want.items()):
            pass
        elif swapped_ok(ref, want, got):
            swapped.append(ref)          # 对调已由 §3.1 放行，只计数、报 FAIL 时不出现
        else:
            for pin, net in sorted(want.items()):
                if got.get(pin, "<网表里没有这个脚>") != net:
                    fails.append(f"[9c] {ref}.{pin} 网络 {got.get(pin)!r}，规格书 §3.1 要求 {net!r}")
        extra = sorted(set(got) - set(want))
        if extra:
            fails.append(f"[9c] {ref} 多出规格书没写的脚：{extra}")
    # 9d：DNP 件必须带 (dnp yes)。本页暂时没有 DNP 件（DNP_REFS 空），反向那条
    #     （没标 DNP 的实例里冒出 (dnp yes)）仍然有效。
    for ref in DNP_REFS:
        blk = next((b for b in blocks if f'"Reference" "{ref}"' in b), None)
        if blk is None:
            fails.append(f"[9d] 文件里找不到实例 {ref}")
        elif "(dnp yes)" not in blk:
            fails.append(f"[9d] {ref} 没有标 (dnp yes)")
    # 反向：没标 DNP 的实例里不该冒出 (dnp yes)（本页 DNP = 无）
    for b in blocks:
        m = re.search(r'"Reference" "([^"]+)"', b)
        if m and "(dnp yes)" in b and m.group(1) not in DNP_REFS:
            fails.append(f"[9d] {m.group(1)} 意外标了 (dnp yes)")
    # 9f：位号必须是「字母前缀 + 纯数字」。02 页规格书原本写 C219B——尾随字母 KiCad 的
    #     annotator 解析不出序号，根图导网表会报 `Warning: schematic has annotation errors`
    #     （该页实测：把 C219B 单独留在图上就复现，改成 C226 后消失）。这类位号能顺利过
    #     检查 1–8，却会让 BOM/PCB 同步出问题，所以单列一项。03 页的位号是 3xx 段，
    #     飞电容 C33j/C34j 也是纯数字（C331–C337 / C341–C347）。
    for ref in refs_here:
        if not re.fullmatch(r"[A-Za-z]+[0-9]+", ref):
            fails.append(f"[9f] 位号 {ref!r} 不合法（必须是字母前缀 + 纯数字，尾随字母 KiCad 不认）")
    # 9g：本页不许出现电源网络。§3.2 末条：本页电源符号 0 个，VBk 全部用局部标签，
    #     每节 74LVC1G17 的「地」就是 VB(k−1)（浮在电芯串上）。一旦某处误接了 GND，
    #     第 k 节的参考点就被拉到板地，半桥栅压会出错，整节失效——而且 ERC 只看
    #     「有没有电源符号」，网表侧没人看，所以在这里量 KiCad 自己连出来的网。
    #     **只查本页的位号**：导出的网表是整张根图的，别的子页（02/04/05）上 GND、+3V3
    #     满天飞——第一版没按 Sheetfile 过滤，凭空报了 79 条（C210.1 之类根本没画在本页）。
    for ref in refs_here:
        for pin, net in sorted(nodes.get(ref, {}).items()):
            if net in POWER_NETS:
                fails.append(f"[9g] {ref}.{pin} 落在电源网络 {net!r} 上，本页不放任何电源符号（§3.2）")

    # 9h：DNP 件除了 (dnp yes) 之外，值里还必须写明 DNP。只标 KiCad 的 dnp 标志不够——
    #     出 BOM/给贴片厂看的是 Value 文本，位号后缀又没有额外标记，值里不写就会「照贴」。
    for b in blocks:
        m = re.search(r'"Reference" "([^"]+)"', b)
        if not m or m.group(1) not in DNP_REFS:
            continue
        vm = re.search(r'"Value" "([^"]*)"', b)
        if not vm or "DNP" not in vm.group(1):
            fails.append(f"[9h] DNP 件 {m.group(1)} 的值 {vm.group(1) if vm else '<无>'!r} 里没写 DNP")
    # 9i：每个器件都必须有 Footprint 与 LCSC。走线/网表核对看不出「封装漏填」——
    #     漏填的器件在原理图上完全正常，直到 PCB 同步时才报「找不到封装」。
    #     嘉立创件的 LCSC 编号还会一路带到 BOM/成本表，空值会静默丢料。
    #     图纸实例属性和网表两处都读：图纸那份是「生成器有没有老实写字段」的源头（不依赖
    #     导出器），网表那份是 BOM/贴片厂真正吃的数据。负例实测两处都会随实例属性一起空掉。
    #     另外 LCSC 要做格式校验——写成 ABC123 这种非立创编号，嘉立创下单时会直接找不到料。
    for b in blocks:
        m = re.search(r'"Reference" "([^"]+)"', b)
        if not m:
            continue
        ref = m.group(1)
        fp = re.search(r'\(property "Footprint" "([^"]*)"', b)
        lc = re.search(r'\(property "LCSC" "([^"]*)"', b)
        if not fp or not fp.group(1).strip():
            fails.append(f"[9i] {ref} 没填 Footprint（实例属性；空着会被库符号的默认封装顶替）")
        if not lc or not lc.group(1).strip():
            fails.append(f"[9i] {ref} 没填 LCSC（嘉立创 C 编号）")
        elif not re.fullmatch(r"C[0-9]+", lc.group(1).strip()):
            fails.append(f"[9i] {ref} 的 LCSC {lc.group(1)!r} 不是立创 C 编号格式")
    # 网表侧再核一遍（网表是 BOM/贴片厂真正吃的那份数据）
    mine = os.path.basename(sch_path)
    n_comp = 0
    for comp in root.iter("comp"):
        props = {p.get("name"): (p.get("value") or "") for p in comp.iter("property")}
        if props.get("Sheetfile") != mine:      # 根图网表含全部子页，只核本页
            continue
        n_comp += 1
        if not (comp.findtext("footprint") or "").strip():
            fails.append(f"[9i] 网表里 {comp.get('ref')} 没有 footprint")

    # 9j：反方向核对——规格书 §3.2 的 60 个网络，逐个核「网络 → 脚集合」。
    #     9c 是「脚 → 网络」（每只脚接对了网）；反过来把同一张表按网络名聚合，再和网表里
    #     同名网络的实际节点集合对一遍。两个方向都过，才能排除「表本身抄漏了一行」这类
    #     错误——例如某节的 DRVk 少写一只脚，9c 只会照着（同样错的）表放行，而按 §3.2 的
    #     网络表聚合时那条网络就少一个成员。两脚无极性件（R/C/F）允许 1、2 脚对调（§3.1
    #     末条），比对时按二端元件处理：脚集合相同即可。
    want_net: dict = {}
    for ref, want in PART_EXPECT.items():
        for pin, net in want.items():
            if net is not None:
                want_net.setdefault(net, {}).setdefault(ref, set()).add(pin)
    got_net: dict = {}
    for net in root.iter("net"):
        nm = netbase(net.get("name"))
        if nm is None:
            continue
        for nd in net.findall("node"):
            if nd.get("ref") in refs_here:
                got_net.setdefault(nm, {}).setdefault(nd.get("ref"), set()).add(nd.get("pin"))
    for nm in sorted(want_net):
        w, g = want_net[nm], got_net.get(nm, {})
        if set(w) != set(g):
            only_w = sorted(set(w) - set(g))
            only_g = sorted(set(g) - set(w))
            fails.append(f"[9j] 网络 {nm} 的成员与 §3.2 不符："
                         f"规格书有而网表没有 {only_w}；网表多出 {only_g}")
            continue
        for ref in sorted(w):
            if w[ref] == g[ref]:
                continue
            # 二端件 1/2 脚对调（§3.1 放行）：网络成员不变，脚序由 9c 一并放行。
            # 注意要按「该器件的总脚数」判断，不能看它在这个网络里的脚数（每网只有 1 个）。
            if ref.startswith(("R", "C", "F")) and len(PART_EXPECT[ref]) == 2:
                continue
            fails.append(f"[9j] 网络 {nm} 上 {ref} 连的是 {sorted(g[ref])}，§3.2 要求 {sorted(w[ref])}")
    n_spec_net = len(want_net)

    # 9l：本页网络全集必须正好是 §3.2 的 60 个，且不得出现 GND/电源/CELL* 网络。
    #     9g 是按脚查电源网（某只脚落到 GND 上就报），这里按网络查：多出一整条规格书
    #     没写的网络（例如误把某节的地接到 02 页的 CELL3 采样网）同样要拦下。
    actual = set()
    for net in root.iter("net"):
        nm = net.get("name")
        if nm.startswith("unconnected-"):
            continue
        if any(nd.get("ref") in refs_here for nd in net.findall("node")):
            actual.add(netbase(nm))
    for extra in sorted(actual - set(want_net)):
        fails.append(f"[9l] 本页多出规格书 §3.2 没写的网络 {extra!r}")
    for miss in sorted(set(want_net) - actual):
        fails.append(f"[9l] 规格书 §3.2 的网络 {miss!r} 在本页没出现")
    for nm in sorted(actual):
        if nm.startswith("CELL") or nm in POWER_NETS:
            fails.append(f"[9l] 本页出现网络 {nm!r}（本页不得有 GND/电源/CELL* 网络，§3.2 末条）")

    # 网表里本页的每件：ref → 库符号名 / 值 / LCSC（9p、9q 共用）
    comps_here = {}
    for comp in root.iter("comp"):
        props = {p.get("name"): (p.get("value") or "") for p in comp.iter("property")}
        if props.get("Sheetfile") != mine:
            continue
        ls = comp.find("libsource")
        comps_here[comp.get("ref")] = {
            "sym": (ls.get("part") if ls is not None else "") or "",
            "value": comp.findtext("value") or "",
            "lcsc": props.get("LCSC", ""),
        }

    # 9p：值/LCSC/库符号核对。分两半——
    #     (a) 第 2 轮换料（PART_VALUE_EXPECT）：逐件核库符号名、值、LCSC；
    #     (b) 全页 113 件对 `docs/02-BOM.csv`：LCSC 必须一格不差，值必须能在该行文字里找到。
    #     为什么 (a) 不能省：(b) 只证明「原理图与 BOM 一致」——两份一起错（比如 R302 全写回
    #     100k）时 (b) 是绿的，而 (a) 是按 §8.1c 的**用户决定**写死的，能把它揪出来。
    #     反过来 (b) 也不能省：(a) 只盯第 2 轮动过的 24 件。
    n_val = 0
    for ref, (sym, val, lcsc) in sorted(PART_VALUE_EXPECT.items()):
        if ref not in refs_here:
            continue
        n_val += 1
        got = comps_here.get(ref, {})
        if got.get("sym") != sym:
            fails.append(f"[9p] {ref} 用的库符号是 {got.get('sym')!r}，第 2 轮换料后应为 {sym!r}")
        if got.get("value") != val:
            fails.append(f"[9p] {ref} 的值是 {got.get('value')!r}，§8.1c 要求 {val!r}")
        if got.get("lcsc") != lcsc:
            fails.append(f"[9p] {ref} 的 LCSC 是 {got.get('lcsc')!r}，应为 {lcsc!r}")
    bom, n_bom, bom_note = {}, 0, f"docs/02-BOM.csv 不存在（{BOM}）"
    if os.path.exists(BOM):
        with open(BOM, encoding="utf-8") as fh:
            for row in list(csv.reader(fh))[1:]:
                if len(row) >= 6 and row[1].strip():
                    for r in expand_refs(row[1]):
                        bom[r] = row
        for ref in sorted(refs_here):
            row = bom.get(ref)
            if row is None:
                continue
            n_bom += 1
            got = comps_here.get(ref, {})
            if got.get("lcsc") != row[5].strip():
                fails.append(f"[9p] {ref} 的 LCSC {got.get('lcsc')!r} 与 docs/02-BOM.csv 的 "
                             f"{row[5].strip()!r} 不一致")
                continue
            btxt = " ".join(row[3:9])
            val = got.get("value", "")
            if val and val not in btxt and val.split()[0] not in btxt:
                fails.append(f"[9p] {ref} 的值 {val!r} 在 docs/02-BOM.csv 该行里找不到"
                             f"（行文字：{btxt.strip()!r}）")
        bom_note = f"docs/02-BOM.csv 逐件核对 {n_bom} 件"

    # 9q：二极管 K/A 方向核对（§3.1 末条「二极管的极性不可对调」+ §3.2 网络表）。
    #     9c/9j 已经能报「D30k.1 接的不是 DRVk」，但它们只在**脚号**层面说话：脚号本身
    #     是靠库符号的 `(number "1")` 认的，谁把库符号的两条腿数字对调（或者换成一个
    #     图形反过来的同封装肖特基），9c 照样全绿。所以这里两头一起核：
    #       (a) 图形：从 lib_symbols 里量三角顶点（阴极）在哪一侧，要求 pin 1 在同一侧，
    #           且阴极横杠/肖特基钩也在那一侧——脚名都是 passive，K/A 只能从图形上认；
    #       (b) 网络：按 §3.2，D30k 的 K=DRVk / A=GNk，D31k 的 K=GPk / A=DRVk。
    #     报错一律用 K/A 的说法，接反了能一眼看出是极性错而不是「脚接错网」。
    geo = diode_polarity_geometry(sch_path)
    POLARITY = {**{f"D30{k}": (f"DRV{k}", f"GN{k}") for k in range(1, 9)},
                **{f"D31{k}": (f"GP{k}", f"DRV{k}") for k in range(1, 9)}}
    n_diode = 0
    for ref, (knet, anet) in sorted(POLARITY.items()):
        if ref not in refs_here:
            continue
        n_diode += 1
        sym = comps_here.get(ref, {}).get("sym", "")
        g = geo.get(f"jlc:{sym}")
        if g is None:
            fails.append(f"[9q] {ref} 用的符号 {sym!r} 里找不到「闭合三角 + 阴极横杠」的二极管图形，"
                         f"K/A 方向无法从图形上认，不放行")
            continue
        ax = "xy".index(g["axis"])
        mid = (g["base"] + g["apex"]) / 2.0
        side = 1 if g["apex"] > mid else -1        # 三角顶点（＝阴极）所在的一侧
        p1 = g["pin"].get("1")
        if p1 is None or (p1[ax] - mid) * side <= 0:
            fails.append(f"[9q] 符号 {sym!r} 的图形里 pin 1 不在三角顶点（阴极）一侧："
                         f"顶点 {g['apex']}、pin1 {p1[ax] if p1 else None}——脚号与图形不符，"
                         f"接对了网也认不出极性")
        if (g["cathode_lo"] - mid) * side <= 0 or (g["cathode_hi"] - mid) * side <= 0:
            fails.append(f"[9q] 符号 {sym!r} 的阴极横杠 [{g['cathode_lo']}, {g['cathode_hi']}] "
                         f"不在三角顶点（阴极）一侧（顶点 {g['apex']}）")
        got = nodes.get(ref, {})
        if got.get("1") != knet or got.get("2") != anet:
            fails.append(f"[9q] {ref} 极性接反/接错：K(脚1) 是 {got.get('1')!r}、A(脚2) 是 "
                         f"{got.get('2')!r}；§3.2 要求 K={knet!r}、A={anet!r}")

    note = f"逐脚核对 {n_checked}/{n_pins} 项（§3.1/§3.2 全页 274 脚，图纸上已画 {len(refs_here)} 件）；" \
           f"网络方向核对 {n_spec_net} 个网络（§3.2）＝网表实际 {len(actual)} 个，本页无 GND/电源/CELL* 网；" \
           f"Footprint/LCSC 核对 {n_comp} 件"
    note += f"；值/LCSC/符号核对 {n_val} 件（第 2 轮换料，§8.1c）；" \
            f"二极管 K/A 方向 {n_diode} 只（图形 + §3.2 网络）；{bom_note}"
    if swapped:
        note += f"；R/C/F 两脚对调 {len(swapped)} 处（§3.1 允许）：{', '.join(swapped)}"
    if missing:
        note += f"；**未画位号 {len(missing)} 个**（留给后续分段）：{', '.join(missing)}"
    return fails, note


# ---------------------------------------------------------------------------
# 检查 9m：网络类核对（规格书 §3.3）
# ---------------------------------------------------------------------------
# §3.3 的要点：3A 的均衡电流走 Xk/VBk，网络类 BAL_3A（线宽/间距按 3A 定）必须真匹配上；
# 而 CLK（BAL_CLK）是一条弱信号线，**不能**被卷进 BAL_3A——所以 BAL 的通配符写成单字符
# `BAL?`（只匹配 BAL0..BAL8）而不是 `BAL*`（会把 BAL_CLK 一起吞掉）。
# 另一条容易翻车的是路径：KiCad 的网表网络名带**图纸名**路径（`/开关电容主动均衡/X1`），
# 不是文件名（`/03_balancer/X1`）——第一版写成文件名，pattern 一条都匹配不上，而原理图上
# 完全看不出来（要等 PCB 布线时才发现 3A 线还是默认线宽）。这里拿网表里真实网络名做匹配。
def netclass_patterns_match(pat: str, name: str) -> bool:
    """KiCad 网络类通配符：`*` 任意串、`?` 单个字符，其余按字面。"""
    rx = "".join(".*" if c == "*" else "." if c == "?" else re.escape(c) for c in pat)
    return re.fullmatch(rx, name) is not None


def netclass_check(sch_path, root_sch):
    """核对本页网络落在哪个网络类（依据 .kicad_pro 的 netclass_patterns）。"""
    pro = os.path.join(os.path.dirname(os.path.abspath(sch_path)), "mp2645a-bms.kicad_pro")
    if not shutil.which("kicad-cli") or not os.path.exists(root_sch) or not os.path.exists(pro):
        return None
    try:
        with open(pro, encoding="utf-8") as f:
            patterns = json.load(f)["net_settings"]["netclass_patterns"]
    except (KeyError, ValueError) as e:
        return [f"[9m] 读不出 {os.path.basename(pro)} 的网络类 pattern：{e!r}"], "读取失败"
    with tempfile.TemporaryDirectory() as td:
        xml = os.path.join(td, "net.xml")
        r = subprocess.run(["kicad-cli", "sch", "export", "netlist",
                            "--format", "kicadxml", "-o", xml, root_sch],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(xml):
            return [f"[9m] 网表导出失败：{r.stderr.strip()[:200]}"], "导出失败"
        root = ET.parse(xml).getroot()

    body = open(sch_path, encoding="utf-8").read()
    refs_here = [m.group(1) for m in re.finditer(r'"Reference" "([^"]+)"', body)]
    nets = {}
    for net in root.iter("net"):
        nm = net.get("name")
        if nm.startswith("unconnected-"):
            continue
        for nd in net.findall("node"):
            if nd.get("ref") in refs_here:
                nets[netbase(nm)] = nm            # 本页网络名 → 网表里的完整网络名
                break

    fails = []
    # pattern 自身要先对：BAL_3A 必须覆盖 X?/VB? 的**图纸名路径**，且 BAL 只写单字符通配符。
    bal_pats = [p["pattern"] for p in patterns if p.get("netclass") == "BAL_3A"]
    cell_pats = [p["pattern"] for p in patterns if p.get("netclass") == "CELL_SENSE"]
    if "BAL*" in bal_pats:
        fails.append("[9m] BAL_3A 里出现 `BAL*`——会把 BAL_CLK 也卷进 3A 网络类（§3.3）")

    def classes_of(name):
        return {p["netclass"] for p in patterns if netclass_patterns_match(p["pattern"], name)}

    # Xk/VBk（3A 均衡电流）与 BALk（板端 3A）必须在 BAL_3A；BAL_CLK 必须不在。
    must_bal = [f"X{k}" for k in range(1, 9)] + [f"VB{k}" for k in range(0, 9)] + \
               [f"BAL{k}" for k in range(0, 9)]
    for nm in must_bal:
        full = nets.get(nm)
        if full is None:
            fails.append(f"[9m] 本页网络 {nm} 不在网表里，无法核对网络类")
            continue
        cls = classes_of(full)
        if "BAL_3A" not in cls:
            fails.append(f"[9m] 网络 {nm}（网表名 {full!r}）没落进 BAL_3A，实际 {sorted(cls) or '默认类'}")
    for nm in ("BAL_CLK",):
        full = nets.get(nm)
        if full is None:
            fails.append(f"[9m] 本页网络 {nm} 不在网表里，无法核对网络类")
            continue
        cls = classes_of(full)
        if "BAL_3A" in cls:
            fails.append(f"[9m] 网络 {nm}（网表名 {full!r}）被卷进 BAL_3A——时钟是弱信号线，"
                         f"不该按 3A 线宽/间距走（§3.3）")
    # 本页不许有网络落进 CELL_SENSE（采样网络类，03 页与采样线无关）。
    for nm, full in sorted(nets.items()):
        if "CELL_SENSE" in classes_of(full):
            fails.append(f"[9m] 本页网络 {nm}（网表名 {full!r}）落进 CELL_SENSE")
    note = (f"网络类：BAL_3A pattern {bal_pats} 匹配 X1–X8/VB0–VB8/BAL0–BAL8 全部命中，"
            f"BAL_CLK 未被卷入；本页无网络落进 CELL_SENSE")
    return fails, note


# ---------------------------------------------------------------------------
# 检查 9n：本页 ERC 必须 0 条（跨页单脚只允许 BAL0..BAL8，且它们在本页就有两个脚）
# ---------------------------------------------------------------------------
def erc_check(root_sch):
    """跑 kicad-cli ERC，核本页（`/开关电容主动均衡/`）0 条违规。"""
    if not shutil.which("kicad-cli") or not os.path.exists(root_sch):
        return None
    with tempfile.TemporaryDirectory() as td:
        js = os.path.join(td, "erc.json")
        r = subprocess.run(["kicad-cli", "sch", "erc", "--severity-all",
                            "--format", "json", "-o", js, root_sch],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(js):
            return [f"[9n] ERC 跑不起来：{r.stderr.strip()[:200]}"], "ERC 失败"
        data = json.load(open(js, encoding="utf-8"))
    fails, mine, others = [], 0, 0
    for sh in data.get("sheets", []):
        path = sh.get("path") or ""
        n = len(sh.get("violations") or [])
        if path == "/开关电容主动均衡/":
            mine += n
            for v in sh.get("violations") or []:
                fails.append(f"[9n] 本页 ERC {v.get('type')}（{v.get('severity')}）："
                             f"{v.get('description')} @ {[i.get('description') for i in v.get('items') or []]}")
        else:
            others += n
    note = (f"ERC：本页 {mine} 条、其它页 {others} 条（别的子页不算本页失败；本页跨页单脚标签只允许 BAL0..BAL8，它们在本页已各有两个脚）")
    return fails, note


# ---------------------------------------------------------------------------
# 检查 9o：8 节同构 + 跨节只允许相邻两节（附录 B 第 3、7 条）
# ---------------------------------------------------------------------------
# 附录 B 第 3 条要的是「把 8 节的网表并排比对」——这里不看上面那张（照着规格书敲的）
# 端子表，只从**网表本身**做结构比对：把第 k 节 11 件器件的每个脚连同它连的网络名做
# 「角色归一化」（网络名里的 k 换成 #、k−1 换成 @），8 节归一化后的结构必须逐字段相同。
# 两处**合理的不对称**（§7.2）要单独点名、其余不同一律报错：
#   ① 第 1 节的 C321.1 接 CLK_R（上游是 R300），不是 DRV0；
#   ② DRV8 只有 5 个脚（没有 C329），DRV1–DRV7 都是 6 个。
# 第 7 条（跨节连接只有飞电容和 1nF 耦合）换一个独立说法：任何网络涉及的「节号」跨度
# 不得超过 1（VBk 本来就连着第 k、k+1 两节；跨度 ≥2 就意味着有导线横穿两节以上）。
def structure_check(sch_path, root_sch):
    if not shutil.which("kicad-cli") or not os.path.exists(root_sch):
        return None
    with tempfile.TemporaryDirectory() as td:
        xml = os.path.join(td, "net.xml")
        r = subprocess.run(["kicad-cli", "sch", "export", "netlist",
                            "--format", "kicadxml", "-o", xml, root_sch],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(xml):
            return [f"[9o] 网表导出失败：{r.stderr.strip()[:200]}"], "导出失败"
        root = ET.parse(xml).getroot()

    body = open(sch_path, encoding="utf-8").read()
    refs_here = set(re.findall(r'"Reference" "([^"]+)"', body))
    sec_ref_k = {}                       # 位号 → 节号 k
    for k in range(1, 9):
        for pre in ("R30", "C30", "C31", "C32", "U30", "R31", "R32", "D30", "D31", "Q30", "Q31"):
            sec_ref_k[f"{pre}{k}"] = k
    fails = []
    # 全局标签只允许 BAL0..BAL8 与 BAL_CLK（附录 B 第 6 条）
    glbl = set(re.findall(r'\(global_label "([^"]+)"', body))
    if glbl != {f"BAL{k}" for k in range(9)} | {"BAL_CLK"}:
        fails.append(f"[9o] 本页全局标签是 {sorted(glbl)}，只允许 BAL0–BAL8 与 BAL_CLK（附录 B 第 6 条）")

    nodes = {}                           # (ref, pin) → 本页网络名
    net_members = {}                     # 本页网络名 → [(ref, pin)]
    for net in root.iter("net"):
        nm = netbase(net.get("name"))
        if nm is None:
            continue
        for nd in net.findall("node"):
            if nd.get("ref") in refs_here:
                nodes[(nd.get("ref"), nd.get("pin"))] = nm
                net_members.setdefault(nm, []).append((nd.get("ref"), nd.get("pin")))

    def role(nm, k):
        if nm == f"VB{k}":
            return "VB#"
        if nm == f"VB{k - 1}":
            return "VB@"
        for pre in ("IN", "DRV", "GN", "GP", "X"):
            if nm == f"{pre}{k}":
                return f"{pre}#"
            if nm == f"{pre}{k - 1}":
                return f"{pre}@"
        return nm                        # CLK_R / BAL_CLK 这类原样

    sig = {}
    for k in range(1, 9):
        sig[k] = {}
        for ref, kk in sec_ref_k.items():
            if kk != k:
                continue
            tmpl = ref[:-1]              # 去掉节号后的模板名（R301 → R30、Q311 → Q31）
            pins = sorted(p for (r_, p) in nodes if r_ == ref)
            sig[k][tmpl] = {p: role(nodes[(ref, p)], k) for p in pins}
    base = sig[2]
    for k in (3, 4, 5, 6, 7, 8):
        if sig[k] != base:
            diff = [f"{pre}:{sig[k].get(pre)}≠{base.get(pre)}"
                    for pre in sorted(set(sig[k]) | set(base)) if sig[k].get(pre) != base.get(pre)]
            fails.append(f"[9o] 第 {k} 节与第 2 节的归一化结构不同（8 节必须同构，§7.2）：{diff}")
    # ① 第 1 节只允许 C32 一处不同：接 CLK_R 而不是 DRV0
    d1 = [pre for pre in base if sig[1].get(pre) != base.get(pre)]
    if d1 != ["C32"]:
        fails.append(f"[9o] 第 1 节与其它节的差异是 {d1}，按 §7.2 只允许 C32（C321.1 接 CLK_R）")
    elif sig[1]["C32"].get("1") != "CLK_R":
        fails.append(f"[9o] 第 1 节 C321.1 是 {sig[1]['C32'].get('1')!r}，应接 CLK_R（§7.2 不对称①）")
    # ② DRVk 的脚数：k=1..7 都是 6，DRV8 是 5（没有 C329）
    cnt = {k: len(net_members.get(f"DRV{k}", [])) for k in range(1, 9)}
    want_cnt = {**{k: 6 for k in range(1, 8)}, 8: 5}
    if cnt != want_cnt:
        fails.append(f"[9o] 各节 DRV 网络的脚数 {cnt}，应 {want_cnt}（§7.2 不对称②）")
    # 跨节跨度 ≤ 1
    for nm, members in sorted(net_members.items()):
        secs = sorted({sec_ref_k[r_] for r_, _ in members if r_ in sec_ref_k})
        if secs and max(secs) - min(secs) > 1:
            fails.append(f"[9o] 网络 {nm} 跨了第 {secs} 节（跨度 >1）：跨节只允许飞电容 Xk→X(k+1) "
                         f"与 1nF 耦合 DRV(k−1)→INk（附录 B 第 7 条）")
    note = (f"8 节同构：第 2–8 节归一化结构完全一致、第 1 节仅 C32 不同（CLK_R）；"
            f"DRV1–7 各 6 脚 / DRV8 5 脚；全局标签 {sorted(glbl)}；无网络跨节跨度 >1")
    return fails, note


# ---------------------------------------------------------------------------
# 检查
# ---------------------------------------------------------------------------
def main():
    wires, junctions, pin_pos, body_boxes, instances, labels, prop_texts, pin_name_boxes = load()
    fails = []

    all_pins = pin_pos.values()

    # 1. 导线经过非端点引脚
    for wi, (a, b) in enumerate(wires):
        for (ref, num), q in pin_pos.items():
            if on_segment(q, a, b, inclusive=False):
                fails.append(f"[1] 导线#{wi} {a}→{b} 穿过 {ref}.{num} 引脚端点 {q}（非端点）")

    # 2. 导线穿过符号本体
    for wi, (a, b) in enumerate(wires):
        for ref, box in body_boxes.items():
            if box is None:
                continue
            if seg_bbox_intersect(a, b, box):
                # 允许：线段端点恰好是该符号的引脚（从引脚引出，不穿本体）
                a_is_pin = any(abs(a[0] - q[0]) < EPS and abs(a[1] - q[1]) < EPS
                               for (r, _), q in pin_pos.items() if r == ref)
                b_is_pin = any(abs(b[0] - q[0]) < EPS and abs(b[1] - q[1]) < EPS
                               for (r, _), q in pin_pos.items() if r == ref)
                if not (a_is_pin or b_is_pin):
                    fails.append(f"[2] 导线#{wi} {a}→{b} 穿过 {ref} 本体 {box}")

    # 3. T 型连接必须有结点（两种情形）
    #    a) 导线端点落在另一段导线内部（wire-wire T）
    for wi, (a, b) in enumerate(wires):
        for ep in (a, b):
            for wj, (c, d) in enumerate(wires):
                if wi == wj:
                    continue
                if on_segment(ep, c, d, inclusive=False):
                    key = (round(ep[0], 4), round(ep[1], 4))
                    if key not in junctions:
                        fails.append(f"[3] 导线#{wi} 端点 {ep} 落在导线#{wj} {c}→{d} 内部，但无 junction")
    #    b) 引脚处两段共线导线端点相接（pin + 两段导线三方 T，复核 P2-6）
    for (ref, num), q in pin_pos.items():
        n_ep = 0
        for (a, b) in wires:
            if (abs(a[0] - q[0]) < EPS and abs(a[1] - q[1]) < EPS) or \
               (abs(b[0] - q[0]) < EPS and abs(b[1] - q[1]) < EPS):
                n_ep += 1
        if n_ep >= 2:
            key = (round(q[0], 4), round(q[1], 4))
            if key not in junctions:
                fails.append(f"[3] 引脚 {ref}.{num} {q} 有 {n_ep} 段导线端点相接（T 型连接），但无 junction")

    # 4. 标签/全局标签/说明文字 与导线重叠（跳过文字锚点所挂接的那条导线）
    for L in labels:
        x0, y0, x1, y1, ax, ay, txt, kind = L[:8]
        for wi, (a, b) in enumerate(wires):
            if on_segment((ax, ay), a, b, inclusive=True):
                continue  # 文字自己的挂接导线，允许压在导线上
            if seg_bbox_intersect(a, b, (x0, y0, x1, y1)):
                fails.append(f"[4] {kind}「{txt}」文字 {x0:.2f},{y0:.2f}–{x1:.2f},{y1:.2f} 与导线#{wi} {a}→{b} 重叠")

    # 5. 引脚名 vs 引脚名（同一符号内文字盒两两相交，抓「GNDOSC2」这类粘连）。
    #    第 3 轮起嵌入符号与库逐字节相同（引脚名一律保留），不再有「应隐藏引脚名」的前提。
    for ref, boxes in pin_name_boxes.items():
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if bbox_overlap(boxes[i][:4], boxes[j][:4]):
                    fails.append(f"[5] {ref} 引脚 {boxes[i][4]}/{boxes[j][4]} 名称粘连 {boxes[i][:4]} vs {boxes[j][:4]}")

    # 6. 可见字段（Reference/Value）压符号本体
    for ref, boxes in prop_texts.items():
        box = body_boxes.get(ref)
        if box is None:
            continue
        for b in boxes:
            if bbox_overlap(b[:4], box, eps=0.0):
                fails.append(f"[6] {ref} 字段「{b[4]}」{b[:4]} 压在本体 {box} 上")

    # 7. 符号本体 ↔ 符号本体（含字段文字）两两不相交 —— 第 3 轮新增。
    #    第 2 轮的检查 1–6 里，2/6 只拿「某器件自己的」字段去比「它自己的」本体，
    #    跨器件的「A 的字段压 B 的本体」无人看管，所以 R55 的位号被 JP1 本体压住没被抓到。
    #    这里把每个实例拆成若干「图元盒」（本体包围盒 / 可见字段文字 / 引脚名文字），
    #    不同实例之间任意两盒都不许相交。
    sym_boxes = {}  # ref → [(x0, y0, x1, y1, 说明)]
    for ref, box in body_boxes.items():
        if box:
            sym_boxes.setdefault(ref, []).append((*box, "本体"))
    for ref, boxes in prop_texts.items():
        for b in boxes:
            sym_boxes.setdefault(ref, []).append((b[0], b[1], b[2], b[3], f"字段{b[4]}"))
    for ref, boxes in pin_name_boxes.items():
        for b in boxes:
            sym_boxes.setdefault(ref, []).append((b[0], b[1], b[2], b[3], f"引脚名{b[4]}"))
    refs = sorted(sym_boxes)
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            for a in sym_boxes[refs[i]]:
                for b in sym_boxes[refs[j]]:
                    if bbox_overlap(a[:4], b[:4]):
                        fails.append(
                            f"[7] {refs[i]} 的{a[4]} {a[:4]} 与 {refs[j]} 的{b[4]} {b[:4]} 相交")

    # 8. 渲染复核（kicad-cli 出 PDF → pymupdf 读文字盒）
    note8 = "SKIP（没装 kicad-cli 或 pymupdf）"
    r8 = rendered_field_check(prop_texts, body_boxes, SCH)
    if r8 is not None:
        f8, note8 = r8
        fails += f8

    # 10–13. 墨迹版面归属（标签压引脚 / 标签叠标签 / 字段挂错器件 / 文字互压）
    f_ink, note_ink = ink_layout_check(labels, prop_texts, body_boxes)
    fails += f_ink

    # 9. 网表逐脚核对
    note9 = "SKIP（没装 kicad-cli 或找不到根图）"
    r9 = netlist_pin_check(SCH, ROOT_SCH)
    if r9 is not None:
        f9, note9 = r9
        fails += f9

    # 9m. 网络类核对（规格书 §3.3）
    note9m = "SKIP（没装 kicad-cli、找不到根图或 .kicad_pro）"
    rm = netclass_check(SCH, ROOT_SCH)
    if rm is not None:
        fm, note9m = rm
        fails += fm

    # 9n. 本页 ERC
    note9n = "SKIP（没装 kicad-cli 或找不到根图）"
    rn = erc_check(ROOT_SCH)
    if rn is not None:
        fn, note9n = rn
        fails += fn

    # 9o. 8 节同构 + 跨节只相邻（附录 B 第 3、6、7 条）
    note9o = "SKIP（没装 kicad-cli 或找不到根图）"
    ro = structure_check(SCH, ROOT_SCH)
    if ro is not None:
        fo, note9o = ro
        fails += fo

    print(f"图元解析：导线 {len(wires)} 段，junction {len(junctions)} 个，实例 {len(instances)} 个，引脚 {len(pin_pos)} 个，文字 {len(labels)} 处，引脚名 {sum(len(v) for v in pin_name_boxes.values())} 个，图元盒 {sum(len(v) for v in sym_boxes.values())} 个")
    print(f"渲染复核：{note8}")
    print(f"墨迹版面：{note_ink}")
    print(f"网表核对：{note9}")
    print(f"网络类核对：{note9m}")
    print(f"ERC 核对：{note9n}")
    print(f"结构核对：{note9o}")
    if fails:
        print(f"FAIL：{len(fails)} 条")
        for f in fails:
            print("  " + f)
        return 1
    print("PASS：检查 1–9 及墨迹版面 10/11/12/13 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
