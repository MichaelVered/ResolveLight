#!/usr/bin/env python3
"""
Demonstration script for the ResolveLight Learning from Human Feedback System.
Shows how the system processes human feedback and generates learning insights.
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


def demo_learning_workflow():
    """Demonstrate the complete learning workflow."""
    print("🎯 ResolveLight Learning System - Live Demonstration")
    print("=" * 60)
    
    try:
        # Initialize components
        db = LearningDatabase()
        processor = FeedbackLearningProcessor()
        generator = LearningPlaybookGenerator()
        
        print("📊 Current System Status:")
        stats = processor.get_learning_statistics()
        print(f"  - Total exceptions: {stats['database_stats']['system_exceptions']}")
        print(f"  - Human feedback entries: {stats['database_stats']['human_feedback']}")
        print(f"  - Exceptions with learning: {stats['exceptions_with_learning']}")
        print(f"  - Pending approval overrides: {stats['pending_approval_overrides']}")
        print(f"  - Playbook entries: {stats['playbook_summary']['total_entries']}")
        
        # Create a realistic example
        print("\n🔄 Creating Example Learning Scenario...")
        
        # Create sample exception
        sample_exception = {
            'exception_id': 'DEMO-EXC-001',
            'invoice_id': 'DEMO-INV-001',
            'po_number': 'DEMO-PO-001',
            'amount': '$2,500.00',
            'supplier': 'Acme Manufacturing Inc',
            'exception_type': 'price_discrepancy',
            'queue': 'price_discrepancies',
            'routing_reason': 'Price increased by 18% from quoted amount',
            'timestamp': '2024-01-15T14:30:00Z',
            'context': json.dumps({
                'original_quoted_price': 2118.64,
                'invoice_price': 2500.00,
                'percentage_increase': 18.0,
                'contract_id': 'CONTRACT-ACME-2024'
            }),
            'raw_data': 'Exception: Price discrepancy detected - 18% increase',
            'status': 'OPEN'
        }
        
        exception_id = db.store_system_exception(sample_exception)
        print(f"✅ Created exception: {exception_id}")
        
        # Create human feedback (approval override)
        feedback_id = db.store_human_feedback(
            invoice_id='DEMO-INV-001',
            original_decision='REJECTED',
            human_correction='APPROVED',
            routing_queue='price_discrepancies',
            feedback_text='This 18% price increase should be approved for Acme Manufacturing. Our contract with them allows up to 20% price increases for raw material cost fluctuations. The increase is within acceptable limits and the supplier has provided proper documentation.',
            expert_name='Sarah Johnson',
            feedback_type='price_override',
            supporting_evidence={
                'contract_allows': True,
                'threshold': '20%',
                'supplier_documentation': 'Provided cost fluctuation report',
                'business_justification': 'Raw material costs increased due to market conditions'
            }
        )
        print(f"✅ Created feedback: {feedback_id}")
        print("   (Learning processing should be triggered automatically)")
        
        # Wait a moment for processing
        import time
        time.sleep(2)
        
        # Check if learning was processed
        updated_exception = db.get_exception_by_id('DEMO-EXC-001')
        if updated_exception and updated_exception.get('learning_insights'):
            print("\n🧠 Learning Processing Results:")
            print(f"   Learning Insights: {updated_exception['learning_insights'][:150]}...")
            print(f"   Corrective Actions: {updated_exception['corrective_actions'][:150]}...")
            print(f"   Learning Timestamp: {updated_exception.get('learning_timestamp', 'N/A')}")
            print(f"   Agent Version: {updated_exception.get('learning_agent_version', 'N/A')}")
        else:
            print("\n⚠️  Learning processing may not have completed (check API key configuration)")
        
        # Show playbook
        print("\n📚 Learning Playbook:")
        playbook_summary = generator.get_playbook_summary()
        print(f"   Total entries: {playbook_summary['total_entries']}")
        
        # Show human-readable format
        print("\n📖 Human-Readable Playbook (latest entry):")
        human_format = generator.format_playbook_for_human()
        # Show the last entry
        entries = human_format.split("ENTRY #")
        if len(entries) > 1:
            last_entry = entries[-1]
            print(last_entry[:800] + "..." if len(last_entry) > 800 else last_entry)
        
        # Show statistics
        print("\n📊 Final Statistics:")
        final_stats = processor.get_learning_statistics()
        print(f"   Exceptions with learning: {final_stats['exceptions_with_learning']}")
        print(f"   Playbook entries: {final_stats['playbook_summary']['total_entries']}")
        
        print("\n✅ Demonstration completed successfully!")
        print("\n💡 Next Steps:")
        print("   1. Review the learning insights in the database")
        print("   2. Check the playbook for human-readable format")
        print("   3. Implement the suggested corrective actions")
        print("   4. Monitor system performance improvements")
        
        # Cleanup
        db.close()
        processor.close()
        generator.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        return False


def show_usage_examples():
    """Show usage examples for the learning system."""
    print("\n📖 Usage Examples:")
    print("=" * 30)
    
    print("\n1. Process all pending learning:")
    print("   python learning_agent/feedback_learning_processor.py --process-all")
    
    print("\n2. Process specific feedback:")
    print("   python learning_agent/feedback_learning_processor.py --feedback-id 123")
    
    print("\n3. Show learning statistics:")
    print("   python learning_agent/feedback_learning_processor.py --stats")
    
    print("\n4. Generate human-readable playbook:")
    print("   python -c \"")
    print("   from learning_agent.learning_playbook_generator import LearningPlaybookGenerator")
    print("   generator = LearningPlaybookGenerator()")
    print("   print(generator.format_playbook_for_human())")
    print("   \"")
    
    print("\n5. Run complete test suite:")
    print("   python test_learning_system.py")


def main():
    """Main demonstration function."""
    print("🚀 Welcome to the ResolveLight Learning System Demo!")
    print("This demonstration shows how the system learns from human feedback.")
    print()
    
    # Check if API key is configured
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  Warning: No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY")
        print("   Learning processing will work but LLM insights may not be generated.")
        print()
    
    # Run demonstration
    success = demo_learning_workflow()
    
    # Show usage examples
    show_usage_examples()
    
    if success:
        print("\n🎉 Demonstration completed successfully!")
        return 0
    else:
        print("\n❌ Demonstration failed. Check the error messages above.")
        return 1


if __name__ == "__main__":
    exit(main())
