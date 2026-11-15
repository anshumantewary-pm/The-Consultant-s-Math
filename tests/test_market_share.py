import json

import pytest

from casemath.calculators import (
    cagr,
    grow,
    hhi,
    market_share,
    project_share,
    relative_market_share,
    required_share,
    rule_of_72,
    share_table,
)
from casemath.core import ValidationError


class TestGrowth:
    def test_cagr(self) -> None:
        assert cagr(100, 121, 2) == pytest.approx(0.10)

    def test_cagr_decline(self) -> None:
        assert cagr(100, 81, 2) == pytest.approx(-0.10)

    def test_grow(self) -> None:
        assert grow(100, 0.1, 2) == pytest.approx(121)
        assert grow(100, 0.1, 0) == 100

    def test_grow_rejects_minus_100(self) -> None:
        with pytest.raises(ValidationError):
            grow(100, -1, 1)

    def test_rule_of_72(self) -> None:
        assert rule_of_72(0.08) == pytest.approx(9)


class TestShare:
    def test_market_share(self) -> None:
        assert market_share(50, 400) == pytest.approx(0.125)

    def test_cannot_exceed_market(self) -> None:
        with pytest.raises(ValidationError, match="cannot exceed"):
            market_share(500, 400)

    def test_relative_share(self) -> None:
        assert relative_market_share(60, 40) == pytest.approx(1.5)

    def test_required_share(self) -> None:
        assert required_share(30, 600) == pytest.approx(0.05)
        assert required_share(900, 600) > 1


class TestShareTable:
    def test_rows_sorted_with_relative_share(self) -> None:
        table = share_table({"B": 30, "A": 50, "C": 20})
        assert [r.name for r in table.rows] == ["A", "B", "C"]
        assert table.leader == "A"
        assert table.total == 100
        assert table.shares() == {"A": 0.5, "B": 0.3, "C": 0.2}
        assert table.rows[0].relative_share == pytest.approx(50 / 30)
        assert table.rows[1].relative_share == pytest.approx(30 / 50)

    def test_single_player(self) -> None:
        table = share_table({"Mono": 10})
        assert table.rows[0].share == 1
        assert table.rows[0].relative_share is None
        assert json.dumps(table.to_dict())  # stays strict JSON (no Infinity)

    def test_rejects_all_zero(self) -> None:
        with pytest.raises(ValidationError, match="all be zero"):
            share_table({"A": 0, "B": 0})

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValidationError, match="revenues\\['A'\\]"):
            share_table({"A": -1})

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            share_table({})


class TestHHI:
    @pytest.mark.parametrize(
        ("shares", "index", "band"),
        [
            ({"M": 1.0}, 10_000, "highly concentrated"),
            ({"A": 0.3, "B": 0.3, "C": 0.2, "D": 0.2}, 2_600, "highly concentrated"),
            ({f"p{i}": 0.1 for i in range(10)}, 1_000, "moderately concentrated"),
            ({f"p{i}": 0.05 for i in range(20)}, 500, "unconcentrated"),
        ],
    )
    def test_bands(self, shares: dict[str, float], index: float, band: str) -> None:
        result = hhi(shares)
        assert result.hhi == pytest.approx(index)
        assert result.band == band
        assert result.players == len(shares)

    def test_rejects_over_100_percent(self) -> None:
        with pytest.raises(ValidationError, match="must not exceed 1"):
            hhi({"A": 0.7, "B": 0.5})

    def test_partial_shares_allowed(self) -> None:
        assert hhi({"A": 0.4}).top_share == 0.4


class TestProjection:
    def test_gains_share_when_outgrowing_market(self) -> None:
        proj = project_share(10, 100, company_growth=0.2, market_growth=0.05, years=3)
        assert proj.years == (0, 1, 2, 3)
        assert proj.share[0] == pytest.approx(0.10)
        assert proj.final_share == pytest.approx(10 * 1.2**3 / (100 * 1.05**3))
        assert list(proj.share) == sorted(proj.share)

    def test_json(self) -> None:
        proj = project_share(10, 100, 0.1, 0.1, 1)
        assert json.loads(json.dumps(proj.to_dict()))["share"] == pytest.approx([0.1, 0.1])

    @pytest.mark.parametrize("years", [-1, 1.5, True])
    def test_rejects_bad_years(self, years: object) -> None:
        with pytest.raises(ValidationError, match="whole number"):
            project_share(10, 100, 0.1, 0.1, years)  # type: ignore[arg-type]
