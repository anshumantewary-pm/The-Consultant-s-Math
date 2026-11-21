# casemath

[![CI](https://github.com/anshumantewary-pm/The-Consultant-s-Math/actions/workflows/ci.yml/badge.svg)](https://github.com/anshumantewary-pm/The-Consultant-s-Math/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20to%203.13-blue)
![Coverage](https://img.shields.io/badge/coverage-%E2%89%A595%25-brightgreen)
![Dependencies](https://img.shields.io/badge/runtime%20deps-0-brightgreen)

A consulting case math toolkit. Profitability, break-even, market share and sizing, pricing, M&A synergy, NPV/IRR and unit economics calculators; sensitivity, goal seek, scenario and Monte Carlo analysis that works on any of them; a MECE issue-tree checker; six fully solved practice cases; a drill mode that quizzes you with checked answers; and two web front ends (a local UI and an in-browser app on GitHub Pages). Python library and CLI, no runtime dependencies.

```console
$ casemath breakeven --fixed-costs 100000 --price 10 --variable-cost 6 --expected-units 40000
Contribution/unit  $4.00  (40.0%)
Break-even units   25,000.00  (sell 25,000)
Break-even revenue $250,000.00
Margin of safety   37.5%
```

## Install

```bash
git clone https://github.com/anshumantewary-pm/The-Consultant-s-Math.git
cd The-Consultant-s-Math
pip install -e ".[dev]"     # or: pip install .   (no dev tools)
```

## What's inside

| Area | Functions | CLI |
|---|---|---|
| **Profitability** | `profit_statement`, `profit_bridge` (price / volume / unit cost / fixed cost, adds up exactly), `segment_profitability` | `profit`, `bridge` |
| **Break-even** | `break_even_units`, `break_even_revenue`, `break_even_price`, `units_for_target_profit`, `margin_of_safety`, `payback_period`, `break_even_analysis` | `breakeven` |
| **Market share** | `market_share`, `relative_market_share`, `required_share`, `share_table`, `hhi`, `project_share`, `cagr` | `share`, `hhi` |
| **Market sizing** | `top_down`, `bottom_up` (every step recorded) | `size` |
| **Pricing** | `price_elasticity` (midpoint), `break_even_volume_change`, `price_change_impact`, `profit_maximising_price`, `optimal_price_linear`, `volume_after_price_change` | `price`, `optimal-price` |
| **M&A synergies** | `SynergyItem` (cost or revenue, with risk haircut), `synergy_schedule` (phase-in, integration costs, payback), `synergy_value`, `acquisition_premium` | `synergy` |
| **Finance** | `npv`, `irr`, `simple_payback`, `discounted_payback`, `annuity_pv`, `perpetuity`, `investment_appraisal` | `invest` |
| **Unit economics** | `lifetime_value`, `cac_payback`, `unit_economics` (LTV/CAC health check) | `unit-econ` |
| **Analysis** | `one_way`, `tornado`, `two_way`, `goal_seek`, `compare_scenarios`, `simulate` with `Uniform` / `Triangular` / `Normal` inputs | `sensitivity`, `goalseek`, `simulate`, `models` |
| **Frameworks** | `profitability_tree`, issue-tree `Node`, `render`, `check_mece` | `tree` |
| **Practice cases** | `get_case("1").solve()` | `case list / show / solve` |
| **Drill** | `drill.generate(topic, count, seed)`, `drill.run_drill` | `drill` |
| **Business advisor** | `advisor.assess(Profile(...))`, `advisor.parse_financials(csv)`, 10 sector benchmarks | `advise`, `sectors` |
| **Web UI** | `web.make_server`, `web.call` (JSON API over the CLI) | `serve` |

## CLI tour

Every command takes `--json` for machine-readable output.

```bash
# P&L from unit economics
casemath profit --price 10 --units 1000 --variable-cost 6 --fixed-costs 2500

# Why did profit move? (PRICE,UNITS,VARIABLE_COST,FIXED_COSTS)
casemath bridge --before 10,1000,6,2000 --after 9,1200,6.5,2300

# Market share and concentration
casemath share --company 60 --market 400 --largest-rival 40
casemath hhi ChargeCo=486000 GridGo=324000 Others=270000

# Top-down sizing
casemath size --population 50000 --filter "use fast charging=0.3" \
              --units-per-customer 72 --price 8

# Will a price rise pay off? Give an elasticity, or measure it from a test (OLD_UNITS,NEW_UNITS)
casemath price --price 40 --new-price 50 --units 8000 --variable-cost 10 --elasticity -0.2
casemath price --price 40 --new-price 44 --units 3000 --variable-cost 10 --test 3000,2550

# Are the synergies worth the premium?
casemath synergy --run-rate 18e6 --multiple 8 --one-off 30e6 --premium 120e6

# The profitability framework, with the question to ask at each node
casemath tree --hints

# Investments: NPV, IRR, profitability index, payback
casemath invest --rate 0.1 -1000000 300000 300000 300000 300000 300000

# Profit-maximising price from two observed (price, volume) points, or from an elasticity
casemath optimal-price --points 120,400,99,470 --unit-cost 24
casemath optimal-price --elasticity -3 --unit-cost 10

# SaaS unit economics
casemath unit-econ --revenue 120 --margin 0.8 --churn 0.03 --cac 1800

# Analysis on built-in models (see: casemath models)
casemath sensitivity profit                                   # tornado, +/-10%
casemath goalseek profit --vary units --between 0:100000      # break-even volume
casemath simulate profit --dist units=tri:20000:40000:45000 --dist variable_cost=normal:6:0.5

# Practice cases (1 to 6)
casemath case list
casemath case show 1
casemath case solve 6

# Drill: 5 mixed questions, answer in plain text ($1.2M, 25%, 41,667). Enter skips, q quits.
casemath drill
casemath drill --topic pricing --count 10 --seed 7   # same seed, same questions
casemath drill --seed 7 --reveal                     # answer key, no quiz

# Web UI: calculators, cases and drill in the browser (localhost only by default)
casemath serve --open
```

`casemath serve` runs a small standard-library HTTP server. The page posts JSON to `/api/<command>`; the body is turned into the same arguments the CLI takes and parsed by the CLI's own parser, so the browser and the terminal always give the same answers and the same errors.

## Business advisor

Give a sector and one year of figures (flags, or a CSV of `metric,value` rows) and get a health score, a comparison with the sector's ranges, a valuation range on sector multiples, break-even revenue, cash runway and prioritised, sector-specific suggestions.

```bash
casemath sectors
casemath advise --sector saas --revenue 4200000 --cogs 1260000 --opex 3600000 \
  --prior-revenue 3000000 --cash 1500000 --arpu 500 --churn 0.025 --cac 9000
casemath advise --file company.csv --json
```

The same engine runs in the browser at `advisor.html` on the GitHub Pages site: upload a CSV (or download the template), check the form, click Analyse, then print the report or download it as JSON. Sector ranges are indicative screening rules of thumb, not market data.

## Library use

```python
from casemath.calculators import profit_statement, profit_bridge
from casemath.frameworks import breakdown_tree, check_mece

before = profit_statement(price=10, units=1_000, variable_cost_per_unit=6, fixed_costs=2_000)
after  = profit_statement(price=9,  units=1_200, variable_cost_per_unit=6.5, fixed_costs=2_300)
bridge = profit_bridge(before, after)
bridge.effects         # {'price': -1200.0, 'volume': 800.0, 'variable_cost': -600.0, 'fixed_cost': -300.0}
bridge.biggest_driver  # 'price'

report = check_mece(breakdown_tree("Revenue", 100, {"Retail": 60, "Online": 30}))
print(report.summary())
# MECE check found 1 issue(s):
#   - [missing_bucket] Revenue: branches add to 90.00 but the total is 100.00; 10.00 is unexplained ...
```

Analysis works on any function of named inputs, so every calculator gets it for free:

```python
from casemath.analysis import Triangular, goal_seek, simulate, tornado

def profit(x):
    return (x["price"] - x["unit_cost"]) * x["units"] - x["fixed"]

base = {"price": 10, "unit_cost": 6, "units": 1_000, "fixed": 2_500}
tornado(profit, base).most_sensitive                                    # 'price'
goal_seek(profit, base, "units", target=0, low=0, high=10_000).value    # 625.0
sim = simulate(profit, {**base, "units": Triangular(400, 1_000, 1_100)})
sim.prob_below_threshold, sim.band_90                                   # chance of a loss, 90% range
```

```console
$ casemath invest --rate 0.09 -12000000 2600000 2728000 2861120 2999565 3143547 3293289 4449021
Discount rate      9.0%
NPV                $3,456,238.52
IRR                16.5%
Profitability idx  1.29x
Payback            4.26 periods
Discounted payback 5.48 periods
Decision (NPV > 0) invest
```

Bad inputs raise `casemath.core.ValidationError` (a `ValueError`) with the argument name, for example `price (5) must be above variable_cost_per_unit (6); every unit loses money, so there is no break-even`. The CLI prints that as `error: ...` and exits with code 2.

## Practice cases

| # | Case | Type | Answer in one line |
|---|---|---|---|
| 1 | [Brewline Beverages](docs/cases/case-01-brewline.md) | Profitability | Juice unit costs (+30%) explain 73% of a $3.8M profit drop; the Energy Drinks price cut explains the rest. Fix Juice pricing, reverse the cut. |
| 2 | [VoltWay EV charging](docs/cases/case-02-voltway.md) | Market entry | Retail-only entry needs 24.7% share and pays back in 7.6 years: no. With a fleet anchor of at least 69,159 sessions a year: yes. |
| 3 | [LedgerLite pricing](docs/cases/case-03-ledgerlite.md) | Pricing | A uniform +15% is a wash: small businesses (e = -1.70) leave faster than the 16.7% limit. A $50 Pro tier for accounting firms (e = -0.21) adds $63K a month. |
| 4 | [Northfield / Crestline](docs/cases/case-04-northfield.md) | M&A | The $120M premium is covered by synergies worth $144M after a revenue haircut, but cost synergies alone ($114M) fall $6M short. Walk away above $544M; put the rest in an earn-out. |
| 5 | [Lumen Analytics](docs/cases/case-05-lumen.md) | SaaS pricing | A 17.5% cut needs +28% volume; the test showed +17.5% (elasticity −0.84). Don't cut: test ~$132 and get churn from 3% to 1.8% to reach 3× LTV/CAC. |
| 6 | [Northwind warehouse](docs/cases/case-06-northwind.md) | Investment under uncertainty | NPV +$3.5M, IRR 16.5%, but a 21% chance of loss in simulation. Negotiate 7.3% off the $12M quote to meet the board's 10% risk rule. |

The reasoning behind them is in [docs/frameworks.md](docs/frameworks.md): the profitability framework, MECE thinking, break-even, share metrics, pricing, synergies, valuation, unit economics and deciding under uncertainty.

## Project layout

```
src/casemath/
├── core/          errors, validation, formatting, Result base
├── calculators/   profitability, breakeven, market_share, market_sizing, growth,
│                  pricing, synergy, finance, unit_economics
├── frameworks/    issue_tree, mece, profitability (the standard tree)
├── analysis/      model, sensitivity, goal_seek, scenarios, distributions,
│                  montecarlo, models (built-in models for the CLI)
├── cases/         base, case_01 … case_06
├── drill.py       random practice questions with checked answers
├── web/           api (JSON over the CLI), server (http.server), index.html
└── cli.py         argparse front end
web/               GitHub Pages app that runs the package in the browser (Pyodide)
tests/             one test module per area plus an import-layering check, 498 tests
docs/              PRD, architecture, frameworks guide, case write-ups
```

Layers only import downward (core ← calculators / frameworks ← analysis ← cases / drill ← cli ← web), and a test enforces it. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Requirements: [docs/PRD.md](docs/PRD.md).

## Development

```bash
ruff check src tests && ruff format --check src tests   # lint + format
mypy                                                    # strict typing
pytest --cov                                            # tests, fails under 95% coverage
```

Optional: `pip install pre-commit && pre-commit install` runs ruff on every commit.

### CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull request:

| Job | What it does |
|---|---|
| Lint | `ruff check` and `ruff format --check`, with annotations inline on the PR |
| Type check | `mypy --strict` |
| Test | 3 OS × Python 3.10–3.13, coverage gate at 95%, coverage table in the job summary |
| Solve practice cases | Runs every registered case, a sensitivity tornado and the profitability tree, posts the output to the job summary |
| Build | Builds sdist and wheel, installs the wheel in a clean venv and smoke-tests the CLI |

[`pages.yml`](.github/workflows/pages.yml) tests, builds the wheel and deploys [`web/`](web/index.html) to GitHub Pages on every push to `main`. The page installs that wheel into Pyodide, so the browser runs exactly the code CI tested.

Pushing a tag like `v0.2.0` runs [`release.yml`](.github/workflows/release.yml): it checks the tag matches the package version, re-runs the checks, and attaches the built files to a GitHub Release. Dependabot keeps actions and dev tools current.

See [CONTRIBUTING.md](CONTRIBUTING.md) to add a calculator or a case, and [CHANGELOG.md](CHANGELOG.md) for releases.

## License

MIT
