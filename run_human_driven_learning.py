#!/usr/bin/env python3
"""
Human-Driven Learning Agent Runner
Focuses on learning from expert feedback rather than autonomous log analysis.
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

from learning_agent.human_driven_learning_agent import HumanDrivenLearningAgent


def main():
    """Main function to run the human-driven learning agent."""
    parser = argparse.ArgumentParser(description="Run the Human-Driven Learning Agent")
    parser.add_argument("--api-key", help="Gemini API key (or set GOOGLE_API_KEY environment variable)")
    parser.add_argument("--repo-root", help="Repository root path (default: current directory)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    print("🧠 Starting Human-Driven Learning Agent...")
    print("=" * 50)
    print("This agent learns from expert feedback, not autonomous log analysis.")
    print("Add feedback through the web GUI, then run this to analyze feedback quality.")
    print("=" * 50)
    
    try:
        # Initialize learning agent
        agent = HumanDrivenLearningAgent(
            repo_root=args.repo_root,
            api_key=args.api_key
        )
        
        if args.verbose:
            print(f"📁 Repository root: {agent.repo_root}")
            print(f"🗄️  Database path: {agent.db.db_path}")
        
        # Analyze human feedback quality
        print("\n🔍 Analyzing human feedback quality...")
        results = agent.analyze_feedback_quality()
        
        # Print detailed results
        print("\n📊 ANALYSIS RESULTS:")
        print("=" * 30)
        print(f"Expert feedback analyzed: {results['feedback_analyzed']}")
        
        if results['feedback_analyzed'] == 0:
            print("\n💡 TIP: Add expert feedback through the web GUI first:")
            print("   python web_gui/human_driven_app.py")
            print("   Then visit http://localhost:5001/feedback")
        
        # Show quality analysis
        if 'quality_analysis' in results:
            analysis = results['quality_analysis']
            print(f"Feedback groups found: {analysis['total_groups']}")
            
            for group_type, group_data in analysis['group_breakdown'].items():
                print(f"  - {group_type}: {group_data['count']} items (quality: {group_data['quality_score']:.2f})")
        
        # Show database statistics
        stats = agent.get_database_stats()
        print(f"📊 DATABASE STATISTICS:")
        print(f"  - Human feedback: {stats['human_feedback']}")
        print(f"  - System exceptions: {stats['system_exceptions']}")
        print(f"  - Pending exceptions: {stats['pending_exceptions']}")
        
        print(f"\n✅ Human-driven learning agent completed successfully!")
        print(f"🌐 Web GUI available at: http://localhost:5001")
        print(f"   (Run 'python web_gui/human_driven_app.py' to start the web interface)")
        
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
