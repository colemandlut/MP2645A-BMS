#!/usr/bin/env python3
"""嘉立创（JLCPCB 国际站）PCB 裸板实时报价：重放报价页的 calculationGoodsCostsNew 接口。

    python3 tools/pcb_quote.py                       # 默认：本项目占位 160×110mm 的几种叠层/铜厚组合
    python3 tools/pcb_quote.py 4 160 110 2 0.5       # 层数 长 宽 外层oz 内层oz

请求模板 tools/jlc_pcb_quote_template.json 取自报价页（2026-09-26，FR4 TG135、1.6mm、绿油白字、HASL 有铅、
单板出货、无阻抗），只改层数/尺寸/数量/铜厚。结果为美元总价（含工程费，不含运费税费）；
国内嘉立创（jlc.com）价格体系不同，以下单页为准。接口改版时重新抓模板。
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

API = "https://cart.jlcpcb.com/api/overseas-core-platform/shoppingCart/calculationGoodsCostsNew"
TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jlc_pcb_quote_template.json")
QTYS = (5, 10, 50, 100)


def quote(layers: int, length: float, width: float, qty: int, cu_out: float = 1, cu_in: float = 0.5) -> float:
    with open(TPL, encoding="utf-8") as fp:
        req = json.load(fp)
    g = req["pcbGoodsRequest"]
    g.update(stencilLayer=layers, stencilLength=length, stencilWidth=width, stencilLengthInch=length,
             stencilWidthInch=width, stencilCounts=qty, cuprumThickness=cu_out,
             insideCuprumThickness=cu_in if layers > 2 else None)
    r = urllib.request.Request(API, data=json.dumps(req).encode(),
                               headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=40) as resp:
        s = resp.read().decode()
    m = re.search(r'"dummyMoney":\s*([0-9.]+)', s)
    if not m:
        raise RuntimeError(s[:300])
    return float(m.group(1))


def main(argv: list[str]) -> int:
    combos = [tuple(float(x) for x in argv)] if argv else [
        (4, 160, 110, 1, 0.5), (4, 160, 110, 2, 0.5), (4, 160, 110, 2, 1), (2, 160, 110, 2, 0.5), (4, 130, 90, 2, 0.5)]
    print("| 层 | 尺寸 mm | 外/内铜 oz | " + " | ".join(f"{q} 块 USD（每块）" for q in QTYS) + " |")
    print("|---|---|---|" + "---|" * len(QTYS))
    for ly, length, width, co, ci in combos:
        cells = []
        for q in QTYS:
            t = quote(int(ly), length, width, q, co, ci)
            cells.append(f"{t:.1f}（{t / q:.2f}）")
        print(f"| {int(ly)} | {length:g}×{width:g} | {co:g}/{ci:g} | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
