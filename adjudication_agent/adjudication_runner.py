#!/usr/bin/env python3
"""
Standalone Adjudication Agent Runner

This script allows manual adjudication of exceptions using the learning playbook.
It shows all exceptions, lets you pick one, and the agent makes a decision.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import google.generativeai as genai
from google.genai import types

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from adjudication_agent.exception_parser import ExceptionParser
from adjudication_agent.playbook_loader import PlaybookLoader


class AdjudicationAgent:
    """The adjudication agent that makes decisions based on playbook rules."""
    
    def __init__(self, repo_root: Path = None):
        """Initialize the adjudication agent."""
        self.repo_root = repo_root or Path(__file__).parent.parent
        self.playbook_path = self.repo_root / "learning_playbooks" / "learning_playbook.jsonl"
        
        # Configure Gemini API
        try:
            from dotenv import load_dotenv
            env_path = self.repo_root.parent / ".env"
            load_dotenv(env_path)
        except ImportError:
            pass
        
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Load playbook
        self.playbook = PlaybookLoader.load_playbook(self.playbook_path)
        print(f"Loaded {len(self.playbook)} entries from playbook.")
    
    def adjudicate(self, exception: Dict) -> str:
        """Make adjudication decision for the exception."""
        exception_type = exception.get('EXCEPTION_TYPE', 'UNKNOWN')
        
        # Format the inputs for the agent
        exception_text = ExceptionParser.format_exception(exception)
        playbook_text = self._get_playbook_context(exception_type)
        
        # Load agent instruction from YAML
        agent_config_path = self.repo_root / "adjudication_agent" / "adjudication_agent.yaml"
        
        instruction = ""
        if agent_config_path.exists():
            import yaml
            with open(agent_config_path, 'r') as f:
                config = yaml.safe_load(f)
            instruction = config.get('instruction', '')
        
        # Create the full prompt
        prompt = f"""{playbook_text}

{exception_text}

Now adjudicate this exception based on the playbook rules above."""
        
        if instruction:
            full_prompt = f"""{instruction}

Now, here is your task:

{prompt}

Provide your FINAL JUDGMENT with DECISION and JUSTIFICATION."""
        else:
            full_prompt = prompt
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"Error during adjudication: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_playbook_context(self, exception_type: str) -> str:
        """Get relevant playbook context for the exception type."""
        relevant_entries = PlaybookLoader.filter_by_exception_type(self.playbook, exception_type)
        return PlaybookLoader.format_playbook_for_agent(relevant_entries)


def display_exceptions(exceptions: List[Dict]):
    """Display exceptions as a numbered list."""
    if not exceptions:
        print("No exceptions found in system logs.")
        return
    
    print("\n" + "="*80)
    print("EXCEPTIONS FOUND:")
    print("="*80)
    
    for i, exc in enumerate(exceptions, 1):
        exc_id = exc.get('EXCEPTION_ID', 'N/A')
        exc_type = exc.get('EXCEPTION_TYPE', 'N/A')
        invoice_id = exc.get('INVOICE_ID', 'N/A')
        po_number = exc.get('PO_NUMBER', 'N/A')
        amount = exc.get('AMOUNT', 'N/A')
        queue = exc.get('QUEUE', 'N/A')
        
        print(f"\n{i}. Exception ID: {exc_id}")
        print(f"   Type: {exc_type}")
        print(f"   Invoice: {invoice_id} | PO: {po_number}")
        print(f"   Amount: {amount}")
        print(f"   Queue: {queue}")


def main():
    """Main entry point for the standalone adjudication agent."""
    base_dir = Path(__file__).parent.parent
    system_logs_dir = base_dir / "system_logs"
    
    print("="*80)
    print("ADJUDICATION AGENT - Standalone Runner")
    print("="*80)
    
    # Load all exceptions
    print("\nLoading exceptions from system logs...")
    exceptions = ExceptionParser.get_all_exceptions(system_logs_dir)
    
    if not exceptions:
        print("No exceptions found. Exiting.")
        return
    
    display_exceptions(exceptions)
    
    # Let user pick an exception
    print("\n" + "="*80)
    try:
        choice = input(f"\nEnter exception number (1-{len(exceptions)}): ").strip()
        choice_num = int(choice)
        
        if choice_num < 1 or choice_num > len(exceptions):
            print("Invalid choice.")
            return
        
        selected_exception = exceptions[choice_num - 1]
        
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")
        return
    
    # Initialize agent
    print("\n" + "="*80)
    print("Loading adjudication agent and playbook...")
    agent = AdjudicationAgent(base_dir)
    
    if not agent.playbook:
        print("Warning: Playbook is empty or not found.")
    
    # Adjudicate
    print("\n" + "="*80)
    print("ADJUDICATING EXCEPTION...")
    print("="*80)
    
    result = agent.adjudicate(selected_exception)
    
    if result:
        print("\n" + result)
    else:
        print("Adjudication failed.")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()

