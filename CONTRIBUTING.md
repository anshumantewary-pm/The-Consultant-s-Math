# Contributing

## Setup

```bash
pip install -e ".[dev]"
pre-commit install        # optional
```

## Before you push

```bash
ruff check src tests && ruff format --check src tests
mypy
pytest --cov
```

CI runs the same checks on Linux, macOS and Windows.

## Adding a calculator

1. Create `src/casemath/calculators/<name>.py`. Functions must be pure: no printing, files or globals.
2. Validate every input with `casemath.core.validate` so bad input raises `ValidationError` naming the argument.
3. Return a float or a `@dataclass(frozen=True)` subclass of `casemath.core.Result`.
4. Re-export from `calculators/__init__.py`.
5. Add `tests/test_<name>.py`: a worked example you checked by hand, edge cases (zero, boundaries), and each validation error.
6. Add a CLI subcommand in `cli.py`: a parser block in `build_parser` and a `_handler` that returns `Output(text, data)`.

## Adding a practice case

1. Create `src/casemath/cases/case_NN_<slug>.py` with a `Case` subclass: `id`, `title`, `case_type`, `skills`, `prompt`, and `data()`, `structure()`, `solve()`.
2. `solve()` must use the calculators, not re-implement the math, and return a `Solution` with steps, findings, a recommendation, and an `answer` dict.
3. Register it in `cases/__init__.py`.
4. Add `tests/test_case_NN.py` asserting every number in `answer`.
5. Write it up in `docs/cases/` and add a row to the README table.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/): `feat(calculators): ...`, `fix(cli): ...`, `docs: ...`, `ci: ...`, `test: ...`, `chore: ...`.
