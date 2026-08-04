"""Offline test of the margin transform.

Mocks Yahoo's income-statement shape so we can prove the maths and the row
selection without any network access. Run: python tests/test_transform.py
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import fetch_margins as fm


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    @property
    def income_stmt(self):
        cols = [pd.Timestamp("2025-12-31"), pd.Timestamp("2024-12-31")]
        # Greggs-like FY2025: revenue 2151.2, operating 187.5 (8.71%),
        # net 122.2 (5.68%); gross 800 (37.2%). Values in millions for the test.
        data = {
            cols[0]: {"Total Revenue": 2151.2, "Gross Profit": 800.0,
                       "Operating Income": 187.5, "Net Income": 122.2},
            cols[1]: {"Total Revenue": 2014.4, "Gross Profit": 770.0,
                       "Operating Income": 195.3, "Net Income": 153.4},
        }
        return pd.DataFrame(data)

    def get_info(self):
        return {"financialCurrency": "GBP"}


def approx(a, b, tol=1e-4):
    return abs(a - b) <= tol


def main():
    fm.yf.Ticker = FakeTicker  # monkeypatch the network call
    row = {"name": "Test Co", "epic": "TST", "yahoo_ticker": "TST.L",
           "sector": "Food & Drug Retailers", "is_fund": "False"}

    class NullLog:
        def write(self, *_):
            pass

    out = fm.fetch_one(row, retries=1, fh=NullLog())

    assert len(out) == 2, f"expected 2 years, got {len(out)}"
    y25 = next(r for r in out if r["fiscal_year"] == 2025)

    checks = {
        "revenue": (y25["revenue"], 2151.0),
        "operating_margin": (y25["operating_margin"], round(187.5 / 2151.2, 4)),
        "net_margin": (y25["net_margin"], round(122.2 / 2151.2, 4)),
        "gross_margin": (y25["gross_margin"], round(800.0 / 2151.2, 4)),
        "currency": (y25["currency"], "GBP"),
    }
    for k, (got, exp) in checks.items():
        if isinstance(exp, float):
            assert approx(got, exp), f"{k}: got {got}, expected {exp}"
        else:
            assert got == exp, f"{k}: got {got}, expected {exp}"
        print(f"  ok  {k:18s} = {got}")

    # a company with no Gross Profit row should yield blank gross margin, not crash
    class NoGross(FakeTicker):
        @property
        def income_stmt(self):
            df = super().income_stmt
            return df.drop(index="Gross Profit")

    fm.yf.Ticker = NoGross
    out2 = fm.fetch_one(row, retries=1, fh=NullLog())
    assert out2[0]["gross_margin"] == "", "missing gross profit should be blank"
    print("  ok  missing gross profit handled gracefully")

    print("\nALL TRANSFORM TESTS PASSED")


if __name__ == "__main__":
    main()
