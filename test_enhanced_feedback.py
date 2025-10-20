#!/usr/bin/env python3
"""
Test script for the enhanced feedback collection system.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent))

from learning_agent.database import LearningDatabase
from learning_agent.feedback_llm_service import FeedbackLLMService


def test_database_migrations():
    """Test that database migrations work correctly."""
    print("🧪 Testing database migrations...")
    
    try:
        db = LearningDatabase("learning_data/test_enhanced_feedback.db")
        
        # Test storing enhanced feedback
        feedback_id = db.store_human_feedback(
            invoice_id="TEST-12345",
            original_decision="REJECTED",
            human_correction="APPROVED",
            routing_queue="price_discrepancies",
            feedback_text="This 15% price increase should be approved for this supplier",
            expert_name="Test Expert",
            feedback_type="price_override",
            conversation_id="test_conv_123",
            is_initial_feedback=True,
            llm_questions='["What is the specific threshold for price increases?", "Does this apply to all contracts?"]',
            human_responses='["15% is acceptable", "Only for this supplier"]',
            feedback_summary='{"business_rules": [{"rule_type": "price_threshold", "threshold_value": "15%"}]}',
            conversation_status="completed",
            quality_score=0.9
        )
        
        print(f"✅ Stored enhanced feedback with ID: {feedback_id}")
        
        # Test retrieving conversation
        conversation = db.get_feedback_conversation("test_conv_123")
        print(f"✅ Retrieved conversation with {len(conversation)} items")
        
        # Test active conversations
        active_conversations = db.get_active_conversations()
        print(f"✅ Found {len(active_conversations)} active conversations")
        
        db.close()
        print("✅ Database migrations test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database migrations test failed: {e}")
        return False


def test_llm_service():
    """Test the LLM service for question generation and summarization."""
    print("\n🧪 Testing LLM service...")
    
    try:
        llm_service = FeedbackLLMService()
        
        # Test question generation
        test_feedback = {
            'invoice_id': 'TEST-12345',
            'original_agent_decision': 'REJECTED',
            'human_correction': 'APPROVED',
            'routing_queue': 'price_discrepancies',
            'feedback_text': 'This 15% price increase should be approved for this supplier',
            'expert_name': 'Test Expert',
            'feedback_type': 'price_override'
        }
        
        print("Testing question generation...")
        questions_result = llm_service.generate_feedback_questions(test_feedback)
        print(f"✅ Generated {len(questions_result.get('questions', []))} questions")
        print(f"   Reasoning: {questions_result.get('reasoning', 'N/A')[:100]}...")
        
        # Test conversation summarization
        print("Testing conversation summarization...")
        # First create a test conversation in the main database
        db = LearningDatabase("learning_data/learning.db")
        
        conversation_id = "test_summary_conv"
        feedback_id = db.store_human_feedback(
            invoice_id="TEST-12345",
            original_decision="REJECTED",
            human_correction="APPROVED",
            routing_queue="price_discrepancies",
            feedback_text="This 15% price increase should be approved for this supplier",
            expert_name="Test Expert",
            feedback_type="price_override",
            conversation_id=conversation_id,
            is_initial_feedback=True,
            llm_questions='["What is the specific threshold?", "Does this apply to all contracts?"]',
            human_responses='["15% is acceptable", "Only for this supplier"]'
        )
        
        db.close()
        
        # Use the same LLM service instance
        summary_result = llm_service.summarize_feedback_conversation(conversation_id)
        
        if 'error' in summary_result:
            print(f"❌ Summarization failed: {summary_result['error']}")
            return False
        
        print(f"✅ Generated summary with {len(summary_result.get('business_rules', []))} business rules")
        print(f"   Quality: {summary_result.get('feedback_quality', {}).get('overall_quality', 'Unknown')}")
        
        llm_service.close()
        print("✅ LLM service test passed!")
        return True
        
    except Exception as e:
        print(f"❌ LLM service test failed: {e}")
        return False


def test_web_routes():
    """Test that web routes are properly configured."""
    print("\n🧪 Testing web routes...")
    
    try:
        # Import the Flask app
        from web_gui.human_driven_app import app
        
        # Check that new routes exist
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        required_routes = [
            '/feedback/submit_initial',
            '/feedback/submit_response', 
            '/feedback/generate_summary',
            '/feedback/complete'
        ]
        
        missing_routes = []
        for route in required_routes:
            if route not in routes:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"❌ Missing routes: {missing_routes}")
            return False
        
        print("✅ All required routes are present")
        print("✅ Web routes test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Web routes test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Enhanced Feedback System Tests...\n")
    
    tests = [
        test_database_migrations,
        test_llm_service,
        test_web_routes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced feedback system is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
