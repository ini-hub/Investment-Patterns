# Investment Patterns

A seasonal pattern scanner for NGX stocks. Enter a ticker and the tool tests every calendar window to find the ones that repeat year after year, the ones that repeatedly fall, and the data problems that make a pattern unreliable. The windows are:

- single months
- rolling 2-month windows
- rolling 3-month windows, which include the standard quarters
- the full year

This is Phase 1 of the plan in [docs/SCOPE.md](docs/SCOPE.md).

> Research tool, not investment advice. Past seasonal behaviour does not guarantee future results.

## What it does

- **37 windows per stock**: 12 single months, 12 rolling 2-month windows and 12 rolling 3-month windows (both include windows that cross the year end, such as Nov-Jan), plus the full year.
- **Per-window statistics**:
  - years up and current streak
  - median, mean, worst year (minimum gain), best year (maximum gain), standard deviation and variance
  - years it beat the market
  - years it beat the stock's own average window that year, which strips out the stock's general trend
  - the dip from entry inside the window
- **Classes**: Tier 1, Tier 2, Watch, Emerging, Negative (exit or avoid), None, Insufficient history. A window with fewer than 8 years can still show as Emerging, with an "Insufficient history" flag. On frozen-price stocks every classified window is marked "Unreliable".
- **Chance check**: monthly returns are shuffled within each year to show how many "patterns" appear by luck alone.
- **Data-quality warnings**: frozen prices, large one-day moves, gaps, missing years, stale data, and ex-dividend months (when you supply the dates).
- **Report views**: patterns, exit or avoid windows, heatmap, calendar of upcoming windows, year-by-year detail, and method.
- **Exports**: statistics CSV, year-by-year CSV, a PDF report and a run-details JSON. Every export records the data hash, code version and settings, so a result can be traced and reproduced.

## Quick start

```bash
git clone https://github.com/ini-hub/Investment-Patterns.git
cd Investment-Patterns
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
streamlit run app/streamlit_app.py
```

Then open the local address Streamlit prints, type a ticker (for example `FCMB`, or `FCMB, VITAFOAM, ETI`) and press **Run scan**.

## Data sources

| Source | How to use it |
|---|---|
| Open NGX dataset ([NairaDB](https://github.com/kennybix/NairaDB)) | Selected by default. About 147 NGX stocks, daily unadjusted closes from December 2015 to 19 December 2025. It has no licence file, so it is **not stored in this repository**: the app downloads it on first run into `data/nairadb/` (ignored by git), pinned to commit `4de805b` so results are reproducible. Needs `git` installed. |
| Your own CSV files | Choose "My CSV files" or "Both" in the sidebar and upload one file per stock. TradingView's *Export chart data* works as is. |
| Index CSV (optional) | Upload, for example, the NGX All-Share Index to use it as the benchmark instead of the market average. |
| Ex-dividend dates (optional) | Paste `TICKER, YYYY-MM-DD` lines in the sidebar. Windows that cover those months get a note, because prices are unadjusted. |

### CSV format

- **File name:** the ticker is read from the file name. For example, `NSENG_FCMB, 1D.csv` becomes `FCMB` and `fcmb.csv` becomes `FCMB`.
- **Columns:**
  - a date column named `date`, `time` or `timestamp`, in `YYYY-MM-DD`, `DD/MM/YYYY` or Unix-seconds format
  - a close column named `close`, `price` or `last`
  - optionally, a volume column named `volume` or `vol`
- **Cleaning on import:**
  - rows with zero, negative or unreadable prices are rejected and listed
  - for duplicate dates, the last row is kept
  - gaps longer than 10 business days are reported

To use a local copy of the dataset instead of downloading it, set `NAIRADB_PATH` to the folder that holds the `*_history.json` files.

## Method in brief

- **Month-end price:** the last available daily close in each month.
- **Window return:** the month-end close of the window's last month divided by the month-end close of the month before it starts, minus 1. A window is labelled by the year it starts in.
- **Complete windows only:** a month counts as complete when the data reaches its last business day.
- **Market benchmark:** a 10% trimmed mean of all stocks in the dataset for the same window and year. A median is not used, because most NGX stocks show 0% in many months.
- **Full definitions and thresholds:** [docs/SCOPE.md](docs/SCOPE.md), section 8, and the *Method* tab in the app.

Default thresholds are in [src/scanner/default.yaml](src/scanner/default.yaml). You can change them in the app sidebar or with a settings file (see [config/example-overrides.yaml](config/example-overrides.yaml)).

## Using the engine in code

```python
from scanner.config import load_config
from scanner.data import load_universe
from scanner.engine import MarketBenchmark, scan_ticker

universe = load_universe()                  # downloads the pinned snapshot on first use
benchmark = MarketBenchmark(universe)
result = scan_ticker("FCMB", universe["FCMB"], benchmark, load_config())

print(result.stats[["window", "class", "up", "n", "streak", "median"]].head(10))
print(result.quality.warnings())
print(result.permutation)
```

## Tests

```bash
pytest                       # everything
pytest tests/unit            # fast, no data needed
pytest tests/regression      # checks results against the research baseline (downloads the dataset)
pytest tests/features        # Gherkin acceptance scenarios
```

- The regression suite holds the research results from 26 November 2026 (Appendix A of the scope) and six prices verified against published sources. If a code change moves any of those numbers, the build fails.
- CI runs all three suites on Python 3.11 and 3.12 for every push and pull request.

## Project layout

```
app/streamlit_app.py        web app
src/scanner/data/           CSV and dataset loaders, validation
src/scanner/engine/         windows, statistics, benchmarks, classification, chance check, quality
src/scanner/report/         tables, heatmap, calendar, CSV and PDF export, method text
tests/unit/                 unit and property-based tests
tests/regression/           baseline results and verified prices
tests/features/             Gherkin specifications and step definitions
docs/SCOPE.md               full project scope
```

## Known limitations (Phase 1)

- The open dataset ends on 19 December 2025. To scan 2026, upload your own CSV files.
- Prices are unadjusted for dividends and bonus issues.
- Trading costs, slippage, daily price limits and liquidity are not modelled. They arrive with the Monte Carlo module in Phase 4.
- Calendar dates use the last business day of each month. NGX public holidays are not modelled.
