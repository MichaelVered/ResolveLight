"""
Learning Insights LLM Service
Generates learning insights and corrective actions from human feedback on exceptions.
Focuses on creative and specific corrective actions for system improvement.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.genai import types

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from learning_agent.database import LearningDatabase


class LearningInsightsLLM:
    """LLM service for generating learning insights and corrective actions from human feedback."""
    
    def __init__(self, repo_root: str = None, api_key: str = None):
        """Initialize the learning insights LLM service."""
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.db = LearningDatabase(os.path.join(self.repo_root, "learning_data", "learning.db"))
        
        # Configure Gemini API
        if api_key:
            genai.configure(api_key=api_key)
        else:
            # Try to get from .env file first
            try:
                from dotenv import load_dotenv
                # Load .env file from projects directory
                env_path = os.path.join(os.path.dirname(self.repo_root), ".env")
                load_dotenv(env_path)
            except ImportError:
                pass
            
            # Try to get from environment variables
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env file or environment variable.")
            genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def generate_learning_insights(self, exception_data: Dict[str, Any], 
                                 feedback_data: Dict[str, Any], 
                                 related_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate learning insights and corrective actions from human feedback.
        
        Args:
            exception_data: The system exception that was corrected
            feedback_data: The human feedback that corrected the decision
            related_data: Related invoice, PO, contract, and other artifacts
            
        Returns:
            Dictionary containing learning_insights and corrective_actions
        """
        
        # Create comprehensive context for the LLM
        context = self._create_learning_context(exception_data, feedback_data, related_data)
        
        prompt = f"""
You are an expert system architect analyzing human feedback on invoice processing exceptions.

CONTEXT:
{context}

TASK: Generate learning insights and corrective actions for this approval override case.

RESPONSE FORMAT (JSON only, no other text):
{{
    "learning_insights": "Brief learning insight (max 200 words)",
    "corrective_actions": "Priority 1 [HIGH]: [Action] - [Description]\\n- File: [path]\\n- Change: [specific change]\\n\\nPriority 2 [MEDIUM]: [Action] - [Description]\\n- File: [path]\\n- Change: [specific change]",
    "business_rules_extracted": ["Rule 1", "Rule 2"],
    "patterns_identified": ["Pattern 1", "Pattern 2"],
    "confidence_score": 0.85,
    "additional_recommendations": "Brief recommendation (max 100 words)"
}}

Keep responses concise and focused. Maximum 500 words total.
"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            json_text = None
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            
            if not json_text:
                print(f"Warning: Could not extract JSON from LLM response: {response_text[:200]}...")
                return {
                    "learning_insights": "Error parsing LLM response",
                    "corrective_actions": "Error parsing LLM response",
                    "business_rules_extracted": [],
                    "patterns_identified": [],
                    "confidence_score": 0.0,
                    "additional_recommendations": "Error in LLM response parsing"
                }
            
            # Clean up the JSON text to handle control characters
            import re
            json_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_text)  # Remove control characters
            
            # Try to fix common JSON issues
            try:
                result = json.loads(json_text)
                return result
            except json.JSONDecodeError as e:
                # Try to fix truncated JSON by adding missing closing braces
                if "Unterminated string" in str(e) or "Expecting" in str(e):
                    # Count opening and closing braces
                    open_braces = json_text.count('{')
                    close_braces = json_text.count('}')
                    if open_braces > close_braces:
                        json_text += '}' * (open_braces - close_braces)
                    try:
                        result = json.loads(json_text)
                        return result
                    except:
                        pass
                
                # If still failing, create a fallback response
                print(f"Warning: Could not parse JSON, creating fallback response: {e}")
                return {
                    "learning_insights": f"Learning insights generated but JSON parsing failed. Raw response: {json_text[:200]}...",
                    "corrective_actions": f"Corrective actions generated but JSON parsing failed. Raw response: {json_text[:200]}...",
                    "business_rules_extracted": ["JSON parsing error - manual review required"],
                    "patterns_identified": ["JSON parsing error - manual review required"],
                    "confidence_score": 0.3,
                    "additional_recommendations": "Manual review of LLM response required due to JSON parsing error"
                }
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Response: {response_text[:500]}...")
            return {
                "learning_insights": f"JSON parsing error: {e}",
                "corrective_actions": f"JSON parsing error: {e}",
                "business_rules_extracted": [],
                "patterns_identified": [],
                "confidence_score": 0.0,
                "additional_recommendations": "Error in JSON parsing"
            }
        except Exception as e:
            print(f"Error generating learning insights: {e}")
            return {
                "learning_insights": f"Error: {e}",
                "corrective_actions": f"Error: {e}",
                "business_rules_extracted": [],
                "patterns_identified": [],
                "confidence_score": 0.0,
                "additional_recommendations": "Error in processing"
            }
    
    def _create_learning_context(self, exception_data: Dict[str, Any], 
                               feedback_data: Dict[str, Any], 
                               related_data: Dict[str, Any]) -> str:
        """Create comprehensive context for learning analysis."""
        context_parts = []
        
        # Exception details
        context_parts.append("EXCEPTION DETAILS")
        context_parts.append("=" * 30)
        context_parts.append(f"Exception ID: {exception_data.get('exception_id', 'N/A')}")
        context_parts.append(f"Invoice ID: {exception_data.get('invoice_id', 'N/A')}")
        context_parts.append(f"Exception Type: {exception_data.get('exception_type', 'N/A')}")
        context_parts.append(f"Queue: {exception_data.get('queue', 'N/A')}")
        context_parts.append(f"PO Number: {exception_data.get('po_number', 'N/A')}")
        context_parts.append(f"Amount: {exception_data.get('amount', 'N/A')}")
        context_parts.append(f"Supplier: {exception_data.get('supplier', 'N/A')}")
        context_parts.append(f"Routing Reason: {exception_data.get('routing_reason', 'N/A')}")
        context_parts.append(f"Context: {exception_data.get('context', 'N/A')}")
        
        # Human feedback details
        context_parts.append("\nHUMAN FEEDBACK")
        context_parts.append("=" * 30)
        context_parts.append(f"Original Agent Decision: {feedback_data.get('original_agent_decision', 'N/A')}")
        context_parts.append(f"Human Correction: {feedback_data.get('human_correction', 'N/A')}")
        context_parts.append(f"Expert Name: {feedback_data.get('expert_name', 'N/A')}")
        context_parts.append(f"Feedback Type: {feedback_data.get('feedback_type', 'N/A')}")
        context_parts.append(f"Feedback Text: {feedback_data.get('feedback_text', 'N/A')}")
        context_parts.append(f"Supporting Evidence: {feedback_data.get('supporting_evidence', 'N/A')}")
        
        # Related data
        context_parts.append("\nRELATED DATA")
        context_parts.append("=" * 30)
        if related_data.get('invoice'):
            context_parts.append("Invoice Data:")
            context_parts.append(json.dumps(related_data['invoice'], indent=2)[:1000] + "...")
        
        if related_data.get('po_item'):
            context_parts.append("\nPO Data:")
            context_parts.append(json.dumps(related_data['po_item'], indent=2)[:1000] + "...")
        
        if related_data.get('contract'):
            context_parts.append("\nContract Data:")
            context_parts.append(json.dumps(related_data['contract'], indent=2)[:1000] + "...")
        
        # System context
        context_parts.append("\nSYSTEM CONTEXT")
        context_parts.append("=" * 30)
        context_parts.append(self._get_system_context())
        
        return "\n".join(context_parts)
    
    def _get_system_context(self) -> str:
        """Get relevant system context for learning analysis."""
        context_parts = []
        
        # Read key source files
        source_files = [
            "root_agent.yaml",
            "sub_agents/validation_agent.yaml",
            "sub_agents/triage_agent.yaml", 
            "sub_agents/contract_matching_agent.yaml",
            "tool_library/validation_runner_tool.py",
            "tool_library/triage_resolution_tool.py",
            "tool_library/price_validation_tool.py",
            "tool_library/supplier_match_tool.py"
        ]
        
        for file_path in source_files:
            full_path = os.path.join(self.repo_root, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    context_parts.append(f"\n--- {file_path} ---")
                    context_parts.append(content[:1500])  # Limit size
                    context_parts.append("...")
                except Exception as e:
                    context_parts.append(f"\n--- {file_path} --- (Error reading: {e})")
        
        return "\n".join(context_parts)
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Test the learning insights LLM service."""
    print("🧠 Testing Learning Insights LLM Service...")
    
    try:
        service = LearningInsightsLLM()
        
        # Test with sample data
        test_exception = {
            'exception_id': 'EXC-12345',
            'invoice_id': 'INV-67890',
            'exception_type': 'price_discrepancy',
            'queue': 'price_discrepancies',
            'po_number': 'PO-2025-001',
            'amount': '$1,250.00',
            'supplier': 'ABC Corp',
            'routing_reason': 'Price increased by 15%',
            'context': {'original_price': 1000, 'new_price': 1150}
        }
        
        test_feedback = {
            'original_agent_decision': 'REJECTED',
            'human_correction': 'APPROVED',
            'expert_name': 'John Smith',
            'feedback_type': 'price_override',
            'feedback_text': 'This 15% price increase should be approved for ABC Corp as per contract terms',
            'supporting_evidence': {'contract_allows': True, 'threshold': '15%'}
        }
        
        test_related_data = {
            'invoice': {'invoice_id': 'INV-67890', 'amount': 1150, 'supplier': 'ABC Corp'},
            'po_item': {'po_number': 'PO-2025-001', 'contract_id': 'CONTRACT-001'},
            'contract': {'contract_id': 'CONTRACT-001', 'price_increase_limit': '15%'}
        }
        
        print("Generating learning insights...")
        result = service.generate_learning_insights(test_exception, test_feedback, test_related_data)
        print(f"Generated insights: {json.dumps(result, indent=2)}")
        
        service.close()
        print("✅ Learning Insights LLM Service test completed!")
        
    except Exception as e:
        print(f"❌ Error testing learning insights service: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
