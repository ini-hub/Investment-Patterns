# NGX Seasonal Pattern Scanner: Full Project Scope

| Item | Detail |
|---|---|
| Document | Project scope, version 1.0 |
| Date | 26 November 2026 |
| Owner | Bolujo Excellent |
| Status | Phase 1 in build |
| Repository | github.com/ini-hub/Investment-Patterns |

---

## 1. Purpose

The NGX Seasonal Pattern Scanner is a standalone web tool. A user enters an NGX ticker symbol, and the tool:

1. Measures how the stock has performed in every calendar window over the available history: single months, rolling 2-month and 3-month windows (which include the standard quarters), and the full year.
2. Identifies windows that repeat consistently, beat the market, and are not explained by the stock's general trend.
3. Identifies windows that repeatedly lose value (exit or avoid windows).
4. Flags data-quality problems that make a pattern unreliable.
5. Produces a report that can be shared.

In later phases, the tool adds a live data feed, watchlist alerts and a Monte Carlo module. That module turns a validated pattern into concrete entry, target, stop and position-size rules.

The tool supports research and decision-making. It does not place trades and does not give investment advice.

---

## 2. Background

This scope comes from a research session on 25 and 26 November 2026. In that session, the scan was run manually on 13 NGX stocks using daily closing prices from December 2015 to 19 December 2025.

Key findings that shaped the design:

- **The strongest repeatable effect is market-wide.** The average NGX stock rose in December in 8 of 9 years and from November to January in 7 of 9 years (median +8.7%). It fell in March in 9 of 10 years.
- **Some stocks amplify that cycle consistently.** Examples: FCMB from October to December (9 of 9 years up) and Vitafoam from November to January (8 of 9 years up, median +31.9%).
- **Chance produces many apparent patterns.** A permutation test found 15 qualifying patterns against an average of about 9.5 to 9.7 expected from random data. About 12% of random runs matched or beat the real count. The tool must therefore show statistical context, not just hit rates.
- **Unadjusted prices produce false negative patterns** around ex-dividend dates. Examples: Vitafoam in February, Learn Africa in September.
- **Some stocks had frozen prices** for long periods (CWG and FTN Cocoa from 2016 to 2020). Their patterns are not reliable.

Appendix A holds the full baseline results. They also serve as regression fixtures for testing.

---

## 3. Goals and non-goals

### 3.1 Goals

| ID | Goal |
|---|---|
| G1 | Reproduce the manual research analysis for any NGX ticker in a single action |
| G2 | Make every number traceable to source prices and a stated method |
| G3 | Separate genuine seasonal behaviour from market-wide moves, the stock's own trend and chance |
| G4 | Warn the user clearly when data is insufficient or unreliable |
| G5 | Produce shareable reports (link, PDF, CSV) |
| G6 | Extend, in later phases, to live data, alerts and Monte Carlo simulation |

### 3.2 Non-goals

| ID | Out of scope |
|---|---|
| N1 | Placing orders, connecting to brokers or automated trading |
| N2 | Intraday analysis or real-time streaming prices |
| N3 | Buy or sell recommendations. The tool reports historical statistics only. |
| N4 | US stocks, ETFs or XAUUSD in the initial phases. The design must allow adding them later (see Section 13). |
| N5 | Pulling data automatically from TradingView or any source whose terms forbid it |

---

## 4. Users

| User type | Phase | Needs |
|---|---|---|
| Owner (single user) | 1 to 2 | Run scans, compare stocks, export results |
| Invited viewers | 3 | Open shared report links without editing |
| Registered users (private group or public) | 3+ | Own watchlists, alerts and saved reports. Depends on the data licence (Section 7.3). |

---

## 5. Delivery phases

| Phase | Name | Scope | Exit criteria |
|---|---|---|---|
| 1 | Prototype | Analysis engine, CSV import, optional loader for the open dataset, Streamlit app, report views, CSV and PDF export, test suite | All Phase 1 acceptance criteria pass. Results match Appendix A within tolerance. |
| 2 | Live data | NGX end-of-day API client, database, nightly update job, market benchmark from the full market or the NGX All-Share Index | Nightly job runs unattended for 10 consecutive trading days with data validation passing |
| 3 | Sharing and alerts | Persistent report links, user accounts, watchlists, alert delivery (email first, then Telegram or WhatsApp Business) | Shared link opens for a logged-out viewer. Alert fires correctly in test scenarios. |
| 4 | Simulation | Monte Carlo module, cost and liquidity model, position sizing | Simulation outputs reproducible with a fixed seed. Validated against analytical cases. |

Each phase is delivered on its own branch and merged by pull request after review.

---

## 6. Functional requirements

### 6.1 Input

