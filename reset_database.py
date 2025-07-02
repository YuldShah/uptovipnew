#!/usr/bin/env python3
# Database Reset Script for YTDLBot

import os
import sys
from sqlalchemy import create_engine, text

def reset_database():
    """Reset the database by dropping and recreating all tables"""
    
    # Get database connection
    db_dsn = os.getenv("DB_DSN")
    if not db_dsn:
        print("❌ Error: DB_DSN environment variable not set")
        print("Please set DB_DSN in your .env file")
        return False
    
    try:
        engine = create_engine(db_dsn)
        
        print("🔄 Resetting database...")
        
        with engine.connect() as conn:
            # Drop existing ENUM types if they exist
            print("🗑️  Dropping existing ENUM types...")
            conn.execute(text("DROP TYPE IF EXISTS quality_enum CASCADE;"))
            conn.execute(text("DROP TYPE IF EXISTS format_enum CASCADE;"))
            
            # Drop all tables
            print("🗑️  Dropping existing tables...")
            conn.execute(text("DROP TABLE IF EXISTS channels CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS settings CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
            
            conn.commit()
        
        print("✅ Database reset complete!")
        print("🔄 Now run your bot to create fresh tables...")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return False

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🚨 WARNING: This will delete ALL data in your bot's database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        success = reset_database()
        if success:
            print("\n🎉 Database has been reset successfully!")
            print("You can now run: python src/main.py")
        else:
            print("\n❌ Database reset failed!")
            sys.exit(1)
    else:
        print("❌ Database reset cancelled.")
        sys.exit(0)
