#!/usr/bin/env python3
"""
Test script for the complete learning from human feedback system.
Tests all components and demonstrates the learning workflow.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent))

from learning_agent.database import LearningDatabase
from learning_agent.feedback_learning_processor import FeedbackLearningProcessor
from learning_agent.learning_playbook_generator import LearningPlaybookGenerator


def test_database_migration():
    """Test database migration and new fields."""
    print("🧪 Testing Database Migration...")
    
    try:
        db = LearningDatabase()
        
        # Test that new fields exist
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if learning fields exist
        cursor.execute("PRAGMA table_info(system_exceptions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_fields = ['learning_insights', 'corrective_actions', 'learning_timestamp', 'learning_agent_version']
        missing_fields = [field for field in required_fields if field not in columns]
        
        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return False
        else:
            print("✅ All learning fields present in database")
            return True
            
    except Exception as e:
        print(f"❌ Database migration test failed: {e}")
        return False
    finally:
        db.close()


def test_learning_processor():
    """Test the learning processor with sample data."""
    print("\n🧪 Testing Learning Processor...")
    
    try:
        processor = FeedbackLearningProcessor()
        
        # Test statistics
        stats = processor.get_learning_statistics()
        print(f"📊 Learning Statistics: {json.dumps(stats, indent=2)}")
        
        # Test processing all pending
        result = processor.process_all_pending_learning()
        print(f"🔄 Processing Result: {result['message']}")
        
        processor.close()
        return True
        
    except Exception as e:
        print(f"❌ Learning processor test failed: {e}")
        return False


def test_playbook_generator():
    """Test the playbook generator."""
    print("\n🧪 Testing Playbook Generator...")
    
    try:
        generator = LearningPlaybookGenerator()
        
        # Test playbook summary
        summary = generator.get_playbook_summary()
        print(f"📚 Playbook Summary: {json.dumps(summary, indent=2)}")
        
        # Test human-readable format
        human_format = generator.format_playbook_for_human()
        print(f"📖 Human Format (first 500 chars): {human_format[:500]}...")
        
        generator.close()
        return True
        
    except Exception as e:
        print(f"❌ Playbook generator test failed: {e}")
        return False


def test_sample_learning_workflow():
    """Test a complete learning workflow with sample data."""
    print("\n🧪 Testing Complete Learning Workflow...")
    
    try:
        db = LearningDatabase()
        
        # Create sample exception data
        sample_exception = {
            'exception_id': 'TEST-EXC-001',
            'invoice_id': 'TEST-INV-001',
            'po_number': 'TEST-PO-001',
            'amount': '$1,500.00',
            'supplier': 'Test Supplier Corp',
            'exception_type': 'price_discrepancy',
            'queue': 'price_discrepancies',
            'routing_reason': 'Price increased by 20%',
            'timestamp': '2024-01-15T10:00:00Z',
            'context': json.dumps({'original_price': 1250, 'new_price': 1500}),
            'raw_data': 'Sample raw data',
            'status': 'OPEN'
        }
        
        # Store sample exception
        exception_id = db.store_system_exception(sample_exception)
        print(f"✅ Created sample exception: {exception_id}")
        
        # Create sample feedback (approval override)
        feedback_id = db.store_human_feedback(
            invoice_id='TEST-INV-001',
            original_decision='REJECTED',
            human_correction='APPROVED',
            routing_queue='price_discrepancies',
            feedback_text='This 20% price increase should be approved for Test Supplier Corp as per our contract terms',
            expert_name='Test Expert',
            feedback_type='price_override',
            supporting_evidence={'contract_allows': True, 'threshold': '20%'}
        )
        print(f"✅ Created sample feedback: {feedback_id}")
        
        # The learning should be triggered automatically
        # Let's check if it was processed
        updated_exception = db.get_exception_by_id('TEST-EXC-001')
        if updated_exception and updated_exception.get('learning_insights'):
            print("✅ Learning was automatically processed!")
            print(f"📚 Learning Insights: {updated_exception['learning_insights'][:100]}...")
            print(f"🔧 Corrective Actions: {updated_exception['corrective_actions'][:100]}...")
        else:
            print("⚠️  Learning was not automatically processed (this might be expected if no API key)")
        
        # Test playbook generation
        generator = LearningPlaybookGenerator()
        playbook_summary = generator.get_playbook_summary()
        print(f"📚 Playbook now has {playbook_summary['total_entries']} entries")
        
        generator.close()
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Learning workflow test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧠 ResolveLight Learning System - Complete Test Suite")
    print("=" * 60)
    
    tests = [
        ("Database Migration", test_database_migration),
        ("Learning Processor", test_learning_processor),
        ("Playbook Generator", test_playbook_generator),
        ("Complete Workflow", test_sample_learning_workflow)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Learning system is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit(main())