| ID | Requirement | Phase |
|---|---|---|
| F-IN-1 | User enters a ticker symbol in NGX format, for example `FCMB` or `LEARNAFRCA`. Input is case-insensitive and trimmed. | 1 |
| F-IN-2 | The app validates that price data exists for the ticker and shows a clear message if not | 1 |
| F-IN-3 | User can upload one or more CSV files of daily prices (Section 7.2) | 1 |
| F-IN-4 | Configurable settings: lookback years, window types, pattern thresholds (Section 8.6), number of permutation runs, random seed | 1 |
| F-IN-5 | Multi-ticker mode: scan a list of tickers and return a combined ranking | 1 |
| F-IN-6 | Ticker search with autocomplete from the stored security list | 2 |

### 6.2 Analysis

| ID | Requirement | Phase |
|---|---|---|
| F-AN-1 | Calculate returns for all 37 standard windows for every year with complete data (Section 8.2) | 1 |
| F-AN-2 | Calculate per-window statistics (Section 8.3) | 1 |
| F-AN-3 | Compare against the market benchmark (Section 8.4) | 1 |
| F-AN-4 | Compare against the stock's own same-year average window (Section 8.4) | 1 |
| F-AN-5 | Classify windows into Tier 1, Tier 2, Watch, Emerging, Negative, None or Insufficient history (Section 8.6) | 1 |
| F-AN-6 | Run the permutation test and report the chance level (Section 8.5) | 1 |
| F-AN-7 | Run data-quality checks and attach flags to the report (Section 8.7) | 1 |
| F-AN-8 | Optional custom windows (any start month, length 1 to 6 months) | 2 |
| F-AN-9 | Optional dividend-adjusted mode when corporate action data is available | 2 |
| F-AN-10 | Out-of-sample check: hold back the most recent N years, detect patterns on the earlier years, report whether they held in the held-back years | 2 |

### 6.3 Report output

| ID | Requirement | Phase |
|---|---|---|
| F-RP-1 | Summary panel: ticker, data range, years analysed, data-quality flags, chance-level result | 1 |
| F-RP-2 | Heatmap: windows as rows, years as columns, colour by return, value shown in each cell | 1 |
| F-RP-3 | Ranked pattern table (Tier 1, then Tier 2) with all statistics from Section 8.3 | 1 |
| F-RP-4 | Negative windows table | 1 |
| F-RP-5 | Seasonal calendar: a 12-month strip showing when each qualifying window opens and closes, with the next opening date highlighted | 1 |
| F-RP-6 | Year-by-year detail for any selected window, including entry and exit prices and the dip inside the window | 1 |
| F-RP-7 | Method and caveats section, generated automatically in every report | 1 |
| F-RP-8 | Export: CSV (full statistics and year by year), PDF (formatted report), JSON (run details: settings, sources, data hashes, code version) | 1 |
| F-RP-9 | Multi-ticker ranking across all scanned stocks | 1 |

### 6.4 Sharing

| ID | Requirement | Phase |
|---|---|---|
| F-SH-1 | Each saved report gets a unique, hard-to-guess link | 3 |
| F-SH-2 | A shared report is read-only and frozen. It shows the data snapshot date and does not change when new data arrives. | 3 |
| F-SH-3 | The owner can revoke a shared link | 3 |
| F-SH-4 | A short text summary of a report can be sent by email or messaging | 3 |

### 6.5 Watchlist and alerts

| ID | Requirement | Phase |
|---|---|---|
| F-AL-1 | User saves tickers to a watchlist | 3 |
| F-AL-2 | A nightly job re-runs the scan for watchlist tickers after the data update | 3 |
| F-AL-3 | Alert when a Tier 1 or Tier 2 window opens within a configurable number of trading days (default 5) | 3 |
| F-AL-4 | Alert when a pattern's classification changes, for example a streak breaks | 3 |
| F-AL-5 | Delivery channels: email first, then Telegram, then WhatsApp Business API | 3 |

### 6.6 Monte Carlo module

| ID | Requirement | Phase |
|---|---|---|
| F-MC-1 | User selects a qualifying pattern and defines rules: entry timing, target %, stop %, time exit | 4 |
| F-MC-2 | Simulate price paths with a block bootstrap of the stock's historical daily returns, drawn only from the same calendar window | 4 |
| F-MC-3 | Apply the NGX daily price limit (configurable, default ±10%) to simulated paths, so a stop can be skipped past or blocked | 4 |
| F-MC-4 | Apply a cost model: brokerage, exchange and regulatory fees, and slippage. All are configurable. | 4 |
| F-MC-5 | Apply a liquidity cap: position size limited to a configurable % of average daily traded value | 4 |
| F-MC-6 | Outputs: probability of hitting the target first, probability of hitting the stop first, probability of a time exit, return percentiles (5th, 25th, 50th, 75th, 95th), expected value after costs, and maximum drawdown distribution | 4 |
| F-MC-7 | Compare a grid of entry offsets, targets and stops, and rank them by expected value per unit of risk | 4 |
| F-MC-8 | Position sizing output: fixed-fractional size from a user-defined maximum loss per trade and a maximum portfolio drawdown | 4 |
| F-MC-9 | Optional reporting currency: NGN, USD or EUR, converted with a stored FX series | 4 |
| F-MC-10 | All simulations reproducible from a stored seed and stored parameters | 4 |

