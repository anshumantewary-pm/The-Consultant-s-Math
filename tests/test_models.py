import pytest

from casemath.analysis.models import MODELS, get_model
from casemath.core import UnknownCaseError, ValidationError


@pytest.mark.parametrize("name", list(MODELS))
def test_defaults_evaluate(name: str) -> None:
    model = get_model(name)
    assert isinstance(model.function(model.defaults), float)


def test_profit_default() -> None:
    m = get_model("profit")
    assert m.function(m.defaults) == pytest.approx(60_000)


def test_npv_flat_matches_annuity() -> None:
    m = get_model("npv")
    x = {**m.defaults, "growth": 0.0, "years": 3.0, "investment": 1_000.0, "cash_flow": 500.0}
    assert m.function(x) == pytest.approx(243.426, abs=1e-3)


def test_npv_needs_a_year() -> None:
    m = get_model("npv")
    with pytest.raises(ValidationError, match="years"):
        m.function({**m.defaults, "years": 0.2})


def test_ltv_cac() -> None:
    m = get_model("ltv-cac")
    assert m.function(m.defaults) == pytest.approx(2_000 / 600)
    with pytest.raises(ValidationError, match="cac"):
        m.function({**m.defaults, "cac": 0})


def test_unknown() -> None:
    with pytest.raises(UnknownCaseError, match="available: profit"):
        get_model("dcf")
