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
# Optional Google SDK imports (fallback if unavailable)
try:
    import google.generativeai as genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception:
    genai = None  # type: ignore
    types = None  # type: ignore

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from learning_agent.database import LearningDatabase


class LearningInsightsLLM:
    """LLM service for generating learning insights and corrective actions from human feedback."""
    
    def __init__(self, repo_root: str = None, api_key: str = None):
        """Initialize the learning insights LLM service with graceful fallback."""
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.db = LearningDatabase(os.path.join(self.repo_root, "learning_data", "learning.db"))

        self.model = None
        self.fallback_mode = False

        # Configure Gemini API if SDK is available
        if genai is not None:
            configured = False
            key_to_use = api_key
            if not key_to_use:
                try:
                    from dotenv import load_dotenv  # type: ignore
                    env_path = os.path.join(os.path.dirname(self.repo_root), ".env")
                    load_dotenv(env_path)
                except Exception:
                    pass
                key_to_use = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            try:
                if key_to_use:
                    genai.configure(api_key=key_to_use)
                    self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    configured = True
            except Exception:
                configured = False
            if not configured:
                self.fallback_mode = True
        else:
            # SDK not available
            self.fallback_mode = True
    
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

TASK: Extract decision rules and criteria from the VALIDATION_DETAILS that explain why the human approved this exception.

YOUR GOAL: Create a generalizable but precise RULE that the adjudication agent can use to approve FUTURE SIMILAR EXCEPTIONS that match the semantic pattern and technical criteria.

CRITICAL ANALYSIS REQUIREMENTS:
1. Examine the VALIDATION_DETAILS section carefully - this contains the EXACT validation failure that occurred
2. Identify what the human approved despite this failure - look for SEMANTIC PATTERNS not exact words
3. Extract SPECIFIC thresholds, differences, and ranges (these must be exact)
4. Extract GENERALIZABLE concepts and explanations (use semantic matching, not exact word matching)
5. Define clear BOUNDARIES to prevent false positives

GENERALIZATION GUIDELINES:
- DO generalize: concepts, semantic patterns, reasonable explanations (e.g., "discount with reasonable explanation" not "loyalty discount")
- DO NOT generalize: exact values, thresholds, validation tools, or fields (these must match exactly)
- Example: If human approved a "loyalty discount", extract the generalizable concept as "discount" with "reasonable documented explanation"
- Look for the SEMANTIC MEANING behind the approval, not the exact wording

RESPONSE FORMAT (JSON only, no other text):
{{
    "learning_insights": "Brief summary of why this exception was approved (max 150 words)",
    "decision_criteria": "Criteria extracted from VALIDATION_DETAILS:\\n\\nVALIDATION PATTERN (EXACT MATCH REQUIRED):\\n- Tool: [same tool]\\n- Field: [same field]\\n- FAILED_RULE: [same rule]\\n\\nACCEPTABLE RANGES (EXACT VALUES):\\n- [Specific condition based on DIFFERENCE, THRESHOLD, or COMPARISON_METHOD]\\n- Example: If DIFFERENCE was 0.02, specify acceptable range (e.g., '≤0.02')\\n\\nSEMANTIC PATTERNS (GENERALIZABLE CONCEPTS):\\n- [Generalizable concepts: e.g., 'discount with documented explanation' not 'loyalty discount']\\n- [Reasonable explanations that justify the exception]\\n\\nMUST HAVE:\\n- [Required technical conditions that must match exactly]\\n- [Required semantic conditions that should match conceptually]\\n\\nDO NOT APPROVE IF:\\n- [Different validation pattern (different tool/field/rule)]\\n- [Threshold/range exceeded]\\n- [No reasonable documented explanation]\\n- [Other issues present besides the approved exception]",
    "key_distinguishing_factors": ["Technical factor", "Semantic/conceptual factor"],
    "validation_signature": "{{Tool: X, Field: Y, Rule: Z, Difference: ≤W}}",
    "approval_conditions": ["Technical condition", "Semantic/conceptual condition"],
    "confidence_score": 0.85,
    "generalization_warning": "WARNING: Technical aspects (tool, field, rule, thresholds) must match exactly. Semantic aspects (explanations, concepts) should match conceptually. Do not approve if validation pattern differs."
}}

