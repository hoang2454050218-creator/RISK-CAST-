"""Reset V2 database — drop all tables and recreate them."""
import asyncio
from riskcast.db.engine import get_engine, Base
import riskcast.db.models  # noqa: F401 — register models


async def reset():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("All V2 tables dropped.")
        await conn.run_sync(Base.metadata.create_all)
        print("All V2 tables recreated.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset())
