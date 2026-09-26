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
    fet_qg_nc: float = 178.0             # IPT012N08N5 Qg ≈ 178nC (C531199)
    fet_rth_ja_eff: float = 20.0         # 装散热器后单管等效 Rth(j-a) K/W
    fet_current_share: float = 1.15      # 均流不平衡系数（最坏的那颗多分 15%）

    # ---- 分流器 ----
    shunt_uohm: float = 100.0

    # ---- 主动均衡 (MP2643 x7，相邻对) ----
    bal_current_a: float = 640 / (3 * 120)   # RUBC=120kΩ → 1.78A（手册式(1)，含容差不超 2A）
    bal_efficiency: float = 0.89             # 手册 Table 2（VCL<3.65V）

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


# ---------------- MP2643 手册公式 ----------------

def mp2643_iubc(r_kohm: float) -> float:
    """buck-balance 电流，手册式 (1)：IUBC = 640 / (3·RUBC[kΩ])。"""
    return 640.0 / (3.0 * r_kohm)


def mp2643_vcu_lim(r1: float, r2: float, vref: float = 1.2) -> float:
    """boost-balance 的 CU 电压上限，手册式 (3)：VCU_LIM = 1.2·(R1+R2)/R2。"""
    return vref * (r1 + r2) / r2


def mp2643_inductor(vcu: float, vcl: float, iubc: float, l_uh: float, fsw_mhz: float = 1.08) -> dict:
    """手册式 (17)(18)：纹波 ΔIL = (VCU-VCL)·VCL/(VCU·L·fsw)，峰值 = VCU/VCL·IUBC + ΔIL/2。"""
    dil = (vcu - vcl) * vcl / (vcu * l_uh * fsw_mhz)
    ipk = vcu / vcl * iubc + dil / 2
    return {"ripple_a": dil, "peak_a": ipk, "isat_min_a": ipk + 1.0}


# ---------------- v0.2 详细设计补充计算 ----------------

CU_RHO_OHM_M = 1.72e-8      # 20°C 铜电阻率
CU_ALPHA = 0.00393          # 铜电阻温度系数 /K


def precharge(v_pack: float, c_load_f: float, r_ohm: float) -> dict:
    """预充电阻: 峰值电流、峰值功率、单次能量、充到 95% 的时间。

    电阻上消耗的能量恒等于电容最终储能 ½CV²（与 R 无关）。
    """
    return {
        "i_peak_a": v_pack / r_ohm,
        "p_peak_w": v_pack ** 2 / r_ohm,
        "energy_j": 0.5 * c_load_f * v_pack ** 2,
        "t95_s": 3 * r_ohm * c_load_f,
    }


def resistor_power_w(i_a: float, r_ohm: float) -> float:
    return i_a ** 2 * r_ohm


def rc_corner_hz(r_ohm: float, c_f: float) -> float:
    return 1.0 / (2 * math.pi * r_ohm * c_f)


def ntc_divider(t_c: float, r_pullup: float = 10e3, r25: float = 10e3,
                beta: float = 3435.0, v_ref: float = 1.0) -> float:
    """NTC 接地、上拉到 v_ref 的分压比（返回 NTC 端电压 / v_ref）。"""
    t = t_c + 273.15
    r_ntc = r25 * math.exp(beta * (1.0 / t - 1.0 / 298.15))
    return v_ref * r_ntc / (r_ntc + r_pullup)


def busbar(i_a: float, width_mm: float, thick_mm: float, length_mm: float,
           temp_c: float = 80.0) -> dict:
    a_m2 = width_mm * thick_mm * 1e-6
    rho = CU_RHO_OHM_M * (1 + CU_ALPHA * (temp_c - 20))
    r = rho * length_mm * 1e-3 / a_m2
    return {
        "j_a_per_mm2": i_a / (width_mm * thick_mm),
        "r_uohm": r * 1e6,
        "p_w": i_a ** 2 * r,
    }


def ipc2221_width_mm(i_a: float, dt_c: float = 10.0, oz: float = 2.0,
                     external: bool = True) -> float:
    """IPC-2221 线宽估算：I = k·ΔT^0.44·A^0.725（A 单位 mil²）。"""
    k = 0.048 if external else 0.024
    area_mil2 = (i_a / (k * dt_c ** 0.44)) ** (1 / 0.725)
    thick_mil = 1.378 * oz
    return area_mil2 / thick_mil * 0.0254


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
    v = d.series * d.cell_v_max
    r.values["precharge"] = precharge(v, 10e-3, 30.0)
    r.values["busbar"] = busbar(d.i_dsg_cont, 20, 2, 150)
    r.values["bal_trace_mm"] = ipc2221_width_mm(d.bal_current_a * 1.5)   # 按 1.5 倍均衡电流
    r.values["cell_rc_hz"] = rc_corner_hz(100, 0.1e-6)
    r.values["shunt_rc_hz"] = rc_corner_hz(2 * 100, 0.1e-6)
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
    print("== 预充 (30Ω, 负载 10mF) ==")
    print(_fmt(r["precharge"]))
    print("== 铜排 20x2mm x150mm @200A, 80°C ==")
    print(_fmt(r["busbar"]))
    print(f"== 均衡走线 (4.5A, ΔT10°C, 2oz 外层) ≥ {r['bal_trace_mm']:.2f} mm")
    print(f"== 滤波转折: 电芯 100Ω/0.1µF {r['cell_rc_hz']:,.0f} Hz, 分流器差模 2x100Ω/0.1µF {r['shunt_rc_hz']:,.0f} Hz")
    ok = r["fet_dsg"]["tj_worst_c"] < 125
    print(f"\n结论: 最坏 MOSFET Tj = {r['fet_dsg']['tj_worst_c']:.1f}°C -> {'OK' if ok else '超限，需增加并联数/散热'}")


if __name__ == "__main__":
    main()
