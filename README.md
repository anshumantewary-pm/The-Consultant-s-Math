# casemath

[![CI](https://github.com/anshumantewary-pm/The-Consultant-s-Math/actions/workflows/ci.yml/badge.svg)](https://github.com/anshumantewary-pm/The-Consultant-s-Math/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20to%203.13-blue)
![Coverage](https://img.shields.io/badge/coverage-%E2%89%A595%25-brightgreen)
![Dependencies](https://img.shields.io/badge/runtime%20deps-0-brightgreen)

A consulting case math toolkit. Profitability, break-even, market share and market sizing calculators, a MECE issue-tree checker, and two fully solved practice cases. Python library and CLI, no runtime dependencies.

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
| **Frameworks** | `profitability_tree`, issue-tree `Node`, `render`, `check_mece` | `tree` |
| **Practice cases** | `get_case("1").solve()` | `case list / show / solve` |

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

# The profitability framework, with the question to ask at each node
casemath tree --hints

# Practice cases
casemath case list
casemath case show 1
casemath case solve 2
```

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

Bad inputs raise `casemath.core.ValidationError` (a `ValueError`) with the argument name, for example `price (5) must be above variable_cost_per_unit (6); every unit loses money, so there is no break-even`. The CLI prints that as `error: ...` and exits with code 2.

## Practice cases

| # | Case | Type | Answer in one line |
|---|---|---|---|
| 1 | [Brewline Beverages](docs/cases/case-01-brewline.md) | Profitability | Juice unit costs (+30%) explain 73% of a $3.8M profit drop; the Energy Drinks price cut explains the rest. Fix Juice pricing, reverse the cut. |
| 2 | [VoltWay EV charging](docs/cases/case-02-voltway.md) | Market entry | Retail-only entry needs 24.7% share and pays back in 7.6 years: no. With a fleet anchor of at least 69,159 sessions a year: yes. |

The reasoning behind both is in [docs/frameworks.md](docs/frameworks.md): the profitability framework, MECE thinking, break-even and share metrics.

## Project layout

```
src/casemath/
├── core/          errors, validation, formatting, Result base
├── calculators/   profitability, breakeven, market_share, market_sizing, growth
├── frameworks/    issue_tree, mece, profitability (the standard tree)
├── cases/         base, case_01_profit_decline, case_02_market_entry
└── cli.py         argparse front end
tests/             one test module per area, 175 tests
docs/              PRD, architecture, frameworks guide, case write-ups
```

Layers only import downward (core ← calculators / frameworks ← cases ← cli). Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Requirements: [docs/PRD.md](docs/PRD.md).

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
| Solve practice cases | Runs both cases and the profitability tree, posts the output to the job summary |
| Build | Builds sdist and wheel, installs the wheel in a clean venv and smoke-tests the CLI |

Pushing a tag like `v0.1.0` runs [`release.yml`](.github/workflows/release.yml): it checks the tag matches the package version, re-runs the checks, and attaches the built files to a GitHub Release. Dependabot keeps actions and dev tools current.

See [CONTRIBUTING.md](CONTRIBUTING.md) to add a calculator or a case, and [CHANGELOG.md](CHANGELOG.md) for releases.

## License

MIT
