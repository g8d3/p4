#!/usr/bin/env python3
"""Swing-math unit tests on synthetic series. Run with ../.venv/bin/python."""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "bin"))
from compute import mkey, pct, median, swings


def series(points):
    return {mkey(y, m): {"p": p, "cape": None} for (y, m, p) in points}


def test_fear_and_relief():
    h = series([(2022, 1, 100), (2022, 6, 110), (2022, 10, 88),
                (2023, 3, 100), (2023, 10, 115)])
    a, b, tk = swings(h, mkey(2022, 11))
    assert a["depth_pct"] == round(100 * (88 - 110) / 110, 2), a
    assert a["months"] == 4, a
    assert b["height_pct"] == round(100 * (115 - 88) / 88, 2), b
    assert b["months"] == 12, b
    print("fear+relief ok")


def test_no_dip_is_null():
    h = series([(2022, m, 100 + m) for m in range(1, 13)] + [(2023, m, 112 + m) for m in range(1, 13)])
    a, b, tk = swings(h, mkey(2022, 11))
    assert a is None, a  # monotonic rise: no fear swing, must be null not zero
    assert b is not None, b
    print("no-dip-null ok")


def test_median():
    assert median([3, 1, 2]) == 2
    assert median([4, 1, 2, 3]) == 2.5
    assert median([]) is None
    assert median([None, 5]) == 5
    assert pct(100, 130) == 30.0
    print("median+pct ok")


if __name__ == "__main__":
    test_fear_and_relief()
    test_no_dip_is_null()
    test_median()
    print("all tests pass")
