"""A small local web front end: ``casemath serve``. Standard library only."""

from casemath.web.api import ApiError, call, check_answer
from casemath.web.server import make_server

__all__ = ["ApiError", "call", "check_answer", "make_server"]
