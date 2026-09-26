# 项目约定

- 回复一律使用中文，每条回复前加时间戳；测试跑完要通知用户。
- 每次回复前先检索 `obsidian-vault/`（用户的永久记忆知识库），新结论写回知识库。
- **EDA 只用 KiCad**（用户 2026-09-26 规定），不使用嘉立创EDA专业版；嘉立创仍是板厂/贴片厂。
- 云端会话先运行 `sudo bash tools/setup_kicad.sh` 安装 KiCad 10（`kicad-cli`、`kicad-python`）和 Freerouting 2.4.1（`freerouting`）。
- 任何原理图/PCB/制造文件任务前加载 `pcb-workflow` 技能并严格遵守。
- 模型分工（画图/复核/泳道/取库/跑工具）以技能目录的 `models.toml` 为准，开工前跑 `python3 <skill>/scripts/models.py show`；不同厂商校验不过或未配置就停下问用户。
- 器件都用嘉立创的（带立创 C 编号），符号与封装形状从嘉立创取得：`python3 tools/fetch_jlc_parts.py`（需放行 easyeda.com），不许用 KiCad 官方库顶替。
- 测试：`python3 -m unittest discover -s tests`、`make -C firmware test`。
