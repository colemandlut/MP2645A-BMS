#!/usr/bin/env python3
"""按 BOM 里的立创编号，从嘉立创/立创 EasyEDA 库批量取符号 + 封装 + 3D（pcb-workflow 规则 0e）。

    python3 tools/fetch_jlc_parts.py                 # 读 docs/02-BOM.csv，取回到 hardware/lib/jlc/
    python3 tools/fetch_jlc_parts.py C25744 C13832   # 只取指定编号

- 输出：hardware/lib/jlc/jlc.kicad_sym、jlc.pretty/、jlc.3dshapes/，并注册到工程库表
  （hardware/sym-lib-table、hardware/fp-lib-table，只改工程库表，不动全局）。
- 报告：hardware/lib/jlc/fetch_report.md —— 每个编号成功/失败及原因，另列「非嘉立创件」（BOM 里没有 C 编号的行）。
- EasyEDA 接口有限流（约 20 次后 403 十几分钟），所以分批 + 退避，并开 --use-cache。
- 取不到就如实报告，**不许退回 KiCad 官方库**（规则 0e）。

退出码：0 全部成功；3 有失败（网络被拦、限流、编号无效）。
"""
from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BOM = os.path.join(ROOT, "docs", "02-BOM.csv")
HW = os.path.join(ROOT, "hardware")
LIB = os.path.join(HW, "lib", "jlc")
BASE = os.path.join(LIB, "jlc")          # easyeda2kicad 以它为前缀生成 .kicad_sym/.pretty/.3dshapes
REPORT = os.path.join(LIB, "fetch_report.md")
CNUM = re.compile(r"^C\d{3,}$")
BATCH, PAUSE_S = 15, 60


def bom_parts() -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """返回 ([(C编号, 位号)], [(位号, 型号, 原因)])。"""
    ok, non = [], []
    with open(BOM, encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            c = (row.get("立创编号") or "").strip()
            if CNUM.match(c):
                ok.append((c, row["位号"]))
            else:
                non.append((row["位号"], row.get("制造商型号", ""), c or "空"))
    return ok, non


def fetch_one(c: str) -> tuple[bool, str]:
    exe = shutil.which("easyeda2kicad")
    if not exe:
        return False, "未安装 easyeda2kicad（pip install easyeda2kicad）"
    cmd = [exe, "--full", f"--lcsc_id={c}", "--output", BASE, "--project-relative", "--use-cache", "--overwrite"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=HW)
    except subprocess.TimeoutExpired:
        return False, "超时"
    out = (p.stdout + p.stderr).strip()
    if "Tunnel connection failed: 403" in out:
        return False, "网络策略拦截 easyeda.com（403）"
    if "[ERROR]" in out or p.returncode != 0:
        last = [ln for ln in out.splitlines() if "ERROR" in ln] or out.splitlines()[-1:]
        return False, last[-1][:160] if last else f"退出码 {p.returncode}"
    return True, "ok"


def register_tables():
    """把 jlc 库写进工程库表（已存在则跳过）。"""
    for fn, kind, uri in (("sym-lib-table", "sym_lib_table", "${KIPRJMOD}/lib/jlc/jlc.kicad_sym"),
                          ("fp-lib-table", "fp_lib_table", "${KIPRJMOD}/lib/jlc/jlc.pretty")):
        path = os.path.join(HW, fn)
        entry = f'  (lib (name "jlc")(type "KiCad")(uri "{uri}")(options "")(descr "嘉立创/立创 EasyEDA 库，规则 0e"))\n'
        if os.path.isfile(path):
            s = open(path, encoding="utf-8").read()
            if '(name "jlc")' in s:
                continue
            s = s.rstrip().rstrip(")") + entry + ")\n"
        else:
            s = f"({kind}\n  (version 7)\n{entry})\n"
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(s)


def main(argv: list[str]) -> int:
    os.makedirs(LIB, exist_ok=True)
    wanted, non = bom_parts()
    if argv:
        wanted = [(c, "命令行") for c in argv]
    seen, results = set(), []
    for i, (c, ref) in enumerate(wanted):
        if c in seen:
            continue
        seen.add(c)
        if i and i % BATCH == 0:
            print(f"已取 {i} 个，按限流规则暂停 {PAUSE_S}s …", flush=True)
            time.sleep(PAUSE_S)
        ok, why = fetch_one(c)
        results.append((c, ref, ok, why))
        print(f"{'✅' if ok else '❌'} {c:<10} {ref:<14} {why}", flush=True)
        if not ok and "网络策略" in why and len(results) >= 2 and not any(r[2] for r in results):
            # 连续被拦就没必要继续打，剩余的直接记为同一原因
            for c2, ref2 in wanted[i + 1:]:
                if c2 not in seen:
                    seen.add(c2)
                    results.append((c2, ref2, False, "网络策略拦截 easyeda.com（未尝试）"))
            break
    if any(r[2] for r in results):
        register_tables()

    with open(REPORT, "w", encoding="utf-8") as fp:
        fp.write("# 嘉立创库取回报告（规则 0e）\n\n")
        fp.write(f"生成：`python3 tools/fetch_jlc_parts.py`，{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n\n")
        fp.write("| 立创编号 | 位号 | 结果 | 说明 |\n|---|---|---|---|\n")
        for c, ref, ok, why in results:
            fp.write(f"| {c} | {ref} | {'✅' if ok else '❌'} | {why} |\n")
        fp.write("\n## 非嘉立创件（BOM 中没有立创编号，需用户定夺：客供 / 换料 / 按原厂手册手画封装）\n\n")
        fp.write("| 位号 | 型号 | 立创编号栏 |\n|---|---|---|\n")
        for ref, mpn, c in non:
            fp.write(f"| {ref} | {mpn} | {c} |\n")
    n_ok = sum(1 for r in results if r[2])
    print(f"\n成功 {n_ok}/{len(results)}；非嘉立创件 {len(non)} 行；报告 {os.path.relpath(REPORT, ROOT)}")
    return 0 if n_ok == len(results) else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
