"""Refresh the FTSE 250 constituent list from Wikipedia.

The index is reviewed every quarter, so members change. This script pulls the
current constituents table, writes data/constituents_raw.tsv, then rebuilds
constituents.csv. Run it after each quarterly review (March, June, Sept, Dec).

    python src/update_constituents.py

Needs internet, so run it locally or let the GitHub Action do it. If Wikipedia
changes its table layout, fix the column names in COLS below.
"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "constituents_raw.tsv")
URL = "https://en.wikipedia.org/wiki/FTSE_250_Index"
COLS = ("Company", "Ticker")


def main():
    tables = pd.read_html(URL)
    # the constituents table is the one with both a Company and a Ticker column
    target = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any(COLS[0] in c for c in cols) and any(COLS[1] in c for c in cols):
            target = t
            break
    if target is None:
        raise SystemExit("Could not find the constituents table. Check the page layout.")

    target.columns = [str(c) for c in target.columns]
    name_col = next(c for c in target.columns if COLS[0] in c)
    tick_col = next(c for c in target.columns if COLS[1] in c)
    sect_col = next((c for c in target.columns if "sector" in c.lower() or "Benchmark" in c), None)

    with open(RAW, "w", encoding="utf-8") as f:
        for _, r in target.iterrows():
            name = str(r[name_col]).strip()
            tick = str(r[tick_col]).strip()
            sect = str(r[sect_col]).strip() if sect_col else ""
            if not name or name.lower() == "nan":
                continue
            f.write(f"{name}\t{tick}\t{sect}\n")
    print(f"Wrote {RAW}. Now run: python src/build_constituents.py")


if __name__ == "__main__":
    main()
