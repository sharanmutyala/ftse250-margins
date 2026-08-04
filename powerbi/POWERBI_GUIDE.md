# Power BI dashboard: FTSE 250 margins

This connects Power BI Desktop directly to the CSVs in this repo. Because it
reads the raw GitHub URL, the dashboard refreshes to the latest data every time
you hit Refresh, and the GitHub Action keeps that data current.

Replace `YOURUSERNAME` below with your GitHub username throughout.

## 1. Populate the data once

If you have not run the fetch yet, do it first so the CSVs are not empty:

```
pip install -r requirements.txt
python src/build_constituents.py
python src/fetch_margins.py            # 151 companies, a few minutes
```

Or just run the GitHub Action once (Actions tab, "Refresh FTSE 250 margins",
Run workflow) and let it commit the data for you.

## 2. Connect Power BI to the data

1. Open Power BI Desktop. Home, Get Data, Web.
2. Paste the raw URL of the history file:
   `https://raw.githubusercontent.com/YOURUSERNAME/ftse250-margins/main/data/margins_history.csv`
3. In the preview, click Transform Data to open Power Query.
4. Confirm the column types: set `gross_margin`, `operating_margin`,
   `net_margin` to Decimal Number, `revenue` and the income columns to Decimal
   Number, `fiscal_year` to Whole Number, and `is_fund` handling is not needed
   here because funds are already excluded.
5. Home, Close and Apply.

Do the same for `margins_latest.csv` if you want a separate latest-year table,
but one history table is enough to build everything.

## 3. Measures (DAX)

Create these as measures (right-click the table, New measure). They make the
visuals respond to whatever year or sector is selected.

```DAX
Avg Operating Margin = AVERAGE ( margins_history[operating_margin] )

Median Operating Margin =
MEDIAN ( margins_history[operating_margin] )

Avg Net Margin = AVERAGE ( margins_history[net_margin] )

Companies = DISTINCTCOUNT ( margins_history[yahoo_ticker] )

Latest Year = MAX ( margins_history[fiscal_year] )

Operating Margin YoY =
VAR cy = MAX ( margins_history[fiscal_year] )
VAR thisyr =
    CALCULATE ( AVERAGE ( margins_history[operating_margin] ),
        margins_history[fiscal_year] = cy )
VAR lastyr =
    CALCULATE ( AVERAGE ( margins_history[operating_margin] ),
        margins_history[fiscal_year] = cy - 1 )
RETURN thisyr - lastyr
```

## 4. Suggested layout

A single page does the job:

- Slicer: `fiscal_year` (set to the latest year by default).
- Slicer: `sector`.
- Cards: `Companies`, `Avg Operating Margin`, `Median Operating Margin`,
  `Operating Margin YoY`.
- Bar chart: top and bottom 15 companies by `operating_margin` (use a Top N
  filter on the visual). Axis `name`, value `operating_margin`.
- Bar chart: `Avg Operating Margin` by `sector`, sorted descending. This is the
  headline view, which sectors run fat margins and which run thin.
- Line chart: `Avg Operating Margin` by `fiscal_year`, to show the trend.
- Table: `name`, `sector`, `revenue`, `gross_margin`, `operating_margin`,
  `net_margin`, with conditional formatting (data bars) on the margin columns.

Format the three margin columns as percentages (they are stored as fractions,
so 0.087 shows as 8.7%).

## 5. Keep it fresh

- The GitHub Action refreshes the CSVs every Monday.
- In Power BI Desktop, just click Refresh to pull the newest data.
- If you publish to the Power BI Service, set up a Scheduled Refresh on the
  dataset so the online dashboard updates without you opening the file.

## Note on the data

Margins are computed from company income statements sourced via Yahoo Finance,
which aggregates published annual filings. Investment trusts, funds and similar
vehicles are excluded because they do not have operating margins, so every
company shown is a like-for-like operating business.
