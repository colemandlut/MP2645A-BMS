#!/usr/bin/env python3
"""8S LiFePO4 / 200A BMS 设计计算器。

用法:  python3 tools/bms_calc.py          # 打印默认设计的全部计算结果
所有输入参数集中在 DesignInput 中，改参数后重新运行即可复核设计。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class DesignInput:
    # ---- 电池组 ----
    series: int = 8
    cell_v_nom: float = 3.20
    cell_v_max: float = 3.65
    cell_v_min: float = 2.50
    cell_capacity_ah: float = 200.0      # 假设 200Ah 电芯（1C = 200A）

    # ---- 电流 ----
    i_dsg_cont: float = 200.0            # 最大持续放电电流
    i_chg_cont: float = 100.0            # 最大持续充电电流 (0.5C)
    i_scp: float = 800.0                 # 短路保护阈值

    # ---- 功率 MOSFET（每个方向并联数量相同，背靠背共源）----
    fet_rds_25c_mohm: float = 1.2        # 80V TOLL, Rds(on) max @25°C, Vgs=10V
    fet_rds_tempco: float = 1.7          # Tj=100°C 相对 25°C 的倍率
    fet_parallel: int = 8                # 每个方向并联数量
    fet_qg_nc: float = 170.0             # 单管 Qg(total) @10V
    fet_rth_ja_eff: float = 20.0         # 装散热器后单管等效 Rth(j-a) K/W
    fet_current_share: float = 1.15      # 均流不平衡系数（最坏的那颗多分 15%）

    # ---- 分流器 ----
    shunt_uohm: float = 100.0

    # ---- 主动均衡 (MP2645A x2) ----
    bal_current_a: float = 3.0           # 设计取值，低于器件上限，留热裕量
    bal_efficiency: float = 0.85

    ambient_c: float = 45.0


@dataclass
class DesignResult:
    values: dict = field(default_factory=dict)

    def __getitem__(self, k):
        return self.values[k]


def pack_voltages(d: DesignInput) -> dict:
    return {
        "pack_v_nom": d.series * d.cell_v_nom,
        "pack_v_max": d.series * d.cell_v_max,
        "pack_v_min": d.series * d.cell_v_min,
        "pack_energy_wh": d.series * d.cell_v_nom * d.cell_capacity_ah,
    }


def fet_path(d: DesignInput, current: float) -> dict:
    """背靠背 CHG+DSG 两组 MOSFET 串联的导通损耗与温升。"""
    r_hot_single = d.fet_rds_25c_mohm * d.fet_rds_tempco * 1e-3
    r_group = r_hot_single / d.fet_parallel               # 一个方向
    r_path = 2 * r_group                                   # CHG + DSG 串联
    p_path = current ** 2 * r_path
    i_worst_fet = current / d.fet_parallel * d.fet_current_share
    p_worst_fet = i_worst_fet ** 2 * r_hot_single
    tj_worst = d.ambient_c + p_worst_fet * d.fet_rth_ja_eff
    return {
        "r_path_mohm": r_path * 1e3,
        "p_path_w": p_path,
        "i_worst_fet_a": i_worst_fet,
        "p_worst_fet_w": p_worst_fet,
        "tj_worst_c": tj_worst,
        "vdrop_path_mv": current * r_path * 1e3,
    }


def gate_turnoff_us(d: DesignInput, sink_current_a: float) -> float:
    """一组 MOSFET 栅极电荷在给定下拉电流下的关断时间估算 (µs)。"""
    q_total = d.fet_qg_nc * 1e-9 * d.fet_parallel
    return q_total / sink_current_a * 1e6


def shunt(d: DesignInput) -> dict:
    r = d.shunt_uohm * 1e-6
    return {
        "v_at_dsg_mv": d.i_dsg_cont * r * 1e3,
        "v_at_scp_mv": d.i_scp * r * 1e3,
        "p_at_dsg_w": d.i_dsg_cont ** 2 * r,
        "lsb_ma_per_uv": 1e-6 / r * 1e3,    # 1µV 对应的电流(mA)
    }


def balance_time_h(d: DesignInput, soc_mismatch_pct: float) -> float:
    """主动均衡把一节电芯的 SOC 偏差拉平所需时间 (h)。

    单向搬运：偏差电荷 / (均衡电流 * 效率)。
    """
    if soc_mismatch_pct < 0:
        raise ValueError("soc_mismatch_pct must be >= 0")
    ah = d.cell_capacity_ah * soc_mismatch_pct / 100.0
    return ah / (d.bal_current_a * d.bal_efficiency)


def passive_balance_time_h(d: DesignInput, soc_mismatch_pct: float, i_bleed_a: float = 0.05) -> float:
    ah = d.cell_capacity_ah * soc_mismatch_pct / 100.0
    return ah / i_bleed_a


def evaluate(d: DesignInput | None = None) -> DesignResult:
    d = d or DesignInput()
    r = DesignResult()
    r.values.update(pack_voltages(d))
    r.values["fet_dsg"] = fet_path(d, d.i_dsg_cont)
    r.values["fet_chg"] = fet_path(d, d.i_chg_cont)
    r.values["shunt"] = shunt(d)
    r.values["gate_off_us_1a"] = gate_turnoff_us(d, 1.0)
    r.values["bal_5pct_h"] = balance_time_h(d, 5.0)
    r.values["bal_5pct_passive_h"] = passive_balance_time_h(d, 5.0)
    return r


def _fmt(d: dict, indent: str = "  ") -> str:
    return "\n".join(f"{indent}{k:<22}= {v:,.3f}" for k, v in d.items())


def main() -> None:
    d = DesignInput()
    r = evaluate(d)
    print("== 电池组 ==")
    print(_fmt({k: r[k] for k in ("pack_v_nom", "pack_v_max", "pack_v_min", "pack_energy_wh")}))
    print(f"== 功率通路 @放电 {d.i_dsg_cont:.0f}A ==")
    print(_fmt(r["fet_dsg"]))
    print(f"== 功率通路 @充电 {d.i_chg_cont:.0f}A ==")
    print(_fmt(r["fet_chg"]))
    print("== 分流器 ==")
    print(_fmt(r["shunt"]))
    print(f"== 栅极 ==\n  {d.fet_parallel} 管并联 @1A 下拉关断 ≈ {r['gate_off_us_1a']:.2f} µs")
    print("== 均衡 (5% SOC 偏差) ==")
    print(f"  MP2645A 主动 {d.bal_current_a}A : {r['bal_5pct_h']:.2f} h")
    print(f"  被动 50mA 对比        : {r['bal_5pct_passive_h']:.1f} h")
    ok = r["fet_dsg"]["tj_worst_c"] < 125
    print(f"\n结论: 最坏 MOSFET Tj = {r['fet_dsg']['tj_worst_c']:.1f}°C -> {'OK' if ok else '超限，需增加并联数/散热'}")


if __name__ == "__main__":
    main()
