# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

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
