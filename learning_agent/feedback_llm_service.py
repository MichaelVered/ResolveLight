"""
LLM Service for Enhanced Human Feedback Collection
Generates specific, actionable questions and summarizes feedback conversations.
"""

import os
import sys
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.genai import types

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from learning_agent.database import LearningDatabase


class FeedbackLLMService:
    """LLM service for generating questions and summarizing feedback conversations."""
    
    def __init__(self, repo_root: str = None, api_key: str = None):
        """Initialize the feedback LLM service."""
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
    
    def generate_feedback_questions(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate specific, actionable questions based on human feedback.
        Focuses on extracting concrete business rules and thresholds.
        """
        
        # Create context for the LLM
        context = self._create_questioning_context(feedback_data)
        
        prompt = f"""
You are an expert business process analyst helping to collect high-quality, actionable feedback from domain experts.

CONTEXT:
{context}

YOUR TASK:
Generate 3-5 specific, actionable questions that will help extract concrete business rules, thresholds, and conditions from the expert's feedback.

QUESTION GUIDELINES:
1. Focus on SPECIFIC THRESHOLDS and LIMITS:
   - "What is the exact percentage limit for price increases?"
   - "What is the maximum acceptable quantity deviation?"
   - "What is the specific dollar amount threshold for approval?"

2. Determine SCOPE of APPLICATION:
   - "Does this rule apply only to this specific contract or all contracts with this supplier?"
   - "Is this a company-wide policy or supplier-specific?"
   - "Does this apply to all invoice types or only certain categories?"

3. Identify CONDITIONS and EXCEPTIONS:
   - "What are the exact conditions under which this exception should be approved?"
   - "Are there any specific documentation requirements?"
   - "What circumstances would override this rule?"

4. Clarify BUSINESS LOGIC:
   - "Should this be approved automatically if conditions are met?"
   - "What is the approval workflow for this type of exception?"
   - "Who has authority to make exceptions to this rule?"

5. Extract ACTIONABLE DETAILS:
   - "What specific changes should be made to the system?"
   - "What validation rules need to be added or modified?"
   - "What are the exact criteria for future similar cases?"

RESPONSE FORMAT (JSON):
{{
    "questions": [
        "Question 1: Specific threshold question",
        "Question 2: Scope of application question", 
        "Question 3: Conditions and exceptions question",
        "Question 4: Business logic clarification question",
        "Question 5: Actionable details question"
    ],
    "reasoning": "Brief explanation of why these questions will extract the most actionable information",
    "expected_outcome": "What concrete business rules we expect to extract from the answers"
}}

Make questions specific enough that the answers can be directly translated into system rules and configurations.
"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                print(f"Warning: Could not extract JSON from LLM response: {response_text[:200]}...")
                return {"questions": [], "reasoning": "Error parsing response", "expected_outcome": ""}
            
            result = json.loads(json_text)
            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Response: {response_text[:500]}...")
            return {"questions": [], "reasoning": f"JSON parsing error: {e}", "expected_outcome": ""}
        except Exception as e:
            print(f"Error generating feedback questions: {e}")
            return {"questions": [], "reasoning": f"Error: {e}", "expected_outcome": ""}
    
    def summarize_feedback_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Summarize a complete feedback conversation for the next learning stage.
        Extracts actionable business rules and system improvements.
        """
        
        # Get the complete conversation
        conversation = self.db.get_feedback_conversation(conversation_id)
        
        if not conversation:
            return {"error": "Conversation not found"}
        
        # Create context for summarization
        context = self._create_summarization_context(conversation)
        
        prompt = f"""
You are an expert business process analyst summarizing a feedback conversation to extract actionable insights for system improvement.

CONVERSATION CONTEXT:
{context}

YOUR TASK:
Summarize this feedback conversation to extract:
1. Specific business rules and thresholds
2. System improvement opportunities  
3. Actionable changes for the next learning stage

SUMMARIZATION REQUIREMENTS:
1. Extract CONCRETE THRESHOLDS and LIMITS mentioned
2. Identify SPECIFIC BUSINESS RULES that should be implemented
3. Determine SCOPE of application (supplier-specific, contract-specific, company-wide)
4. List ACTIONABLE SYSTEM CHANGES needed
5. Note any EXCEPTIONS or SPECIAL CONDITIONS
6. Assess FEEDBACK QUALITY and COMPLETENESS

RESPONSE FORMAT (JSON):
{{
    "business_rules": [
        {{
            "rule_type": "price_threshold|quantity_limit|approval_workflow|etc",
            "description": "Clear description of the rule",
            "threshold_value": "Specific value or condition",
            "scope": "supplier_specific|contract_specific|company_wide",
            "conditions": ["List of conditions that apply"],
            "exceptions": ["List of any exceptions mentioned"]
        }}
    ],
    "system_improvements": [
        {{
            "improvement_type": "validation_rule|routing_logic|approval_process|etc",
            "description": "What needs to be changed",
            "specific_changes": "Exact changes to implement",
            "priority": "high|medium|low",
            "impact": "Expected impact on system performance"
        }}
    ],
    "feedback_quality": {{
        "completeness_score": 0.0-1.0,
        "actionability_score": 0.0-1.0,
        "specificity_score": 0.0-1.0,
        "overall_quality": "excellent|good|fair|poor",
        "missing_information": ["What additional info would be helpful"]
    }},
    "next_steps": [
        "Specific actions to take based on this feedback",
        "Questions to ask for clarification if needed",
        "System changes to implement"
    ],
    "summary": "Overall summary of the feedback conversation and its value for system improvement"
}}

Focus on extracting information that can be directly used to improve the system's decision-making capabilities.
"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                print(f"Warning: Could not extract JSON from LLM response: {response_text[:200]}...")
                return {"error": "Could not parse LLM response"}
            
            result = json.loads(json_text)
            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Response: {response_text[:500]}...")
            return {"error": f"JSON parsing error: {e}"}
        except Exception as e:
            print(f"Error summarizing feedback conversation: {e}")
            return {"error": f"Error: {e}"}
    
    def _create_questioning_context(self, feedback_data: Dict[str, Any]) -> str:
        """Create context for question generation."""
        context_parts = []
        
        context_parts.append("HUMAN FEEDBACK CONTEXT")
        context_parts.append("=" * 30)
        context_parts.append(f"Invoice ID: {feedback_data.get('invoice_id', 'N/A')}")
        context_parts.append(f"Original Agent Decision: {feedback_data.get('original_agent_decision', 'N/A')}")
        context_parts.append(f"Human Correction: {feedback_data.get('human_correction', 'N/A')}")
        context_parts.append(f"Routing Queue: {feedback_data.get('routing_queue', 'N/A')}")
        context_parts.append(f"Expert Name: {feedback_data.get('expert_name', 'N/A')}")
        context_parts.append(f"Feedback Type: {feedback_data.get('feedback_type', 'N/A')}")
        context_parts.append(f"Feedback Text: {feedback_data.get('feedback_text', 'N/A')}")
        
        # Add system context
        context_parts.append("\nSYSTEM CONTEXT:")
        context_parts.append(self._get_system_context())
        
        return "\n".join(context_parts)
    
    def _create_summarization_context(self, conversation: List[Dict[str, Any]]) -> str:
        """Create context for conversation summarization."""
        context_parts = []
        
        context_parts.append("FEEDBACK CONVERSATION SUMMARY")
        context_parts.append("=" * 40)
        context_parts.append(f"Conversation ID: {conversation[0].get('conversation_id', 'N/A')}")
        context_parts.append(f"Number of Exchanges: {len(conversation)}")
        context_parts.append(f"Expert: {conversation[0].get('expert_name', 'N/A')}")
        
        context_parts.append("\nCONVERSATION DETAILS:")
        for i, exchange in enumerate(conversation, 1):
            context_parts.append(f"\n--- Exchange {i} ---")
            context_parts.append(f"Type: {'Initial Feedback' if exchange.get('is_initial_feedback') else 'Follow-up'}")
            context_parts.append(f"Feedback: {exchange.get('feedback_text', 'N/A')}")
            if exchange.get('llm_questions'):
                context_parts.append(f"LLM Questions: {exchange.get('llm_questions')}")
            if exchange.get('human_responses'):
                context_parts.append(f"Human Responses: {exchange.get('human_responses')}")
        
        return "\n".join(context_parts)
    
    def _get_system_context(self) -> str:
        """Get relevant system context for LLM analysis."""
        context_parts = []
        
        # Read key source files
        source_files = [
            "root_agent.yaml",
            "sub_agents/validation_agent.yaml",
            "sub_agents/triage_agent.yaml", 
            "sub_agents/contract_matching_agent.yaml",
            "tool_library/validation_runner_tool.py",
            "tool_library/triage_resolution_tool.py"
        ]
        
        for file_path in source_files:
            full_path = os.path.join(self.repo_root, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    context_parts.append(f"\n--- {file_path} ---")
                    context_parts.append(content[:1000])  # Limit size
                    context_parts.append("...")
                except Exception as e:
                    context_parts.append(f"\n--- {file_path} --- (Error reading: {e})")
        
        return "\n".join(context_parts)
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Test the feedback LLM service."""
    print("🧠 Testing Feedback LLM Service...")
    
    try:
        service = FeedbackLLMService()
        
        # Test question generation
        test_feedback = {
            'invoice_id': 'INV-12345',
            'original_agent_decision': 'REJECTED',
            'human_correction': 'APPROVED',
            'routing_queue': 'price_discrepancies',
            'feedback_text': 'This 15% price increase should be approved for this supplier',
            'expert_name': 'John Smith',
            'feedback_type': 'price_override'
        }
        
        print("Testing question generation...")
        questions = service.generate_feedback_questions(test_feedback)
        print(f"Generated questions: {json.dumps(questions, indent=2)}")
        
        service.close()
        print("✅ Feedback LLM Service test completed!")
        
    except Exception as e:
        print(f"❌ Error testing feedback LLM service: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
