#!/usr/bin/env bash
# 用本机 claude CLI 驱动第三方模型当「带工具的子代理」（读写文件、跑 kicad-cli）。
#   tools/llm_agent.sh <deepseek|aliyun> <模型> <工作目录> < 任务.md > 输出.txt
# 走各家的 Anthropic 兼容接口；在干净环境（env -i、独立 HOME）里启动，避免继承本会话的 Claude 凭据。
# 密钥只从环境变量读：DEEPSEEK_API_KEY / DASHSCOPE_API_KEY（阿里云地址可用 DASHSCOPE_BASE_URL 覆盖，须为 .../anthropic）。
set -euo pipefail
prov=${1:?提供方}; model=${2:?模型}; wd=${3:?工作目录}
case "$prov" in
  deepseek) base=https://api.deepseek.com/anthropic; key=${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY 未设置}; fast=deepseek-flash ;;
  aliyun)   base=${DASHSCOPE_BASE_URL:-https://dashscope.aliyuncs.com/apps/anthropic}; key=${DASHSCOPE_API_KEY:?DASHSCOPE_API_KEY 未设置}; fast=qwen3.8-flash ;;
  *) echo "未知提供方 $prov" >&2; exit 2 ;;
esac
# 用户 2026-09-27：禁用 deepseek-v4-pro（DeepSeek 接口会把 claude-opus-* 自动映射成 v4-pro，所以下面把 opus/sonnet/子代理默认模型都钉死）
[ "$model" = "deepseek-v4-pro" ] && { echo "deepseek-v4-pro 已被用户禁用，请用 deepseek-flash（即 DeepSeek-V4.1-Flash）" >&2; exit 2; }
case "$base" in */anthropic) ;; *) echo "地址须为 Anthropic 兼容端点（以 /anthropic 结尾）：$base" >&2; exit 2 ;; esac
mkdir -p "$wd/.agent-home"
cd "$wd"
exec env -i PATH="$PATH" HOME="$wd/.agent-home" TERM=dumb LANG=C.UTF-8 \
  HTTPS_PROXY="${HTTPS_PROXY:-}" HTTP_PROXY="${HTTP_PROXY:-}" NO_PROXY="${NO_PROXY:-}" \
  https_proxy="${https_proxy:-}" http_proxy="${http_proxy:-}" no_proxy="${no_proxy:-}" \
  NODE_EXTRA_CA_CERTS="${NODE_EXTRA_CA_CERTS:-/root/.ccr/ca-bundle.crt}" SSL_CERT_FILE="${SSL_CERT_FILE:-}" \
  ANTHROPIC_BASE_URL="$base" ANTHROPIC_AUTH_TOKEN="$key" ANTHROPIC_MODEL="$model" \
  ANTHROPIC_SMALL_FAST_MODEL="$fast" ANTHROPIC_DEFAULT_HAIKU_MODEL="$fast" \
  ANTHROPIC_DEFAULT_OPUS_MODEL="$model" ANTHROPIC_DEFAULT_SONNET_MODEL="$model" CLAUDE_CODE_SUBAGENT_MODEL="$model" \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS="${CLAUDE_CODE_MAX_CONTEXT_TOKENS:-128000}" CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  timeout "${AGENT_TIMEOUT:-3600}" claude -p --permission-mode acceptEdits --allowedTools Bash Read Write Edit Glob Grep
