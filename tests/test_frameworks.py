import json

import pytest

from casemath.calculators import profit_statement
from casemath.core import ValidationError
from casemath.frameworks import (
    Node,
    branch,
    breakdown_tree,
    check_mece,
    computed_value,
    evaluate,
    find,
    leaf,
    profitability_tree,
    render,
    walk,
)


class TestNode:
    def test_leaf_and_branch(self) -> None:
        tree = branch("Revenue", "product", leaf("Price", 10), leaf("Volume", 5))
        assert not tree.is_leaf
        assert tree.children[0].is_leaf
        assert evaluate(tree) == 50

    def test_blank_label(self) -> None:
        with pytest.raises(ValidationError, match="blank"):
            leaf("  ")

    def test_bad_op(self) -> None:
        with pytest.raises(ValidationError, match="op must be one of"):
            Node("X", op="divide")  # type: ignore[arg-type]

    def test_leaf_with_children(self) -> None:
        with pytest.raises(ValidationError, match="no op"):
            Node("X", children=(leaf("a"),))

    @pytest.mark.parametrize(("op", "expected"), [("sum", 6), ("difference", 0), ("product", 6)])
    def test_ops(self, op: str, expected: float) -> None:
        tree = branch("T", op, leaf("a", 3), leaf("b", 2), leaf("c", 1))  # type: ignore[arg-type]
        assert evaluate(tree) == expected

    def test_unknown_leaf_makes_parent_unknown(self) -> None:
        assert evaluate(branch("T", "sum", leaf("a", 1), leaf("b"))) is None

    def test_stated_value_wins_in_evaluate(self) -> None:
        tree = branch("T", "sum", leaf("a", 1), leaf("b", 1), value=5)
        assert evaluate(tree) == 5
        assert computed_value(tree) == 2

    def test_empty_branch_has_no_value(self) -> None:
        assert computed_value(branch("T", "sum")) is None

    def test_json(self) -> None:
        tree = branch("T", "sum", leaf("a", 1), leaf("b", 2))
        data = json.loads(json.dumps(tree.to_dict()))
        assert data["children"][1]["value"] == 2


class TestNavigation:
    def test_walk_paths(self) -> None:
        tree = branch("A", "sum", leaf("B"), branch("C", "sum", leaf("D"), leaf("E")))
        paths = [" > ".join(p) for p, _ in walk(tree)]
        assert paths == ["A", "A > B", "A > C", "A > C > D", "A > C > E"]

    def test_find(self) -> None:
        tree = profitability_tree()
        assert find(tree, "Revenue", "Price").label == "Price"
        with pytest.raises(ValidationError, match="has no child 'Nope'"):
            find(tree, "Revenue", "Nope")


class TestRender:
    def test_render_shape(self) -> None:
        tree = branch("Profit", "difference", leaf("Revenue", 100), leaf("Costs", 60))
        assert render(tree, fmt="{:.0f}") == ("Profit [-] = 40\n├── Revenue = 100\n└── Costs = 60")

    def test_render_nested_and_hints(self) -> None:
        text = render(profitability_tree(), show_hints=True)
        assert "│   ├── Price" in text
        assert "(Have we or competitors changed prices? Mix shift?)" in text
        assert "Market share" in text


class TestProfitabilityTree:
    def test_numbers_match_profit_statement(self) -> None:
        tree = profitability_tree(
            price=10, units=1_000, variable_cost_per_unit=6, fixed_costs=2_500
        )
        st = profit_statement(10, 1_000, 6, 2_500)
        assert evaluate(tree) == pytest.approx(st.profit)
        assert evaluate(find(tree, "Revenue")) == pytest.approx(st.revenue)
        assert evaluate(find(tree, "Costs")) == pytest.approx(st.total_costs)

    def test_blank_framework_is_structurally_mece(self) -> None:
        report = check_mece(profitability_tree())
        assert report.ok
        assert report.nodes_checked == 13
        assert "passed" in report.summary()

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValidationError, match="price"):
            profitability_tree(price=-1)


class TestMece:
    def test_missing_bucket(self) -> None:
        tree = breakdown_tree("Revenue", 100, {"Retail": 60, "Online": 30})
        report = check_mece(tree)
        assert report.kinds() == {"missing_bucket"}
        assert "10.00 is unexplained" in report.issues[0].message

    def test_double_count(self) -> None:
        report = check_mece(breakdown_tree("Revenue", 100, {"Retail": 60, "Online": 50}))
        assert report.kinds() == {"double_count"}

    def test_within_tolerance(self) -> None:
        assert check_mece(breakdown_tree("Revenue", 100, {"A": 60, "B": 40.2})).ok

    def test_mismatch_on_product(self) -> None:
        tree = branch("Revenue", "product", leaf("Price", 10), leaf("Volume", 5), value=60)
        assert check_mece(tree).kinds() == {"mismatch"}

    def test_single_split_and_duplicate(self) -> None:
        tree = branch(
            "Costs",
            "sum",
            branch("Fixed", "sum", leaf("Rent")),
            leaf("Labour"),
            leaf("labour "),
        )
        report = check_mece(tree)
        assert report.kinds() == {"single_split", "duplicate"}
        assert "Costs > Fixed" in report.summary()

    def test_empty_branch(self) -> None:
        assert check_mece(branch("X", "sum")).kinds() == {"empty_branch"}

    def test_unknown_parts_skip_reconciliation(self) -> None:
        tree = branch("Revenue", "sum", leaf("A", 1), leaf("B"), value=100)
        assert check_mece(tree).ok

    def test_breakdown_without_total(self) -> None:
        assert check_mece(breakdown_tree("Revenue", None, {"A": 1, "B": 2})).ok

    def test_breakdown_validation(self) -> None:
        with pytest.raises(ValidationError):
            breakdown_tree("Revenue", 100, {})
        with pytest.raises(ValidationError):
            breakdown_tree("Revenue", -1, {"A": 1})