---

## 7. Data

### 7.1 Data required

| Data | Purpose | Phase |
|---|---|---|
| Daily close per ticker | All window calculations | 1 |
| Daily volume and traded value per ticker | Liquidity checks and the liquidity cap | 1 if available in CSV, otherwise 2 |
| Daily close for the full market (all listed equities) or the NGX All-Share Index | Market benchmark | 1 (open dataset), 2 (live) |
| Corporate actions (dividends, bonus issues, splits) with ex-dates | Dividend-adjusted mode and ex-dividend flags | 2 |
| FX rates (USDNGN, EURNGN) | Reporting currency option | 4 |

### 7.2 CSV import specification (Phase 1)

- One file per ticker. The ticker is taken from the file name or chosen by the user.
- Required columns: a date column and a close column.
- Optional columns: open, high, low, volume.
- Accepted header variants (case-insensitive):
  - date: `date`, `time`, `timestamp`
  - close: `close`, `price`, `last`
  - volume: `volume`, `vol`
- Date formats accepted: ISO (`YYYY-MM-DD`), `DD/MM/YYYY`, and Unix seconds. TradingView exports use `time` and may use Unix seconds or ISO dates. Both must parse.
- Validation on import:
  - reject non-positive prices
  - de-duplicate dates (keep the last)
  - sort ascending
  - report the number of rows, the date range and any gaps longer than 10 trading days

### 7.3 Data sources and licensing

| Source | Use | Status |
|---|---|---|
| Manual CSV exports (for example TradingView "Export chart data") | Phase 1 input, personal use only | Allowed for personal analysis. The tool must not fetch from TradingView automatically. |
| NairaDB open dataset (GitHub: kennybix/NairaDB) | Phase 1 testing and baseline. Daily closes from December 2015 to 19 December 2025, about 147 NGX stocks. | Check its licence before copying any data into the repository. Until then the app downloads it at runtime and it is listed in `.gitignore`. |
| NGX Market Data API, end-of-day tier | Phase 2 live feed | Local annual pricing at research time: N50,000 for end-of-day. Showing data or derived results to other people may need a redistribution licence. Confirm with NGX before Phase 3 opens access to other users. |
| Third-party providers (iTick, Mansa API) | Backup or alternative feed | Paid. Accuracy must be validated against NGX before use. |

### 7.4 Known data characteristics

- Prices in the open dataset are **unadjusted** for dividends and bonus issues.
- The closing price often stays the same for many sessions. Under the NGX rules the official close moves only on qualifying trades, so an unchanged price does not by itself mean there was no trading. Liquidity must be judged from volume and traded value, not from unchanged prices.
- Daily moves are capped by the exchange's price limit. The research data showed many sessions closing at exactly -10.0%.
- Some tickers have gaps. Ikeja Hotel, for example, has no 2017 data in the open dataset.

---

## 8. Analysis methodology

These definitions are the specification. The engine must implement them exactly, and the report must describe them in plain language.

### 8.1 Month-end price

The month-end price for a ticker is the last available daily close in that calendar month.

### 8.2 Windows

| Type | Count | Definition |
|---|---|---|
| Single month | 12 | Start month m, length 1 |
| Rolling 2-month | 12 | Start month m, length 2, crossing the year end where needed (for example Dec to Jan) |
| Rolling 3-month | 12 | Start month m, length 3. Includes the standard quarters Jan to Mar, Apr to Jun, Jul to Sep and Oct to Dec. |
| Full year | 1 | January to December |

Total: 37 windows per ticker.

**Window return** for year Y = month-end close of the window's last month ÷ month-end close of the month before the window starts, minus 1.

**Year label:** a window is labelled with the year in which it starts. Nov 2024 to Jan 2025 is labelled 2024.

**Completeness:** a window-year is included only if both the entry month-end and the exit month-end exist and the exit month is fully complete in the data. Example: with data ending 19 December 2025, every window ending in December 2025 or later is excluded.

### 8.3 Per-window statistics

| Statistic | Definition |
|---|---|
| n | Number of complete years |
| up | Number of years with return > 0 |
| hit rate | up ÷ n |
| current streak | Consecutive positive years counting back from the most recent complete year |
| longest streak | Longest run of consecutive positive years |
| median, mean | Of the yearly returns |
| worst, best | Minimum and maximum yearly return |
| beat market | Number of years the window return exceeded the market benchmark for the same window and year |
| median excess vs market | Median of (window return minus benchmark) |
| beat own average | Number of years the window return exceeded the stock's own average window of the same length in the same year |
| median excess vs own | Median of (window return minus own average) |
| dip inside window | For each year: (lowest daily close inside the window ÷ entry close) minus 1. Report the median and the worst. |
| binomial p-value (up) | One-sided test of `up` against a 50% base rate |
| binomial p-value (own) | One-sided test of "beat own average" against a 50% base rate |
| year-by-year string | Every year's return, shown in the detail view and the CSV export |

### 8.4 Benchmarks

