#!/bin/sh
# 用 Claude Code CLI 跑 DeepSeek（Anthropic 兼容接口），作 pcb-workflow 的画图方（models.toml cloud.draw）。
# 用法：tools/deepseek_claude.sh <任务书.md> <输出.md>    （在工程根目录运行）
# 干净环境：不继承宿主会话的 Claude 认证/遥测变量；密钥只从 DEEPSEEK_API_KEY 读取，不打印。
set -eu
TASK="$1"; OUT="$2"
: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY 未设置}"
: "${DS_MODEL:=deepseek-flash}"   # 用户 2026-09-27 13:07 JST：deepseek-v4-pro 一律换成 deepseek-flash
mkdir -p /tmp/ds-claude-home
exec env -i \
  HOME=/tmp/ds-claude-home PATH="$PATH" LANG=C.UTF-8 TERM=dumb \
  HTTPS_PROXY="${HTTPS_PROXY:-}" https_proxy="${https_proxy:-}" NO_PROXY="${NO_PROXY:-}" no_proxy="${no_proxy:-}" \
  NODE_EXTRA_CA_CERTS="${NODE_EXTRA_CA_CERTS:-}" SSL_CERT_FILE="${SSL_CERT_FILE:-}" \
  ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
  ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY" \
  ANTHROPIC_MODEL="$DS_MODEL" ANTHROPIC_SMALL_FAST_MODEL=deepseek-flash ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-flash \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=1000000 \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_TELEMETRY=1 DISABLE_AUTOUPDATER=1 \
  claude -p --model "$DS_MODEL" --permission-mode acceptEdits \
    --allowedTools "Read" "Write" "Edit" "Glob" "Grep" \
      "Bash(kicad-cli *)" "Bash(python3 *)" "Bash(cp *)" "Bash(mkdir *)" "Bash(ls *)" "Bash(cat *)" "Bash(diff *)" \
  < "$TASK" > "$OUT"
