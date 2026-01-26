"""Check database tables"""
from sqlalchemy import create_engine, text, inspect

engine = create_engine('sqlite:///./data/crmit.db')

# Use inspector to get tables
inspector = inspect(engine)
tables = inspector.get_table_names()

print("Tables in database:")
print("=" * 60)

with engine.connect() as conn:
    for t in tables:
        try:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).fetchone()[0]
            print(f"  {t}: {count} rows")
        except Exception as e:
            print(f"  {t}: Error - {e}")

    # Check samples table structure
    if 'samples' in tables:
        print("\n\nSample records:")
        print("-" * 60)
        result = conn.execute(text("SELECT id, sample_id, user_id FROM samples LIMIT 10"))
        for row in result.fetchall():
            print(f"  ID={row[0]}, SampleID={row[1]}, UserID={row[2]}")
    
    # Check alerts table
    if 'alerts' in tables:
        print("\n\nAlert records:")
        print("-" * 60)
        result = conn.execute(text("SELECT id, title, severity, user_id FROM alerts LIMIT 10"))
        for row in result.fetchall():
            print(f"  ID={row[0]}, Title={row[1][:40] if row[1] else 'N/A'}..., Severity={row[2]}, UserID={row[3]}")
