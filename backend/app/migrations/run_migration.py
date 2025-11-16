"""
Run database migration to add user tracking
"""
import asyncio
import aiosqlite
import os

async def run_migration():
    """Apply migration 001 - Add user tracking columns"""
    db_path = "/app/analytics.db"

    # Read migration SQL
    migration_path = os.path.join(os.path.dirname(__file__), "001_add_user_tracking.sql")
    with open(migration_path, 'r') as f:
        sql_commands = f.read()

    # Split by semicolon to get individual commands
    commands = [cmd.strip() for cmd in sql_commands.split(';') if cmd.strip() and not cmd.strip().startswith('--')]

    async with aiosqlite.connect(db_path) as db:
        for command in commands:
            if command:
                try:
                    print(f"Executing: {command[:50]}...")
                    await db.execute(command)
                    print("  ✓ Success")
                except Exception as e:
                    # Column may already exist
                    if "duplicate column name" in str(e).lower():
                        print(f"  ℹ Column already exists, skipping")
                    else:
                        print(f"  ✗ Error: {e}")
                        raise

        await db.commit()
        print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
