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
    Analyzes feedback quality and provides insights for system improvement.
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
    
    def analyze_feedback_quality(self) -> Dict[str, Any]:
        """
        Analyze human feedback quality and provide summary.
        This function analyzes expert feedback for quality assessment.
        """
        print("🔍 Analyzing human feedback quality...")
        
        # Get all human feedback
        feedback_items = self.db.get_human_feedback()
        
        if not feedback_items:
            print("ℹ️  No human feedback found. Please add feedback through the web GUI.")
            return {
                'feedback_analyzed': 0,
                'message': 'No human feedback available for analysis'
            }
        
        print(f"📝 Found {len(feedback_items)} feedback items to analyze")
        
        # Group feedback by type and patterns
        grouped_feedback = self._group_feedback_by_patterns(feedback_items)
        
        # Analyze feedback quality
        quality_analysis = self._analyze_feedback_quality(grouped_feedback)
        
        print(f"✅ Analyzed {len(feedback_items)} feedback items")
        
        return {
            'feedback_analyzed': len(feedback_items),
            'quality_analysis': quality_analysis,
            'grouped_feedback': grouped_feedback
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
    
    def _analyze_feedback_quality(self, grouped_feedback: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze the quality of feedback groups."""
        analysis = {
            'total_groups': len(grouped_feedback),
            'group_breakdown': {},
            'quality_issues': [],
            'recommendations': []
        }
        
        for pattern_type, feedback_group in grouped_feedback.items():
            group_analysis = {
                'count': len(feedback_group),
                'quality_score': 0.0,
                'completeness': 'unknown'
            }
            
            # Simple quality assessment
            if len(feedback_group) > 0:
                # Check for conversation completeness
                completed_conversations = sum(1 for f in feedback_group if f.get('conversation_status') == 'completed')
                group_analysis['completeness'] = 'high' if completed_conversations > 0 else 'low'
                group_analysis['quality_score'] = min(1.0, completed_conversations / len(feedback_group))
            
            analysis['group_breakdown'][pattern_type] = group_analysis
        
        return analysis
    
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
        
        # Analyze human feedback quality
        results = agent.analyze_feedback_quality()
        
        # Print results
        print("\n📋 ANALYSIS SUMMARY:")
        print(f"Human feedback analyzed: {results['feedback_analyzed']}")
        
        # Show quality analysis
        if 'quality_analysis' in results:
            analysis = results['quality_analysis']
            print(f"Feedback groups found: {analysis['total_groups']}")
            
            for group_type, group_data in analysis['group_breakdown'].items():
                print(f"  - {group_type}: {group_data['count']} items (quality: {group_data['quality_score']:.2f})")
        
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
