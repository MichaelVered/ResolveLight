"""
Learning Playbook Generator
Generates human-readable learning playbooks from database learning insights.
Creates JSONL format playbooks for human review and LLM prompt generation.
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


class LearningPlaybookGenerator:
    """Generates human-readable learning playbooks from database learning insights."""
    
    def __init__(self, repo_root: str = None):
        """Initialize the learning playbook generator."""
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.db = LearningDatabase(os.path.join(self.repo_root, "learning_data", "learning.db"))
        self.playbook_dir = os.path.join(self.repo_root, "learning_playbooks")
        self.playbook_file = os.path.join(self.playbook_dir, "learning_playbook.jsonl")
        
        # Ensure playbook directory exists
        os.makedirs(self.playbook_dir, exist_ok=True)
    
    def generate_playbook_entry(self, exception_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a single playbook entry from exception data with learning insights.
        
        Args:
            exception_data: Exception data including learning insights and decision criteria
            
        Returns:
            Formatted playbook entry optimized for adjudication agent
        """
        entry = {
            "timestamp": exception_data.get('learning_timestamp', datetime.now().isoformat()),
            "exception_id": exception_data.get('exception_id', 'N/A'),
            "invoice_id": exception_data.get('invoice_id', 'N/A'),
            "exception_type": exception_data.get('exception_type', 'N/A'),
            "queue": exception_data.get('queue', 'N/A'),
            "supplier": exception_data.get('supplier', 'N/A'),
            "amount": exception_data.get('amount', 'N/A'),
            "po_number": exception_data.get('po_number', 'N/A'),
            "original_decision": exception_data.get('human_correction', 'N/A'),
            "expert_name": exception_data.get('expert_name', 'N/A'),
            "expert_feedback": exception_data.get('expert_feedback', 'N/A'),
            "learning_insights": exception_data.get('learning_insights', 'N/A'),
            "decision_criteria": exception_data.get('decision_criteria', 'N/A'),
            "validation_signature": exception_data.get('validation_signature', 'N/A'),
            "key_distinguishing_factors": exception_data.get('key_distinguishing_factors', []),
            "approval_conditions": exception_data.get('approval_conditions', []),
            "confidence_score": exception_data.get('confidence_score', 0.0),
            "generalization_warning": exception_data.get('generalization_warning', ''),
            "learning_agent_version": exception_data.get('learning_agent_version', '1.0'),
            "status": "active"
        }
        
        # Add VALIDATION_DETAILS to playbook entry for reference
        if 'VALIDATION_DETAILS' in exception_data:
            entry['validation_details'] = exception_data['VALIDATION_DETAILS']
        
        return entry
    
    def append_to_playbook(self, exception_data: Dict[str, Any]) -> bool:
        """
        Append a new learning entry to the playbook file.
        
        Args:
            exception_data: Exception data with learning insights
            
        Returns:
            True if successful, False otherwise
        """
        try:
            entry = self.generate_playbook_entry(exception_data)
            
            # Append to JSONL file
            with open(self.playbook_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            print(f"✅ Added learning entry to playbook: {entry['exception_id']}")
            
            # Generate formatted text file after appending
            self._generate_formatted_txt()
            
            return True
            
        except Exception as e:
            print(f"❌ Error appending to playbook: {e}")
            return False
    
    def generate_full_playbook(self) -> bool:
        """
        Generate a complete playbook from all exceptions with learning insights.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all exceptions with learning insights
            exceptions_with_learning = self.db.get_exceptions_with_learning()
            
            if not exceptions_with_learning:
                print("ℹ️  No exceptions with learning insights found.")
                return True
            
            # Clear existing playbook
            with open(self.playbook_file, 'w', encoding='utf-8') as f:
                f.write("")  # Clear the file
            
            # Generate entries for all exceptions
            success_count = 0
            for exception in exceptions_with_learning:
                if self.append_to_playbook(exception):
                    success_count += 1
            
            print(f"✅ Generated playbook with {success_count} learning entries")
            print(f"📁 Playbook location: {self.playbook_file}")
            
            # Generate formatted text file after generating full playbook
            self._generate_formatted_txt()
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating full playbook: {e}")
            return False
    
    def get_playbook_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current playbook.
        
        Returns:
            Dictionary with playbook statistics
        """
        try:
            if not os.path.exists(self.playbook_file):
                return {
                    "total_entries": 0,
                    "file_exists": False,
                    "file_path": self.playbook_file
                }
            
            entries = []
            with open(self.playbook_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            # Count by status
            status_counts = {}
            for entry in entries:
                status = entry.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by exception type
            type_counts = {}
            for entry in entries:
                exc_type = entry.get('exception_type', 'unknown')
                type_counts[exc_type] = type_counts.get(exc_type, 0) + 1
            
            return {
                "total_entries": len(entries),
                "file_exists": True,
                "file_path": self.playbook_file,
                "status_breakdown": status_counts,
                "type_breakdown": type_counts,
                "latest_entry": entries[-1] if entries else None
            }
            
        except Exception as e:
            print(f"❌ Error getting playbook summary: {e}")
            return {
                "total_entries": 0,
                "file_exists": False,
                "file_path": self.playbook_file,
                "error": str(e)
            }
    
    def _generate_formatted_txt(self) -> bool:
        """
        Generate a human-readable formatted text file from the JSONL playbook.
        Parses ALL entries and overwrites the formatted.txt file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.playbook_file):
                return False
            
            # Read all entries from JSONL
            entries = []
            with open(self.playbook_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            if not entries:
                return False
            
            # Generate formatted output
            output_lines = []
            output_lines.append("=" * 80)
            output_lines.append("LEARNING PLAYBOOK - HUMAN READABLE FORMAT")
            output_lines.append("=" * 80)
            output_lines.append("")
            
            for idx, entry in enumerate(entries, 1):
                output_lines.append(f"\n{'=' * 80}")
                output_lines.append(f"ENTRY #{idx}")
                output_lines.append(f"{'=' * 80}")
                output_lines.append(f"\nTimestamp: {entry.get('timestamp', 'N/A')}")
                output_lines.append(f"Status: {entry.get('status', 'N/A').upper()}")
                output_lines.append(f"Learning Agent Version: {entry.get('learning_agent_version', 'N/A')}")
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("EXCEPTION DETAILS")
                output_lines.append(f"{'-' * 80}")
                output_lines.append(f"Exception ID:     {entry.get('exception_id', 'N/A')}")
                output_lines.append(f"Invoice ID:       {entry.get('invoice_id', 'N/A')}")
                output_lines.append(f"Exception Type:   {entry.get('exception_type', 'N/A')}")
                output_lines.append(f"Queue:            {entry.get('queue', 'N/A')}")
                output_lines.append(f"Supplier:         {entry.get('supplier', 'N/A')}")
                output_lines.append(f"Amount:           {entry.get('amount', 'N/A')}")
                output_lines.append(f"PO Number:        {entry.get('po_number', 'N/A')}")
                output_lines.append(f"Original Decision: {entry.get('original_decision', 'N/A')}")
                
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("EXPERT FEEDBACK")
                output_lines.append(f"{'-' * 80}")
                output_lines.append(f"Expert Name: {entry.get('expert_name', 'N/A')}")
                output_lines.append(f"\nFeedback:")
                feedback = entry.get('expert_feedback', 'N/A')
                # Break long lines
                words = feedback.split()
                line = ""
                for word in words:
                    if len(line + word) > 70:
                        output_lines.append(line.strip())
                        line = word + " "
                    else:
                        line += word + " "
                if line.strip():
                    output_lines.append(line.strip())
                
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("LEARNING INSIGHTS")
                output_lines.append(f"{'-' * 80}")
                insights = entry.get('learning_insights', 'N/A')
                words = insights.split()
                line = ""
                for word in words:
                    if len(line + word) > 70:
                        output_lines.append(line.strip())
                        line = word + " "
                    else:
                        line += word + " "
                if line.strip():
                    output_lines.append(line.strip())
                
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("DECISION CRITERIA")
                output_lines.append(f"{'-' * 80}")
                criteria = entry.get('decision_criteria', 'N/A')
                # Process multi-line criteria
                for criteria_line in criteria.split('\n'):
                    if criteria_line.strip():
                        words = criteria_line.split()
                        line = ""
                        for word in words:
                            if len(line + word) > 70:
                                output_lines.append(line.strip())
                                line = word + " "
                            else:
                                line += word + " "
                        if line.strip():
                            output_lines.append(line.strip())
                    else:
                        output_lines.append("")
                
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("VALIDATION SIGNATURE")
                output_lines.append(f"{'-' * 80}")
                output_lines.append(entry.get('validation_signature', 'N/A'))
                
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("KEY DISTINGUISHING FACTORS")
                output_lines.append(f"{'-' * 80}")
                joint_factors = entry.get('key_distinguishing_factors', [])
                
                # Handle both list and string formats
                if isinstance(joint_factors, str):
                    # If it's a string, split by newlines to get individual factors
                    factors = [line.strip() for line in joint_factors.split('\n') if line.strip()]
                elif isinstance(joint_factors, list):
                    factors = joint_factors
                else:
                    factors = []
                
                if factors:
                    for i, factor in enumerate(factors, 1):
                        # Remove existing numbering if present (e.g., "1. " or "2. ")
                        factor_clean = factor.strip()
                        if factor_clean and factor_clean[0].isdigit():
                            # Check if it starts with a number pattern like "1. " or "2. "
                            import re
                            match = re.match(r'^\d+\.\s*', factor_clean)
                            if match:
                                factor_clean = factor_clean[match.end():]
                        
                        # Handle long factors by word-wrapping
                        words = factor_clean.split()
                        line = ""
                        is_first_line = True
                        for word in words:
                            if len(line + word) > 70:
                                if is_first_line:
                                    output_lines.append(f"{i}. {line.strip()}")
                                    is_first_line = False
                                else:
                                    output_lines.append(f"   {line.strip()}")
                                line = word + " "
                            else:
                                line += word + " "
                        if line.strip():
                            if is_first_line:
                                output_lines.append(f"{i}. {line.strip()}")
                            else:
                                output_lines.append(f"   {line.strip()}")
                else:
                    output_lines.append("N/A")
                
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("APPROVAL CONDITIONS")
                output_lines.append(f"{'-' * 80}")
                joint_conditions = entry.get('approval_conditions', [])
                
                # Handle both list and string formats
                if isinstance(joint_conditions, str):
                    # If it's a string, split by newlines to get individual conditions
                    conditions = [line.strip() for line in joint_conditions.split('\n') if line.strip()]
                elif isinstance(joint_conditions, list):
                    conditions = joint_conditions
                else:
                    conditions = []
                
                if conditions:
                    for i, condition in enumerate(conditions, 1):
                        # Remove existing numbering if present (e.g., "1. " or "2. ")
                        condition_clean = condition.strip()
                        if condition_clean and condition_clean[0].isdigit():
                            # Check if it starts with a number pattern like "1. " or "2. "
                            import re
                            match = re.match(r'^\d+\.\s*', condition_clean)
                            if match:
                                condition_clean = condition_clean[match.end():]
                        
                        # Handle long conditions by word-wrapping
                        words = condition_clean.split()
                        line = ""
                        is_first_line = True
                        for word in words:
                            if len(line + word) > 70:
                                if is_first_line:
                                    output_lines.append(f"{i}. {line.strip()}")
                                    is_first_line = False
                                else:
                                    output_lines.append(f"   {line.strip()}")
                                line = word + " "
                            else:
                                line += word + " "
                        if line.strip():
                            if is_first_line:
                                output_lines.append(f"{i}. {line.strip()}")
                            else:
                                output_lines.append(f"   {line.strip()}")
                else:
                    output_lines.append("N/A")
                
                output_lines.append(f"\n{'-' * 80}")
                output_lines.append("CONFIDENCE & GENERALIZATION")
                output_lines.append(f"{'-' * 80}")
                output_lines.append(f"Confidence Score: {entry.get('confidence_score', 'N/A')}")
                output_lines.append(f"\nGeneralization Warning:")
                warning = entry.get('generalization_warning', 'N/A')
                words = warning.split()
                line = ""
                for word in words:
                    if len(line + word) > 70:
                        output_lines.append(line.strip())
                        line = word + " "
                    else:
                        line += word + " "
                if line.strip():
                    output_lines.append(line.strip())
                
                output_lines.append("")
            
            # Write formatted file
            formatted_file = os.path.join(self.playbook_dir, "learning_playbook_formatted.txt")
            with open(formatted_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            
            print(f"✅ Generated formatted playbook: {formatted_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating formatted text file: {e}")
            return False
    
    def format_playbook_for_human(self) -> str:
        """
        Format the playbook in a human-readable format.
        
        Returns:
            Formatted playbook as string
        """
        try:
            if not os.path.exists(self.playbook_file):
                return "No playbook file found."
            
            entries = []
            with open(self.playbook_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            if not entries:
                return "No learning entries found in playbook."
            
            # Format for human reading
            formatted_parts = []
            formatted_parts.append("=" * 80)
            formatted_parts.append("RESOLVELIGHT LEARNING PLAYBOOK")
            formatted_parts.append("=" * 80)
            formatted_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            formatted_parts.append(f"Total Entries: {len(entries)}")
            formatted_parts.append("")
            
            for i, entry in enumerate(entries, 1):
                formatted_parts.append(f"ENTRY #{i}")
                formatted_parts.append("-" * 40)
                formatted_parts.append(f"Timestamp: {entry.get('timestamp', 'N/A')}")
                formatted_parts.append(f"Exception ID: {entry.get('exception_id', 'N/A')}")
                formatted_parts.append(f"Invoice ID: {entry.get('invoice_id', 'N/A')}")
                formatted_parts.append(f"Exception Type: {entry.get('exception_type', 'N/A')}")
                formatted_parts.append(f"Queue: {entry.get('queue', 'N/A')}")
                formatted_parts.append(f"Supplier: {entry.get('supplier', 'N/A')}")
                formatted_parts.append(f"Amount: {entry.get('amount', 'N/A')}")
                formatted_parts.append(f"PO Number: {entry.get('po_number', 'N/A')}")
                formatted_parts.append(f"Original Decision: {entry.get('original_decision', 'N/A')}")
                formatted_parts.append(f"Expert: {entry.get('expert_name', 'N/A')}")
                formatted_parts.append(f"Expert Feedback: {entry.get('expert_feedback', 'N/A')}")
                formatted_parts.append("")
                formatted_parts.append("LEARNING INSIGHTS:")
                formatted_parts.append(entry.get('learning_insights', 'N/A'))
                formatted_parts.append("")
                formatted_parts.append("CORRECTIVE ACTIONS:")
                formatted_parts.append(entry.get('corrective_actions', 'N/A'))
                formatted_parts.append("")
                formatted_parts.append("=" * 80)
                formatted_parts.append("")
            
            return "\n".join(formatted_parts)
            
        except Exception as e:
            return f"Error formatting playbook: {e}"
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Test the learning playbook generator."""
    print("📚 Testing Learning Playbook Generator...")
    
    try:
        generator = LearningPlaybookGenerator()
        
        # Test playbook summary
        print("Getting playbook summary...")
        summary = generator.get_playbook_summary()
        print(f"Playbook summary: {json.dumps(summary, indent=2)}")
        
        # Test human-readable format
        print("\nGenerating human-readable format...")
        human_format = generator.format_playbook_for_human()
        print(human_format[:500] + "..." if len(human_format) > 500 else human_format)
        
        generator.close()
        print("✅ Learning Playbook Generator test completed!")
        
    except Exception as e:
        print(f"❌ Error testing playbook generator: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
