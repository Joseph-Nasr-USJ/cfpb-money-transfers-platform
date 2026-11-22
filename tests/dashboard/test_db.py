
import json
from unittest.mock import MagicMock, patch

import pytest

# The pipeline image may not include Streamlit or Redis yet.
pytest.importorskip("streamlit")
pytest.importorskip("redis")

from dashboard.components import db


FILTERS = {"date_from": "2024-01-01", "date_to": "2024-12-31"}
RESULT = {"total_complaints": 25, "timely_pct": 80.0}


def test_cache_hit():
    cache = MagicMock()
    cache.get.return_value = json.dumps(RESULT)
    query = MagicMock()

    with patch.object(db, "get_redis_client", return_value=cache):
        result = db.cached_query("kpi_summary", FILTERS, query)

    assert result == RESULT
    query.assert_not_called()


def test_cache_miss():
    cache = MagicMock()
    cache.get.return_value = None

    database = MagicMock()
    query = MagicMock(return_value=RESULT)

    with patch.object(db, "get_redis_client", return_value=cache):
        with patch.object(db, "get_database", return_value=database):
            result = db.cached_query("kpi_summary", FILTERS, query)

    assert result == RESULT
    query.assert_called_once_with(database, FILTERS)
    cache.setex.assert_called_once()


def test_cache_uses_600_second_ttl():
    cache = MagicMock()
    cache.get.return_value = None

    with patch.object(db, "get_redis_client", return_value=cache):
        with patch.object(db, "get_database", return_value=MagicMock()):
            with patch.dict("os.environ", {"CACHE_TTL_SECONDS": "600"}):
                db.cached_query(
                    "kpi_summary",
                    FILTERS,
                    lambda database, filters: RESULT
                )

    args = cache.setex.call_args.args
    assert args[1] == 600
    assert json.loads(args[2]) == RESULT


def test_redis_unavailable_falls_back_to_mongo():
    import redis

    database = MagicMock()
    query = MagicMock(return_value=RESULT)

    with patch.object(
        db,
        "get_redis_client",
        side_effect=redis.ConnectionError("Redis unavailable")
    ):
        with patch.object(db, "get_database", return_value=database):
            result = db.cached_query("kpi_summary", FILTERS, query)

    assert result == RESULT
    query.assert_called_once_with(database, FILTERS)
