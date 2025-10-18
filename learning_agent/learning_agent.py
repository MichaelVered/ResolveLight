"""
Main learning agent that analyzes system logs and generates learning plans.
Uses LLM to intelligently determine optimization strategies.
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.genai import types

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from learning_agent.database import LearningDatabase
from learning_agent.log_analyzer import LogAnalyzer


class LearningAgent:
    """Main learning agent that generates intelligent optimization plans."""
    
    def __init__(self, repo_root: str = None, api_key: str = None):
        """Initialize the learning agent."""
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.db = LearningDatabase(os.path.join(self.repo_root, "learning_data", "learning.db"))
        self.log_analyzer = LogAnalyzer(self.repo_root)
        
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
    
    def run_learning_analysis(self) -> Dict[str, Any]:
        """Run complete learning analysis and generate plans."""
        print("🔍 Starting learning analysis...")
        
        # Step 1: Analyze system logs
        print("📊 Analyzing system logs...")
        learning_opportunities = self.log_analyzer.analyze_all_logs()
        print(f"Found {len(learning_opportunities)} learning opportunities")
        
        # Step 2: Store learning records in database
        print("💾 Storing learning records...")
        learning_record_ids = []
        for opp in learning_opportunities:
            record_id = self.db.store_learning_record(
                source_type=opp['source_type'],
                source_file=opp['source_file'],
                source_data=opp['source_data'],
                learning_opportunity=opp['learning_opportunity'],
                confidence_score=opp['confidence_score'],
                analysis_notes=opp['analysis_notes']
            )
            learning_record_ids.append(record_id)
        
        # Step 3: Generate learning plans using LLM
        print("🧠 Generating learning plans with LLM...")
        learning_plans = self._generate_learning_plans(learning_opportunities)
        
        # Step 4: Store learning plans
        print("💾 Storing learning plans...")
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
        
        # Step 5: Generate summary
        summary = {
            'learning_opportunities_found': len(learning_opportunities),
            'learning_plans_generated': len(learning_plans),
            'learning_record_ids': learning_record_ids,
            'learning_plan_ids': plan_ids,
            'system_overview': self.log_analyzer.get_system_overview()
        }
        
        print("✅ Learning analysis complete!")
        print(f"Generated {len(learning_plans)} learning plans")
        
        return summary
    
    def _generate_learning_plans(self, learning_opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate learning plans using LLM analysis."""
        if not learning_opportunities:
            return []
        
        # Group opportunities by type for better analysis
        grouped_opportunities = self._group_learning_opportunities(learning_opportunities)
        
        learning_plans = []
        
        for group_type, opportunities in grouped_opportunities.items():
            if len(opportunities) == 0:
                continue
                
            # Create context for LLM
            context = self._create_llm_context(opportunities)
            
            # Generate learning plan for this group
            plan = self._generate_single_learning_plan(group_type, opportunities, context)
            if plan:
                learning_plans.append(plan)
        
        return learning_plans
    
    def _group_learning_opportunities(self, opportunities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group learning opportunities by type for better analysis."""
        groups = {
            'exception_patterns': [],
            'queue_issues': [],
            'rejection_issues': [],
            'confidence_issues': [],
            'high_value_issues': [],
            'other': []
        }
        
        for opp in opportunities:
            source_type = opp['source_type']
            if source_type == 'exception_pattern':
                groups['exception_patterns'].append(opp)
            elif source_type in ['queue_volume', 'routing_pattern', 'queue_concentration']:
                groups['queue_issues'].append(opp)
            elif source_type == 'rejection_rate':
                groups['rejection_issues'].append(opp)
            elif source_type == 'confidence_analysis':
                groups['confidence_issues'].append(opp)
            elif source_type == 'high_value_rejection':
                groups['high_value_issues'].append(opp)
            else:
                groups['other'].append(opp)
        
        return groups
    
    def _create_llm_context(self, opportunities: List[Dict[str, Any]]) -> str:
        """Create context string for LLM analysis."""
        context_parts = []
        
        # Add system overview
        context_parts.append("SYSTEM OVERVIEW:")
        context_parts.append(f"- Repository: {self.repo_root}")
        context_parts.append(f"- Learning opportunities found: {len(opportunities)}")
        
        # Add source code context (read-only access)
        context_parts.append("\nSOURCE CODE CONTEXT:")
        context_parts.append(self._get_source_code_context())
        
        # Add learning opportunities
        context_parts.append("\nLEARNING OPPORTUNITIES:")
        for i, opp in enumerate(opportunities, 1):
            context_parts.append(f"{i}. {opp['learning_opportunity']}")
            context_parts.append(f"   Source: {opp['source_file']}")
            context_parts.append(f"   Confidence: {opp['confidence_score']:.2f}")
            context_parts.append(f"   Analysis: {opp['analysis_notes']}")
            context_parts.append("")
        
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
    
    def _generate_single_learning_plan(self, group_type: str, opportunities: List[Dict[str, Any]], context: str) -> Optional[Dict[str, Any]]:
        """Generate a single learning plan for a group of opportunities."""
        
        prompt = f"""
You are an expert system optimization analyst. Based on the learning opportunities and source code context below, generate a specific, actionable learning plan.

CONTEXT:
{context}

GROUP TYPE: {group_type}
NUMBER OF OPPORTUNITIES: {len(opportunities)}

REQUIREMENTS:
1. Analyze the learning opportunities and identify the ROOT CAUSE
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

3. Provide SPECIFIC, CODE-LEVEL changes:
   - If prompt optimization: Show the EXACT new prompt
   - If tool enhancement: Show the EXACT code changes
   - If new validation rule: Show the EXACT implementation
   - If threshold adjustment: Show the EXACT new values

4. Include impact analysis and implementation complexity

RESPONSE FORMAT (JSON):
{{
    "plan_type": "chosen_optimization_strategy",
    "title": "Clear, descriptive title",
    "description": "Detailed description of the problem and solution",
    "suggested_changes": {{
        "file_path": "path/to/file",
        "change_type": "replace|add|modify",
        "old_code": "existing code to change",
        "new_code": "new code implementation",
        "additional_files": ["list", "of", "files", "to", "modify"]
    }},
    "impact_analysis": {{
        "affected_invoices": "estimated number",
        "improvement_expected": "description of expected improvement",
        "risk_level": "low|medium|high",
        "implementation_effort": "low|medium|high"
    }},
    "priority": "low|medium|high|critical",
    "llm_reasoning": "Detailed explanation of why this approach was chosen and how it addresses the root cause"
}}

Focus on SPECIFIC, ACTIONABLE changes that directly address the identified issues.
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
            
            # Add source learning record IDs
            plan_data['source_learning_records'] = [opp.get('id', i) for i, opp in enumerate(opportunities)]
            
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
    
    def get_learning_records(self, status: str = None) -> List[Dict[str, Any]]:
        """Get learning records from database."""
        return self.db.get_learning_records(status)
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        return self.db.get_database_stats()
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main function to run the learning agent."""
    print("🚀 Starting Learning Agent...")
    
    try:
        # Initialize learning agent
        agent = LearningAgent()
        
        # Run learning analysis
        results = agent.run_learning_analysis()
        
        # Print results
        print("\n📋 RESULTS SUMMARY:")
        print(f"Learning opportunities found: {results['learning_opportunities_found']}")
        print(f"Learning plans generated: {results['learning_plans_generated']}")
        
        # Show learning plans
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
        print("✅ Learning agent completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running learning agent: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
