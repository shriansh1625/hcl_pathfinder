"""Grounded AI explanation layer. The LLM never mutates learner or path state."""

from app.services.explanation.schema import AIContext, GroundedAnswer
from app.services.explanation.service import explain, set_provider

__all__ = ["AIContext", "GroundedAnswer", "explain", "set_provider"]
