#!/usr/bin/env python3
"""按 docs/02-BOM.csv 计算每块板的元器件成本（嘉立创实时价 + MPS 客供件 + 扩展库上料费）。

    python3 tools/cost.py                 # 默认批量 1/5/10/50/100 块，写 docs/05-成本估算.md
    python3 tools/cost.py 20 200          # 指定批量

口径：
- 来源 JLC：嘉立创 SMT 料号接口的阶梯价（美元，按「单板用量 × 板数」取档），× USD_CNY 换算；
- 来源 MPS客供：MPS 官网阶梯价（人民币，用户 2026-09-26 截图）+ 每单运费 5 美元；
- 扩展库上料费：每种扩展库料一次性收费（不随片数变，pcb-workflow 规则 0b），DNP 不计；
- 非嘉立创件（熔断器、铜排、散热器）只给粗估，单列；
- **不含** PCB 制板费、SMT 工程/钢网/焊点费、运费、税——这些要在嘉立创下单页报价。
"""
from __future__ import annotations

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jlc_api  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOM = os.path.join(ROOT, "docs", "02-BOM.csv")
OUT = os.path.join(ROOT, "docs", "05-成本估算.md")

USD_CNY = 7.10                   # 假设汇率
EXT_FEE_CNY = 8.0                # 扩展库每种上料费（标准型；经济型为 20，见规则 0b）
MPS_SHIP_CNY = 5 * USD_CNY
# MP2643GR-Z，MPS 官网（用户截图 2026-09-26）
MPS_TIERS = {"MPS MP2643GR-Z": [(1, 19.28), (10, 17.25), (100, 14.46), (250, 13.78), (500, 12.09), (1000, 9.85)]}
# 非嘉立创件粗估（元/套），仅作量级参考
ROUGH = {"F1": (30, 60), "BUS": (30, 60), "HS": (30, 80)}


NOTES = """
## 已采用的降本（2026-09-26 用户同意）

- **主动均衡改为分立开关电容（方案 B）**：替代 MP2643×7 及其电感、22µF、光耦、7A 保险丝、2×9 端子；均衡部分约 ¥186/块 → 约 ¥25/块；代价：电流随压差变化（100mV≈0.2A），平台区几乎不搬。

| 项 | 原方案 | 现方案 | 风险 / 代价 |
|---|---|---|---|
| 主 MOSFET | Infineon IPT012N08N5 ×16（C531199） | **Tokmas IPT012N08N5 ×12（C19626224）**，每方向 6 颗 | Rds(on) 典型 0.9 / 最大 1.2mΩ（同原厂），但 **Tj,max 150°C**（原厂 175°C），Qg 240nC；最坏值下 200A 通路 27.2W、最坏单管 Tj ≈ 105°C（45°C 环境），裕量 45°C；嘉立创库存 746（够 62 块） |
| MCU | STM32G0B1CBT6（C2847904，嘉立创库存 0） | **WCH CH32V203C8T6（C3001172）** | CAN 2.0B（非 FD）够用；固件底层驱动改写，逻辑层不变 |
| 4.7µF/100V 1210 | Murata GRM32ER72A475KE14L（C162515，库存 0） | **风华 FS32X475K101EGG（C381466）** | 同规格 X7R；封装同为 1210 |
| 扩展库种类 | 120k/150k/2M（0402 扩展库）、30Ω、62Ω×2、240k、100nF/50V 0402 | 改为 **0603 基础库** 120k/150k/2M、33Ω 0805、单 120Ω 终端、470k/20k 反馈、100nF/50V 0603 | 与规则 00②「封装下探」冲突：为减少扩展库上料费而选 0603；MP9486A 输出 4.9V |

## 库存风险

- Tokmas MOSFET 嘉立创库存 746：每块 12 颗，最多 62 块；量产前需备货或确认补货。
- MP2013AGQ-33-Z（C6096988）库存约 49、SMBJ33A（C78419）约 47：够小批量，不够 100 块。
- v0.3 起主动均衡改为分立开关电容（全部嘉立创料），不再有 MPS 客供件。
"""


def tier(tiers, qty):
    p = tiers[0][1]
    for start, price in sorted(tiers):
        if qty >= start:
            p = price
    return p


