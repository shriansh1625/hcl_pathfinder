"""Shared pytest defaults for PathFinder."""

from __future__ import annotations

import pytest

from app.core import config


@pytest.fixture(autouse=True)
def disable_semantic_for_non_semantic_tests(request, monkeypatch):
    if request.node.fspath and "test_semantic_retrieval.py" in str(request.node.fspath):
        return
    monkeypatch.setattr(config.settings, "semantic_enabled", False)
