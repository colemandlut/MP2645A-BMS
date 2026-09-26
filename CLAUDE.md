# 项目约定

- 回复一律使用中文，每条回复前加时间戳；测试跑完要通知用户。
- 每次回复前先检索 `obsidian-vault/`（用户的永久记忆知识库），新结论写回知识库。
- **EDA 只用 KiCad**（用户 2026-09-26 规定），不使用嘉立创EDA专业版；嘉立创仍是板厂/贴片厂。
- 云端会话先运行 `sudo bash tools/setup_kicad.sh` 安装 KiCad 10（`kicad-cli`、`kicad-python`）。
- 任何原理图/PCB/制造文件任务前加载 `pcb-workflow` 技能并严格遵守。
- 测试：`python3 -m unittest discover -s tests`、`make -C firmware test`。
