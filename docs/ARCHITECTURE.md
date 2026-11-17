# Architecture

casemath is a layered library with a thin CLI on top. Each layer only imports from the layers below it.

```
            ┌──────────────────────────────────────────┐
  Interface │  cli.py  (argparse, text / --json output) │
            └───────────────┬──────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────┐
  Use cases │  cases/   1 profitability · 2 entry      │
            │           3 pricing · 4 M&A synergy      │
            │  drill.py random questions, checked      │
            └───────┬───────────────────────┬──────────┘
                    │                       │
   ┌────────────────▼──────────┐ ┌──────────▼───────────────┐
   │ calculators/              │ │ frameworks/              │
   │  profitability.py         │ │  issue_tree.py  (Node,   │
   │  breakeven.py             │ │   evaluate, render)      │
   │  market_share.py          │ │  mece.py  (checker)      │
   │  market_sizing.py         │ │  profitability.py (the   │
   │  growth.py                │ │   standard tree)         │
   │  pricing.py · synergy.py  │ │                          │
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
| Cases | `casemath.cases` | Practice cases: data + a `solve()` that chains calculators | calculators, frameworks, core |
| Drill | `casemath.drill` | Seeded question generators whose answer key comes from the calculators; `run_drill` takes `ask`/`say` callables | calculators, core |
| Interface | `casemath.cli` | Parse arguments, call the library, print text or JSON | everything |

Calculators and frameworks do not import each other. The CLI is the only place that does I/O: `drill.run_drill` asks and prints only through the `input`/`print` callables the CLI hands it.

## Design rules

1. **Pure functions.** Every calculator takes plain numbers and returns a value. No globals, no printing, no files. This is what makes them trivial to test and reuse from a notebook, a web API or the CLI.
2. **Validate at the edge of each function.** Each calculator checks its own inputs with `core.validate` and raises `ValidationError` with the argument name in the message. There is no "garbage in, garbage out".
3. **Immutable, serialisable results.** Results are `@dataclass(frozen=True)` subclasses of `core.Result`, which gives them `to_dict()`. The CLI's `--json` flag is just `json.dumps(result.to_dict())`.
4. **Show the work.** Multi-step results (market sizing, case solutions) carry an ordered list of `Step(label, value, unit)` so the reasoning is part of the output, which is how a case should be presented.
5. **Exact decompositions.** Where we split a number into parts (profit bridge, MECE reconciliation) the parts must add back to the whole. Tests assert this.
6. **Floats in, rounding only for display.** Math uses `float`; `core.formatting` rounds when printing. Tests compare with `pytest.approx`.

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
UnknownCaseError (CaseMathError, KeyError)   bad case id
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
