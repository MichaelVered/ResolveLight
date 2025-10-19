#!/usr/bin/env python3
"""
Clear Database Utility for ResolveLight Learning Agent
Clears all data from the learning database for fresh testing.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from learning_agent.database import LearningDatabase

def show_database_status(db_path: str = None):
    """Show database status without clearing."""
    if db_path is None:
        # Default database path
        repo_root = Path(__file__).parent.parent.parent
        db_path = repo_root / "learning_data" / "learning.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    try:
        # Create database connection
        db = LearningDatabase(str(db_path))
        
        # Get current stats
        stats = db.get_database_stats()
        
        print("📊 Database Status:")
        print("=" * 30)
        print(f"🗄️  Database path: {db_path}")
        print()
        
        # Exception statistics
        total_exceptions = stats.get('system_exceptions', 0)
        pending_exceptions = stats.get('pending_exceptions', 0)
        reviewed_exceptions = total_exceptions - pending_exceptions
        
        print("📋 Exception Statistics:")
        print(f"  - Total system exceptions: {total_exceptions}")
        print(f"  - Pending (unreviewed): {pending_exceptions}")
        print(f"  - Human reviewed: {reviewed_exceptions}")
        print()
        
        # Other statistics
        print("📈 Other Statistics:")
        print(f"  - Human feedback: {stats.get('human_feedback', 0)}")
        print(f"  - Learning plans: {stats.get('learning_plans', 0)}")
        print(f"  - Learning records: {stats.get('learning_records', 0)}")
        print(f"  - Draft plans: {stats.get('draft_plans', 0)}")
        print(f"  - Approved plans: {stats.get('approved_plans', 0)}")
        
        # Summary
        total_exceptions = stats.get('system_exceptions', 0)
        other_items = (stats.get('human_feedback', 0) + 
                      stats.get('learning_plans', 0) + 
                      stats.get('learning_records', 0))
        
        if total_exceptions == 0 and other_items == 0:
            print("\n✅ Database is EMPTY")
        else:
            print(f"\n📊 Summary:")
            print(f"  - Total exceptions: {total_exceptions}")
            print(f"  - Other items: {other_items}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking database status: {e}")
        return False

def clear_database(db_path: str = None):
    """Clear all data from the learning database."""
    if db_path is None:
        # Default database path
        repo_root = Path(__file__).parent.parent.parent
        db_path = repo_root / "learning_data" / "learning.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    try:
        # Create database connection
        db = LearningDatabase(str(db_path))
        
        # Get current stats before clearing
        stats = db.get_database_stats()
        print(f"📊 Current database statistics:")
        print(f"  - System exceptions: {stats.get('system_exceptions', 0)}")
        print(f"  - Human feedback: {stats.get('human_feedback', 0)}")
        print(f"  - Learning plans: {stats.get('learning_plans', 0)}")
        print(f"  - Learning records: {stats.get('learning_records', 0)}")
        print()
        
        # Clear all tables
        print("🧹 Clearing database...")
        db._drop_tables()
        db._create_tables_if_not_exist()
        db.conn.commit()
        
        print("✅ Database cleared successfully!")
        print(f"🗄️  Database path: {db_path}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False

def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear the ResolveLight Learning Agent database")
    parser.add_argument("--db-path", help="Path to database file (default: learning_data/learning.db)")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--status", action="store_true", help="Show database status without clearing")
    
    args = parser.parse_args()
    
    print("🧹 ResolveLight Learning Agent - Database Utility")
    print("=" * 55)
    
    # Handle status option
    if args.status:
        success = show_database_status(args.db_path)
        return 0 if success else 1
    
    # Handle clear operation
    if not args.confirm:
        response = input("⚠️  This will DELETE ALL DATA from the learning database. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled.")
            return 1
    
    success = clear_database(args.db_path)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
