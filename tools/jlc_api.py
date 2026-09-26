#!/usr/bin/env python3
"""嘉立创（JLCPCB SMT）料号查询：库存、基础库/扩展库、阶梯价（美元）。

    python3 tools/jlc_api.py C25744 C92243          # 按 C 编号精确查
    python3 tools/jlc_api.py -k "0402WGF1073TCE"    # 关键字搜索（型号/规格）

数据来自 jlcpcb.com 的 SMT 料号搜索接口（与嘉立创下单页同源），
「嘉立创库存」与立创商城库存是两个独立料池——贴片以这里为准（pcb-workflow 规则 0b）。
"""
from __future__ import annotations

import json
import sys
import urllib.request

API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"


def search(keyword: str, size: int = 10) -> list[dict]:
    body = json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": size}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json",
                                                          "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    return (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []


def part(code: str) -> dict | None:
    """按 C 编号精确取一条；取不到返回 None。"""
    for c in search(code, 5):
        if c.get("componentCode") == code:
            return c
    return None


def summary(c: dict) -> dict:
    prices = [(p["startNumber"], p["productPrice"]) for p in (c.get("componentPrices") or [])]
    return {
        "code": c.get("componentCode"),
        "mpn": c.get("componentModelEn"),
        "brand": c.get("componentBrandEn"),
        "package": c.get("componentSpecificationEn"),
        "desc": (c.get("describe") or "")[:80],
        "stock": c.get("stockCount"),
        "lib": {"base": "基础库", "expand": "扩展库"}.get(c.get("componentLibraryType"), c.get("componentLibraryType")),
        "preferred": c.get("preferredComponentFlag") is True,
        "prices_usd": prices,
    }


def unit_price(s: dict, qty: int) -> float | None:
    p = None
    for start, price in sorted(s["prices_usd"]):
        if qty >= start:
            p = price
    return p if p is not None else (s["prices_usd"][0][1] if s["prices_usd"] else None)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "-k":
        rows = [summary(c) for c in search(" ".join(argv[1:]))]
    else:
        rows = []
        for code in argv:
            c = part(code)
            rows.append(summary(c) if c else {"code": code, "mpn": "（嘉立创未找到）"})
    for s in rows:
        pr = ", ".join(f"{q}+:${p}" for q, p in s.get("prices_usd", [])[:3])
        print(f"{s['code']:<12} {s.get('lib', ''):<4} 库存 {s.get('stock', '-')!s:>9}  {s.get('mpn', '')} | "
              f"{s.get('package', '')} | {s.get('desc', '')} | {pr}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
