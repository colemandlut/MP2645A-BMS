# MP2645A-BMS：8S LiFePO4 200A 主动均衡 BMS（MPS 方案）

| 项目 | 内容 |
|---|---|
| 电池 | 8S LFP，25.6V 标称（20~29.2V） |
| 电流 | 持续放电 200A / 充电 100A，硬件短路 800A |
| AFE | MPS **MP2797**（监测、库仑计、高边驱动、硬件保护、被动均衡） |
| 均衡 | MPS **MP2645A** ×2 级联，电感式双向主动均衡（A 级电流） |
| 功率 | 高边背靠背 NMOS，每方向 8 并联（80V/1.2mΩ TOLL） |

## 目录

- `docs/01-系统设计说明.md` —— 完整方案：架构、选型、功率/采样/均衡电路、保护参数、布局、验证计划
- `docs/02-BOM.csv` —— 主要物料清单
- `tools/bms_calc.py` —— 设计计算器（MOSFET 损耗温升、分流器、均衡时间）
- `firmware/` —— 与硬件无关的保护状态机 + LFP 均衡策略（C11），附主机端单元测试
- `obsidian-vault/` —— 项目知识库（Obsidian 仓库，可直接用 Obsidian 打开）

## EDA

全部使用 **KiCad 10**。云端容器安装：`sudo bash tools/setup_kicad.sh`（之后可用 `kicad-cli`、`kicad-python`）。

## 运行

```bash
python3 tools/bms_calc.py                 # 打印设计计算
python3 -m unittest discover -s tests     # 计算器测试
make -C firmware test                     # 固件逻辑测试
```

> 标注【待核】的参数来自 MPS 产品简介，画原理图前需对照正式数据手册确认。
