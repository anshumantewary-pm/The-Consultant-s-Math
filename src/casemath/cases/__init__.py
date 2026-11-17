"""Practice cases. Look one up with ``get_case("1")``."""

from casemath.cases.base import Case, Solution, render_case, render_solution
from casemath.cases.case_01_profit_decline import ProfitDeclineCase
from casemath.cases.case_02_market_entry import MarketEntryCase
from casemath.cases.case_03_saas_pricing import SaasPricingCase
from casemath.core.errors import UnknownCaseError

_REGISTRY: dict[str, type[Case]] = {
    case.id: case for case in (ProfitDeclineCase, MarketEntryCase, SaasPricingCase)
}


def list_cases() -> list[Case]:
    return [cls() for cls in _REGISTRY.values()]


def get_case(case_id: str) -> Case:
    try:
        return _REGISTRY[str(case_id)]()
    except KeyError:
        known = ", ".join(_REGISTRY)
        raise UnknownCaseError(f"no case {case_id!r}; available: {known}") from None


__all__ = [
    "Case",
    "MarketEntryCase",
    "ProfitDeclineCase",
    "SaasPricingCase",
    "Solution",
    "get_case",
    "list_cases",
    "render_case",
    "render_solution",
]
