import json

import pytest

from casemath.calculators.unit_economics import (
    cac_payback,
    customer_lifetime,
    lifetime_value,
    unit_economics,
)
from casemath.core import ValidationError


def test_customer_lifetime() -> None:
    assert customer_lifetime(0.04) == pytest.approx(25)


class TestLifetimeValue:
    def test_undiscounted(self) -> None:
        # $100/month at 80% margin, 4% monthly churn: 80 x 25 = 2,000
        assert lifetime_value(100, 0.8, 0.04) == pytest.approx(2_000)

    def test_discounting_lowers_ltv(self) -> None:
        # 80 x 1.01 / 0.05 = 1,616
        assert lifetime_value(100, 0.8, 0.04, discount_rate=0.01) == pytest.approx(1_616)

    def test_zero_churn_rejected(self) -> None:
        with pytest.raises(ValidationError, match="lasts forever"):
            lifetime_value(100, 0.8, 0)

    def test_margin_must_be_fraction(self) -> None:
        with pytest.raises(ValidationError, match="gross_margin"):
            lifetime_value(100, 80, 0.04)


class TestCacPayback:
    def test_months(self) -> None:
        assert cac_payback(600, 100, 0.8) == pytest.approx(7.5)

    def test_zero_margin(self) -> None:
        with pytest.raises(ValidationError, match="pay back CAC"):
            cac_payback(600, 100, 0)


class TestUnitEconomics:
    def test_healthy(self) -> None:
        ue = unit_economics(100, 0.8, 0.04, cac=600)
        assert ue.ltv_to_cac == pytest.approx(2_000 / 600)
        assert ue.cac_payback_periods == pytest.approx(7.5)
        assert ue.payback_within_lifetime
        assert ue.healthy

    def test_unhealthy_ratio(self) -> None:
        assert not unit_economics(100, 0.8, 0.04, cac=1_000).healthy

    def test_payback_after_churn(self) -> None:
        # Lifetime 2 months, payback 10 months.
        ue = unit_economics(10, 0.5, 0.5, cac=50)
        assert not ue.payback_within_lifetime
        assert not ue.healthy

    def test_cac_positive(self) -> None:
        with pytest.raises(ValidationError, match="cac"):
            unit_economics(100, 0.8, 0.04, cac=0)

    def test_json(self) -> None:
        assert json.loads(json.dumps(unit_economics(100, 0.8, 0.04, 600).to_dict()))["ltv"] == 2000
