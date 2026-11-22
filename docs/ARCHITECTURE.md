# Architecture

casemath is a layered library with a thin CLI on top. Each layer only imports from the layers below it.

```
            ┌──────────────────────────────────────────────────────┐
  Browser   │  src/casemath/web/  local UI: POST /api/<command>     │
            │    api.call → cli parser + handler                    │
            │  web/ (repo root)   GitHub Pages apps: Pyodide runs   │
            │    cli.main() in the browser (index · advisor.html)   │
            └──────────────────────────┬───────────────────────────┘
                                       │
            ┌──────────────────────────▼───────────────────────────┐
  Interface │  cli.py  (argparse, text / --json output)             │
            └──────────────────────────┬───────────────────────────┘
                                       │
            ┌──────────────────────────▼───────────────────────────┐
  Use cases │  cases/  1 profitability · 2 entry · 3 pricing ·      │
            │          4 M&A synergy · 5 SaaS pricing · 6 investment│
            │  drill.py  random questions, checked answers          │
            │  advisor.py  sector benchmarks, score, suggestions    │
            └───────┬──────────────────────┬───────────────┬───────┘
                    │                      │               │
            ┌───────▼──────────────────────┴──┐            │
  Analysis  │ analysis/  model · sensitivity  │            │
            │  goal_seek · scenarios ·        │            │
            │  distributions · montecarlo ·   │            │
            │  models (built-in, for the CLI) │            │
            └───────┬─────────────────────────┘            │
                    │                                      │
   ┌────────────────▼──────────┐ ┌─────────────────────────▼┐
   │ calculators/              │ │ frameworks/              │
   │  profitability · breakeven│ │  issue_tree.py  (Node,   │
   │  market_share · sizing    │ │   evaluate, render)      │
   │  growth · finance         │ │  mece.py  (checker)      │
   │  pricing · synergy        │ │  profitability.py        │
   │  unit_economics           │ │                          │
   └────────────────┬──────────┘ └──────────┬───────────────┘
                    │                       │
            ┌───────▼───────────────────────▼──────────┐
  Core      │  core/  errors · validate · formatting   │
            │         Result base (to_dict)            │
            └──────────────────────────────────────────┘
```

## Layers

