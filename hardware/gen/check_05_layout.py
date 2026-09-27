#!/usr/bin/env python3
"""自检脚本：对 hardware/05_mcu_comm.kicad_sch 做第 3 轮任务书的几何检查 1–3。

    python3 hardware/gen/check_05_layout.py

直接解析生成的 .kicad_sch（不是 gen 脚本的数据），做三件事：
  1. 导线不许经过非端点的引脚端点；
  2. 导线不许穿过符号本体（rectangle/polyline/arc/circle 包络 + 实例坐标变换）；
  3. T 型连接必须有 junction（导线端点落在另一段导线内部时）。

全部通过 → exit 0；任何一条失败 → 打印 FAIL 并 exit 1。
"""
from __future__ import annotations

import os
import re
import sys

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCH = os.path.join(HW, "05_mcu_comm.kicad_sch")

EPS = 1e-3


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
def pin_world(px, py, rot, ix, iy):
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
    """effects → (水平, 垂直) 对齐，默认 left / center。"""
    hj, vj = "left", "center"
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
    """水平文字（旋转角 0）的近似包围盒；锚点 (x, y)。"""
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


def pin_dir_world(inst_rot, pin_rot):
    """引脚方向（尖端→本体）在世界坐标下的单位向量。"""
    dx = {0: 1, 90: 0, 180: -1, 270: 0}[pin_rot % 360]
    dy = {0: 0, 90: 1, 180: 0, 270: -1}[pin_rot % 360]
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
                    for xy in children(el, "xy"):
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
        instances[ref] = (unq(lib_id[1]), float(at[1]), float(at[2]), float(at[3]), nums)
        for prop in children(sym, "property"):
            pname = unq(prop[1]) if len(prop) > 1 else ""
            if pname not in ("Reference", "Value"):
                continue
            pval = unq(prop[2]) if len(prop) > 2 else ""
            pat = child(prop, "at")
            peff = child(prop, "effects")
            if pat and pval:
                ang = float(pat[3]) if len(pat) > 3 else 0.0
                if int(ang) % 360 == 0:  # 只查水平字段（本轮修改的都是水平文字）
                    h, _ = font_size(peff)
                    hj, vj = justify(peff)
                    prop_texts.setdefault(ref, []).append(
                        (*text_bbox(float(pat[1]), float(pat[2]), pval, h, hj, vj), pname))

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
    for ref, (lib, x, y, rot, nums) in instances.items():
        lp = lib_pins.get(lib, {})
        for num in nums:
            if num in lp:
                ix, iy = lp[num]
                pin_world_pos[(ref, num)] = pin_world(x, y, rot, ix, iy)

    # --- 本体世界包围盒 ---
    body_boxes = {}  # ref -> (xmin, ymin, xmax, ymax)
    for ref, (lib, x, y, rot, nums) in instances.items():
        pts = lib_body.get(lib, [])
        if not pts:
            body_boxes[ref] = None
            continue
        ws = [pin_world(x, y, rot, ix, iy) for (ix, iy) in pts]
        xs = [p[0] for p in ws]
        ys = [p[1] for p in ws]
        body_boxes[ref] = (min(xs), min(ys), max(xs), max(ys))

    # --- 标签/全局标签/说明文字：文字盒 + 锚点 ---
    labels = []  # (x0, y0, x1, y1, ax, ay, txt, kind)
    for kind, key in [("label", "label"), ("global_label", "global_label")]:
        for node in children(root, key):
            at = child(node, "at")
            eff = child(node, "effects")
            txt = unq(node[1]) if len(node) > 1 else ""
            if at and txt:
                h, _ = font_size(eff)
                hj, vj = justify(eff)
                labels.append((*text_bbox(float(at[1]), float(at[2]), txt, h, hj, vj),
                               float(at[1]), float(at[2]), txt, kind))
    for node in children(root, "text"):
        at = child(node, "at")
        eff = child(node, "effects")
        txt = unq(node[1]) if len(node) > 1 else ""
        if at and txt:
            h, _ = font_size(eff)
            hj, vj = justify(eff)
            labels.append((*text_bbox(float(at[1]), float(at[2]), txt, h, hj, vj),
                           float(at[1]), float(at[2]), txt, "text"))

    # --- 引脚名世界文字盒（非空引脚名，近似本体端位置）---
    pin_name_boxes = {}  # ref → [(x0, y0, x1, y1, num)]
    for ref, (lib, x, y, rot, nums) in instances.items():
        meta = lib_pinmeta.get(lib, {})
        for num in nums:
            m = meta.get(num)
            if not m or not m["name"]:
                continue
            tip = pin_world(x, y, rot, m["ix"], m["iy"])
            wx, wy = pin_dir_world(rot, m["rot"])
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
    for (x0, y0, x1, y1, ax, ay, txt, kind) in labels:
        for wi, (a, b) in enumerate(wires):
            if on_segment((ax, ay), a, b, inclusive=True):
                continue  # 文字自己的挂接导线，允许压在导线上
            if seg_bbox_intersect(a, b, (x0, y0, x1, y1)):
                fails.append(f"[4] {kind}「{txt}」文字 {x0:.2f},{y0:.2f}–{x1:.2f},{y1:.2f} 与导线#{wi} {a}→{b} 重叠")

    # 5. 引脚名 vs 引脚名（同一符号内文字盒两两相交，抓「GNDOSC2」这类粘连）；
    #    并对指定小封装符号核验引脚名确已隐藏（置空）。
    for ref, boxes in pin_name_boxes.items():
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if bbox_overlap(boxes[i][:4], boxes[j][:4]):
                    fails.append(f"[5] {ref} 引脚 {boxes[i][4]}/{boxes[j][4]} 名称粘连 {boxes[i][:4]} vs {boxes[j][:4]}")
    HIDE = {"X322512MSB4SI", "0402CG330J500NT", "FC-2012HRK-620D", "0805G"}
    for ref, (lib, *_rest) in instances.items():
        if lib in HIDE and pin_name_boxes.get(ref):
            fails.append(f"[5] {ref}({lib}) 应隐藏引脚名但仍显示：{[b[4] for b in pin_name_boxes[ref]]}")

    # 6. 可见字段（Reference/Value）压符号本体
    for ref, boxes in prop_texts.items():
        box = body_boxes.get(ref)
        if box is None:
            continue
        for b in boxes:
            if bbox_overlap(b[:4], box, eps=0.0):
                fails.append(f"[6] {ref} 字段「{b[4]}」{b[:4]} 压在本体 {box} 上")

    print(f"图元解析：导线 {len(wires)} 段，junction {len(junctions)} 个，实例 {len(instances)} 个，引脚 {len(pin_pos)} 个，文字 {len(labels)} 处，引脚名 {sum(len(v) for v in pin_name_boxes.values())} 个")
    if fails:
        print(f"FAIL：{len(fails)} 条")
        for f in fails:
            print("  " + f)
        return 1
    print("PASS：检查 1/2/3/4/5/6 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
