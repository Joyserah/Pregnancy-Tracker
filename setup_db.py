#!/usr/bin/env python3
"""
Database setup script for Pregnancy Tracker
Run this script to initialize the database tables
"""

import os
import sys
import json

# Add current directory to path so we can import from app.py
sys.path.insert(0, os.path.dirname(__file__))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import sqlite3
except ImportError:
    print("Database libraries not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)

def setup_postgres():
    """Set up PostgreSQL database"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL environment variable not set")
        return False

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Create patients table
        cur.execute('''CREATE TABLE IF NOT EXISTS patients (
            username VARCHAR(255) PRIMARY KEY,
            password TEXT NOT NULL,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            gmail VARCHAR(255),
            recovery TEXT,
            email_verified BOOLEAN DEFAULT FALSE,
            registration_date TIMESTAMP,
            pregnancy_week INTEGER,
            vaccines_received JSONB,
            completed_tasks JSONB,
            zipcode VARCHAR(10),
            daily_logs JSONB,
            reminder_time VARCHAR(10),
            clinicians JSONB,
            next_appointment DATE,
            trimester VARCHAR(50),
            month VARCHAR(50),
            hospital_portal_synced BOOLEAN DEFAULT FALSE,
            chat_messages JSONB,
            emergency_contacts JSONB
        )''')

        conn.commit()
        cur.close()
        conn.close()
        print("✅ PostgreSQL database initialized successfully")
        return True

    except Exception as e:
        print(f"❌ PostgreSQL setup failed: {e}")
        return False

def setup_sqlite():
    """Set up SQLite database"""
    try:
        conn = sqlite3.connect('patients.db')
        cur = conn.cursor()

        # Create patients table
        cur.execute('''CREATE TABLE IF NOT EXISTS patients (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            gmail TEXT,
            recovery TEXT,
            email_verified BOOLEAN DEFAULT 0,
            registration_date TEXT,
            pregnancy_week INTEGER,
            vaccines_received TEXT,  -- JSON string
            completed_tasks TEXT,    -- JSON string
            zipcode TEXT,
            daily_logs TEXT,         -- JSON string
            reminder_time TEXT,
            clinicians TEXT,         -- JSON string
            next_appointment TEXT,
            trimester TEXT,
            month TEXT,
            hospital_portal_synced BOOLEAN DEFAULT 0,
            chat_messages TEXT,      -- JSON string
            emergency_contacts TEXT  -- JSON string
        )''')

        conn.commit()
        conn.close()
        print("✅ SQLite database initialized successfully")
        return True

    except Exception as e:
        print(f"❌ SQLite setup failed: {e}")
        return False

def migrate_from_json():
    """Migrate existing JSON data to database"""
    json_file = 'patients.json'
    if not os.path.exists(json_file):
        print("ℹ️  No existing patients.json file found")
        return

    try:
        with open(json_file, 'r') as f:
            patients = json.load(f)

        if not patients:
            print("ℹ️  patients.json is empty")
            return

        # Import the database functions from app.py
        from app import save_patients
        save_patients(patients)
        print(f"✅ Migrated {len(patients)} users from JSON to database")

    except Exception as e:
        print(f"❌ Migration failed: {e}")

def main():
    db_type = os.environ.get('DB_TYPE', 'json')

    print(f"Setting up database for DB_TYPE: {db_type}")

    if db_type == 'postgres':
        if setup_postgres():
            migrate_from_json()
    elif db_type == 'sqlite':
        if setup_sqlite():
            migrate_from_json()
    else:
        print("ℹ️  Using JSON storage (development mode)")
        print("   To use a database, set DB_TYPE environment variable to 'sqlite' or 'postgres'")

    print("\n📋 Environment variables for production:")
    print("   DB_TYPE=sqlite          # For file-based database")
    print("   DB_TYPE=postgres        # For PostgreSQL (Render/Heroku)")
    print("   DATABASE_URL=...        # PostgreSQL connection string")
    print("   SECRET_KEY=your-secret-key-here")

if __name__ == '__main__':
    main()