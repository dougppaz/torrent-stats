from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from torrent_stats.interfaces.api.depends import get_tracker_stats_repository
from torrent_stats.interfaces.api.main import app


@pytest.fixture(autouse=True)
def default_dependency_overrides():
    mock_tracker_repo = MagicMock()
    mock_tracker_repo.find_by_info_hash.return_value = []
    app.dependency_overrides[get_tracker_stats_repository] = lambda: mock_tracker_repo
    yield
    app.dependency_overrides.clear()
