
import json
import os
from datetime import date, datetime
from decimal import Decimal

import redis
import streamlit as st
from pymongo import MongoClient


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
        url, decode_responses=True,
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
        st.error("MongoDB is unavailable. Please check the database service.")
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
    cache_key = query_name + ":" + json.dumps(
        filters, sort_keys=True, default=json_converter
    )

    ttl = int(os.getenv("CACHE_TTL_SECONDS", "600"))

    try:
        cache = get_redis_client()
        saved = cache.get(cache_key)

        if saved is not None:
            return json.loads(saved)
    except (redis.RedisError, OSError):
        cache = None

    # Execute Christopher's query function
    database = get_database()
    if database is None:
        return []

    try:
        result = query_function(database, filters)
    except Exception:
        st.error("The database query failed. Please check the logs.")
        return []

    # Save the query result for the next request
    if cache is not None:
        try:
            cache.setex(
                cache_key,
                ttl,
                json.dumps(result, default=json_converter)
            )
        except (redis.RedisError, OSError):
            pass

    return result