CRITICAL CONSTRAINTS:
- Match TECHNICAL aspects exactly (tool, field, rule, thresholds)
- Match SEMANTIC aspects conceptually (generalizable concepts and explanations)
- Include clear BOUNDARIES to prevent false positives
- Maximum 500 words total
"""

        try:
            if self.fallback_mode or self.model is None:
                # Deterministic fallback without external LLM
                summary = self._fallback_summarize_context(exception_data, feedback_data, related_data)
                actions = self._fallback_generate_actions(exception_data, feedback_data)
                validation_details = exception_data.get('VALIDATION_DETAILS', [])
                signature = "Unknown"
                if validation_details and len(validation_details) > 0:
                    block = validation_details[0]
                    tool = block.get('Tool', 'N/A')
                    field = block.get('Field', 'N/A')
                    rule = block.get('FAILED_RULE', 'N/A')
                    diff = block.get('DIFFERENCE', 'N/A')
                    signature = f"{{Tool: {tool}, Field: {field}, Rule: {rule}, Difference: {diff}}}"
                return {
                    "learning_insights": summary,
                    "decision_criteria": actions,
                    "key_distinguishing_factors": [],
                    "validation_signature": signature,
                    "approval_conditions": [],
                    "confidence_score": 0.5,
                    "generalization_warning": "Generated in fallback mode without external LLM."
                }

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
                    "decision_criteria": "Error parsing LLM response",
                    "key_distinguishing_factors": [],
                    "validation_signature": "Unknown",
                    "approval_conditions": [],
                    "confidence_score": 0.0,
                    "generalization_warning": "Error in LLM response parsing"
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
                    "decision_criteria": f"Decision criteria generated but JSON parsing failed. Raw response: {json_text[:200]}...",
                    "key_distinguishing_factors": ["JSON parsing error - manual review required"],
                    "validation_signature": "Unknown",
                    "approval_conditions": ["JSON parsing error - manual review required"],
                    "confidence_score": 0.3,
                    "generalization_warning": "Manual review of LLM response required due to JSON parsing error"
                }
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Response: {response_text[:500]}...")
            return {
                "learning_insights": f"JSON parsing error: {e}",
                "decision_criteria": f"JSON parsing error: {e}",
                "key_distinguishing_factors": [],
                "validation_signature": "Unknown",
                "approval_conditions": [],
                "confidence_score": 0.0,
                "generalization_warning": "Error in JSON parsing"
            }
        except Exception as e:
            # Final fallback
            print(f"Error generating learning insights: {e}")
            summary = self._fallback_summarize_context(exception_data, feedback_data, related_data)
            actions = self._fallback_generate_actions(exception_data, feedback_data)
            validation_details = exception_data.get('VALIDATION_DETAILS', [])
            signature = "Unknown"
            if validation_details and len(validation_details) > 0:
                block = validation_details[0]
                tool = block.get('Tool', 'N/A')
                field = block.get('Field', 'N/A')
                rule = block.get('FAILED_RULE', 'N/A')
                diff = block.get('DIFFERENCE', 'N/A')
                signature = f"{{Tool: {tool}, Field: {field}, Rule: {rule}, Difference: {diff}}}"
            return {
                "learning_insights": summary,
                "decision_criteria": actions,
                "key_distinguishing_factors": [],
                "validation_signature": signature,
                "approval_conditions": [],
                "confidence_score": 0.4,
                "generalization_warning": "Fallback mode used due to error."
            }

    def _fallback_summarize_context(self, exception_data: Dict[str, Any], feedback_data: Dict[str, Any], related_data: Dict[str, Any]) -> str:
        parts = []
        parts.append(f"Invoice {exception_data.get('invoice_id','N/A')} rejected by agent but approved by expert.")
        if exception_data.get('exception_type'):
            parts.append(f"Exception: {exception_data.get('exception_type')} in {exception_data.get('queue','N/A')} queue.")
        rationale = feedback_data.get('feedback_text') or ''
        if rationale:
            parts.append(f"Expert rationale: {rationale[:300]}.")
        if related_data.get('invoice'):
            parts.append("Invoice data considered.")
        if related_data.get('po_item'):
            parts.append("PO data considered.")
        if related_data.get('contract'):
            parts.append("Contract data considered.")
        return " ".join(parts)

    def _fallback_generate_actions(self, exception_data: Dict[str, Any], feedback_data: Dict[str, Any]) -> str:
        exc_type = exception_data.get('exception_type','N/A')
        queue = exception_data.get('queue','general_exceptions')
        validation_details = exception_data.get('VALIDATION_DETAILS', [])
        
        criteria = "VALIDATION PATTERN (EXACT MATCH REQUIRED):\n"
        if validation_details and len(validation_details) > 0:
            block = validation_details[0]
            tool = block.get('Tool', 'N/A')
            field = block.get('Field', 'N/A')
            rule = block.get('FAILED_RULE', 'N/A')
            criteria += f"- Tool: {tool}\n- Field: {field}\n- FAILED_RULE: {rule}\n\n"
        else:
            criteria += f"- Exception Type: {exc_type}\n- Queue: {queue}\n\n"
        
        criteria += "ACCEPTABLE RANGES (EXACT VALUES):\n"
        criteria += "- Review feedback text for specific thresholds\n\n"
        
        criteria += "SEMANTIC PATTERNS (GENERALIZABLE CONCEPTS):\n"
        criteria += "- Extract generalizable concepts from expert feedback\n"
        criteria += "- Look for semantic patterns, not exact words\n\n"
        
        criteria += "MUST HAVE:\n"
        criteria += f"- Same exception type: {exc_type}\n"
        criteria += f"- Same queue: {queue}\n"
        criteria += "- Technical aspects match exactly\n"
        criteria += "- Semantic aspects match conceptually\n\n"
        
        criteria += "DO NOT APPROVE IF:\n"
        criteria += "- Different validation pattern\n"
        criteria += "- Threshold exceeded\n"
        criteria += "- No reasonable documented explanation\n\n"
        
        criteria += "CONTEXTUAL FACTORS:\n"
        criteria += f"- Expert feedback: {feedback_data.get('feedback_text', 'N/A')[:200]}"
        
        return criteria
    
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
        
        # Add VALIDATION_DETAILS if present (this is the KEY information)
        if 'VALIDATION_DETAILS' in exception_data and exception_data['VALIDATION_DETAILS']:
            context_parts.append("\nVALIDATION_DETAILS:")
            context_parts.append("=" * 30)
            for i, block in enumerate(exception_data['VALIDATION_DETAILS'], 1):
                context_parts.append(f"\nBlock {i}:")
                for key, value in block.items():
                    context_parts.append(f"  {key}: {value}")
        
        context_parts.append(f"\nContext: {exception_data.get('context', 'N/A')}")
        
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
