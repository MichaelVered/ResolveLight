#!/usr/bin/env python3
"""
Main script to run the learning agent.
This script analyzes system logs and generates learning plans.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from projects directory
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)
except ImportError:
    pass

from learning_agent.learning_agent import LearningAgent


def main():
    """Main function to run the learning agent."""
    parser = argparse.ArgumentParser(description="Run the ResolveLight Learning Agent")
    parser.add_argument("--api-key", help="Gemini API key (or set GOOGLE_API_KEY environment variable)")
    parser.add_argument("--repo-root", help="Repository root path (default: current directory)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    print("🚀 Starting ResolveLight Learning Agent...")
    print("=" * 50)
    
    try:
        # Initialize learning agent
        agent = LearningAgent(
            repo_root=args.repo_root,
            api_key=args.api_key
        )
        
        if args.verbose:
            print(f"📁 Repository root: {agent.repo_root}")
            print(f"🗄️  Database path: {agent.db.db_path}")
        
        # Run learning analysis
        print("\n🔍 Running learning analysis...")
        results = agent.run_learning_analysis()
        
        # Print detailed results
        print("\n📊 ANALYSIS RESULTS:")
        print("=" * 30)
        print(f"Learning opportunities found: {results['learning_opportunities_found']}")
        print(f"Learning plans generated: {results['learning_plans_generated']}")
        
        # Show system overview
        overview = results['system_overview']
        print(f"\n📈 SYSTEM OVERVIEW:")
        print(f"  - Log files analyzed: {overview['log_files_analyzed']}")
        print(f"  - Exception patterns: {overview['exception_patterns']}")
        print(f"  - Queue issues: {overview['queue_issues']}")
        print(f"  - Rejection rate: {overview['rejection_rate']:.1%}")
        print(f"  - High-value issues: {overview['high_value_issues']}")
        
        # Show generated learning plans
        plans = agent.get_learning_plans()
        if plans:
            print(f"\n📝 GENERATED LEARNING PLANS:")
            print("=" * 35)
            for i, plan in enumerate(plans, 1):
                print(f"{i}. {plan['title']}")
                print(f"   Type: {plan['plan_type']}")
                print(f"   Priority: {plan['priority']}")
                print(f"   Status: {plan['status']}")
                print(f"   Reasoning: {plan['llm_reasoning'][:100]}...")
                print()
        
        # Show database statistics
        stats = agent.get_database_stats()
        print(f"📊 DATABASE STATISTICS:")
        print(f"  - Learning records: {stats['learning_records']}")
        print(f"  - Human feedback: {stats['human_feedback']}")
        print(f"  - Learning plans: {stats['learning_plans']}")
        print(f"  - Draft plans: {stats['draft_plans']}")
        print(f"  - Approved plans: {stats['approved_plans']}")
        
        print(f"\n✅ Learning agent completed successfully!")
        print(f"🌐 Web GUI available at: http://localhost:5000")
        print(f"   (Run 'python web_gui/app.py' to start the web interface)")
        
        agent.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error running learning agent: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
