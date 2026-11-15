"""Pure calculation functions. Each returns a frozen ``Result`` dataclass or a float."""

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
    "ProfitBridge",
    "ProfitStatement",
    "Segment",
    "SegmentLine",
    "SegmentReport",
    "profit_bridge",
    "profit_statement",
    "segment_profitability",
]