- **Market benchmark (Phase 1):** for each window and year, the 10% trimmed mean of the window returns of all stocks with complete data. It applies only when at least 30 stocks qualify. A median is not used, because most NGX stocks show 0% in many months, which makes the median meaningless.
- **Market benchmark (Phase 2):** the NGX All-Share Index when licensed data is available, with the trimmed mean kept as a secondary benchmark.
- **Own-average benchmark:** for a window of length L in year Y, the mean of the stock's 12 rolling windows of length L in year Y. This removes the stock's general uptrend or downtrend, so a stock that rose every month is not reported as seasonal. It is not applied to the full-year window.

### 8.5 Permutation test (chance level)

1. Convert the ticker's month-end prices to monthly log returns.
2. Shuffle the 12 monthly returns randomly within each calendar year. This keeps each year's total trend and destroys any seasonal ordering.
3. Rebuild the windows and count how many pass the pattern filter.
4. Repeat R times (default 300, with a configurable seed).
5. Report:
   - the actual pattern count
   - the mean count under shuffling
   - the 95th percentile under shuffling
   - the share of shuffled runs with a count at or above the actual count

In multi-ticker mode, the test runs on the combined set and is also reported per ticker.

### 8.6 Classification rules (defaults, all configurable)

| Class | Rule |
|---|---|
| Candidate | n ≥ 8, hit rate ≥ 80%, beat own average in ≥ 70% of years, median return ≥ 5%. Single, 2-month and 3-month windows only. |
| Tier 1 | Candidate, plus current streak ≥ 4, plus beat market in ≥ 2/3 of years |
| Tier 2 | Candidate that is not Tier 1 |
| Watch | Not a candidate, but n ≥ 8, hit rate ≥ 70%, median ≥ 5%, beat own average in ≥ 60% of years, and current streak ≥ 3 |
| Negative | n ≥ 8, hit rate ≤ 20% and median ≤ -5% |
| None | Everything else |

Rules for ranking within a tier:
- Rank Tier 1, Tier 2 and Watch by score = 0.4 × hit rate + 0.3 × own-average beat rate + 0.3 × market beat rate.
- Rank Negative windows by hit rate (lowest first), then median (most negative first).
- Break ties by median return.
- A window with insufficient history (n < 8) is never classified Tier 1, Tier 2, Watch or Negative. It is listed as "Insufficient history", unless it meets the Emerging rule below, in which case it is listed as "Emerging". Either way it carries the "Insufficient history" flag.
- A window that does not qualify for any tier but has a current streak of 5 or more years and a median of at least 5% is listed separately as "Emerging". Example: Learn Africa May to Jul, up in each of the last 5 years.

### 8.7 Data-quality flags

| Flag | Trigger | Effect |
|---|---|---|
| Insufficient history | Fewer than 8 complete years for the window | Flag on the window. Classified only as "Emerging" (if it meets that rule) or "Insufficient history". |
| Frozen price | More than 30% of month-end to month-end changes are exactly 0% over the history | Warning at the top of the report. Every Tier 1, Tier 2, Watch, Emerging and Negative window is marked "Unreliable". |
| Possible corporate action | Any single-day move beyond ±10.5% | Listed with date and size for the user to review |
| Ex-dividend distortion | Window covers a month with a known ex-dividend date. Phase 1: dates supplied by the user. Phase 2: corporate actions data. | Window annotated: "price-only return understates the holder's return". |
| Data gap | Missing year or a gap longer than 10 trading days | Listed |
| Stale data | Last data date older than 5 trading days before today | Warning |

### 8.8 Caveats included automatically in every report

- Past seasonal behaviour does not guarantee future results.
- Prices are unadjusted unless dividend-adjusted mode is on.
- Results exclude trading costs, slippage and the effect of daily price limits (until Phase 4).
- The permutation test result, with plain wording about how likely the patterns are to be chance.
- The data source and snapshot date.

---

## 9. Architecture

### 9.1 Phase 1

- Single Python application.
- The engine is a pure Python package with no user-interface code, so it can be tested on its own and reused in later phases.
- Streamlit provides the user interface.
- Files are stored locally. Nothing persists beyond the session apart from exports.

### 9.2 Phase 2 onward

| Component | Choice (proposed) |
|---|---|
| Engine | Same package as Phase 1, unchanged interface |
| Database | SQLite in Phase 2, PostgreSQL when multi-user access starts in Phase 3 |
| Scheduler | Server cron or GitHub Actions scheduled workflow, after NGX close on trading days |
| Web layer | Streamlit for internal use. If public access is required, a FastAPI backend with a separate frontend. |
| Report storage | Frozen report snapshots (JSON and PDF) keyed by report ID |
| Alerts | Email provider first; Telegram Bot API; WhatsApp Business API last because of approval requirements |
| Hosting | To be decided (open decision D3) |

### 9.3 Proposed repository structure

