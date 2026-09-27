#!/usr/bin/env python3
"""调用第三方大模型（OpenAI 兼容接口）：DeepSeek、阿里云百炼（通义千问）。

    python3 tools/llm.py providers                         # 各提供方的密钥变量是否已设置（不打印密钥）
    python3 tools/llm.py models  aliyun                    # 列出可用模型
    python3 tools/llm.py chat    aliyun qwen-max  task.md  # 把 task.md 作为用户消息发出，回答打印到 stdout

密钥只从环境变量读，**不写进仓库、不打印**：
- DeepSeek：DEEPSEEK_API_KEY  → https://api.deepseek.com
- 阿里云百炼：DASHSCOPE_API_KEY → https://dashscope.aliyuncs.com/compatible-mode/v1
  （国际站账号可设 DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1）
在云端环境里：会话标题栏的环境菜单 → Edit → 环境变量里添加，新会话生效。
"""
from __future__ import annotations

import json
import os
import sys
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


def _req(name: str, path: str, body: dict | None = None) -> dict:
    key, base = _cfg(name)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=600) as resp:
        return json.load(resp)


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "providers":
        for n, (kv, _, _) in PROVIDERS.items():
            print(f"{n:9s} {kv:18s} {'已设置' if os.environ.get(kv) else '未设置'}")
        return 0
    if argv[0] == "models" and len(argv) == 2:
        for m in _req(argv[1], "/models").get("data", []):
            print(m.get("id"))
        return 0
    if argv[0] == "chat" and len(argv) == 4:
        with open(argv[3], encoding="utf-8") as fp:
            prompt = fp.read()
        d = _req(argv[1], "/chat/completions", {"model": argv[2], "messages": [{"role": "user", "content": prompt}]})
        print(d["choices"][0]["message"]["content"])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
