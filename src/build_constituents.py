"""Build data/constituents.csv from the raw FTSE 250 list.

Converts LSE EPIC codes to Yahoo Finance tickers (append '.L') and flags
investment trusts, funds and REITs, which do not have meaningful operating
margins. The dashboard excludes funds by default so the comparison stays like
for like. This is a deliberate analyst choice, documented in the README.

Source of the raw list: Wikipedia, FTSE 250 constituents after the 21 April
2026 review. Re-run update_constituents.py to refresh after a quarterly review.
"""
import csv
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "constituents_raw.tsv")
OUT = os.path.join(HERE, "data", "constituents.csv")

FUND_SECTOR_HINTS = (
    "investment trust", "collective investments", "hedge funds",
    "equity investments", "general financial",
)
FUND_NAME_HINTS = (
    "trust", "fund", " investments", "investment company", "vct",
    "capital partners", "private equity", "infrastructure",
)


def is_fund(name: str, sector: str) -> bool:
    s, n = sector.lower(), name.lower()
    if any(h in s for h in FUND_SECTOR_HINTS):
        return True
    if any(h in n for h in FUND_NAME_HINTS):
        return True
    return False


def yahoo_ticker(epic: str) -> str:
    # LSE EPIC to Yahoo symbol: strip spaces/dots, append '.L'.
    return epic.strip().replace(".", "").replace(" ", "") + ".L"


def main():
    rows = []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            name, epic, sector = line.split("\t")
            rows.append({
                "name": name.strip(),
                "epic": epic.strip(),
                "yahoo_ticker": yahoo_ticker(epic),
                "sector": sector.strip(),
                "is_fund": is_fund(name, sector),
            })
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "epic", "yahoo_ticker", "sector", "is_fund"])
        w.writeheader()
        w.writerows(rows)
    funds = sum(r["is_fund"] for r in rows)
    print(f"Wrote {len(rows)} constituents to {OUT}")
    print(f"  operating companies: {len(rows) - funds}")
    print(f"  funds / trusts (excluded from margins by default): {funds}")


if __name__ == "__main__":
    main()
