"""
Playbook Loader for Adjudication Agent
Loads and manages the learning playbook for adjudication decisions.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class PlaybookLoader:
    """Loads and manages the learning playbook."""
    
    @staticmethod
    def load_playbook(playbook_path: Path) -> List[Dict]:
        """Load all entries from the JSONL playbook file."""
        entries = []
        
        try:
            with open(playbook_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError as e:
                            print(f"Warning: Skipping malformed playbook entry: {e}")
        except FileNotFoundError:
            print(f"Warning: Playbook file not found: {playbook_path}")
        except Exception as e:
            print(f"Error loading playbook: {e}")
        
        return entries
    
    @staticmethod
    def filter_by_exception_type(playbook: List[Dict], exception_type: str) -> List[Dict]:
        """Filter playbook entries relevant to the exception type."""
        exception_type_normalized = exception_type.upper().replace("_", "_")
        
        relevant_entries = []
        for entry in playbook:
            if entry.get('exception_type', '').upper().replace("_", "_") == exception_type_normalized:
                relevant_entries.append(entry)
        
        return relevant_entries
    
    @staticmethod
    def format_playbook_for_agent(entries: List[Dict]) -> str:
        """Format playbook entries for agent prompt."""
        if not entries:
            return "No relevant playbook entries found for this exception type."
        
        formatted = "RELEVANT PLAYBOOK ENTRIES:\n\n"
        for i, entry in enumerate(entries, 1):
            formatted += f"""=== ENTRY {i} ===
Timestamp: {entry.get('timestamp', 'N/A')}
Exception ID: {entry.get('exception_id', 'N/A')}
Invoice ID: {entry.get('invoice_id', 'N/A')}
Exception Type: {entry.get('exception_type', 'N/A')}
Supplier: {entry.get('supplier', 'N/A')}
Amount: {entry.get('amount', 'N/A')}
Original Decision: {entry.get('original_decision', 'N/A')}
Expert Name: {entry.get('expert_name', 'N/A')}

Expert Feedback:
{entry.get('expert_feedback', 'N/A')}

Learning Insights:
{entry.get('learning_insights', 'N/A')}

VALIDATION SIGNATURE (MUST MATCH THIS EXACT PATTERN):
{entry.get('validation_signature', 'N/A')}

DECISION CRITERIA (USE THIS TO EVALUATE FUTURE EXCEPTIONS):
{entry.get('decision_criteria', 'N/A')}

Key Distinguishing Factors:
{', '.join(entry.get('key_distinguishing_factors', []))}

Approval Conditions:
{chr(10).join('- ' + cond for cond in entry.get('approval_conditions', []))}

Generalization Warning:
{entry.get('generalization_warning', 'None')}

---

"""
        
        return formatted

