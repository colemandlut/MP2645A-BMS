#!/usr/bin/env python3
"""生成 KiCad 10 工程骨架（幂等：每次运行都完整重写骨架文件）。

    python3 tools/gen_kicad_skeleton.py            # 写 .kicad_pro / 原理图骨架
    kicad-python tools/gen_kicad_skeleton.py --pcb # 另外用 pcbnew 生成四层板骨架

内容：
  * 层次原理图：根图 + 5 张子图（每张子图只放接口契约说明，电路待数据手册核对后再画）
  * 网络类 + 按网络名自动归类的规则（线宽/间距/过孔按 v0.2 详细设计）
  * 四层叠层（pcb-workflow 规则 0a）：F.Cu 信号 / In1.Cu GND 平面 / In2.Cu 电源平面 / B.Cu 信号
  * 占位板框 160x110mm（待机械结构确认）

⚠ 只在骨架阶段使用。原理图开画后不要再运行，否则会覆盖子图内容。
"""
from __future__ import annotations

import json
import os
import sys
import uuid

PROJ = "mp2645a-bms"
HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hardware")

# 命名空间固定，保证重复运行 uuid 不变
NS = uuid.UUID("6f1b0c52-8e0a-4c1e-9a52-2645a0b3e5d1")


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


SHEETS = [
    ("01_power_path", "功率回路",
     "B+ 熔断器 / CHG、DSG 各 8 并联 NMOS / 栅极网络与 PNP 快速关断 / 分流器 / TVS / 预充 / P+ P- 端子",
     ["BAT+", "BAT-", "PACK+", "PACK-", "FET_MID", "CHG_G", "DSG_G", "SRP", "SRN", "NTC_FET", "NTC_SHUNT", "PRECHG_EN"]),
    ("02_afe", "MP2797 采集与保护",
     "电芯采样 RC / 电流采样滤波 / 4 路 NTC / 高边驱动输出 / 通讯与中断 / 被动均衡",
     ["CELL0..CELL8", "SRP", "SRN", "CHG_G", "DSG_G", "FET_MID", "PACK+", "NTC_CELL1", "NTC_CELL2",
      "NTC_FET", "NTC_SHUNT", "I2C_SCL", "I2C_SDA", "AFE_ALERT", "AFE_WAKE", "+3V3", "GND"]),
    ("03_balancer", "MP2643 x7 主动均衡",
     "U_BAL1..7：第 k 颗 PGND=BAL(k-1)、CL=BALk、CU=BAL(k+1) / 每颗 2 只光耦(EN、MODE) / 电感下方全层禁铜 / 7 个本地地铜岛",
     ["BAL0..BAL8", "BAL_EN1..BAL_EN7", "BAL_MODE1..BAL_MODE7", "NTC_BAL", "+3V3", "GND"]),
    ("04_power_supply", "辅助电源",
     "BAT+ → 输入保护 → LMR16006X buck → +3V3（取消 5V 轨与 LDO）",
     ["BAT+", "BAT-", "+3V3", "GND"]),
    ("05_mcu_comm", "MCU 与通讯",
     "CH32V203C8T6 / SWD / CAN(SN65HVD230 3.3V + ESD + 可选 120Ω) / RS485 可选 / 状态 LED / 按键",
     ["I2C_SCL", "I2C_SDA", "AFE_ALERT", "AFE_WAKE", "BAL_EN1..7", "BAL_MODE1..7", "NTC_BAL", "PRECHG_EN",
      "CAN_H", "CAN_L", "RS485_A", "RS485_B", "+3V3", "GND"]),
]

