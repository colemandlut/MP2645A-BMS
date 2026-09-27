#!/usr/bin/env bash
# 第三方模型「带工具子代理」合格测试：复制工程到临时目录，让模型跑 ERC、数位号、核对 U4 料号，自动对答案。
#   tools/llm_agent_selftest.sh <deepseek|aliyun> <模型>
set -uo pipefail
prov=$1; model=$2; root=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d /tmp/llmtest.XXXX); cp -r "$root/hardware" "$T/"; cp "$root/docs/02-BOM.csv" "$T/"
mountpoint -q /opt/kicad-root/home/user 2>/dev/null || sudo bash "$root/tools/setup_kicad.sh" >/dev/null 2>&1
( cd "$T" && kicad-cli sch erc --format json -o "$T/truth.json" hardware/mp2645a-bms.kicad_sch >/dev/null 2>&1 )
nerc=$(python3 -c "import json;d=json.load(open('$T/truth.json'));print(sum(len(s['violations']) for s in d['sheets']))")
nref=$(python3 -c "import re;s=open('$T/hardware/04_power_supply.kicad_sch').read();print(len({r for r in re.findall(r'\(property \"Reference\" \"([A-Z_]+[0-9]+)\"',s)}))")
u4=$(awk -F, '$2=="U4"{print $6}' "$T/02-BOM.csv")
cat > "$T/task.md" <<EOT
你在目录 $T 里工作（KiCad 10 工程在 hardware/，BOM 在 02-BOM.csv）。只在这个目录里读写。
1. 运行 \`kicad-cli sch erc --format json -o erc.json hardware/mp2645a-bms.kicad_sch\`，统计违规总数并按 type 分类计数。
2. 读 hardware/04_power_supply.kicad_sch，列出所有器件位号（去掉 #PWR 等电源符号）及 U4 的 LCSC 字段值。
3. 在 02-BOM.csv 找位号 U4 的行，核对 LCSC 编号是否与原理图一致。
4. 结果写到 report.md（中文），必须包含三行机器可读结论：\`ERC_TOTAL=<数>\`、\`REF_COUNT=<数>\`、\`U4_LCSC=<值>\`。
完成后只回复 DONE。
EOT
start=$(date +%s)
"$root/tools/llm_agent.sh" "$prov" "$model" "$T" < "$T/task.md" > "$T/out.txt" 2> "$T/err.txt"; rc=$?
dt=$(( $(date +%s) - start ))
got() { grep -oE "$1=[A-Za-z0-9]+" "$T/report.md" 2>/dev/null | head -1 | cut -d= -f2; }
ok=0
[ "$(got ERC_TOTAL)" = "$nerc" ] && ok=$((ok+1)); [ "$(got REF_COUNT)" = "$nref" ] && ok=$((ok+1)); [ "$(got U4_LCSC)" = "$u4" ] && ok=$((ok+1))
echo "提供方=$prov 模型=$model 退出码=$rc 用时=${dt}s 正确=$ok/3（答案 ERC_TOTAL=$nerc REF_COUNT=$nref U4_LCSC=$u4；模型 ERC_TOTAL=$(got ERC_TOTAL) REF_COUNT=$(got REF_COUNT) U4_LCSC=$(got U4_LCSC)）"
[ $rc -ne 0 ] && grep -v unrecognized_model "$T/err.txt" | tail -5 | sed -E 's/(sk-|Bearer )[A-Za-z0-9._-]+/\1***/g'
[ $ok -eq 3 ] && [ $rc -eq 0 ]
