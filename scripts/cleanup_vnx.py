"""Clean up old VNX seeded data for re-seeding."""
import asyncio
from sqlalchemy import text
from riskcast.db.engine import get_engine

async def cleanup():
    engine = get_engine()
    async with engine.begin() as conn:
        r1 = await conn.execute(text("DELETE FROM v2_orders WHERE order_number LIKE 'VNX-%'"))
        r2 = await conn.execute(text("DELETE FROM v2_customers WHERE code = 'VNX-001'"))
        r3 = await conn.execute(text("DELETE FROM v2_routes WHERE name LIKE 'VNHCM%'"))
        print(f"Deleted: {r1.rowcount} orders, {r2.rowcount} customers, {r3.rowcount} routes")

asyncio.run(cleanup())
