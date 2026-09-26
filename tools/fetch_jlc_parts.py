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


def _run(args: list[str]) -> tuple[int, str]:
    exe = shutil.which("easyeda2kicad")
    cmd = [exe, *args, "--output", BASE, "--project-relative", "--use-cache", "--overwrite"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=HW)
    except subprocess.TimeoutExpired:
        return -1, "超时"
    return p.returncode, (p.stdout + p.stderr).strip()


def _why(rc: int, out: str) -> str:
    if "Tunnel connection failed: 403" in out:
        return "网络策略拦截（403）"
    last = [ln for ln in out.splitlines() if "ERROR" in ln or "Error" in ln] or out.splitlines()[-1:]
    return (last[-1][:160] if last else f"退出码 {rc}")


def fetch_one(c: str) -> tuple[bool, str]:
    """符号 + 封装为必需（规则 0e）；3D 模型单独取（在 modules.easyeda.com，可能被拦），失败只记录。"""
    if not shutil.which("easyeda2kicad"):
        return False, "未安装 easyeda2kicad（pip install easyeda2kicad）"
    rc, out = _run(["--symbol", "--footprint", f"--lcsc_id={c}"])
    ok = rc == 0 and f"Created Kicad symbol for ID : {c}" in out and "footprint" in out.lower() and "[ERROR]" not in out
    if not ok:
        return False, "符号/封装失败：" + _why(rc, out)
    rc3, out3 = _run(["--3d", f"--lcsc_id={c}"])
    if rc3 == 0 and "[ERROR]" not in out3 and "Traceback" not in out3:
        return True, "符号+封装+3D"
    return True, "符号+封装（3D 未取到：" + _why(rc3, out3) + "）"


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


def upgrade_library() -> str:
    """用 kicad-cli 把 easyeda2kicad 写的旧格式库重存为 KiCad 当前格式（同时去掉重复定义）。
    不做这一步，嵌入原理图的符号（arc 等图元）与库加载后的内部表示不一致，ERC 报 lib_symbol_mismatch 假告警。"""
    sym = BASE + ".kicad_sym"
    cli = shutil.which("kicad-cli")
    if not (cli and os.path.exists(sym)):
        return "跳过（无 kicad-cli）"
    tmp = BASE + "_up.kicad_sym"
    p = subprocess.run([cli, "sym", "upgrade", "--force", "-o", tmp, sym], capture_output=True, text=True, cwd=HW)
    if p.returncode or not os.path.exists(tmp):
        return f"失败：{(p.stdout + p.stderr).strip()[-200:]}"
    os.replace(tmp, sym)
    return "完成"


def normalize_pin_types() -> int:
    """EasyEDA 库的引脚电气类型没有信息量（全是 unspecified，电容还有 input），会让 ERC 刷假告警。
    统一改成 passive：只改电气类型，不动引脚号/名称/坐标/图形/封装/LCSC。幂等。返回改动数。"""
    sym = BASE + ".kicad_sym"
    if not os.path.exists(sym):
        return 0
    with open(sym, encoding="utf-8") as fp:
        s = fp.read()
    s2, n = re.subn(r"\(pin (?:input|output|unspecified|bidirectional|tri_state) ", "(pin passive ", s)
    if n:
        with open(sym, "w", encoding="utf-8") as fp:
            fp.write(s2)
    return n


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
    print(f"库升级为 KiCad 当前格式：{upgrade_library()}")
    print(f"引脚电气类型归一为 passive：{normalize_pin_types()} 处")

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
    if sys.argv[1:] == ["--normalize-only"]:
        print(f"库升级为 KiCad 当前格式：{upgrade_library()}")
        print(f"引脚电气类型归一为 passive：{normalize_pin_types()} 处")
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
