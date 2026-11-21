# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added

- Business Advisor: `casemath.advisor` compares a company's figures with indicative ranges for 10 sectors (SaaS, e-commerce, retail, manufacturing, restaurants, professional services, healthcare, fintech, logistics, consumer goods). It returns a 0-100 health score, gross/EBITDA/opex margins, growth, Rule of 40, debt/EBITDA, a valuation on sector multiples, break-even revenue, cash runway, unit economics and prioritised suggestions that use each sector's own levers. `parse_financials` reads an uploaded `metric,value` CSV (multi-year rows supported).
- CLI: `advise` (flags or `--file data.csv`) and `sectors`.
- Web: `advisor.html` on GitHub Pages lets you upload a CSV or fill in a form and get the report in the browser, with print-to-PDF and JSON download.

## [0.4.0] - 2026-11-18

Combines the advanced-analytics work with 0.2.0 and 0.3.0 below.

### Added

- Finance: `npv`, `irr` (bracketed bisection), simple and discounted payback, annuity PV, Gordon-growth perpetuity, `investment_appraisal` (NPV, IRR, profitability index, both paybacks, accept flag).
- Pricing: `optimal_price_linear` (best price on a straight-line demand curve through two observations) and `volume_after_price_change` under constant elasticity, alongside the 0.2.0 pricing calculators.
- Unit economics: customer lifetime, LTV (optionally discounted), CAC payback, `unit_economics` with a 3x LTV/CAC health check.
- Break-even: degree of operating leverage.
- New `casemath.analysis` layer working on any model (a function of named inputs): one-way sensitivity, tornado, two-way data table, goal seek, weighted scenarios with expected value, Monte Carlo with Fixed / Uniform / Triangular / Normal inputs, percentiles, probability below a threshold and a histogram. Seeded and reproducible.
- Built-in models (`profit`, `npv`, `ltv-cac`) for the CLI.
- CLI: `invest`, `unit-econ`, `optimal-price`, `models`, `sensitivity`, `goalseek`, `simulate`.
- Practice cases: Case 5 Lumen Analytics (SaaS pricing), Case 6 Northwind (investment under uncertainty).
- GitHub Pages web app (Pyodide) with panels for the calculators, analysis tools and all six cases.
- `UnknownModelError` and a shared `UnknownNameError` base; `require_count` and `require_numbers` validators.
- Tests that enforce the layered import rules and keep the package and pyproject versions in step.
- Docs: frameworks guide sections on valuation, unit economics and uncertainty; Case 5 and 6 write-ups; architecture and PRD updated.

### Changed

- CI solves every registered case (no hard-coded list), adds a tornado to the job summary and smoke-tests `invest` and `simulate` from the built wheel.
- Case 6's seeded solution is memoised, keeping the test suite fast.

### Fixed

- `casemath serve` on Windows: the server now asks for exclusive use of its port, so a port already in use is reported instead of silently shared (which also hung the test suite).

## [0.3.0] - 2026-11-17

### Added

- `casemath serve`: a local web UI with every calculator, the four practice cases and the drill. Standard library only (`http.server`), localhost by default, `--open` to launch a browser.
- `casemath.web.call(command, body)`: JSON API that maps a body onto CLI arguments and runs the CLI's own parser and handler, so web and terminal results never differ. `POST /api/check` grades a drill answer.

## [0.2.0] - 2026-11-17

### Added

- Pricing calculators: arc (midpoint) price elasticity, break-even volume change for a price move, price-change impact under a linear elasticity, profit-maximising price for constant-elasticity demand.
- M&A synergy calculators: `SynergyItem` (cost or revenue, margin, probability haircut), `synergy_schedule` with phase-in, integration costs and payback year, `synergy_value`, `acquisition_premium`.
- Practice cases: Case 3 LedgerLite (pricing and segmentation), Case 4 Northfield Foods / Crestline Snacks (M&A synergies vs premium).
- `casemath drill`: random practice questions across profit, break-even, share, sizing, growth, pricing and synergy topics. Seeded for repeatability, forgiving answer parsing, `--reveal` / `--json` answer keys.
- CLI `price` and `synergy` commands.

### Changed

- CI solves all four cases in the job summary.

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
