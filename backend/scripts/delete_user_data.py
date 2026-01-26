"""
Delete user data script
Removes all samples and alerts for a specific user
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Connect to the PostgreSQL database
DATABASE_URL = os.environ.get(
    'CRMIT_DATABASE_URL', 
    'postgresql://crmit:crmit123@localhost:5432/crmit_db'
)
# Use sync driver for psycopg2
sync_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
engine = create_engine(sync_url)
Session = sessionmaker(bind=engine)
session = Session()

TARGET_EMAIL = 'sumit.malhotra@crmit.com'

print(f"Looking for user: {TARGET_EMAIL}")
print("=" * 60)

# First find the user
user_result = session.execute(text("SELECT id, email, name FROM users WHERE email = :email"), {"email": TARGET_EMAIL})
user = user_result.fetchone()

if user:
    user_id = user[0]
    print(f"User found: ID={user_id}, Email={user[1]}, Name={user[2]}")
    
    # Count samples
    sample_row = session.execute(text("SELECT COUNT(*) FROM samples WHERE user_id = :uid"), {"uid": user_id}).fetchone()
    sample_count = sample_row[0] if sample_row else 0
    print(f"Samples to delete: {sample_count}")
    
    # Count alerts
    alert_row = session.execute(text("SELECT COUNT(*) FROM alerts WHERE user_id = :uid"), {"uid": user_id}).fetchone()
    alert_count = alert_row[0] if alert_row else 0
    print(f"Alerts to delete: {alert_count}")
    
    # Delete alerts first (they reference samples)
    if alert_count > 0:
        session.execute(text("DELETE FROM alerts WHERE user_id = :uid"), {"uid": user_id})
        print(f"✅ Deleted {alert_count} alerts")
    
    # Get sample IDs for cascade delete
    sample_ids = session.execute(text("SELECT id FROM samples WHERE user_id = :uid"), {"uid": user_id}).fetchall()
    sample_id_list = [s[0] for s in sample_ids]
    
    if sample_id_list:
        # Delete related records first
        for sid in sample_id_list:
            # Delete FCS results
            session.execute(text("DELETE FROM fcs_results WHERE sample_id = :sid"), {"sid": sid})
            # Delete NTA results
            session.execute(text("DELETE FROM nta_results WHERE sample_id = :sid"), {"sid": sid})
            # Delete QC reports
            session.execute(text("DELETE FROM qc_reports WHERE sample_id = :sid"), {"sid": sid})
            # Delete processing jobs
            session.execute(text("DELETE FROM processing_jobs WHERE sample_id = :sid"), {"sid": sid})
            # Delete experimental conditions
            session.execute(text("DELETE FROM experimental_conditions WHERE sample_id = :sid"), {"sid": sid})
            # Delete alerts for sample
            session.execute(text("DELETE FROM alerts WHERE sample_id = :sid"), {"sid": sid})
        
        # Now delete samples
        session.execute(text("DELETE FROM samples WHERE user_id = :uid"), {"uid": user_id})
        print(f"✅ Deleted {sample_count} samples and all related records")
    
    session.commit()
    print("\n✅ All data deleted successfully!")
    
else:
    # Check all users
    all_users = session.execute(text("SELECT id, email, name FROM users")).fetchall()
    print("User not found. All users in database:")
    for u in all_users:
        print(f"  ID={u[0]}, Email={u[1]}, Name={u[2]}")
    
    # Check if there are any samples without user
    orphan_row = session.execute(text("SELECT COUNT(*) FROM samples")).fetchone()
    orphan_samples = orphan_row[0] if orphan_row else 0
    print(f"\nTotal samples in database: {orphan_samples}")
    
    # Check alerts
    alerts_row = session.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()
    all_alerts = alerts_row[0] if alerts_row else 0
    print(f"Total alerts in database: {all_alerts}")

session.close()
