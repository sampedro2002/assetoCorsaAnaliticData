"""
Migration script to add normalized_position column to existing telemetry table
Run this once to update your existing database
"""
import sqlite3
import os
from backend.config import DB_CONFIG

def migrate():
    db_path = DB_CONFIG['database_path']
    
    if not os.path.exists(db_path):
        print("❌ Database not found. No migration needed.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(telemetry)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'normalized_position' in columns:
            print("✓ normalized_position column already exists. No migration needed.")
            return
        
        # Add the column
        print("Adding normalized_position column to telemetry table...")
        cursor.execute("""
            ALTER TABLE telemetry 
            ADD COLUMN normalized_position REAL DEFAULT 0.0
        """)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        print("  - Added normalized_position column to telemetry table")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
