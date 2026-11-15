"""Pure calculation functions. Each returns a frozen ``Result`` dataclass or a float."""

from casemath.calculators.breakeven import (
    BreakEvenAnalysis,
    break_even_analysis,
    break_even_price,
    break_even_revenue,
    break_even_units,
    margin_of_safety,
    payback_period,
    units_for_target_profit,
)
from casemath.calculators.profitability import (
    ProfitBridge,
    ProfitStatement,
    Segment,
    SegmentLine,
    SegmentReport,
    profit_bridge,
    profit_statement,
    segment_profitability,
)

__all__ = [
    "BreakEvenAnalysis",
    "ProfitBridge",
    "ProfitStatement",
    "Segment",
    "SegmentLine",
    "SegmentReport",
    "break_even_analysis",
    "break_even_price",
    "break_even_revenue",
    "break_even_units",
    "margin_of_safety",
    "payback_period",
    "profit_bridge",
    "profit_statement",
    "segment_profitability",
    "units_for_target_profit",
]
