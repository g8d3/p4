#!/usr/bin/env python3
"""q71: each relative-strength scan records BTC and ETH at scan time.

No network: the CoinGecko/DefiLlama calls are replaced with fixture rows, and
the scan writes to a temporary directory. Paper research only; no timers.
"""
import csv
import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(os.path.dirname(HERE), "scripts", "rstrength_scan.py")


def load_module():
    spec = importlib.util.spec_from_file_location("rstrength_scan_under_test", SCAN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def coin(cid, sym, price, r7, r30, mcap=1_000_000):
    return {"id": cid, "symbol": sym, "current_price": price,
            "price_change_percentage_7d_in_currency": r7,
            "price_change_percentage_30d_in_currency": r30,
            "market_cap": mcap, "total_volume": 1_000_000}


class ScanBaselineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mod = load_module()
        self.mod.CSV_PATH = os.path.join(self.tmp, "flags.csv")
        self.mod.SCAN_PATH = os.path.join(self.tmp, "scans.csv")
        self.mod.LOG_PATH = os.path.join(self.tmp, "scan.log")
        self.fixture = [
            coin("bitcoin", "btc", 60000.0, 1.0, 5.0, 1_200_000_000_000),
            coin("ethereum", "eth", 3000.0, 2.0, 4.0, 400_000_000_000),
            coin("solana", "sol", 150.0, -2.0, -10.0, 70_000_000_000),
            coin("token-x", "TOK", 2.5, 20.0, 10.0),
        ]

    def fake_world(self):
        mod = self.mod

        def markets(ids=None, category=None):
            if category:
                return []
            return [dict(c) for c in self.fixture]

        mod.markets = markets
        mod.defillama_fees = lambda: {}
        mod.get_json = lambda *a, **k: {"coins": []}
        mod.log = lambda _msg: None

    def read_scan(self):
        with open(self.mod.SCAN_PATH) as f:
            return list(csv.DictReader(f))

    def test_scan_writes_btc_eth_baseline_row(self):
        self.fake_world()
        self.assertEqual(self.mod.main(), 0)
        rows = self.read_scan()
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertEqual(float(row["btc_usd"]), 60000.0)
        self.assertEqual(float(row["eth_usd"]), 3000.0)
        self.assertEqual(float(row["sol_usd"]), 150.0)
        self.assertEqual(row["sol_ret_30d"], "-10.0")
        self.assertTrue(row["scan_at"], "scan timestamp must be recorded")
        # the fixture's TOK still becomes a normal paper flag; BTC is never a pick
        with open(self.mod.CSV_PATH) as f:
            flags = list(csv.DictReader(f))
        self.assertEqual([r["token"] for r in flags], ["TOK"], flags)

    def test_missing_baseline_is_blank_not_aborted(self):
        self.fixture = [c for c in self.fixture if c["id"] != "bitcoin"]
        self.fake_world()
        self.assertEqual(self.mod.main(), 0)
        row = self.read_scan()[0]
        self.assertEqual(row["btc_usd"], "")
        self.assertEqual(row["eth_usd"], "3000.0")

    def test_watchlist_has_no_btc_and_listener_never_sees_it(self):
        # BTC is a baseline only. WATCHLIST drives the listener's 1h coins dict,
        # mints() and fundamentals.refresh, so it must never contain bitcoin.
        self.assertNotIn("BTC", self.mod.WATCHLIST)
        self.assertNotIn("bitcoin", self.mod.WATCHLIST.values())
        self.assertEqual(self.mod.BASELINE, {"BTC": "bitcoin"})
        scripts = os.path.join(os.path.dirname(HERE), "scripts")
        sys.path.insert(0, scripts)
        try:
            import rstrength_listener as listener
        finally:
            sys.path.remove(scripts)
        self.assertNotIn("BTC", listener.scan.WATCHLIST)
        self.assertNotIn("bitcoin", listener.scan.WATCHLIST.values())
        self.assertNotIn("bitcoin", ",".join(listener.scan.WATCHLIST.values()),
                         "the listener's CoinGecko ids= and mints() must not ask for bitcoin")

    def test_same_timestamp_is_not_duplicated(self):
        self.assertTrue(self.mod.append_scan_row("2026-10-26T03:00:00-05:00", 60000, 3000, 150, -10))
        self.assertFalse(self.mod.append_scan_row("2026-10-26T03:00:00-05:00", 60001, 3001, 151, -9))
        rows = self.read_scan()
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["btc_usd"]), 60000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
