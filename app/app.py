import asyncio
import hashlib
import os
import time
import uuid
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException


MIN_DURATION_SECONDS = float(
    os.getenv("MIN_DURATION_SECONDS", "5.0")
)

HASH_ROUNDS = int(
    os.getenv("HASH_ROUNDS", "10000")
)


def cpu_work(rounds: int) -> str:
    """
    Perform a small amount of CPU work.

    This creates enough CPU pressure for Kubernetes HPA
    to observe and react to increased load.
    """
    value = os.urandom(32)

    for _ in range(rounds):
        value = hashlib.sha256(value).digest()

    return value.hex()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Create the PostgreSQL connection pool when the
    application starts and close it when it stops.
    """

    app.state.pool = await asyncpg.create_pool(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],

        min_size=1,

        
        max_size=int(
            os.getenv("DB_POOL_SIZE", "10")
        ),

        command_timeout=30,
    )

    
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workload_results (
                id UUID PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                processing_seconds DOUBLE PRECISION NOT NULL,
                hash_prefix TEXT NOT NULL
            )
            """
        )

    yield

    await app.state.pool.close()


app = FastAPI(
    title="Managed Kubernetes + DBaaS Benchmark",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """
    Lightweight endpoint used by Kubernetes
    readiness and liveness probes.
    """
    return {
        "status": "ok"
    }


@app.get("/work")
async def work():
    """
    Benchmark workload.

    Each request:
    1. Performs CPU work.
    2. Runs for at least 5 seconds.
    3. Writes one result into PostgreSQL.
    4. Returns timing information.
    """

    request_id = uuid.uuid4()

    started = time.perf_counter()

    
    digest = cpu_work(HASH_ROUNDS)

    
    elapsed = time.perf_counter() - started

    if elapsed < MIN_DURATION_SECONDS:
        await asyncio.sleep(
            MIN_DURATION_SECONDS - elapsed
        )

    processing_seconds = (
        time.perf_counter() - started
    )

    try:
        async with app.state.pool.acquire(
            timeout=30
        ) as conn:

            await conn.execute(
                """
                INSERT INTO workload_results(
                    id,
                    processing_seconds,
                    hash_prefix
                )
                VALUES($1, $2, $3)
                """,
                request_id,
                processing_seconds,
                digest[:16],
            )

    except Exception as exc:
        print(
            "Database operation failed: "
            f"{type(exc).__name__}: {exc!r}",
            flush=True,
        )

        
        raise HTTPException(
            status_code=503,
            detail=(
                "database operation failed: "
                f"{type(exc).__name__}"
            ),
        )

    total = time.perf_counter() - started

    return {
        "request_id": str(request_id),
        "processing_seconds": round(
            total,
            6,
        ),
        "hash_prefix": digest[:16],
    }