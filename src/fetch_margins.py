"""Fetch FTSE 250 income statements from Yahoo Finance and compute margins.

Reads data/constituents.csv, pulls the annual income statement for each
operating company, computes gross, operating and net margin for every year
available, and writes two tidy files the Power BI dashboard reads:

    data/margins_history.csv   one row per company per fiscal year (long format)
    data/margins_latest.csv    the most recent fiscal year per company

Funds and investment trusts are skipped by default because they do not have
operating margins. Pass --include-funds to override.

Run:
    python src/fetch_margins.py                 # all operating companies
    python src/fetch_margins.py --limit 15      # quick test on the first 15
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import sys
import time

import pandas as pd
import yfinance as yf

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
CONSTITUENTS = os.path.join(DATA, "constituents.csv")
HISTORY_OUT = os.path.join(DATA, "margins_history.csv")
LATEST_OUT = os.path.join(DATA, "margins_latest.csv")
LOG_OUT = os.path.join(DATA, "fetch_log.txt")

# Yahoo income-statement line items we look for. Yahoo occasionally renames
# rows, so each field lists the labels we accept, in order of preference.
FIELD_LABELS = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "gross_profit": ["Gross Profit"],
    "operating_income": ["Operating Income", "Operating Income Or Loss", "EBIT"],
    "net_income": ["Net Income", "Net Income Common Stockholders",
                   "Net Income From Continuing Operation Net Minority Interest"],
}


def log(msg: str, fh) -> None:
    line = f"{dt.datetime.utcnow().isoformat(timespec='seconds')}Z  {msg}"
    print(line)
    fh.write(line + "\n")


def pick_row(df: pd.DataFrame, labels: list[str]):
    for lab in labels:
        if lab in df.index:
            return df.loc[lab]
    return None


def safe_num(series, col):
    if series is None:
        return None
    try:
        v = series.get(col)
        if v is None or pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


def fetch_one(row: dict, retries: int, fh) -> list[dict]:
    ticker = row["yahoo_ticker"]
    out = []
    for attempt in range(1, retries + 1):
        try:
            tk = yf.Ticker(ticker)
            df = tk.income_stmt  # annual, most recent columns first
            if df is None or df.empty:
                raise ValueError("empty income statement")
            currency = None
            try:
                currency = (tk.get_info() or {}).get("financialCurrency")
            except Exception:
                currency = None

            revenue = pick_row(df, FIELD_LABELS["revenue"])
            gross = pick_row(df, FIELD_LABELS["gross_profit"])
            oper = pick_row(df, FIELD_LABELS["operating_income"])
            net = pick_row(df, FIELD_LABELS["net_income"])

            for col in df.columns:
                rev = safe_num(revenue, col)
                if not rev:  # no revenue means no meaningful margin
                    continue
                gp = safe_num(gross, col)
                oi = safe_num(oper, col)
                ni = safe_num(net, col)
                fy = col.year if hasattr(col, "year") else str(col)
                out.append({
                    "name": row["name"],
                    "epic": row["epic"],
                    "yahoo_ticker": ticker,
                    "sector": row["sector"],
                    "fiscal_year": fy,
                    "currency": currency or "",
                    "revenue": round(rev, 0),
                    "gross_profit": round(gp, 0) if gp is not None else "",
                    "operating_income": round(oi, 0) if oi is not None else "",
                    "net_income": round(ni, 0) if ni is not None else "",
                    "gross_margin": round(gp / rev, 4) if gp is not None else "",
                    "operating_margin": round(oi / rev, 4) if oi is not None else "",
                    "net_margin": round(ni / rev, 4) if ni is not None else "",
                    "retrieved_at": dt.date.today().isoformat(),
                })
            log(f"OK   {ticker:8s} {row['name'][:32]:32s} {len(out)} years", fh)
            return out
        except Exception as e:
            if attempt < retries:
                time.sleep(2 * attempt)
                continue
            log(f"FAIL {ticker:8s} {row['name'][:32]:32s} {e}", fh)
            return []
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only the first N companies")
    ap.add_argument("--include-funds", action="store_true", help="do not skip funds")
    ap.add_argument("--sleep", type=float, default=1.0, help="pause between tickers (s)")
    ap.add_argument("--retries", type=int, default=3)
    args = ap.parse_args()

    with open(CONSTITUENTS, encoding="utf-8") as f:
        companies = list(csv.DictReader(f))
    if not args.include_funds:
        companies = [c for c in companies if c["is_fund"].strip().lower() != "true"]
    if args.limit:
        companies = companies[: args.limit]

    all_rows: list[dict] = []
    ok = fail = 0
    with open(LOG_OUT, "w", encoding="utf-8") as fh:
        log(f"Starting fetch of {len(companies)} companies", fh)
        for i, c in enumerate(companies, 1):
            rows = fetch_one(c, args.retries, fh)
            if rows:
                all_rows.extend(rows)
                ok += 1
            else:
                fail += 1
            if i % 25 == 0:
                log(f"...progress {i}/{len(companies)} (ok {ok}, fail {fail})", fh)
            time.sleep(args.sleep)
        log(f"Done. companies ok {ok}, failed {fail}, rows {len(all_rows)}", fh)

    if not all_rows:
        print("No data fetched. See data/fetch_log.txt", file=sys.stderr)
        sys.exit(1)

    hist = pd.DataFrame(all_rows).sort_values(["name", "fiscal_year"])
    hist.to_csv(HISTORY_OUT, index=False)

    latest = (hist.sort_values("fiscal_year")
                  .groupby("yahoo_ticker", as_index=False)
                  .tail(1)
                  .sort_values("name"))
    latest.to_csv(LATEST_OUT, index=False)
    print(f"Wrote {HISTORY_OUT} ({len(hist)} rows)")
    print(f"Wrote {LATEST_OUT} ({len(latest)} rows)")


if __name__ == "__main__":
    main()
