#!/usr/bin/env python3
"""调用第三方大模型（OpenAI 兼容接口）：DeepSeek、阿里云百炼（通义千问）。

    python3 tools/llm.py providers                         # 各提供方的密钥变量是否已设置（不打印密钥）
    python3 tools/llm.py models  aliyun                    # 列出可用模型（阿里云 Anthropic 兼容端点不支持，404）
    python3 tools/llm.py chat    aliyun qwen3-max task.md  # 把 task.md 作为用户消息发出，回答打印到 stdout

密钥只从环境变量读，**不写进仓库、不打印**：
- DeepSeek：DEEPSEEK_API_KEY  → https://api.deepseek.com
- 阿里云百炼：DASHSCOPE_API_KEY → https://dashscope.aliyuncs.com/compatible-mode/v1
  （国际站账号可设 DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1；
   地址以 /anthropic 结尾时自动改用 Anthropic Messages 格式：POST {base}/v1/messages）
在云端环境里：会话标题栏的环境菜单 → Edit → 环境变量里添加，新会话生效。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PROVIDERS = {
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "aliyun": ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
}


def _cfg(name: str) -> tuple[str, str]:
    key_var, url_var, url = PROVIDERS[name]
    key = os.environ.get(key_var)
    if not key:
        sys.exit(f"{key_var} 未设置：请在环境设置里添加该环境变量（不要把密钥贴进对话或仓库）")
    return key, os.environ.get(url_var, url).rstrip("/")


def _is_anthropic(base: str) -> bool:
    return base.endswith("/anthropic")


def _req(name: str, path: str, body: dict | None = None) -> dict:
    key, base = _cfg(name)
    data = json.dumps(body).encode() if body is not None else None
    if _is_anthropic(base):
        headers = {"x-api-key": key, "Authorization": f"Bearer {key}",
                   "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    else:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    r = urllib.request.Request(base + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {base + path}：{e.read().decode(errors='replace')[:300]}")


def _chat(name: str, model: str, prompt: str) -> str:
    _, base = _cfg(name)
    if _is_anthropic(base):
        d = _req(name, "/v1/messages", {"model": model, "max_tokens": 8192,
                                         "messages": [{"role": "user", "content": prompt}]})
        return "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    d = _req(name, "/chat/completions", {"model": model, "messages": [{"role": "user", "content": prompt}]})
    return d["choices"][0]["message"]["content"]


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "providers":
        for n, (kv, uv, url) in PROVIDERS.items():
            base = os.environ.get(uv, url).rstrip("/")
            fmt = "Anthropic" if _is_anthropic(base) else "OpenAI"
            print(f"{n:9s} {kv:18s} {'已设置' if os.environ.get(kv) else '未设置'}  {base}（{fmt} 格式）")
        return 0
    if argv[0] == "models" and len(argv) == 2:
        _, base = _cfg(argv[1])
        for m in _req(argv[1], "/v1/models" if _is_anthropic(base) else "/models").get("data", []):
            print(m.get("id"))
        return 0
    if argv[0] == "chat" and len(argv) == 4:
        with open(argv[3], encoding="utf-8") as fp:
            prompt = fp.read()
        print(_chat(argv[1], argv[2], prompt))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
