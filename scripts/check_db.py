"""Quick DB check script."""
import asyncio
from sqlalchemy import text
from riskcast.db.engine import get_engine

async def check():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT name, metadata::text FROM v2_routes WHERE name LIKE 'VNHCM%'"
        ))
        print("ROUTES:")
        for row in result.all():
            meta = row[1] or "NULL"
            print(f"  {row[0]}: {meta[:300]}")

        result2 = await conn.execute(text(
            "SELECT order_number, metadata::text FROM v2_orders WHERE order_number LIKE 'VNX%' LIMIT 3"
        ))
        print("\nORDERS:")
        for row in result2.all():
            meta = row[1] or "NULL"
            print(f"  {row[0]}: {meta[:300]}")

        # Check company IDs
        result3 = await conn.execute(text(
            "SELECT id::text, name FROM v2_companies ORDER BY created_at LIMIT 5"
        ))
        print("\nCOMPANIES:")
        for row in result3.all():
            print(f"  {row[0]} = {row[1]}")

asyncio.run(check())
