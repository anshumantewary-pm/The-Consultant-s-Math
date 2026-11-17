# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [0.2.0] - 2026-11-18

### Added

- Finance: `npv`, `irr` (bracketed bisection), simple and discounted payback, annuity PV, Gordon-growth perpetuity, `investment_appraisal` (NPV, IRR, profitability index, both paybacks, accept flag).
- Pricing: arc elasticity, break-even volume for a price change, volume under constant elasticity, Lerner markup price, linear-demand optimal price.
- Unit economics: customer lifetime, LTV (optionally discounted), CAC payback, `unit_economics` with a 3x LTV/CAC health check.
- Break-even: degree of operating leverage.
- New `casemath.analysis` layer working on any model (a function of named inputs): one-way sensitivity, tornado, two-way data table, goal seek, weighted scenarios with expected value, Monte Carlo with Fixed / Uniform / Triangular / Normal inputs, percentiles, probability below a threshold and a histogram. Seeded and reproducible.
- Built-in models (`profit`, `npv`, `ltv-cac`) for the CLI.
- CLI: `invest`, `unit-econ`, `pricing change|elasticity|optimal`, `models`, `sensitivity`, `goalseek`, `simulate`.
- Practice cases: Case 3 Lumen Analytics (SaaS pricing), Case 4 Northwind (investment under uncertainty).
- Web app (GitHub Pages, Pyodide) with panels for every command, including the new ones.
- `UnknownModelError` and a shared `UnknownNameError` base; `require_count` and `require_numbers` validators.
- Test that enforces the layered import rules; test that the package and pyproject versions match.
- Docs: frameworks guide sections on valuation, pricing, unit economics and uncertainty; Case 3 and 4 write-ups; architecture and PRD updated for v0.2.

### Changed

- CI solves every registered case (no hard-coded list), adds a tornado to the job summary and smoke-tests `invest` and `simulate` from the built wheel.
- Case 4's seeded solution is memoised, keeping the test suite fast.

## [0.1.0] - 2026-11-15

### Added

- Core: error hierarchy, input validation, number formatting, `Result` base with `to_dict()`.
- Profitability: profit statement, exact four-way profit bridge, segment profitability.
- Break-even: units, revenue, price, units for target profit, margin of safety, payback.
- Market share: share, relative share, required share, share table, HHI with concentration bands, share projection, CAGR.
- Market sizing: top-down and bottom-up with recorded steps.
- Frameworks: issue-tree model, standard profitability tree with interviewer questions, MECE checker.
- Practice cases: Case 1 Brewline Beverages (profitability), Case 2 VoltWay (market entry).
- CLI `casemath` with `profit`, `bridge`, `breakeven`, `share`, `hhi`, `size`, `tree`, `case`, all with `--json`.
- CI: lint, strict typing, 12-cell test matrix with 95% coverage gate, case solutions in job summary, wheel build and smoke test. Tag-triggered release workflow. Dependabot.
- Docs: PRD, architecture, frameworks guide, case write-ups.

### Fixed

- Issue trees now print through Windows pipes (stdout forced to UTF-8).
