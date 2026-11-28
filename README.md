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

Then open the local address Streamlit prints (usually http://localhost:8501). After pulling changes to the engine (`src/`), stop the app with Ctrl+C and start it again: Streamlit reloads the app folder by itself, but not the installed `scanner` package. Always start it from the repository root, so the app picks up its theme in `.streamlit/config.toml`.

The app has three screens:

- **Scan**: pick one ticker for a single report, or several to compare, up to every stock ("All stocks" quick pick; a full-market scan takes about 2 minutes, with a progress bar). Choose the price data (open dataset, your CSV files, or both), adjust settings, and reopen recent scans from this session.
- **Results**: one stock. Summary tiles, the next window to open, and tabs for patterns, exit or avoid windows, heatmap, calendar, year-by-year detail, chance check, all windows and method. Exports: CSV, PDF and run details (JSON).
- **Compare**: several stocks. Filter out frozen-price stocks or stocks with no rising pattern, and sort by Tier 1 count, best median, chance check, exit windows or ticker. Up to 6 stocks show as cards with a window-by-window table; more show as a sortable stock table and a ranked pattern list (click a row to open that stock). The seasonal map and the chance check appear in both. Filters only change what is shown: exports and the chance check always cover every stock scanned.

Company names and sectors come from [src/scanner/data/securities.csv](src/scanner/data/securities.csv), kept by hand for now. A ticker that is not listed still scans; it just shows without a name.

## Public site (invest.bolujo.com)

A static version of the app for visitors lives in [site/](site/): plain HTML, CSS and JavaScript, no server. At build time `python -m scanner.publish` scans every stock with the default settings and writes JSON to `site/data/`; the page reads those files. It publishes returns and statistics only, never closing prices (see docs/SCOPE.md 7.3). Visitors can pick stocks, open single-stock results and compare any number of stocks with filters; they cannot upload files or change settings. The Streamlit app stays the full research tool.

**Year roadmap** (`#/roadmap`): visitors add stocks from Compare (one at a time, or every stock shown after filtering) or from a stock's report. Each stock starts with its Tier 1 and Tier 2 windows, leaving out any that overlap a stronger one; Watch and Emerging windows can be switched on per stock. Twelve month boxes show what to buy, hold and sell each month, with the stock's exit-or-avoid months as warnings (hidden in months where that stock is planned). The plan is kept in the visitor's browser (`localStorage`) for a chosen year and exports as CSV, a calendar file (`.ics`, all-day Buy and Sell events) or print/PDF. A share link (`#/roadmap/2027/FCMB:10.3,ETI:12.2`, i.e. ticker and `start_month.length` keys) opens the same plan read-only, with an option to save it. The date logic lives in [site/roadmap.js](site/roadmap.js) and is tested with `node --test 'tests/site/*.test.mjs'`.

Build and preview locally:

```bash
bash scripts/build_site.sh            # about 2 minutes; writes site/data/
python -m http.server 8600 -d site    # then open http://localhost:8600
```

### Cloudflare setup (one time)

The site is a Cloudflare Worker with static assets, configured by [wrangler.jsonc](wrangler.jsonc).

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Import a repository** → choose `ini-hub/Investment-Patterns`. Project name: `investment-patterns` (it must match `name` in wrangler.jsonc).
2. In the Worker → **Settings** → **Build**:
   - Branch: `main`
   - Build command: leave empty. `wrangler deploy` runs `bash scripts/build_site.sh` itself (the `build` block in wrangler.jsonc); without that step the page deploys with no `data/` and shows "data/index.json: HTTP 404"
   - Deploy command: `npx wrangler deploy`
   - Non-production branch deploy command: `npx wrangler preview` (the default; it builds a preview for each pull request and needs the `previews` block in wrangler.jsonc)
   - Root directory: leave empty
   - Build variables: `PYTHON_VERSION` = `3.12`
3. Deploy. A build takes about 4 to 7 minutes. In the log, `[custom build]` lines show the scan, then `Site ready in site/ (147 stocks)`, then the asset upload (about 150 files).
4. In the Worker → **Settings** → **Domains & Routes** → **Add** → **Custom domain** → `invest.bolujo.com`. With bolujo.com on Cloudflare, the DNS record and SSL certificate are created for you.

Every merge to `main` rebuilds the site. [site/_headers](site/_headers) sets security headers and data caching.

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

universe = load_universe()  # downloads the pinned snapshot on first use
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
pytest tests/integration     # app smoke tests: each screen renders (needs the dataset)
ruff check . && ruff format --check .   # lint, as CI runs it
```

- The regression suite holds the research results from 26 November 2026 (Appendix A of the scope) and six prices verified against published sources. If a code change moves any of those numbers, the build fails.
- CI runs all three suites on Python 3.11 and 3.12 for every push and pull request.

## Project layout

```
app/streamlit_app.py        web app entry: navigation and top bar
app/views/                  Scan, Results and Compare screens
app/state.py, app/ui.py     shared session state and visual components
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
