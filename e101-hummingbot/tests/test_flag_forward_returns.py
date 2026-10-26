#!/usr/bin/env python3
"""Tiny fixture test for scripts/flag_forward_returns.py (no network, paper only)."""
import csv
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "flag_forward_returns.py")


def load_module():
    spec = importlib.util.spec_from_file_location("flag_forward_returns_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ForwardReturnsTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.tmp = tempfile.mkdtemp()
        self.flags = os.path.join(self.tmp, "flags.csv")
        self.series = os.path.join(self.tmp, "series.csv")
        rows = [
            ("2026-10-25T10:00:00-05:00", "X", 100),
            ("2026-10-25T11:00:00-05:00", "X", 110),
            ("2026-10-25T12:00:00-05:00", "X", 121),
            ("2026-10-25T13:00:00-05:00", "X", 100),
            ("2026-10-25T14:00:00-05:00", "X", 90),
            ("2026-10-25T15:00:00-05:00", "X", 108),
            ("2026-10-25T16:00:00-05:00", "X", 120),
            ("2026-10-26T10:00:00-05:00", "X", 130),
            ("2026-10-26T12:00:00-05:00", "X", 140),
        ]
        with open(self.series, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts", "token", "price", "vol_m5", "vol_h1", "liq_usd"])
            for ts, tok, p in rows:
                w.writerow([ts, tok, p, 1, 1, 1000])
        with open(self.flags, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts", "kind", "token", "rule", "price"])
            w.writerow(["2026-10-25T10:00:00-05:00", "COIN", "X", "UP", 100])
            w.writerow(["2026-10-25T12:00:00-05:00", "COIN", "X", "DOWN", 121])
            w.writerow(["2026-10-25T17:00:00-05:00", "COIN", "C", "UP", 5])  # no series

    def rows(self):
        flags = self.mod.load_flags(self.flags)
        series = self.mod.load_series(self.series)
        return self.mod.summarize(flags, series, horizons=(1, 4, 24), draws=5, seed=3)

    def find(self, rows, rule, horizon):
        return next(r for r in rows if r["rule"] == rule and r["horizon"] == horizon)

    def test_forward_returns_medians_hits_and_missing(self):
        rows = self.rows()
        up1 = self.find(rows, "UP", 1)
        self.assertEqual(up1["flag"]["n"], 1)
        self.assertAlmostEqual(up1["flag"]["median"], 10.0)
        self.assertEqual(up1["flag"]["hit"], 100.0)
        up4 = self.find(rows, "UP", 4)
        self.assertAlmostEqual(up4["flag"]["median"], -10.0)
        self.assertEqual(up4["flag"]["hit"], 0.0)
        up24 = self.find(rows, "UP", 24)
        self.assertAlmostEqual(up24["flag"]["median"], 30.0)
        down1 = self.find(rows, "DOWN", 1)
        self.assertAlmostEqual(down1["flag"]["median"], -17.36, places=2)
        down4 = self.find(rows, "DOWN", 4)
        self.assertAlmostEqual(down4["flag"]["median"], -0.83, places=2)
        # token C has no series: never counted
        self.assertEqual(self.find(rows, "UP", 1)["flag"]["n"], 1)
        # baseline draws exist where the flag has a horizon and are labelled small
        self.assertGreater(up1["base"]["n"], 0)
        self.assertEqual(up1["verdict"], "too small")

    def test_tolerance_and_no_data(self):
        self.mod.TOL = self.mod.timedelta(minutes=10)
        series = self.mod.load_series(self.series)
        inside = self.mod.forward_at(series, "X", {"ts": self.mod.parse_ts("2026-10-25T10:00:00-05:00"), "token": "X", "price": 100}, 1)
        self.assertIsNotNone(inside)
        outside = self.mod.forward_at(series, "X", {"ts": self.mod.parse_ts("2026-10-25T10:00:00-05:00"), "token": "X", "price": 100}, 25)
        self.assertIsNone(outside, "no +25h sample in the fixture")

    def test_markdown_has_the_table_and_no_fake_confidence(self):
        md = self.mod.markdown(self.rows(), 3, 1, (1, 4, 24))
        self.assertIn("| Rule | Horizon |", md)
        self.assertIn("too small", md)
        self.assertIn("draws are not independent", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
