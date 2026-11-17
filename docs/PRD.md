# PRD: casemath, a consulting case math toolkit

| | |
|---|---|
| Owner | Anshuman Tewary |
| Status | v0.3 shipped |
| Last updated | 2026-11-17 |

## 1. Problem

Case interviews and early consulting work run on a small set of calculations: profit decomposition, break-even, market share and market sizing. Candidates usually do this math on paper under time pressure. The common mistakes repeat:

- **Arithmetic slips** in multi-step profit and break-even math.
- **Non-MECE structures**: branches that overlap, or that leave out a bucket so the numbers do not add back to the total.
- **No "so what"**: a correct number with no recommendation attached.

Spreadsheets fix the arithmetic but not the structure, and they are slow to set up for a 30-minute case.

## 2. Goal

A small, dependency-free Python library and CLI that:

1. Does the standard case calculations correctly and explains each step.
2. Builds a profitability issue tree and checks whether a structure is MECE.
3. Ships fully solved practice cases that use the calculators end to end (two in v0.1, four in v0.2).
4. Is tested and checked by CI on every push, so the numbers can be trusted.

### Non-goals

- No hosted web app. v0.3 adds a local-only UI (`casemath serve`); there are no accounts, no storage and no deployment.
- No financial modelling beyond case-interview scope: no DCF, tax or working capital.
- No automatic judgement of *qualitative* MECE quality. The checker flags structural and numeric faults; a human still decides whether "Channel" and "Region" are a sensible split.

## 3. Users

| User | Need | Example |
|---|---|---|
| Case-interview candidate | Check practice math fast and drill structure | "Is my break-even of 41,667 units right?" |
| Junior consultant / analyst | Quick back-of-envelope numbers with a clean audit trail | "What share do we need to recover the entry cost?" |
| Coach / study group | Worked cases to teach from | Walk through Case 1 step by step |

## 4. User stories

- **US-1** As a candidate, I enter price, volume, unit cost and fixed cost and get revenue, contribution, profit and margins.
- **US-2** As a candidate, I compare two periods and see how much of the profit change came from price, volume, unit cost and fixed cost, and the parts add exactly to the total change.
- **US-3** As a candidate, I get break-even units, break-even revenue, units for a target profit, margin of safety and payback period.
- **US-4** As an analyst, I compute market share, relative market share, market concentration (HHI) and the share needed to hit a revenue target.
- **US-5** As an analyst, I size a market top-down or bottom-up.
- **US-6** As a candidate, I print the standard profitability tree and run a MECE check on a tree with numbers.
- **US-9** As a candidate, I enter a price change and an elasticity (or a test result) and see whether it pays off and how much volume I can afford to lose.
- **US-10** As an analyst, I value a list of cost and revenue synergies, phase them in, and compare their value with the premium being paid.
- **US-11** As a learner, I get random practice questions, type answers the way I would say them ("$1.2M", "25%"), and am told if I am right and why.
- **US-7** As a learner, I list the practice cases, read the prompt and print the full solution with steps and a recommendation.
- **US-8** As any user, I get a clear error (not a crash or a silent wrong answer) when inputs make no sense, such as price below unit cost in a break-even.

## 5. Functional requirements

| ID | Requirement | Story |
|---|---|---|
| FR-1 | `profit_statement(price, units, variable_cost, fixed_costs)` returns revenue, variable costs, contribution, contribution margin %, profit, profit margin % | US-1 |
| FR-2 | `profit_bridge(before, after)` splits ΔProfit into price, volume, variable-cost and fixed-cost effects that sum *exactly* to ΔProfit | US-2 |
| FR-3 | `segment_profitability(segments)` returns per-segment statements, totals and each segment's share of profit | US-2 |
| FR-4 | Break-even: units, revenue, price, target-profit units, margin of safety, payback | US-3 |
| FR-5 | Market share: share, relative share, share table, HHI with DOJ/FTC band, required share, projected share under growth, CAGR | US-4 |
| FR-6 | Market sizing: top-down funnel and bottom-up (units × price) with each step recorded | US-5 |
| FR-7 | Issue tree model with `sum`, `difference` and `product` nodes, evaluation, text rendering | US-6 |
| FR-8 | MECE checker: flags single-child splits, duplicate sibling labels, and parts that do not reconcile to a stated total | US-6 |
| FR-9 | Case registry with two solved cases; each solution has ordered steps and a recommendation | US-7 |
| FR-10 | CLI `casemath` with subcommands `profit`, `bridge`, `breakeven`, `share`, `hhi`, `size`, `tree`, `case`; every command supports `--json` | All |
| FR-12 | Pricing: arc elasticity, break-even volume change, price-change impact under a linear elasticity, constant-elasticity markup rule | US-9 |
| FR-13 | Synergies: cost and revenue items with margin and probability haircut, phase-in schedule with integration costs and payback year, value at a multiple, premium % | US-10 |
| FR-14 | Cases 3 (pricing) and 4 (M&A synergy) in the registry, same rules as FR-9 | US-7 |
| FR-15 | `casemath drill`: seeded questions across seven topics, answer parsing (`$`, `K/M/B`, `%`, `x`), tolerance check, `--reveal` and `--json` answer keys; CLI adds `price` and `synergy` | US-11 |
| FR-16 | `casemath serve`: local web UI (calculators, cases, drill) over a JSON API that reuses the CLI parser and handlers; stdlib only, binds to localhost by default, 64 KB body limit | All |
| FR-11 | All invalid inputs raise `casemath.ValidationError` (a `ValueError`); the CLI turns these into a one-line message and exit code 2 | US-8 |

## 6. Non-functional requirements

| ID | Requirement | How it is checked |
|---|---|---|
| NFR-1 | Zero runtime dependencies | `dependencies = []` in `pyproject.toml` |
| NFR-2 | Python 3.10 to 3.13 on Linux, macOS, Windows | CI test matrix |
| NFR-3 | Fully typed; `mypy --strict` passes | CI `typecheck` job |
| NFR-4 | Lint and format clean | CI `lint` job (ruff) |
| NFR-5 | ≥ 95% branch coverage | `fail_under = 95` in coverage config |
| NFR-6 | Results are immutable and JSON-serialisable | Frozen dataclasses + `to_dict()`; tests round-trip through `json.dumps` |
| NFR-7 | Each calculator is a pure function: same input, same output, no I/O | Architecture rule; see [ARCHITECTURE.md](ARCHITECTURE.md) |

## 7. Success metrics

- All practice cases produce the documented answers in CI on every push.
- CI green on all 12 matrix cells (3 OS × 4 Python versions).
- A new calculator can be added by touching one module, its tests and one CLI handler, without editing any other calculator.

## 8. Release plan

| Version | Scope |
|---|---|
| v0.1 | FR-1 to FR-11, two cases, CI, docs |
| v0.2 | Pricing and synergy calculators, Case 3 (pricing), Case 4 (M&A synergy), `casemath drill`, CLI `price` and `synergy` (FR-12 to FR-15) |
| **v0.3** (this release) | Local web front end on top of the CLI's JSON output (FR-16) |

## 9. Risks

| Risk | Mitigation |
|---|---|
| Floating-point noise makes answers look wrong (e.g. 0.30000000000000004) | Formatting layer rounds for display; tests use `pytest.approx` |
| Users trust the MECE checker too much | Docs and checker output say it checks structure and numbers, not judgement |
| Scope creep into full financial modelling | Non-goals above; anything beyond case scope goes to the backlog |
