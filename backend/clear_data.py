"""Script to clear all user accounts and uploaded data."""
import asyncio
from sqlalchemy import text
from src.database.connection import get_engine


async def clear_all_data():
    """Delete all records from database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Get list of tables
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))
        tables = [row[0] for row in result.fetchall()]
        print(f"Found tables: {tables}")
        
        # Delete from existing tables in correct order (respecting foreign keys)
        tables_to_clear = [
            'qc_reports', 
            'processing_jobs', 
            'fcs_results', 
            'nta_results', 
            'experimental_conditions', 
            'samples', 
            'users'
        ]
        
        for table in tables_to_clear:
            if table in tables:
                await conn.execute(text(f'DELETE FROM {table}'))
                print(f"  ✅ Cleared: {table}")
            else:
                print(f"  ⏭️  Skipped (not exists): {table}")
        
        print("\n✅ All database records deleted!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_all_data())
