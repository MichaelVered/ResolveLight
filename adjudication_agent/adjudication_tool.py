"""
Adjudication Tool for ADK Agent Integration
Provides tools that the adjudication agent can call.
"""

from typing import Dict, List, Any
from pathlib import Path


def query_playbook(exception_type: str, playbook_path: str = None) -> Dict[str, Any]:
    """
    Tool for ADK agent to query the playbook for relevant entries.
    
    Args:
        exception_type: The type of exception (e.g., 'PRICE_DISCREPANCY')
        playbook_path: Path to the learning playbook JSONL file
    
    Returns:
        Dictionary containing relevant playbook entries and metadata
    """
    from .playbook_loader import PlaybookLoader
    
    # Default playbook path
    if playbook_path is None:
        playbook_path = Path(__file__).parent.parent / "learning_playbooks" / "learning_playbook.jsonl"
    
    playbook_path = Path(playbook_path)
    
    # Load and filter playbook
    playbook = PlaybookLoader.load_playbook(playbook_path)
    relevant_entries = PlaybookLoader.filter_by_exception_type(playbook, exception_type)
    formatted_entries = PlaybookLoader.format_playbook_for_agent(relevant_entries)
    
    return {
        "exception_type": exception_type,
        "total_entries_found": len(relevant_entries),
        "entries": relevant_entries,
        "formatted_entries": formatted_entries
    }

