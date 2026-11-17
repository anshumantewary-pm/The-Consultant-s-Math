"""Ready-made models for the CLI and web app, built from the calculators.

Each entry has a description, its default base case and the function itself, so
``casemath sensitivity profit`` works with no setup and any input can be overridden.
"""

from __future__ import annotations

from dataclasses import dataclass

from casemath.analysis.model import Inputs, Model
from casemath.calculators.finance import npv
from casemath.calculators.profitability import profit_statement
from casemath.calculators.unit_economics import lifetime_value
from casemath.core.errors import UnknownCaseError, ValidationError


def _profit(x: Inputs) -> float:
    return profit_statement(x["price"], x["units"], x["variable_cost"], x["fixed_costs"]).profit


def _project_npv(x: Inputs) -> float:
    years = round(x["years"])
    if years < 1:
        raise ValidationError("years must be at least 1")
    flows = [-x["investment"]] + [
        x["cash_flow"] * (1 + x["growth"]) ** (t - 1) for t in range(1, years + 1)
    ]
    return npv(x["rate"], flows)


def _ltv_to_cac(x: Inputs) -> float:
    if x["cac"] <= 0:
        raise ValidationError("cac must be > 0")
    return lifetime_value(x["revenue"], x["margin"], x["churn"]) / x["cac"]


@dataclass(frozen=True)
class BuiltinModel:
    name: str
    description: str
    output: str
    defaults: dict[str, float]
    function: Model


MODELS: dict[str, BuiltinModel] = {
    m.name: m
    for m in (
        BuiltinModel(
            "profit",
            "One-period profit from unit economics",
            "profit",
            {"price": 10.0, "units": 40_000.0, "variable_cost": 6.0, "fixed_costs": 100_000.0},
            _profit,
        ),
        BuiltinModel(
            "npv",
            "NPV of an investment with a growing annual cash flow",
            "NPV",
            {
                "investment": 1_000_000.0,
                "cash_flow": 250_000.0,
                "growth": 0.03,
                "years": 5.0,
                "rate": 0.10,
            },
            _project_npv,
        ),
        BuiltinModel(
            "ltv-cac",
            "Customer lifetime value divided by acquisition cost (monthly rates)",
            "LTV/CAC",
            {"revenue": 100.0, "margin": 0.8, "churn": 0.04, "cac": 600.0},
            _ltv_to_cac,
        ),
    )
}


def get_model(name: str) -> BuiltinModel:
    try:
        return MODELS[name]
    except KeyError:
        raise UnknownCaseError(f"no model {name!r}; available: {', '.join(MODELS)}") from None
