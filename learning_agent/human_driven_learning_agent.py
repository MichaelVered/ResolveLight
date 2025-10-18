"""
Human-Driven Learning Agent
Focuses on learning from human expert feedback rather than autonomous log analysis.
This aligns with the original design where domain experts provide feedback on specific exceptions.
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


class HumanDrivenLearningAgent:
    """
    Learning agent that focuses on human expert feedback.
    Generates learning plans based on human corrections and domain expertise.
    """
    
    def __init__(self, repo_root: str = None, api_key: str = None):
        """Initialize the human-driven learning agent."""
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
    
    def generate_learning_plans_from_feedback(self) -> Dict[str, Any]:
        """
        Generate learning plans based on human feedback.
        This is the core function that analyzes expert feedback and creates optimization plans.
        """
        print("🧠 Analyzing human feedback to generate learning plans...")
        
        # Get all human feedback
        feedback_items = self.db.get_human_feedback()
        
        if not feedback_items:
            print("ℹ️  No human feedback found. Please add feedback through the web GUI.")
            return {
                'learning_plans_generated': 0,
                'feedback_analyzed': 0,
                'message': 'No human feedback available for analysis'
            }
        
        print(f"📝 Found {len(feedback_items)} feedback items to analyze")
        
        # Group feedback by type and patterns
        grouped_feedback = self._group_feedback_by_patterns(feedback_items)
        
        learning_plans = []
        
        # Generate learning plans for each feedback group
        for pattern_type, feedback_group in grouped_feedback.items():
            if len(feedback_group) >= 1:  # Generate plans even for single feedback items
                plan = self._generate_plan_from_feedback_group(pattern_type, feedback_group)
                if plan:
                    learning_plans.append(plan)
        
        # Store learning plans
        plan_ids = []
        for plan in learning_plans:
            plan_id = self.db.store_learning_plan(
                plan_type=plan['plan_type'],
                title=plan['title'],
                description=plan['description'],
                source_learning_records=plan['source_learning_records'],
                suggested_changes=plan['suggested_changes'],
                impact_analysis=plan['impact_analysis'],
                priority=plan['priority'],
                llm_reasoning=plan['llm_reasoning']
            )
            plan_ids.append(plan_id)
        
        print(f"✅ Generated {len(learning_plans)} learning plans from human feedback")
        
        return {
            'learning_plans_generated': len(learning_plans),
            'feedback_analyzed': len(feedback_items),
            'learning_plan_ids': plan_ids,
            'learning_plans': learning_plans
        }
    
    def _group_feedback_by_patterns(self, feedback_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group feedback items by patterns and types."""
        groups = {
            'routing_corrections': [],
            'validation_overrides': [],
            'business_rule_violations': [],
            'data_quality_issues': [],
            'false_positives': [],
            'false_negatives': [],
            'other': []
        }
        
        for feedback in feedback_items:
            feedback_type = feedback.get('feedback_type', 'other')
            
            if feedback_type == 'routing_correction':
                groups['routing_corrections'].append(feedback)
            elif feedback_type == 'validation_override':
                groups['validation_overrides'].append(feedback)
            elif feedback_type == 'business_rule':
                groups['business_rule_violations'].append(feedback)
            elif feedback_type == 'data_quality':
                groups['data_quality_issues'].append(feedback)
            elif feedback_type == 'false_positive':
                groups['false_positives'].append(feedback)
            elif feedback_type == 'false_negative':
                groups['false_negatives'].append(feedback)
            else:
                groups['other'].append(feedback)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _generate_plan_from_feedback_group(self, pattern_type: str, feedback_group: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate a learning plan from a group of similar feedback."""
        
        # Create context for LLM
        context = self._create_feedback_context(pattern_type, feedback_group)
        
        # Generate learning plan using LLM
        plan = self._generate_single_learning_plan(pattern_type, feedback_group, context)
        
        if plan:
            # Add source learning record IDs (we'll create them from feedback)
            plan['source_learning_records'] = [f['id'] for f in feedback_group]
        
        return plan
    
    def _create_feedback_context(self, pattern_type: str, feedback_group: List[Dict[str, Any]]) -> str:
        """Create context string for LLM analysis of human feedback."""
        context_parts = []
        
        # Add system overview
        context_parts.append("HUMAN EXPERT FEEDBACK ANALYSIS")
        context_parts.append("=" * 40)
        context_parts.append(f"Pattern Type: {pattern_type}")
        context_parts.append(f"Number of Feedback Items: {len(feedback_group)}")
        
        # Add source code context
        context_parts.append("\nSOURCE CODE CONTEXT:")
        context_parts.append(self._get_source_code_context())
        
        # Add feedback details
        context_parts.append(f"\nHUMAN FEEDBACK DETAILS ({pattern_type}):")
        for i, feedback in enumerate(feedback_group, 1):
            context_parts.append(f"\n{i}. Invoice ID: {feedback['invoice_id']}")
            context_parts.append(f"   Original Decision: {feedback['original_agent_decision']}")
            context_parts.append(f"   Human Correction: {feedback['human_correction']}")
            context_parts.append(f"   Expert: {feedback['expert_name']}")
            context_parts.append(f"   Feedback Type: {feedback['feedback_type']}")
            context_parts.append(f"   Feedback Text: {feedback['feedback_text']}")
            if feedback.get('routing_queue'):
                context_parts.append(f"   Routing Queue: {feedback['routing_queue']}")
        
        return "\n".join(context_parts)
    
    def _get_source_code_context(self) -> str:
        """Get relevant source code context for LLM analysis."""
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
                    context_parts.append(content[:2000])  # Limit size
                    context_parts.append("...")
                except Exception as e:
                    context_parts.append(f"\n--- {file_path} --- (Error reading: {e})")
        
        return "\n".join(context_parts)
    
    def _generate_single_learning_plan(self, pattern_type: str, feedback_group: List[Dict[str, Any]], context: str) -> Optional[Dict[str, Any]]:
        """Generate a single learning plan using LLM analysis of human feedback."""
        
        prompt = f"""
You are an expert system optimization analyst. Based on the human expert feedback and source code context below, generate a specific, actionable learning plan.

CONTEXT:
{context}

FEEDBACK PATTERN TYPE: {pattern_type}
NUMBER OF FEEDBACK ITEMS: {len(feedback_group)}

REQUIREMENTS:
1. Analyze the human expert feedback to understand the ROOT CAUSE of the issues
2. Determine the BEST optimization strategy from these options:
   - prompt_optimization: Improve agent instructions/prompts
   - tool_enhancement: Modify existing validation tools
   - new_validation_rule: Add new business logic
   - fuzzy_matching_improvement: Enhance matching algorithms
   - confidence_threshold_adjustment: Tune decision thresholds
   - routing_logic_optimization: Improve queue routing
   - data_validation_enhancement: Better data quality checks
   - exception_handling_improvement: Better error handling
   - business_rule_addition: Add new business rules
   - performance_optimization: Speed/memory improvements

3. Provide SPECIFIC, CODE-LEVEL changes based on the human feedback:
   - If prompt optimization: Show the EXACT new prompt
   - If tool enhancement: Show the EXACT code changes
   - If new validation rule: Show the EXACT implementation
   - If threshold adjustment: Show the EXACT new values

4. Focus on addressing the specific issues mentioned in the human feedback
5. Include impact analysis and implementation complexity

RESPONSE FORMAT (JSON):
{{
    "plan_type": "chosen_optimization_strategy",
    "title": "Clear, descriptive title based on human feedback",
    "description": "Detailed description of the problem and solution based on expert feedback",
    "suggested_changes": {{
        "file_path": "path/to/file",
        "change_type": "replace|add|modify",
        "old_code": "existing code to change",
        "new_code": "new code implementation",
        "additional_files": ["list", "of", "files", "to", "modify"]
    }},
    "impact_analysis": {{
        "affected_invoices": "estimated number based on feedback patterns",
        "improvement_expected": "description of expected improvement",
        "risk_level": "low|medium|high",
        "implementation_effort": "low|medium|high"
    }},
    "priority": "low|medium|high|critical",
    "llm_reasoning": "Detailed explanation of why this approach was chosen based on the human feedback and how it addresses the specific issues mentioned by experts"
}}

Focus on SPECIFIC, ACTIONABLE changes that directly address the issues mentioned in the human expert feedback.
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
                return None
            
            plan_data = json.loads(json_text)
            return plan_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Response: {response_text[:500]}...")
            return None
        except Exception as e:
            print(f"Error generating learning plan: {e}")
            return None
    
    def get_learning_plans(self, status: str = None) -> List[Dict[str, Any]]:
        """Get learning plans from database."""
        return self.db.get_learning_plans(status)
    
    def get_human_feedback(self) -> List[Dict[str, Any]]:
        """Get human feedback from database."""
        return self.db.get_human_feedback()
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        return self.db.get_database_stats()
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main function to run the human-driven learning agent."""
    print("🧠 Starting Human-Driven Learning Agent...")
    
    try:
        # Initialize learning agent
        agent = HumanDrivenLearningAgent()
        
        # Generate learning plans from human feedback
        results = agent.generate_learning_plans_from_feedback()
        
        # Print results
        print("\n📋 RESULTS SUMMARY:")
        print(f"Human feedback analyzed: {results['feedback_analyzed']}")
        print(f"Learning plans generated: {results['learning_plans_generated']}")
        
        # Show generated learning plans
        plans = agent.get_learning_plans()
        if plans:
            print(f"\n📝 GENERATED LEARNING PLANS:")
            for i, plan in enumerate(plans, 1):
                print(f"{i}. {plan['title']}")
                print(f"   Type: {plan['plan_type']}")
                print(f"   Priority: {plan['priority']}")
                print(f"   Status: {plan['status']}")
                print(f"   Reasoning: {plan['llm_reasoning'][:100]}...")
                print()
        
        # Show database stats
        stats = agent.get_database_stats()
        print(f"📊 DATABASE STATS: {stats}")
        
        agent.close()
        print("✅ Human-driven learning agent completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running learning agent: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