```
Investment-Patterns/
├── README.md
├── docs/
│   └── SCOPE.md                  # this document
├── config/
│   └── example-overrides.yaml    # sample settings file
├── src/scanner/
│   ├── default.yaml              # thresholds, window sets, seeds
│   ├── data/
│   │   ├── csv_loader.py
│   │   ├── nairadb_loader.py
│   │   ├── ngx_api.py            # Phase 2
│   │   └── validation.py
│   ├── engine/
│   │   ├── windows.py
│   │   ├── metrics.py
│   │   ├── benchmark.py
│   │   ├── significance.py
│   │   ├── quality.py
│   │   └── classify.py
│   ├── report/
│   │   ├── tables.py
│   │   ├── heatmap.py
│   │   ├── calendar.py
│   │   └── export.py             # CSV and PDF
│   └── simulation/               # Phase 4
├── app/
│   └── streamlit_app.py
├── tests/
│   ├── unit/
│   ├── regression/
│   │   └── fixtures/             # verified prices and Appendix A results
│   └── features/                 # Gherkin acceptance specifications
├── .github/workflows/
│   └── ci.yml
├── requirements.txt
└── .gitignore                    # excludes data/ and exports/
```

### 9.4 Data model (Phase 2)

| Table | Key fields |
|---|---|
| securities | ticker, name, sector, listing date, status |
| daily_prices | ticker, date, open, high, low, close, volume, value, source, ingested_at |
| corporate_actions | ticker, type, ex_date, amount or ratio, source |
| scan_runs | run_id, ticker(s), parameters (JSON), data snapshot date, data hash, created_at |
| window_results | run_id, ticker, window, year, return, dip, excess vs market, excess vs own |
| window_stats | run_id, ticker, window, all Section 8.3 statistics, class |
| reports | report_id, run_id, owner, share token, revoked flag, created_at |
| watchlists, alerts | user, ticker, alert settings, last fired |

---

## 10. Non-functional requirements

| ID | Requirement |
|---|---|
| NF-1 | A single-ticker scan with 10 years of daily data and 300 permutation runs completes in under 15 seconds on a standard laptop |
| NF-2 | Results are reproducible: the same data snapshot, parameters and seed produce identical output |
| NF-3 | Every report records the data source, snapshot date, data hash, parameters and code version |
| NF-4 | No credentials or API keys in the repository. Secrets go through environment variables or the host's secret store. |
| NF-5 | Raw price data is not committed to the repository unless its licence allows it |
| NF-6 | The app handles a ticker with partial or missing data without crashing and states the reason |
| NF-7 | Shared report links use unguessable tokens and can be revoked |
| NF-8 | Accessibility: heatmap colours readable for common colour-vision deficiencies, with values printed in each cell |

---

## 11. Quality assurance and testing

### 11.1 Test levels

| Level | Coverage |
|---|---|
| Unit | Month-end selection, window return formula, year-end crossing windows, completeness rule, every statistic in Section 8.3, trimmed-mean benchmark, own-average benchmark, classification boundaries, quality flags |
| Property-based | Returns invariant to price scaling. Shuffle test keeps annual totals. Hit rate between 0 and 1. A constant-price series produces no patterns and triggers the frozen flag. |
| Regression | Golden results from the research session (Appendix A) on the fixed dataset snapshot. Any change to these numbers fails the build unless the fixtures are deliberately updated. |
| Data validation | Schema and range checks on every import and every nightly load |
| Integration | CSV upload to report, multi-ticker scan, exports open correctly |
| Acceptance | Gherkin scenarios (Section 11.3), run in CI |

### 11.2 Verified price fixtures

These closes were confirmed against independently published figures during the research session:

| Ticker | Date | Close (NGN) |
|---|---|---|
| LEARNAFRCA | 2021-12-31 | 1.17 |
| LEARNAFRCA | 2022-12-16 | 2.12 |
| LEARNAFRCA | 2025-12-12 | 6.30 |
| VITAFOAM | 2019-05-23 | 4.25 |
| VITAFOAM | 2020-01-21 | 5.00 |
| VITAFOAM | 2024-04-22 | 17.15 |

Window return fixtures, recomputed independently from raw closes:

| Ticker | Window | Year | Entry close | Exit close | Return |
|---|---|---|---|---|---|
| FCMB | Oct to Dec | 2017 | 1.07 (2017-09-29) | 1.48 (2017-12-29) | +38.3% |
| VITAFOAM | Nov to Jan | 2019 | 3.50 (2019-10-31) | 5.50 (2020-01-31) | +57.1% |
| IKEJAHOTEL | Dec to Feb | 2023 | 4.20 (2023-11-30) | 7.50 (2024-02-29) | +78.6% |

### 11.3 Acceptance criteria (Gherkin)

The executable copies of these scenarios are in `tests/features/` and must be kept identical.