def load_bom():
    with open(BOM, encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def fetch_prices(rows):
    info = {}
    for r in rows:
        c = r["立创编号"].strip()
        if r["来源"] == "JLC" and c.startswith("C") and c not in info:
            p = jlc_api.part(c)
            info[c] = jlc_api.summary(p) if p else None
            time.sleep(0.2)
    return info


def compute(rows, info, n):
    lines, total, ext_types, missing = [], 0.0, set(), []
    mps_total = 0.0
    for r in rows:
        src, q = r["来源"], int(r["数量"])
        if src == "DNP":
            continue
        if src == "JLC":
            s = info.get(r["立创编号"])
            if not s:
                missing.append(r["立创编号"])
                continue
            unit = jlc_api.unit_price(s, q * n) * USD_CNY
            if s["lib"] == "扩展库":
                ext_types.add(r["立创编号"])
            cost = unit * q
            total += cost
            lines.append((r["模块"], r["位号"], q, r["制造商型号"], r["立创编号"], s["lib"], s["stock"], unit, cost))
        elif src == "MPS客供":
            unit = tier(MPS_TIERS[r["制造商型号"]], q * n)
            cost = unit * q
            mps_total += cost
            lines.append((r["模块"], r["位号"], q, r["制造商型号"], "MPS", "客供", "-", unit, cost))
    ext_fee = len(ext_types) * EXT_FEE_CNY
    ship = MPS_SHIP_CNY if mps_total else 0.0
    return {
        "n": n, "lines": lines, "jlc_parts": total, "mps_parts": mps_total,
        "mps_ship_per_board": ship / n, "ext_types": len(ext_types),
        "ext_fee_per_board": ext_fee / n, "missing": missing,
        "per_board": total + mps_total + ship / n + ext_fee / n,
    }


def main(argv):
    ns = [int(x) for x in argv] or [1, 5, 10, 50, 100]
    rows = load_bom()
    info = fetch_prices(rows)
    res = [compute(rows, info, n) for n in ns]
    rough_lo = sum(v[0] for v in ROUGH.values())
    rough_hi = sum(v[1] for v in ROUGH.values())

    out = ["# 成本估算（元器件）\n",
           f"> 生成：`python3 tools/cost.py`，{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}。"
           f"嘉立创价为实时接口的美元阶梯价 × {USD_CNY}（假设汇率）；MP2643 为 MPS 官网人民币价。",
           "> **不含 PCB 制板、SMT 工程/钢网/焊点费、运费、税**，这些以嘉立创下单页报价为准。\n",
           "## 每块板成本（元）\n",
           "| 批量(块) | 嘉立创元器件 | MPS 客供件 | MPS 运费分摊 | 扩展库上料费分摊 | **元器件合计/块** | 客供件占比 |",
           "|---|---|---|---|---|---|---|"]
    for r in res:
        out.append(f"| {r['n']} | {r['jlc_parts']:.2f} | {r['mps_parts']:.2f} | {r['mps_ship_per_board']:.2f} | "
                   f"{r['ext_fee_per_board']:.2f}（{r['ext_types']} 种 × ¥{EXT_FEE_CNY:.0f}） | "
                   f"**{r['per_board']:.2f}** | {r['mps_parts'] / r['per_board'] * 100:.0f}% |")
    out.append(f"\n非嘉立创机械件（300A 熔断器、铜排与 M8 螺柱、散热器）粗估 **¥{rough_lo}–{rough_hi}/套**，未计入上表。\n")

    ref = res[min(range(len(res)), key=lambda i: abs(res[i]['n'] - 10))]
    out.append(f"## 明细（按 {ref['n']} 块批量取价，单位：元）\n")
    out.append("| 模块 | 位号 | 数量 | 型号 | 编号 | 库 | 嘉立创库存 | 单价 | 单板小计 |\n|---|---|---|---|---|---|---|---|---|")
    for ln in sorted(ref["lines"], key=lambda x: -x[8]):
        m, refs, q, mpn, c, lib, stock, unit, cost = ln
        out.append(f"| {m} | {refs} | {q} | {mpn} | {c} | {lib} | {stock} | {unit:.4f} | {cost:.2f} |")
    by_mod = {}
    for ln in ref["lines"]:
        by_mod[ln[0]] = by_mod.get(ln[0], 0) + ln[8]
    out.append("\n## 按模块（元/块，" + str(ref["n"]) + " 块批量）\n")
    out.append("| 模块 | 小计 | 占比 |\n|---|---|---|")
    tot = sum(by_mod.values())
    for m, v in sorted(by_mod.items(), key=lambda x: -x[1]):
        out.append(f"| {m} | {v:.2f} | {v / tot * 100:.0f}% |")
    low_stock = [ln for ln in ref["lines"] if isinstance(ln[6], int) and ln[6] < ln[2] * 100]
    if low_stock:
        out.append("\n## ⚠ 嘉立创库存不足 100 块用量的料\n")
        for ln in low_stock:
            out.append(f"- {ln[1]} {ln[3]}（{ln[4]}）：库存 {ln[6]}，单板用 {ln[2]}")
    if ref["missing"]:
        out.append("\n## ⚠ 嘉立创查不到价格的料号\n\n" + ", ".join(ref["missing"]))
    out.append(NOTES)
    with open(OUT, "w", encoding="utf-8") as fp:
        fp.write("\n".join(out) + "\n")

    for r in res:
        print(f"{r['n']:>4} 块：元器件 ¥{r['per_board']:.2f}/块（嘉立创 {r['jlc_parts']:.2f} + MPS客供 {r['mps_parts']:.2f}"
              f" + 运费 {r['mps_ship_per_board']:.2f} + 上料费 {r['ext_fee_per_board']:.2f}）")
    print(f"机械件粗估 ¥{rough_lo}–{rough_hi}/套；报告 {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