| Layer | Package | Job | May import |
|---|---|---|---|
| Core | `casemath.core` | Errors, input validation, number formatting, the `Result` base class | stdlib only |
| Calculators | `casemath.calculators` | Pure math functions that return frozen result dataclasses | core |
| Frameworks | `casemath.frameworks` | Issue tree model, MECE checker, the standard profitability tree | core |
| Analysis | `casemath.analysis` | Model-agnostic tools: sensitivity (one-way, tornado, two-way), goal seek, scenarios, Monte Carlo. Only `models.py` (the CLI's built-in models) imports calculators | core (+ calculators in `models.py`) |
| Cases | `casemath.cases` | Practice cases: data + a `solve()` that chains calculators and analysis | analysis, calculators, frameworks, core |
| Drill | `casemath.drill` | Seeded question generators whose answer key comes from the calculators; `run_drill` takes `ask`/`say` callables | calculators, core |
| Advisor | `casemath.advisor` | Business Advisor: 10 sector benchmark sets, `parse_financials` (metric,value CSV), `assess` returns a 0-100 score, valuation range, break-even, runway, unit economics and prioritised suggestions | calculators, core |
| Interface | `casemath.cli` | Parse arguments, call the library, print text or JSON | everything |
| Web | `casemath.web` | Turn a JSON body into CLI arguments, run the CLI handler, serve the page | cli, drill |

Calculators and frameworks do not import each other. The CLI is the only place that does I/O: `drill.run_drill` asks and prints only through the `input`/`print` callables the CLI hands it.

### The Model abstraction

`analysis` never knows what it is analysing. A `Model` is any function from a mapping of named inputs to one number:

```python
def profit(x):  # Model = Callable[[Mapping[str, float]], float]
    return (x["price"] - x["unit_cost"]) * x["units"] - x["fixed"]

tornado(profit, base)                         # which input matters most
goal_seek(profit, base, "units", target=0, low=0, high=1e6)
simulate(profit, {**base, "units": Triangular(800, 1000, 1100)})
```

So every calculator gets sensitivity, goal seek and simulation for free with a one-line wrapper, and the tools compose: Case 4 goal-seeks on a model whose output is itself a simulated probability.

## Deployment and launch

```
push to main ──► ci.yml     lint · mypy · tests (3 OS × 4 Pythons) · cases · wheel smoke test
             └─► pages.yml  test ─► build wheel ─► copy web/ + wheel ─► deploy GitHub Pages
tag vX.Y.Z  ───► release.yml  tag == package version ─► checks ─► GitHub Release with sdist + wheel
```

| Surface | Where it runs | How to launch |
|---|---|---|
| Calculators web app | Browser (Pyodide loads the CI-built wheel) | https://anshumantewary-pm.github.io/The-Consultant-s-Math/ |
| Business Advisor | Browser (Pyodide) | https://anshumantewary-pm.github.io/The-Consultant-s-Math/advisor.html |
| Local web UI | `http.server` on 127.0.0.1 | `casemath serve --open` |
| CLI / library | Python 3.10+ | `pip install -e .` then `casemath --help` |

The Pages apps have no backend: the first load downloads Pyodide (about 10 MB, then cached), installs the wheel and calls `cli.main()` in the page, so nothing a user types or uploads leaves the browser.

## Design rules

1. **Pure functions.** Every calculator takes plain numbers and returns a value. No globals, no printing, no files. This is what makes them trivial to test and reuse from a notebook, a web API or the CLI.
2. **Validate at the edge of each function.** Each calculator checks its own inputs with `core.validate` and raises `ValidationError` with the argument name in the message. There is no "garbage in, garbage out".
3. **Immutable, serialisable results.** Results are `@dataclass(frozen=True)` subclasses of `core.Result`, which gives them `to_dict()`. The CLI's `--json` flag is just `json.dumps(result.to_dict())`.
4. **Show the work.** Multi-step results (market sizing, case solutions) carry an ordered list of `Step(label, value, unit)` so the reasoning is part of the output, which is how a case should be presented.
5. **Exact decompositions.** Where we split a number into parts (profit bridge, MECE reconciliation) the parts must add back to the whole. Tests assert this.
6. **Reproducible randomness.** Monte Carlo draws from an injected `random.Random(seed)`; the default seed is fixed, so the same inputs always give the same answer and tests can assert exact values.
7. **Floats in, rounding only for display.** Math uses `float`; `core.formatting` rounds when printing. Tests compare with `pytest.approx`.

## Data flow: `casemath case solve 1`

```
cli.main(argv)
  └─ cases.get_case("1")                     registry lookup
       └─ Case.solve()
            ├─ calculators.profit_statement   × 2 years × 3 segments
            ├─ calculators.profit_bridge      per segment
            ├─ frameworks.check_mece          revenue tree reconciles?
            └─ returns Solution(steps, findings, recommendation)
  └─ render text, or json.dumps(solution.to_dict())
```

## Error handling

```
ValidationError (ValueError)      bad input; CLI prints "error: ..." and exits 2
CaseMathError (Exception)         base class for anything raised on purpose
UnknownNameError (CaseMathError, KeyError)   failed lookup by name
  ├─ UnknownCaseError                        bad case id
  └─ UnknownModelError                       bad built-in model name
```

The CLI catches `CaseMathError` only. Anything else is a bug and should surface with a traceback.

## Adding a calculator

1. Add `calculators/<name>.py` with pure functions and a frozen result dataclass.
2. Re-export it from `calculators/__init__.py`.
3. Add `tests/test_<name>.py` (happy path, edge cases, validation errors).
4. Add a subcommand in `cli.py` (a parser builder plus a handler).

No other module changes. CI enforces typing, lint and coverage.

## CI/CD

```
push / PR ──► lint (ruff check + format) ─┐
          ──► typecheck (mypy --strict) ──┼─► build (sdist + wheel, CLI smoke test)
          ──► test matrix 3 OS × 4 Py ────┘        │
                 coverage ≥ 95%                    ▼
                                           artifact: dist/
tag v* ──► release workflow: build, test, attach dist/ to a GitHub Release
weekly ──► Dependabot: GitHub Actions + pip updates
```