```gherkin
Feature: Seasonal window scan for a single ticker

  Background:
    Given the NairaDB dataset snapshot ending 2025-12-19 is loaded
    And default classification thresholds are in use

  Scenario: Scan returns all standard windows
    When I scan the ticker "FCMB"
    Then the report contains 37 windows
    And every window shows n, up, streak, median, worst, beat market and dip statistics

  Scenario: Known Tier 1 pattern is detected
    When I scan the ticker "FCMB"
    Then the window "Oct-Dec" is classified as "Tier 1"
    And it shows 9 up years out of 9
    And its median return is 12.1% within a tolerance of 0.1 percentage points

  Scenario: Incomplete final month is excluded
    When I scan the ticker "VITAFOAM"
    Then no window ending in December 2025 is included
    And the last complete month is "2025-11"
    And the report states that December 2025 is incomplete

  Scenario: Year-end crossing window is labelled by its start year
    When I scan the ticker "VITAFOAM"
    And I open the year detail for window "Nov-Jan"
    Then the 2019 row shows entry close 3.50 on 2019-10-31
    And exit close 5.50 on 2020-01-31
    And a return of 57.1%

  Scenario: Frozen price stock is flagged
    When I scan the ticker "CWG"
    Then the report shows the "Frozen price" warning
    And no window is classified above "None" without an "Unreliable" label

  Scenario: Short history is not classified
    When I scan the ticker "BUAFOODS"
    Then every window shows the "Insufficient history" flag
    And no window is classified as "Tier 1" or "Tier 2"

  Scenario: Consistent negative window is reported
    When I scan the ticker "ETI"
    Then the window "Feb-Mar" is classified as "Negative"
    And it shows 0 up years out of 10

  Scenario: Permutation result is reproducible
    Given the permutation seed is 7 and runs are 300
    When I scan the ticker "FCMB" twice
    Then both reports show identical permutation results

  Scenario: Unknown ticker
    When I scan the tickers "NOTREAL"
    Then I see the message "No price data found for NOTREAL"
    And no report is generated

Feature: CSV import

  Scenario: TradingView export with Unix timestamps
    Given a CSV file "NSENG_FCMB, 1D.csv" with columns "time,open,high,low,close,Volume"
    And the time column contains Unix seconds
    When I upload the file
    Then the import succeeds for ticker "FCMB"
    And the summary shows first date 2025-01-02 and last date 2025-01-06

  Scenario: Invalid prices are rejected
    Given a CSV file "x.csv" containing a close price of 0
    When I upload the file
    Then the import reports 1 invalid row
    And the row is excluded from analysis
```

### 11.4 Continuous integration

- Every push and pull request runs linting, unit, property-based, regression and acceptance tests.
- The main branch is protected, and changes merge only by pull request with passing checks.

---

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Data licensing breach when sharing results | Legal exposure, service shutdown | Personal use only until the NGX redistribution terms are confirmed. No automated pulling from TradingView. |
| Data errors in third-party or digitised sources | Wrong patterns | Spot-check fixtures, validation on import, cross-check against a second source in Phase 2 |
| Overfitting and data mining | False confidence in chance patterns | Permutation test, own-average benchmark, out-of-sample check (F-AN-10), plain-language caveats |
| Unadjusted prices | False negative windows around ex-dividend dates | Ex-dividend flag from user-supplied dates (Phase 1), adjusted mode (Phase 2) |
| Illiquidity | Patterns that cannot be traded at size | Volume-based checks, liquidity cap in simulation |
| Daily price limits | Stops not filled at the intended price | Limit modelling in the Monte Carlo module |
| Changes in market conditions | Past patterns stop working | Watchlist alerts on classification changes. Re-scan with each new year. |
| Users treating output as advice | Financial loss, reputational risk | Fixed disclaimer, no buy or sell wording, statistics only |
| Survivorship bias | Market benchmark overstated | Include delisted securities when licensed history allows. State the limitation until then. |

---

## 13. Future extensions (not in current phases)

- US stocks and ETFs, using a licensed US data provider, with the same engine and US-specific cost assumptions
- XAUUSD session and weekend-gap analysis using exported broker history, with a separate intraday engine
- Earnings-date and dividend-date event studies (returns before and after announcements)
- Portfolio-level calendar: combining patterns across stocks into one seasonal allocation plan

---

## 14. Open decisions

| ID | Decision | Options | Needed by |
|---|---|---|---|
| D1 | Who uses the tool | Resolved 26 Nov 2026: public. The owner accepts the Section 7.3 licensing risk; the public site publishes returns and statistics only, never closing prices | Closed |
| D2 | Data budget | NGX end-of-day subscription, third-party provider, manual CSV only | Before Phase 2 |
| D3 | Hosting | Resolved 26 Nov 2026: public static site on Cloudflare Pages at investment.bolujo.com (built from main); the Streamlit app stays a private research tool | Closed |
| D4 | Repository | Resolved: ini-hub/Investment-Patterns, Phase 1 on branch phase-1-pattern-scanner | Closed |
| D5 | Missing tickers | Confirm exact NGX tickers for "Greenwich" and "SIAML" and whether they are ETFs | Before Phase 1 regression run |
| D6 | NairaDB licence | Resolved in Phase 1: the dataset has no licence file, so it is downloaded at runtime (pinned commit) and never committed | Closed |
| D7 | Default thresholds | Accept the Section 8.6 defaults or adjust | Phase 1 review |

