#!/usr/bin/env python3
"""
Test script for the learning agent without LLM dependency.
Tests log analysis and database functionality.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

from learning_agent.log_analyzer import LogAnalyzer
from learning_agent.database import LearningDatabase


def test_log_analysis():
    """Test the log analysis functionality."""
    print("🔍 Testing log analysis...")
    
    analyzer = LogAnalyzer()
    opportunities = analyzer.analyze_all_logs()
    
    print(f"Found {len(opportunities)} learning opportunities:")
    for i, opp in enumerate(opportunities, 1):
        print(f"{i}. {opp['learning_opportunity']}")
        print(f"   Source: {opp['source_file']}")
        print(f"   Confidence: {opp['confidence_score']:.2f}")
        print(f"   Type: {opp['source_type']}")
        print()
    
    # Show system overview
    overview = analyzer.get_system_overview()
    print("📊 SYSTEM OVERVIEW:")
    print(f"  - Total opportunities: {overview['total_learning_opportunities']}")
    print(f"  - Log files analyzed: {overview['log_files_analyzed']}")
    print(f"  - Exception patterns: {overview['exception_patterns']}")
    print(f"  - Queue issues: {overview['queue_issues']}")
    print(f"  - Rejection rate: {overview['rejection_rate']:.1%}")
    print(f"  - High-value issues: {overview['high_value_issues']}")
    
    return opportunities


def test_database():
    """Test the database functionality."""
    print("\n🗄️  Testing database...")
    
    db = LearningDatabase("learning_data/test_learning.db")
    
    # Test storing learning records
    test_record_id = db.store_learning_record(
        source_type="test_pattern",
        source_file="test.log",
        source_data={"test": "data"},
        learning_opportunity="Test learning opportunity",
        confidence_score=0.8,
        analysis_notes="Test analysis"
    )
    print(f"✅ Stored test learning record with ID: {test_record_id}")
    
    # Test storing human feedback
    test_feedback_id = db.store_human_feedback(
        invoice_id="TEST-001",
        original_decision="REJECTED",
        human_correction="APPROVED",
        routing_queue="test_queue",
        feedback_text="Test feedback",
        expert_name="Test Expert",
        feedback_type="test_type",
        supporting_evidence={"test": "evidence"},
        learning_record_id=test_record_id
    )
    print(f"✅ Stored test human feedback with ID: {test_feedback_id}")
    
    # Test storing learning plan
    test_plan_id = db.store_learning_plan(
        plan_type="test_optimization",
        title="Test Learning Plan",
        description="Test description",
        source_learning_records=[test_record_id],
        suggested_changes={"test": "changes"},
        impact_analysis={"test": "impact"},
        priority="medium",
        llm_reasoning="Test reasoning"
    )
    print(f"✅ Stored test learning plan with ID: {test_plan_id}")
    
    # Test retrieving data
    records = db.get_learning_records()
    feedback = db.get_human_feedback()
    plans = db.get_learning_plans()
    
    print(f"✅ Retrieved {len(records)} learning records")
    print(f"✅ Retrieved {len(feedback)} human feedback items")
    print(f"✅ Retrieved {len(plans)} learning plans")
    
    # Show database stats
    stats = db.get_database_stats()
    print(f"📊 Database stats: {stats}")
    
    db.close()
    return True


def main():
    """Main test function."""
    print("🧪 Testing Learning Agent Components")
    print("=" * 40)
    
    try:
        # Test log analysis
        opportunities = test_log_analysis()
        
        # Test database
        test_database()
        
        print("\n✅ All tests completed successfully!")
        print(f"🌐 Web GUI available at: http://localhost:5000")
        print(f"   (Run 'python web_gui/app.py' to start the web interface)")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
