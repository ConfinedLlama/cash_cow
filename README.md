# cash_cow

Research workspace for US-market strategies on a small Singapore-based account. **Historical screening only; no broker connection, background paper runner, live orders or approved trading strategy.**

The latest completed work is **v3/v3b intraday research**: eight paper-based variants, 236 candidate/benchmark/diagnostic runs and 63 passing tests. Real minute data covers July–December 2022, with five evaluation months. No tested run produced a 10% month. This short pilot cannot establish reliable monthly performance. The **multi-year v4 pipeline is prepared but awaiting local Alpaca keys and validated data**.

- [Latest intraday findings and next dependency](docs/DECISION_V3.md)
- [Intraday papers, data, execution and account assumptions](docs/INTRADAY_V3.md)
- [Prepared multi-year specification — not yet run](configs/experiment_v4.json)
- Completed pilot pointers: [v3](reports/LATEST_V3.txt), [v3b follow-up](reports/LATEST_V3B.txt)

The prior **v2** experiment evaluates **12 higher-risk daily paper adaptations × 10 scenarios**, seven benchmarks and 19 earlier-period diagnostics. Its best base-case candidate compounded at 2.98% monthly in 2016–2024, with a 66.27% maximum drawdown. These are retrospective results, not expected live returns. Each simulation starts with its own research account.

- [V2 results and research decision](docs/DECISION_V2.md)
- [Nine source papers, twelve implementations, and deferred intraday research](docs/PAPERS_V2.md)
- [V2 configuration](configs/experiment_v2.json)
- Latest v2 run: [reports/LATEST_V2.txt](reports/LATEST_V2.txt)

The original v1 experiment retains its ten conservative candidates, ten scenarios and three benchmarks:

- [Start here: results and initial decision](docs/DECISION.md)
- [Research and Singapore broker recommendation](docs/RESEARCH.md)
- [Exact simulation methodology and limitations](docs/METHODOLOGY.md)
- [Frozen experiment configuration](configs/experiment_v1.json)
- [Trial registry](docs/TRIAL_REGISTRY.md)
- Latest completed results: read the relative path in [reports/LATEST.txt](reports/LATEST.txt)

## Run locally

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m cash_cow.intraday.data --sample
.venv/bin/python -m cash_cow.intraday.run
.venv/bin/python -m cash_cow.intraday.followup
# Multi-year data and evaluation, only after saving local Alpaca keys:
.venv/bin/python -m cash_cow.intraday.multiyear --fetch
# Prior daily-bar experiment:
.venv/bin/python -m cash_cow.run_v2 --fetch
.venv/bin/python -m cash_cow.verify_v2
# Original v1 experiment:
.venv/bin/python -m cash_cow.run --fetch --label v1
```

Downloads use unofficial Yahoo Finance data via yfinance for personal research. Cached raw data, detailed paths and trade logs remain local and are excluded from Git; aggregate summaries, manifests, reports and charts are reviewable. No keys or broker credentials are required. Omit `--fetch` to reuse a validated local cache. Failed or interrupted runs may leave an incomplete directory; `LATEST.txt` (v1) and `LATEST_V2.txt` point only to completed runs.

## Research boundaries

USD 2,000 is an unconfirmed currency assumption. V1 limits candidate allocation to 25%; v2 increases it to 95%, including actual 3× daily leveraged ETFs. Neither daily-bar experiment simulates account borrowing or shorts. **V3/v4 explicitly separate cash long-only accounts from hypothetical margin/short references**, whose eligibility is not established. All returns are marked-to-market historical simulations with assumptions about fees, slippage, settlement and distributions; they are not a monthly income promise.

V1 uses 2008–2024 diagnostics and 2016–2024 comparisons. V2 uses 2011–2015 diagnostics and **reuses** 2016–2024. Both warm up on earlier observations. **2025 onward price bars have not been fetched.** Known 2025 corporate-action facts restore historical nominal units in v2. These retrospective evaluations are not future paper performance. Changing parameters after seeing results consumes information and must be logged.

Recommended next broker to investigate: **Interactive Brokers Singapore, Pro cash account, tiered pricing**. Account eligibility, permissions, fractional API execution and all costs still need account-specific confirmation. See the linked research for primary sources and alternatives.

## Layout

```text
cash_cow/data.py         data retrieval, provenance and input validation
cash_cow/strategies.py   fixed causal candidate rules
cash_cow/engine.py       daily cash-account simulation and metrics
cash_cow/run.py          experiment orchestration, statistics and report
configs/                frozen research specification
tests/                  accounting, timing and leakage tests
data/manifest.json      source provenance; raw data stays local
docs/                   research, methodology and trial history
reports/runs/           immutable result folders
```

Future broker integration should be a separate adapter with explicit paper-account selection, risk limits, order deduplication and reconciliation. This project currently cannot submit any order.