# (名称, 线宽, 间距, 过孔外径, 过孔孔径, 差分线宽, 差分间距, 匹配网络名的通配符)
# 过孔全部满足嘉立创四层板下限：孔 ≥0.3mm、盘 ≥0.45mm（pcb-workflow 规则 2b）
NETCLASSES = [
    ("Default",    0.20, 0.20, 0.60, 0.30, 0.20, 0.20, []),
    ("HV_POWER",   3.00, 0.50, 1.00, 0.50, 3.00, 0.50, ["BAT+", "BAT-", "PACK+", "PACK-", "FET_MID"]),
    ("BAL_3A",     1.20, 0.30, 0.80, 0.40, 1.20, 0.30, ["BAL?", "/03_balancer/SW*", "/03_balancer/LX*"]),
    ("CELL_SENSE", 0.25, 0.30, 0.60, 0.30, 0.25, 0.30, ["CELL*"]),
    ("GATE",       0.40, 0.30, 0.60, 0.30, 0.40, 0.30, ["CHG_G", "DSG_G"]),
    ("KELVIN",     0.20, 0.20, 0.60, 0.30, 0.20, 0.20, ["SRP", "SRN"]),
    # CAN 120Ω 差分：线宽/线距必须按嘉立创实际叠层用阻抗计算器重算（规则 0c），此处为占位
    ("CAN_DIFF",   0.20, 0.20, 0.60, 0.30, 0.20, 0.20, ["CAN_H", "CAN_L", "RS485_A", "RS485_B"]),
    ("LV_POWER",   0.50, 0.20, 0.60, 0.30, 0.50, 0.20, ["+3V3"]),
    ("GND",        0.50, 0.20, 0.60, 0.30, 0.50, 0.20, ["GND"]),
]


def netclass_json(name, tw, cl, vd, vh, dw, dg, prio):
    return {
        "bus_width": 12, "clearance": cl, "diff_pair_gap": dg, "diff_pair_via_gap": dg,
        "diff_pair_width": dw, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
        "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": prio,
        "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": tw, "tuning_profile": "",
        "via_diameter": vd, "via_drill": vh, "wire_width": 6,
    }


def write_project():
    classes, patterns = [], []
    for i, (n, tw, cl, vd, vh, dw, dg, pats) in enumerate(NETCLASSES):
        prio = 2147483647 if n == "Default" else i
        classes.append(netclass_json(n, tw, cl, vd, vh, dw, dg, prio))
        patterns += [{"netclass": n, "pattern": p} for p in pats]
    pro = {
        "meta": {"filename": f"{PROJ}.kicad_pro", "version": 3},
        "net_settings": {"classes": classes, "meta": {"version": 5}, "net_colors": None,
                         "netclass_assignments": None, "netclass_patterns": patterns},
        "sheets": [[uid("root"), "Root"]] + [[uid(f), f] for f, *_ in SHEETS],
        "text_variables": {"PROJECT": "8S LFP 200A BMS", "REV": "v0.3-skeleton"},
    }
    with open(os.path.join(HW, f"{PROJ}.kicad_pro"), "w") as fp:
        json.dump(pro, fp, indent=2, ensure_ascii=False)


def s(txt: str) -> str:
    return txt.replace("\\", "\\\\").replace('"', '\\"')


def text_item(x, y, txt, size=2.0):
    return (f'\t(text "{s(txt)}"\n\t\t(exclude_from_sim no)\n\t\t(at {x} {y} 0)\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t)\n'
            f'\t\t\t(justify left top)\n\t\t)\n\t\t(uuid "{uid("t" + txt)}")\n\t)\n')


def sch_header(name, title, page_uuid):
    return (f'(kicad_sch\n\t(version 20250610)\n\t(generator "gen_kicad_skeleton")\n'
            f'\t(generator_version "10.0")\n\t(uuid "{page_uuid}")\n\t(paper "A3")\n'
            f'\t(title_block\n\t\t(title "{s(title)}")\n\t\t(date "2026-09-26")\n'
            f'\t\t(rev "v0.3-skeleton")\n\t\t(company "MP2645A-BMS")\n'
            f'\t\t(comment 1 "8S LiFePO4 200A BMS · MPS MP2797 + MP2643x7")\n\t)\n'
            f'\t(lib_symbols)\n')


