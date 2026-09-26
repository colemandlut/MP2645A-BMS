import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import bms_calc as bc  # noqa: E402


class TestBmsCalc(unittest.TestCase):
    def setUp(self):
        self.d = bc.DesignInput()
        self.r = bc.evaluate(self.d)

    def test_pack_voltage(self):
        self.assertAlmostEqual(self.r["pack_v_nom"], 25.6)
        self.assertAlmostEqual(self.r["pack_v_max"], 29.2)
        self.assertAlmostEqual(self.r["pack_v_min"], 20.0)

    def test_fet_thermal_margin_at_200a(self):
        fet = self.r["fet_dsg"]
        # Tokmas Tj,max = 150°C：最坏值（Rds 取最大 1.2mΩ）下仍留 ≥ 30°C 裕量
        self.assertLess(fet["tj_worst_c"], 150.0 - 30.0)
        self.assertLess(fet["p_path_w"], 30.0)

    def test_fet_path_resistance(self):
        # 1.2mΩ*1.7/6*2 = 0.68mΩ
        self.assertAlmostEqual(self.r["fet_dsg"]["r_path_mohm"], 0.68, places=3)

    def test_shunt_signal_levels(self):
        s = self.r["shunt"]
        self.assertAlmostEqual(s["v_at_dsg_mv"], 20.0)
        self.assertAlmostEqual(s["v_at_scp_mv"], 80.0)
        self.assertAlmostEqual(s["p_at_dsg_w"], 4.0)

    def test_active_balance_much_faster_than_passive(self):
        # 开关电容 @100mV 约 0.21A，比 50mA 被动快约 4 倍
        self.assertLess(self.r["bal_5pct_h"] * 3, self.r["bal_5pct_passive_h"])
        # 120Ah*5% = 6Ah / (0.18A*0.95)
        self.assertAlmostEqual(self.r["bal_5pct_h"], 6 / (0.18 * 0.95), places=3)

    def test_balance_time_rejects_negative(self):
        with self.assertRaises(ValueError):
            bc.balance_time_h(self.d, -1)

    def test_gate_turnoff(self):
        # 6*240nC = 1.44µC @1A -> 1.44µs
        self.assertAlmostEqual(bc.gate_turnoff_us(self.d, 1.0), 1.44, places=3)

    def test_fewer_fets_gets_hotter(self):
        d4 = bc.DesignInput(fet_parallel=4)
        self.assertGreater(bc.fet_path(d4, 200)["tj_worst_c"], self.r["fet_dsg"]["tj_worst_c"])


class TestDetailCalc(unittest.TestCase):
    def test_precharge_energy_independent_of_r(self):
        a = bc.precharge(29.2, 10e-3, 30)
        b = bc.precharge(29.2, 10e-3, 100)
        self.assertAlmostEqual(a["energy_j"], b["energy_j"])
        self.assertAlmostEqual(a["energy_j"], 0.5 * 10e-3 * 29.2 ** 2)
        self.assertAlmostEqual(a["i_peak_a"], 29.2 / 30)
        self.assertAlmostEqual(a["t95_s"], 0.9)

    def test_rc_corner(self):
        self.assertAlmostEqual(bc.rc_corner_hz(100, 0.1e-6), 15915.49, places=1)

    def test_ntc_divider_25c_is_half(self):
        self.assertAlmostEqual(bc.ntc_divider(25.0), 0.5)
        self.assertGreater(bc.ntc_divider(0.0), bc.ntc_divider(60.0))   # NTC: 温度越高电压越低

    def test_busbar(self):
        b = bc.busbar(200, 20, 2, 150, temp_c=20)
        self.assertAlmostEqual(b["j_a_per_mm2"], 5.0)
        self.assertAlmostEqual(b["r_uohm"], 1.72e-8 * 0.15 / 40e-6 * 1e6)

    def test_ipc2221_monotonic(self):
        self.assertGreater(bc.ipc2221_width_mm(5), bc.ipc2221_width_mm(3))
        self.assertGreater(bc.ipc2221_width_mm(3, oz=1), bc.ipc2221_width_mm(3, oz=2))
        self.assertGreater(bc.ipc2221_width_mm(3, external=False), bc.ipc2221_width_mm(3))

    def test_resistor_power(self):
        self.assertAlmostEqual(bc.resistor_power_w(0.058, 30), 0.10092)


class TestSwitchedCap(unittest.TestCase):
    def test_current_proportional_to_dv(self):
        a, b = bc.sc_equalizer(0.1)["i_a"], bc.sc_equalizer(0.3)["i_a"]
        self.assertAlmostEqual(b / a, 3.0)

    def test_default_design_point(self):
        r = bc.sc_equalizer(0.1)
        # R_SSL = 1/(50k*150µ) = 0.133Ω；R_FSL = 4*(0.036+0.042+0.055) = 0.532Ω（含 2 只保险丝冷阻）
        self.assertAlmostEqual(r["r_ssl_ohm"], 0.1333, places=3)
        self.assertAlmostEqual(r["r_fsl_ohm"], 0.532, places=3)
        self.assertAlmostEqual(r["i_a"], 0.1 / (0.1333 ** 2 + 0.532 ** 2) ** 0.5, places=3)
        self.assertGreater(r["i_a"], 0.17)

    def test_default_matches_design_input(self):
        self.assertAlmostEqual(bc.DesignInput().bal_current_a, round(bc.sc_equalizer(0.1)["i_a"], 2))

    def test_higher_freq_lower_resistance(self):
        self.assertLess(bc.sc_equalizer(0.1, f_khz=100)["r_eq_ohm"], bc.sc_equalizer(0.1)["r_eq_ohm"])


class TestMP2643(unittest.TestCase):
    def test_iubc_matches_datasheet_table(self):
        # 手册 EC 表：107k→2A, 215k→1A, 430k→0.5A
        self.assertAlmostEqual(bc.mp2643_iubc(107), 1.99, places=2)
        self.assertAlmostEqual(bc.mp2643_iubc(215), 0.99, places=2)
        self.assertAlmostEqual(bc.mp2643_iubc(430), 0.50, places=2)
        self.assertLess(bc.mp2643_iubc(120) * 1.1, 2.0 + 0.01)   # 120k 含 +10% 容差不超 2A

    def test_vcu_lim(self):
        # 手册：R1=2M, R2=402k → 7.17V
        self.assertAlmostEqual(bc.mp2643_vcu_lim(2000, 402), 7.17, places=2)
        self.assertGreater(bc.mp2643_vcu_lim(2000, 392), 7.3)   # 本设计 392k：允许 2×3.65V

    def test_inductor_table9(self):
        # 手册 Table 9：VCU=6.2 VCL=3 IUBC=2A L=2.2µH → Isat > 5.75A
        r = bc.mp2643_inductor(6.2, 3.0, 2.0, 2.2)
        self.assertGreater(r["ripple_a"], 0.5)
        self.assertLess(r["ripple_a"], 1.24)
        # 表中 Isat>5.75A 按纹波上限 1.24A 取：6.2/3×2 + 1.24/2 + 1 = 5.75；实际纹波更小，故应 ≤ 5.75
        self.assertLessEqual(r["isat_min_a"], 5.75)
        self.assertAlmostEqual(6.2 / 3 * 2 + 1.24 / 2 + 1, 5.75, places=2)


if __name__ == "__main__":
    unittest.main()
