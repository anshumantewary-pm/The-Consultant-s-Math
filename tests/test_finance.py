import pytest

from casemath.calculators.finance import (
    annuity_pv,
    discount_factor,
    npv,
    perpetuity,
    present_value,
)
from casemath.core import ValidationError


class TestDiscounting:
    def test_discount_factor(self) -> None:
        assert discount_factor(0.10, 2) == pytest.approx(1 / 1.21)

    def test_today_is_undiscounted(self) -> None:
        assert discount_factor(0.10, 0) == 1

    def test_present_value(self) -> None:
        assert present_value(121, 0.10, 2) == pytest.approx(100)

    def test_rejects_negative_period(self) -> None:
        with pytest.raises(ValidationError, match="period"):
            discount_factor(0.1, -1)


class TestNpv:
    def test_textbook(self) -> None:
        # -1000 today, then 500 for three years at 10%: 243.43
        assert npv(0.10, [-1_000, 500, 500, 500]) == pytest.approx(243.4260, abs=1e-3)

    def test_zero_rate_is_plain_sum(self) -> None:
        assert npv(0, [-10, 4, 4, 4]) == pytest.approx(2)

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="flows must not be empty"):
            npv(0.1, [])

    def test_rejects_rate_at_minus_100(self) -> None:
        with pytest.raises(ValidationError, match="rate"):
            npv(-1, [1])


class TestAnnuity:
    def test_matches_npv(self) -> None:
        assert annuity_pv(500, 0.10, 3) == pytest.approx(npv(0.10, [0, 500, 500, 500]))

    def test_zero_rate(self) -> None:
        assert annuity_pv(100, 0, 5) == 500

    @pytest.mark.parametrize("bad", [-1, 2.5, True])
    def test_rejects_bad_periods(self, bad: object) -> None:
        with pytest.raises(ValidationError, match="periods"):
            annuity_pv(100, 0.1, bad)  # type: ignore[arg-type]


class TestPerpetuity:
    def test_flat(self) -> None:
        assert perpetuity(100, 0.08) == pytest.approx(1_250)

    def test_growing(self) -> None:
        assert perpetuity(100, 0.10, growth=0.02) == pytest.approx(1_250)

    def test_rejects_growth_at_or_above_rate(self) -> None:
        with pytest.raises(ValidationError, match="infinitely"):
            perpetuity(100, 0.05, growth=0.05)
