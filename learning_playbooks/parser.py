"""
Parser for learning playbook formatted text files.
Extracts structured learning entries from the formatted text.
"""

import re
from datetime import datetime
from typing import List, Dict, Optional


def parse_learning_playbook(file_path: str) -> List[Dict]:
    """
    Parse a formatted learning playbook text file and extract learning entries.
    
    Args:
        file_path: Path to the formatted text file
        
    Returns:
        List of learning entry dictionaries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content by entry separator
    entries = content.split('ENTRY #')
    
    learning_entries = []
    
    for i, entry in enumerate(entries[1:], start=1):  # Skip first empty entry
        try:
            learning_entry = _parse_entry(entry, i)
            if learning_entry:
                learning_entries.append(learning_entry)
        except Exception as e:
            print(f"Error parsing entry #{i}: {e}")
            continue
    
    return learning_entries


def _parse_entry(entry_text: str, entry_number: int) -> Optional[Dict]:
    """Parse a single learning entry."""
    
    # Extract timestamp
    timestamp_match = re.search(r'Timestamp:\s*(.+)', entry_text)
    timestamp = timestamp_match.group(1).strip() if timestamp_match else None
    
    # Extract status
    status_match = re.search(r'Status:\s*(.+)', entry_text)
    status = status_match.group(1).strip() if status_match else 'UNKNOWN'
    
    # Extract learning agent version
    version_match = re.search(r'Learning Agent Version:\s*(.+)', entry_text)
    version = version_match.group(1).strip() if version_match else 'Unknown'
    
    # Extract exception details
    exception_details = _extract_section_by_name(entry_text, 'EXCEPTION DETAILS')
    exception_id = _extract_field(exception_details, 'Exception ID')
    invoice_id = _extract_field(exception_details, 'Invoice ID')
    exception_type = _extract_field(exception_details, 'Exception Type')
    queue = _extract_field(exception_details, 'Queue')
    supplier = _extract_field(exception_details, 'Supplier')
    amount = _extract_field(exception_details, 'Amount')
    po_number = _extract_field(exception_details, 'PO Number')
    original_decision = _extract_field(exception_details, 'Original Decision')
    
    # Extract expert feedback
    expert_feedback = _extract_section_by_name(entry_text, 'EXPERT FEEDBACK')
    expert_name = _extract_field(expert_feedback, 'Expert Name')
    feedback_text = _extract_field(expert_feedback, 'Feedback', multiline=True)
    
    # Extract learning insights
    learning_insights = _extract_section_by_name(entry_text, 'LEARNING INSIGHTS')
    
    # Extract decision criteria
    decision_criteria = _extract_section_by_name(entry_text, 'DECISION CRITERIA')
    
    # Extract validation signature
    validation_signature = _extract_section_by_name(entry_text, 'VALIDATION SIGNATURE')
    
    # Extract key distinguishing factors
    key_factors = _extract_section_by_name(entry_text, 'KEY DISTINGUISHING FACTORS')
    
    # Extract approval conditions
    approval_conditions = _extract_section_by_name(entry_text, 'APPROVAL CONDITIONS')
    
    # Extract confidence and generalization
    confidence_section = _extract_section_by_name(entry_text, 'CONFIDENCE & GENERALIZATION')
    confidence_match = re.search(r'Confidence Score:\s*([\d.]+)', confidence_section)
    confidence_score = float(confidence_match.group(1)) if confidence_match else 0.0
    generalization_warning = _extract_field(confidence_section, 'Generalization Warning', multiline=True)
    
    return {
        'entry_number': entry_number,
        'timestamp': timestamp,
        'status': status,
        'learning_agent_version': version,
        'exception_id': exception_id,
        'invoice_id': invoice_id,
        'exception_type': exception_type,
        'queue': queue,
        'supplier': supplier,
        'amount': amount,
        'po_number': po_number,
        'original_decision': original_decision,
        'expert_name': expert_name,
        'feedback_text': feedback_text,
        'learning_insights': learning_insights,
        'decision_criteria': decision_criteria,
        'validation_signature': validation_signature,
        'key_distinguishing_factors': key_factors,
        'approval_conditions': approval_conditions,
        'confidence_score': confidence_score,
        'generalization_warning': generalization_warning
    }


def _extract_section_by_name(text: str, section_name: str) -> str:
    """Extract a section by its name."""
    # Find the section header pattern
    pattern = rf'-{{80,}}\s*{re.escape(section_name)}\s*-{{80,}}'
    
    # Find start position
    match = re.search(pattern, text)
    if not match:
        return ''
    
    start_pos = match.end()
    
    # Find the next section header (or entry separator)
    remaining_text = text[start_pos:]
    
    # Find next separator: lines of dashes
    next_sep = re.search(r'\n-{80,}\n', remaining_text)
    if next_sep:
        return remaining_text[:next_sep.start()].strip()
    
    # Check for next ENTRY
    next_entry = re.search(r'\n+ENTRY #', remaining_text)
    if next_entry:
        return remaining_text[:next_entry.start()].strip()
    
    return remaining_text.strip()


def _extract_field(text: str, field_name: str, multiline: bool = False) -> str:
    """Extract a field value from a section."""
    if multiline:
        # For multiline fields, capture everything until next field or empty line
        pattern = rf'{field_name}:\s*(.*?)(?=\n[A-Z][a-z]+:|\n\n|$)'
    else:
        # For single line fields
        pattern = rf'{field_name}:\s*(.+?)(?=\n[A-Z][a-z]+:|$)'
    
    match = re.search(pattern, text, re.DOTALL)
    if match:
        value = match.group(1).strip()
        # Clean up: remove trailing dashes
        lines = value.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith('-') and len(line.strip()) > 70:
                break
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines).strip()
    
    return ''


def save_to_jsonl(entries: List[Dict], file_path: str):
    """Save learning entries to JSONL format."""
    import json
    with open(file_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def load_from_jsonl(file_path: str) -> List[Dict]:
    """Load learning entries from JSONL format."""
    import json
    entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except FileNotFoundError:
        pass
    return entries
