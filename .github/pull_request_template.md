## What and why

<!-- One or two sentences. Link the PRD requirement (FR-x) if there is one. -->

## Checklist

- [ ] Calculators stay pure (no printing, no I/O) and validate their inputs
- [ ] New results are frozen dataclasses that `to_dict()` cleanly
- [ ] Tests cover the happy path, edge cases and validation errors
- [ ] `ruff check`, `ruff format --check`, `mypy` and `pytest --cov` pass locally
- [ ] README / docs updated if behaviour changed