---

## 15. Definition of done (per phase)

- All requirements for the phase are implemented or deferred with a recorded reason
- All automated tests pass in CI
- Regression results match Appendix A, or any difference is explained and approved
- README updated with setup, usage and data-source instructions
- Pull request reviewed and merged by the owner

---

## Appendix A: Baseline research results

Dataset: NairaDB daily closes, December 2015 to 19 December 2025, unadjusted. Windows ending in December 2025 are excluded. The market benchmark is the 10% trimmed mean across about 147 stocks. These values are the regression reference for Phase 1.

### A.1 Market-wide seasonality (average NGX stock)

| Window | Years up | Median |
|---|---|---|
| December | 8 of 9 | +1.7% |
| Nov to Jan | 7 of 9 | +8.7% |
| January | 7 of 10 | +3.5% |
| March | 1 of 10 | -1.9% |
| Feb to Apr | 3 of 10 | -2.0% |

These tables apply the exact Section 8.6 rules. They differ slightly from the informal ranking given in the research chat: FCMB January, Vitafoam January and FCMB Dec to Jan qualify as Tier 1 under the formal rules, and PZ December and Honeywell Flour December fall to Watch.

### A.2 Tier 1 (8 windows)

| Rank | Stock | Window | Up / n | Streak | Median | Worst year | Beat market | Median dip | Worst dip |
|---|---|---|---|---|---|---|---|---|---|
| 1 | FCMB | Oct to Dec | 9 / 9 | 9 | +12.1% | +2.8% | 8 / 9 | -4.2% | -25.8% |
| 2 | IKEJAHOTEL | Dec to Feb | 7 / 8 | 7 | +25.7% | 0.0% | 7 / 8 | 0.0% | -17.3% |
| 3 | FCMB | January | 9 / 10 | 9 | +6.4% | -42.0% | 8 / 10 | -3.2% | -42.6% |
| 4 | VITAFOAM | Nov to Jan | 8 / 9 | 8 | +31.9% | -2.8% | 6 / 9 | -4.5% | -11.4% |
| 5 | ETI | Dec to Jan | 8 / 9 | 6 | +19.2% | -12.2% | 6 / 9 | -3.2% | -15.4% |
| 6 | VITAFOAM | January | 8 / 10 | 8 | +9.2% | -15.7% | 8 / 10 | -1.1% | -15.7% |
| 7 | FCMB | Dec to Jan | 8 / 9 | 5 | +24.2% | -5.5% | 6 / 9 | -3.3% | -14.1% |
| 8 | LEARNAFRCA | Nov to Jan | 8 / 9 | 4 | +16.3% | -8.2% | 6 / 9 | -9.4% | -11.8% |

### A.3 Tier 2 (7 windows)

| Stock | Window | Up / n | Streak | Median | Worst year |
|---|---|---|---|---|---|
| VITAFOAM | Mar to May | 9 / 10 | 1 | +10.2% | -33.3% |
| CONOIL | May | 8 / 10 | 0 | +7.9% | -10.0% |
| ETI | May | 8 / 10 | 1 | +7.8% | -18.1% |
| FCMB | Nov to Jan | 8 / 9 | 3 | +25.3% | -1.9% |
| VITAFOAM | Mar to Apr | 8 / 10 | 1 | +11.8% | -33.3% |
| CONOIL | May to Jun | 8 / 10 | 0 | +13.8% | -29.2% |
| VITAFOAM | Apr to May | 8 / 10 | 1 | +13.2% | -15.2% |

### A.3.1 Watch (16 windows, top 8 shown)

| Stock | Window | Up / n | Streak | Median | Worst year |
|---|---|---|---|---|---|
| ETI | Nov to Jan | 7 / 9 | 6 | +17.6% | -12.5% |
| ETI | January | 7 / 10 | 6 | +11.6% | -12.1% |
| IKEJAHOTEL | Nov to Dec | 6 / 8 | 6 | +5.4% | -32.6% |
| ETERNA | Dec to Jan | 7 / 9 | 3 | +21.5% | -14.3% |
| PZ | Dec to Feb | 7 / 9 | 5 | +9.6% | -14.3% |
| IKEJAHOTEL | Apr to Jun | 7 / 9 | 6 | +20.9% | -23.9% |
| PZ | December | 7 / 9 | 7 | +6.1% | -6.5% |
| IKEJAHOTEL | Nov to Jan | 6 / 8 | 6 | +10.1% | -33.9% |

The other 8 Watch windows are HONYFLOUR December, IKEJAHOTEL Jan to Feb, HONYFLOUR Nov to Dec, PZ Feb to Apr, ETERNA January, FCMB May, FCMB May to Jul and LEARNAFRCA Jun to Aug.

### A.4 Negative windows (25 windows, top 11 shown)

