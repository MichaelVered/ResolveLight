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
import json


def _format_conversation_items(items):
    """Format a list of human_feedback rows into a readable free-text conversation."""
    lines = []
    for item in items:
        prefix = "Initial Feedback" if item.get("is_initial_feedback") else "Response"
        expert_name = item.get("expert_name") or "Expert"
        created_at = item.get("created_at") or ""
        feedback_text = item.get("feedback_text") or ""

        lines.append(f"[{created_at}] {prefix} by {expert_name}:")
        if feedback_text:
            lines.append(f"  {feedback_text}")

        # LLM questions (stored as JSON array in text), only show once if present on this item
        llm_questions_raw = item.get("llm_questions")
        if llm_questions_raw:
            try:
                questions = json.loads(llm_questions_raw)
                if isinstance(questions, list) and questions:
                    lines.append("  LLM Questions:")
                    for q in questions:
                        lines.append(f"    - {q}")
            except Exception:
                pass

        # Human responses (stored as JSON array in text)
        human_responses_raw = item.get("human_responses")
        if human_responses_raw:
            try:
                responses = json.loads(human_responses_raw)
                if isinstance(responses, list) and responses:
                    lines.append("  Human Responses:")
                    for r in responses:
                        lines.append(f"    - {r}")
            except Exception:
                pass

        # Optional summary
        if item.get("feedback_summary"):
            lines.append("  Conversation Summary:")
            lines.append(f"    {item['feedback_summary']}")

        # Quality score if available
        if item.get("quality_score") is not None:
            try:
                score = float(item["quality_score"])  # may be 0.0 by default
                lines.append(f"  Quality Score: {score:.2f}")
            except Exception:
                pass

        lines.append("")  # blank line between turns

    return "\n".join(lines).rstrip()


def print_all_human_feedback(db_path: str = None) -> bool:
    """Print all exceptions that have human feedback, including multi-turn conversations.

    Output format:
    - One block per exception having feedback
    - Free-text conversation including initial feedback, LLM questions, human responses, and summary
    - Delimited by a line of dashes between exceptions
    """
    if db_path is None:
        repo_root = Path(__file__).parent.parent.parent
        db_path = repo_root / "learning_data" / "learning.db"

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False

    try:
        db = LearningDatabase(str(db_path))

        conn = db.get_connection()
        cur = conn.cursor()

        # Fetch all exceptions
        cur.execute("""
            SELECT exception_id, invoice_id, exception_type, queue, created_at, expert_reviewed,
                   expert_name, expert_feedback, human_correction
            FROM system_exceptions
            ORDER BY created_at ASC
        """)
        exceptions = [dict(r) for r in cur.fetchall()]

        # Fetch all human feedback once
        cur.execute("""
            SELECT * FROM human_feedback ORDER BY created_at ASC
        """)
        all_feedback = [dict(r) for r in cur.fetchall()]
        conn.close()

        # Group feedback by invoice_id and conversation
        invoice_to_conversations = {}
        for fb in all_feedback:
            inv = fb.get("invoice_id")
            conv = fb.get("conversation_id") or f"conv:{inv}:none"
            if not inv:
                # Skip feedback without invoice_id since we can't link to exception
                continue
            invoice_to_conversations.setdefault(inv, {}).setdefault(conv, []).append(fb)

        printed_any = False
        linked_invoices = set()
        for ex in exceptions:
            invoice_id = ex.get("invoice_id")
            exception_id = ex.get("exception_id")

            conversations = invoice_to_conversations.get(invoice_id)
            if not conversations:
                continue  # no feedback for this exception

            linked_invoices.add(invoice_id)
            printed_any = True
            header = (
                f"Exception: {exception_id} | Invoice: {invoice_id} | "
                f"Type: {ex.get('exception_type','')} | Queue: {ex.get('queue','')} | Created: {ex.get('created_at','')}"
            ).strip()
            print(header)
            print("-" * len(header))

            # Print each conversation in chronological order by first item timestamp
            def conv_sort_key(items):
                return (items[0].get("created_at") or "") if items else ""

            for _, items in sorted(conversations.items(), key=lambda kv: conv_sort_key(kv[1])):
                # Ensure chronological order within conversation
                items_sorted = sorted(items, key=lambda it: it.get("created_at") or "")
                text = _format_conversation_items(items_sorted)
                if text:
                    print(text)

            # Delimiter between exceptions
            print("\n" + "=" * 80 + "\n")

        # Also print any feedback that has no matching exception row
        unlinked = [inv for inv in invoice_to_conversations.keys() if inv and inv not in linked_invoices]
        for invoice_id in sorted(unlinked):
            printed_any = True
            header = f"Invoice (no matching exception): {invoice_id}"
            print(header)
            print("-" * len(header))

            conversations = invoice_to_conversations[invoice_id]

            def conv_sort_key(items):
                return (items[0].get("created_at") or "") if items else ""

            for _, items in sorted(conversations.items(), key=lambda kv: conv_sort_key(kv[1])):
                items_sorted = sorted(items, key=lambda it: it.get("created_at") or "")
                text = _format_conversation_items(items_sorted)
                if text:
                    print(text)

            print("\n" + "=" * 80 + "\n")

        if not printed_any:
            print("No human feedback found.")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Error reading feedback: {e}")
        return False

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
    parser.add_argument("--print-feedback", action="store_true", help="Print all human feedback grouped by exception (read-only)")
    
    args = parser.parse_args()
    
    print("🧹 ResolveLight Learning Agent - Database Utility")
    print("=" * 55)
    
    # Handle read-only utilities first
    if args.status:
        success = show_database_status(args.db_path)
        return 0 if success else 1

    if args.print_feedback:
        success = print_all_human_feedback(args.db_path)
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
