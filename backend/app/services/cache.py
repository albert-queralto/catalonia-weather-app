from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import settings


class RedisCache:
    def __init__(self) -> None:
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def get_json(self, key: str) -> Optional[Any]:
        await self.connect()
        assert self._redis is not None
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self.connect()
        assert self._redis is not None
        await self._redis.set(key, json.dumps(value), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self.connect()
        assert self._redis is not None
        await self._redis.delete(key)


cache = RedisCache()
