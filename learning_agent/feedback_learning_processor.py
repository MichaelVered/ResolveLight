"""
Feedback Learning Processor
Main processor that handles learning from human feedback on exceptions.
Processes exceptions where human said "should be approved but was rejected".
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from learning_agent.database import LearningDatabase
from learning_agent.learning_insights_llm import LearningInsightsLLM
from learning_agent.learning_playbook_generator import LearningPlaybookGenerator


class FeedbackLearningProcessor:
    """Main processor for learning from human feedback on exceptions."""
    
    def __init__(self, repo_root: str = None, api_key: str = None):
        """Initialize the feedback learning processor."""
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.db = LearningDatabase(os.path.join(self.repo_root, "learning_data", "learning.db"))
        self.llm_service = LearningInsightsLLM(self.repo_root, api_key)
        self.playbook_generator = LearningPlaybookGenerator(self.repo_root)
        self.learning_agent_version = "1.0"
    
    def process_feedback_learning(self, feedback_id: int) -> bool:
        """
        Process learning from a specific human feedback entry.
        
        Args:
            feedback_id: ID of the human feedback to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the feedback data
            feedback_data = self._get_feedback_by_id(feedback_id)
            if not feedback_data:
                print(f"❌ Feedback ID {feedback_id} not found")
                return False
            
            # Check if this is a "should be approved but was rejected" case
            if not self._is_approval_override_case(feedback_data):
                print(f"ℹ️  Feedback {feedback_id} is not an approval override case, skipping")
                return True
            
            # Get the related exception
            exception_data = self._get_exception_by_invoice_id(feedback_data['invoice_id'])
            if not exception_data:
                print(f"❌ No exception found for invoice {feedback_data['invoice_id']}")
                return False
            
            # Get related data (invoice, PO, contract, etc.)
            related_data = self.db.get_related_data(feedback_data['invoice_id'])
            
            # Generate learning insights using LLM
            print(f"🧠 Generating learning insights for exception {exception_data['exception_id']}...")
            learning_result = self.llm_service.generate_learning_insights(
                exception_data, feedback_data, related_data
            )
            
            # Store learning insights in database
            success = self.db.update_exception_learning(
                exception_id=exception_data['exception_id'],
                learning_insights=learning_result['learning_insights'],
                corrective_actions=learning_result['corrective_actions'],
                learning_agent_version=self.learning_agent_version
            )
            
            if not success:
                print(f"❌ Failed to update exception {exception_data['exception_id']} with learning insights")
                return False
            
            # Add to learning playbook
            updated_exception = self._get_exception_by_id(exception_data['exception_id'])
            playbook_success = self.playbook_generator.append_to_playbook(updated_exception)
            
            if not playbook_success:
                print(f"⚠️  Failed to add to playbook, but learning was stored in database")
            
            print(f"✅ Successfully processed learning for exception {exception_data['exception_id']}")
            print(f"📚 Learning insights: {learning_result['learning_insights'][:100]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing feedback learning for ID {feedback_id}: {e}")
            return False
    
    def process_all_pending_learning(self) -> Dict[str, Any]:
        """
        Process learning for all pending feedback that hasn't been processed yet.
        
        Returns:
            Dictionary with processing results
        """
        try:
            # Get all feedback that represents approval overrides
            pending_feedback = self._get_pending_approval_overrides()
            
            if not pending_feedback:
                return {
                    "processed_count": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "message": "No pending approval override feedback found"
                }
            
            print(f"🔄 Processing {len(pending_feedback)} pending approval override feedback entries...")
            
            success_count = 0
            error_count = 0
            
            for feedback in pending_feedback:
                try:
                    if self.process_feedback_learning(feedback['id']):
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    print(f"❌ Error processing feedback {feedback['id']}: {e}")
                    error_count += 1
            
            result = {
                "processed_count": len(pending_feedback),
                "success_count": success_count,
                "error_count": error_count,
                "message": f"Processed {success_count}/{len(pending_feedback)} feedback entries successfully"
            }
            
            print(f"✅ Batch processing completed: {result['message']}")
            return result
            
        except Exception as e:
            print(f"❌ Error in batch processing: {e}")
            return {
                "processed_count": 0,
                "success_count": 0,
                "error_count": 0,
                "message": f"Error: {e}"
            }
    
    def _is_approval_override_case(self, feedback_data: Dict[str, Any]) -> bool:
        """Check if this feedback represents an approval override case."""
        original_decision = feedback_data.get('original_agent_decision', '').upper()
        human_correction = feedback_data.get('human_correction', '').upper()
        
        # Check if human said it should be approved but was rejected
        return (original_decision == 'REJECTED' and 
                human_correction == 'APPROVED')
    
    def _get_feedback_by_id(self, feedback_id: int) -> Optional[Dict[str, Any]]:
        """Get feedback data by ID."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM human_feedback WHERE id = ?", (feedback_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            feedback = dict(row)
            # Parse JSON fields
            if feedback.get('supporting_evidence'):
                try:
                    feedback['supporting_evidence'] = json.loads(feedback['supporting_evidence'])
                except:
                    pass
            return feedback
        
        return None
    
    def _get_exception_by_invoice_id(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get exception data by invoice ID."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM system_exceptions WHERE invoice_id = ?", (invoice_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def _get_exception_by_id(self, exception_id: str) -> Optional[Dict[str, Any]]:
        """Get exception data by exception ID."""
        return self.db.get_exception_by_id(exception_id)
    
    def _get_pending_approval_overrides(self) -> List[Dict[str, Any]]:
        """Get all feedback that represents approval overrides and hasn't been processed for learning."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get feedback where human corrected REJECTED to APPROVED
        # and the related exception doesn't have learning insights yet
        cursor.execute("""
            SELECT hf.* FROM human_feedback hf
            LEFT JOIN system_exceptions se ON hf.invoice_id = se.invoice_id
            WHERE hf.original_agent_decision = 'REJECTED' 
            AND hf.human_correction = 'APPROVED'
            AND (se.learning_insights IS NULL OR se.learning_insights = '')
            ORDER BY hf.created_at ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        feedback_list = []
        for row in rows:
            feedback = dict(row)
            # Parse JSON fields
            if feedback.get('supporting_evidence'):
                try:
                    feedback['supporting_evidence'] = json.loads(feedback['supporting_evidence'])
                except:
                    pass
            feedback_list.append(feedback)
        
        return feedback_list
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics about learning processing."""
        try:
            # Get database stats
            db_stats = self.db.get_database_stats()
            
            # Get exceptions with learning
            exceptions_with_learning = self.db.get_exceptions_with_learning()
            
            # Get pending approval overrides
            pending_overrides = self._get_pending_approval_overrides()
            
            # Get playbook summary
            playbook_summary = self.playbook_generator.get_playbook_summary()
            
            return {
                "database_stats": db_stats,
                "exceptions_with_learning": len(exceptions_with_learning),
                "pending_approval_overrides": len(pending_overrides),
                "playbook_summary": playbook_summary,
                "learning_agent_version": self.learning_agent_version
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "learning_agent_version": self.learning_agent_version
            }
    
    def close(self):
        """Close all connections."""
        self.db.close()
        self.llm_service.close()
        self.playbook_generator.close()


def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process learning from human feedback")
    parser.add_argument("--feedback-id", type=int, help="Process specific feedback ID")
    parser.add_argument("--process-all", action="store_true", help="Process all pending feedback")
    parser.add_argument("--stats", action="store_true", help="Show learning statistics")
    parser.add_argument("--api-key", help="Gemini API key")
    
    args = parser.parse_args()
    
    print("🧠 ResolveLight Feedback Learning Processor")
    print("=" * 50)
    
    try:
        processor = FeedbackLearningProcessor(api_key=args.api_key)
        
        if args.stats:
            # Show statistics
            stats = processor.get_learning_statistics()
            print("📊 Learning Statistics:")
            print(json.dumps(stats, indent=2))
            
        elif args.feedback_id:
            # Process specific feedback
            print(f"Processing feedback ID {args.feedback_id}...")
            success = processor.process_feedback_learning(args.feedback_id)
            if success:
                print("✅ Processing completed successfully!")
            else:
                print("❌ Processing failed!")
                return 1
                
        elif args.process_all:
            # Process all pending
            print("Processing all pending approval overrides...")
            result = processor.process_all_pending_learning()
            print(f"Result: {result['message']}")
            if result['error_count'] > 0:
                return 1
                
        else:
            # Show help
            parser.print_help()
            return 1
        
        processor.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