def write_root():
    out = sch_header("root", "8S LFP 200A BMS — 总图", uid("root"))
    out += text_item(20, 20, "层次结构（v0.3 骨架）：主动均衡 MP2643 x7；电路按 datasheets/ 手册逐 IC 核对后再画", 3.0)
    for i, (f, title, desc, _) in enumerate(SHEETS):
        x, y = 20 + (i % 3) * 130, 50 + (i // 3) * 90
        out += (f'\t(sheet\n\t\t(at {x} {y})\n\t\t(size 110 60)\n\t\t(exclude_from_sim no)\n'
                f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
                f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n'
                f'\t\t(fill\n\t\t\t(color 0 0 0 0.0000)\n\t\t)\n\t\t(uuid "{uid("sheet" + f)}")\n'
                f'\t\t(property "Sheetname" "{s(title)}"\n\t\t\t(at {x} {y - 0.8} 0)\n'
                f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 2 2)\n\t\t\t\t)\n'
                f'\t\t\t\t(justify left bottom)\n\t\t\t)\n\t\t)\n'
                f'\t\t(property "Sheetfile" "{f}.kicad_sch"\n\t\t\t(at {x} {y + 61} 0)\n'
                f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.5 1.5)\n\t\t\t\t)\n'
                f'\t\t\t\t(justify left top)\n\t\t\t)\n\t\t)\n'
                f'\t\t(instances\n\t\t\t(project "{PROJ}"\n\t\t\t\t(path "/{uid("root")}"\n'
                f'\t\t\t\t\t(page "{i + 2}")\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
    out += '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n'
    with open(os.path.join(HW, f"{PROJ}.kicad_sch"), "w") as fp:
        fp.write(out)


def write_subsheets():
    for f, title, desc, nets in SHEETS:
        out = sch_header(f, title, uid("page" + f))
        out += text_item(20, 20, f"{title}", 4.0)
        out += text_item(20, 35, f"内容：{desc}", 2.0)
        out += text_item(20, 45, "接口网络（跨页用全局标签，名称以本清单为准）：", 2.0)
        for k, n in enumerate(nets):
            out += text_item(25 + (k // 12) * 70, 52 + (k % 12) * 5, f"· {n}", 1.8)
        out += text_item(20, 130, "状态：待画。详细设计见 docs/03-详细设计.md；按 pcb-workflow 规则 00/00c/00d 执行。", 2.0)
        out += '\t(embedded_fonts no)\n)\n'
        with open(os.path.join(HW, f"{f}.kicad_sch"), "w") as fp:
            fp.write(out)


def write_pcb():
    import pcbnew  # 仅 kicad-python 下可用

    b = pcbnew.BOARD()
    b.SetCopperLayerCount(4)
    b.SetLayerName(pcbnew.In1_Cu, "In1.GND")
    b.SetLayerName(pcbnew.In2_Cu, "In2.PWR")
    b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    ds = b.GetDesignSettings()
    ds.m_MinThroughDrill = pcbnew.FromMM(0.3)
    ds.m_ViasMinSize = pcbnew.FromMM(0.45)
    ds.m_CopperEdgeClearance = pcbnew.FromMM(0.3)
    ds.m_TrackMinWidth = pcbnew.FromMM(0.127)
    ds.m_MinClearance = pcbnew.FromMM(0.127)
    w, h = 160.0, 110.0          # 占位板框，待机械结构确认（规则 0 ①）
    pts = [(0, 0), (w, 0), (w, h), (0, h)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(b)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1 + 20), pcbnew.FromMM(y1 + 20)))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2 + 20), pcbnew.FromMM(y2 + 20)))
        b.Add(seg)
    pcbnew.SaveBoard(os.path.join(HW, f"{PROJ}.kicad_pcb"), b)


def main():
    os.makedirs(HW, exist_ok=True)
    if "--pcb" in sys.argv:
        write_pcb()
        write_project()          # SaveBoard 会用默认值重写 .kicad_pro，这里恢复网络类
        print("pcb 骨架已生成")
        return
    write_project()
    write_root()
    write_subsheets()
    print(f"工程骨架已生成: {os.path.abspath(HW)}")


if __name__ == "__main__":
    main()
