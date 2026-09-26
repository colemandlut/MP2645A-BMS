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
        self.assertLess(fet["tj_worst_c"], 125.0)       # 留 50°C 以上裕量 (Tj,max=175)
        self.assertLess(fet["p_path_w"], 25.0)

    def test_fet_path_resistance(self):
        # 1.2mΩ*1.7/8*2 = 0.51mΩ
        self.assertAlmostEqual(self.r["fet_dsg"]["r_path_mohm"], 0.51, places=3)

    def test_shunt_signal_levels(self):
        s = self.r["shunt"]
        self.assertAlmostEqual(s["v_at_dsg_mv"], 20.0)
        self.assertAlmostEqual(s["v_at_scp_mv"], 80.0)
        self.assertAlmostEqual(s["p_at_dsg_w"], 4.0)

    def test_active_balance_much_faster_than_passive(self):
        self.assertLess(self.r["bal_5pct_h"] * 10, self.r["bal_5pct_passive_h"])
        # 200Ah*5% = 10Ah / (3A*0.85) = 3.92h
        self.assertAlmostEqual(self.r["bal_5pct_h"], 10 / 2.55, places=3)

    def test_balance_time_rejects_negative(self):
        with self.assertRaises(ValueError):
            bc.balance_time_h(self.d, -1)

    def test_gate_turnoff(self):
        # 8*170nC = 1.36µC @1A -> 1.36µs
        self.assertAlmostEqual(bc.gate_turnoff_us(self.d, 1.0), 1.36, places=3)

    def test_fewer_fets_gets_hotter(self):
        d4 = bc.DesignInput(fet_parallel=4)
        self.assertGreater(bc.fet_path(d4, 200)["tj_worst_c"], self.r["fet_dsg"]["tj_worst_c"])


if __name__ == "__main__":
    unittest.main()
