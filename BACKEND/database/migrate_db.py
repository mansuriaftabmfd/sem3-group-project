"""
Migration Script - Adds wallet_balance column to users table
and creates the transactions table if they don't exist.

Run this ONCE on your production database to apply schema changes.
Safe to run multiple times - uses IF NOT EXISTS checks.
"""

import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()


def run_migrations(app):
    """Run all pending schema migrations safely."""
    with app.app_context():
        from models import db
        
        # Skip raw SQL migrations for SQLite as db.create_all() handles schema creation
        if db.engine.dialect.name == 'sqlite':
            print("Skipping raw SQL migrations for SQLite database.")
            return

        print("Running database migrations...")

        with db.engine.connect() as conn:

            # ── 1. Add wallet_balance to users ──────────────────────────────
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'wallet_balance'
                AND table_schema = 'public'
            """))
            if result.fetchone() is None:
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN wallet_balance FLOAT NOT NULL DEFAULT 0.0
                """))
                conn.commit()
                print("[OK] Added wallet_balance column to users table")
            else:
                print("[OK] wallet_balance column already exists")

            # ── 1.5 Add pending_approval to services ────────────────────────
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'services'
                AND column_name = 'pending_approval'
                AND table_schema = 'public'
            """))
            if result.fetchone() is None:
                conn.execute(text("""
                    ALTER TABLE services
                    ADD COLUMN pending_approval BOOLEAN DEFAULT FALSE
                """))
                conn.commit()
                print("[OK] Added pending_approval column to services table")
            else:
                print("[OK] pending_approval column already exists")

            # ── 2. Create transactions table ─────────────────────────────────
            # First check if table exists but is invalid (missing txn_id)
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transactions' 
                AND column_name = 'txn_id'
                AND table_schema = 'public'
            """))
            is_valid = result.fetchone() is not None
            
            # Check if table exists at all
            result = conn.execute(text("""
                SELECT to_regclass('public.transactions')
            """))
            table_exists = result.scalar() is not None

            if table_exists and not is_valid:
                print("[INFO] Dropping malformed transactions table to recreate it...")
                conn.execute(text("DROP TABLE transactions CASCADE"))
                conn.commit()

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id          SERIAL PRIMARY KEY,
                    txn_id      VARCHAR(50) NOT NULL,
                    user_id     INTEGER NOT NULL REFERENCES users(id),
                    username    VARCHAR(80),
                    amount      FLOAT NOT NULL,
                    method      VARCHAR(20),
                    status      VARCHAR(20),
                    txn_type    VARCHAR(10),
                    description TEXT,
                    new_balance FLOAT,
                    timestamp   TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_transactions_txn_id  
                ON transactions (txn_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_transactions_user_id 
                ON transactions (user_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_transactions_timestamp 
                ON transactions (timestamp)
            """))
            conn.commit()
            print("[OK] transactions table ready")

            # ── 3. Create certificates table ──────────────────────────────────
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS certificates (
                    id           SERIAL PRIMARY KEY,
                    cert_id      VARCHAR(20) UNIQUE NOT NULL,
                    order_id     INTEGER UNIQUE NOT NULL REFERENCES orders(id),
                    student_id   INTEGER NOT NULL REFERENCES users(id),
                    provider_id  INTEGER NOT NULL REFERENCES users(id),
                    skill_name   VARCHAR(200) NOT NULL,
                    pdf_filename VARCHAR(255) NOT NULL,
                    issued_at    TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            print("[OK] certificates table ready")

        print("All migrations complete [OK]")

    # ── 4. Create required directories ─────────────────────────────────
    base = os.path.abspath(os.path.dirname(__file__))
    os.makedirs(os.path.join(base, 'static', 'certificates'), exist_ok=True)
    os.makedirs(os.path.join(base, 'static', 'fonts'), exist_ok=True)
    print("[OK] Static folders verified")
