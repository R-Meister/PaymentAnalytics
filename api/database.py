import os
import asyncpg

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "payment_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

_pool = None


async def connect():
    global _pool
    _pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        min_size=2,
        max_size=10,
    )


async def close():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def fetch(query, *args):
    async with _pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query, *args):
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query, *args):
    async with _pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query, *args):
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)
