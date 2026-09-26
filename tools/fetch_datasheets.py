#!/usr/bin/env python3
"""按 BOM 立创编号从 datasheet.lcsc.com 下载数据手册到 datasheets/（pcb-workflow：拿原厂手册的门路 1）。

    python3 tools/fetch_datasheets.py              # 全部
    python3 tools/fetch_datasheets.py C18198873    # 指定

校验：下载结果必须是真 PDF（以 %PDF 开头），否则记失败——商城主站返回的
"This website requires JavaScript" HTML 不算手册。已存在且有效的文件跳过。
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOM = os.path.join(ROOT, "docs", "02-BOM.csv")
OUT = os.path.join(ROOT, "datasheets")
CNUM = re.compile(r"^C\d{3,}$")


def parts() -> list[tuple[str, str]]:
    res, seen = [], set()
    with open(BOM, encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            c = (row.get("立创编号") or "").strip()
            if CNUM.match(c) and c not in seen:
                seen.add(c)
                mpn = re.sub(r"[^\w.+-]+", "_", row.get("制造商型号", "")).strip("_")
                res.append((c, mpn))
    return res


def is_pdf(path: str) -> bool:
    try:
        with open(path, "rb") as fp:
            return fp.read(5) == b"%PDF-"
    except OSError:
        return False


def main(argv: list[str]) -> int:
    os.makedirs(OUT, exist_ok=True)
    todo = [(c, "") for c in argv] if argv else parts()
    bad = 0
    for c, mpn in todo:
        path = os.path.join(OUT, f"{c}_{mpn}.pdf" if mpn else f"{c}.pdf")
        if is_pdf(path):
            print(f"= {c:<10} 已有 {os.path.basename(path)}")
            continue
        url = f"https://datasheet.lcsc.com/lcsc/{c}.pdf"
        subprocess.run(["curl", "-sS", "-L", "-m", "120", "-o", path, url], capture_output=True)
        if is_pdf(path):
            print(f"✅ {c:<10} {os.path.getsize(path) // 1024:>6} KB  {os.path.basename(path)}")
        else:
            bad += 1
            if os.path.exists(path):
                os.remove(path)
            print(f"❌ {c:<10} 不是 PDF / 下载失败  {url}")
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
