"""Fix database constraint for treatment column."""
import asyncio
from sqlalchemy import text
from src.database.connection import get_engine

async def fix_treatment_constraint():
    """Drop NOT NULL constraint from treatment column."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE samples ALTER COLUMN treatment DROP NOT NULL"))
        print("✅ Fixed: treatment column now allows NULL values")

if __name__ == "__main__":
    asyncio.run(fix_treatment_constraint())