| Stock | Window | Up / n | Median | Likely cause |
|---|---|---|---|---|
| IKEJAHOTEL | March | 0 / 9 | -14.3% | Selling after the Dec to Feb rally |
| ETI | Feb to Mar | 0 / 10 | -8.4% | Selling after the January rally |
| FTNCOCOA | Feb to Mar | 0 / 10 | -7.9% | Stock flagged as frozen price; unreliable |
| CONOIL | Mar to Apr | 0 / 10 | -7.6% | Not confirmed |
| FCMB | Feb to Mar | 1 / 10 | -9.6% | Selling after the January rally |
| CONOIL | March | 1 / 10 | -8.3% | Not confirmed |
| LEARNAFRCA | September | 1 / 10 | -6.7% | Ex-dividend drop in September |
| IKEJAHOTEL | Jul to Sep | 1 / 9 | -11.4% | Not confirmed |
| FTNCOCOA | Jan to Mar | 1 / 9 | -7.7% | Stock flagged as frozen price; unreliable |
| IKEJAHOTEL | Jul to Aug | 1 / 9 | -5.7% | Not confirmed |
| VITAFOAM | Feb to Mar | 2 / 10 | -16.3% | Ex-dividend drop in mid-February |

### A.5 Not classifiable

| Stock | Reason |
|---|---|
| CWG | Frozen prices from 2016 to 2020 (53% of monthly changes are 0%) |
| FTNCOCOA | Frozen prices from 2016 to 2020 (50% of monthly changes are 0%) |

| BUACEMENT | Listed 2020. At most 6 years of data. |
| BUAFOODS | Listed 2022. At most 4 years of data. Also triggers the frozen-price flag (38% of monthly changes are 0%). |
| Greenwich, SIAML | Not in the dataset. Tickers to be confirmed. |

Emerging: LEARNAFRCA May to Jul, up in each of the last 5 years (2021 to 2025), median +10.5% over the full 10 years.

### A.6 Permutation test (13 stocks combined)

| Measure | Value |
|---|---|
| Actual qualifying patterns | 15 |
| Mean under random shuffling (300 runs, seed 7) | 9.68 |
| 95th percentile under shuffling (smallest run count at or above the 95% point) | 17 |
| Share of shuffled runs ≥ actual | 12% |

---

## Appendix B: Phase 1 change log against this scope

| Date | Change | Reason |
|---|---|---|
| 26 Nov 2026 | Dropped the price-based ex-dividend heuristic (recurring same-month drops) in favour of user-supplied ex-dividend dates | Tested on the research stocks, sharp one-day drops of 5 to 7% occur in almost every month on the NGX, so the heuristic flagged nearly every window and carried no information |
| 26 Nov 2026 | Tier 1 market test set to 0.666 (two thirds) | A stored value of 0.6667 rejected exactly 6 of 9 years, which the rule intends to accept |
| 26 Nov 2026 | Settings file moved into the package (src/scanner/default.yaml) | So the defaults install with the package and the app works from any folder |
| 26 Nov 2026 | A window with fewer than 8 years can be classified Emerging; it keeps the "Insufficient history" flag | Sections 8.6 and 8.7 contradicted each other; the owner chose to show short-history streaks rather than hide them |
| 26 Nov 2026 | The "Unreliable" label on frozen-price stocks now also covers Negative windows | Appendix A.4 already treats FTNCOCOA's negative windows as unreliable |
| 26 Nov 2026 | Every CSV row carries data hash, code version and settings hash; a JSON run-details export holds the full settings | NF-3 provenance, while keeping the CSVs readable in Excel and pandas |
| 26 Nov 2026 | Gherkin scenarios in 11.3 replaced by exact copies of `tests/features/` | The scope and the executable specifications had drifted apart |
| 26 Nov 2026 | Appendix A.6 average under shuffling changed from 9.5 to 9.68; the 95th percentile is reported as a whole number of patterns | The research session's shuffle used a different random sequence. The Phase 1 code (300 runs, seed 7) gives 15 / 9.68 / 17 / 12%; the actual count, 95th percentile and share match the research, and the conclusion is unchanged |
| 26 Nov 2026 | Multi-ticker scans now report the chance check for each stock as well as for the group | Section 8.5 required it; the first build only ran the combined test |
| 26 Nov 2026 | App redesigned into Scan, Results and Compare screens from the owner's design canvas; company names and sectors added from a hand-kept list (src/scanner/data/securities.csv) | Owner design review. Names have no data source until Phase 2's securities table |
| 26 Nov 2026 | Compare accepts any number of stocks (an "All stocks" pick scans the whole dataset); above 6 it switches to a sortable stock table and ranked pattern list; filters exclude frozen-price stocks and stocks with no rising pattern (Tier 1, Tier 2, Watch or Emerging) | Owner request. The chance check always covers the full scan, so filtering cannot make chance patterns look real |
| 26 Nov 2026 | Public static site for investment.bolujo.com (site/, built by scanner.publish, hosted on Cloudflare Pages): all stocks pre-scanned with default settings; no uploads or custom settings; no closing prices published | Owner chose a public site (D1) with free hosting (D3); a static build cannot be overloaded and limits the data published |
