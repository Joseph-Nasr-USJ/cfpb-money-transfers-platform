
import json
import logging
import os
from datetime import date, datetime
from decimal import Decimal

import redis
import streamlit as st
from pymongo import MongoClient


# Logger for recording errors in Docker logs
logger = logging.getLogger(__name__)


@st.cache_resource
def get_mongo_client():
    """Create one reusable MongoDB connection."""
    uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
    return MongoClient(uri, serverSelectionTimeoutMS=3000)


@st.cache_resource
def get_redis_client():
    """Create one reusable Redis connection."""
    url = os.getenv("REDIS_URL", "redis://redis:6379/0")

    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2
    )


def get_database():
    """Return the MongoDB database or show a clear error."""
    try:
        client = get_mongo_client()
        client.admin.command("ping")

        name = os.getenv("MONGO_DB", "cfpb_money_transfers")
        return client[name]

    except Exception:
        logger.exception("MongoDB connection failed")

        st.error(
            "MongoDB is unavailable. "
            "Please check the database service."
        )

        return None


def json_converter(value):
    """Convert common MongoDB results to JSON-compatible values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return str(value)


def cached_query(query_name, filters, query_function):
    """
    Cache-aside:
    1. Read from Redis.
    2. On a miss, run the MongoDB query.
    3. Store the result with a TTL.
    4. If Redis fails, continue using MongoDB.
    """

    # Create a unique cache key for the query and selected filters
    cache_key = query_name + ":" + json.dumps(
        filters,
        sort_keys=True,
        default=json_converter
    )

    # Cache lifetime: 600 seconds (10 minutes)
    ttl = int(os.getenv("CACHE_TTL_SECONDS", "600"))

    # Step 1: Try getting the result from Redis
    try:
        cache = get_redis_client()
        saved = cache.get(cache_key)

        if saved is not None:
            return json.loads(saved)

    except (redis.RedisError, OSError):
        logger.warning(
            "Redis unavailable for query '%s'; using MongoDB.",
            query_name,
            exc_info=True
        )
        cache = None

    # Step 2: Get the MongoDB database
    database = get_database()

    if database is None:
        return []

    # Step 3: Execute Christopher's MongoDB query
    try:
        result = query_function(database, filters)

    except Exception:
        logger.exception(
            "Dashboard query '%s' failed",
            query_name
        )

        st.error(
            "The database query failed. "
            "Please check the logs."
        )

        return []

    # Step 4: Convert results to a consistent JSON-compatible format
    serialized_result = json.dumps(
        result,
        default=json_converter
    )

    # Step 5: Save the result in Redis for the next request
    if cache is not None:
        try:
            cache.setex(
                cache_key,
                ttl,
                serialized_result
            )

        except (redis.RedisError, OSError):
            logger.warning(
                "Could not save query '%s' to Redis.",
                query_name,
                exc_info=True
            )

    # Step 6: Return the same result type on a cache hit or miss
    return json.loads(serialized_result)
