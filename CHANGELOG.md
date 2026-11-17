# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

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
