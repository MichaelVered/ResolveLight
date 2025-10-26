"""
Log analyzer for the learning agent system.
Processes all system logs to extract learning opportunities and patterns.
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from pathlib import Path
from collections import defaultdict, Counter


class LogAnalyzer:
    """Analyzes system logs to identify learning opportunities."""
    
    def __init__(self, repo_root: str = None):
        """Initialize with repository root path."""
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.system_logs_dir = os.path.join(self.repo_root, "system_logs")
        self.json_files_dir = os.path.join(self.repo_root, "json_files")
        self.memory_dir = os.path.join(self.repo_root, "memory")
    
    def analyze_all_logs(self) -> List[Dict[str, Any]]:
        """Analyze all system logs and return learning opportunities."""
        learning_opportunities = []
        
        # Analyze different types of logs
        learning_opportunities.extend(self._analyze_exception_ledger())
        learning_opportunities.extend(self._analyze_queue_logs())
        learning_opportunities.extend(self._analyze_processed_invoices())
        learning_opportunities.extend(self._analyze_payments_log())
        learning_opportunities.extend(self._analyze_memory_sessions())
        
        return learning_opportunities
    
    def _analyze_exception_ledger(self) -> List[Dict[str, Any]]:
        """Analyze exceptions_ledger.log for patterns."""
        opportunities = []
        exceptions_file = os.path.join(self.system_logs_dir, "exceptions_ledger.log")
        
        if not os.path.exists(exceptions_file):
            return opportunities
        
        try:
            with open(exceptions_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Group exceptions by type and queue
            exception_patterns = defaultdict(list)
            queue_patterns = defaultdict(list)
            
            for line in lines:
                if "EXCEPTION" in line:
                    # Parse exception line: [EXCEPTION] [timestamp] id=... status=... type=... invoice_id=... queue=...
                    match = re.search(r'id=(\w+)\s+status=(\w+)\s+type=(\w+)\s+invoice_id=([^\s]+)\s+queue=([^\s]+)', line)
                    if match:
                        exc_id, status, exc_type, invoice_id, queue = match.groups()
                        exception_patterns[exc_type].append({
                            'id': exc_id,
                            'status': status,
                            'invoice_id': invoice_id,
                            'queue': queue,
                            'line': line.strip()
                        })
                        queue_patterns[queue].append(exc_type)
            
            # Identify patterns
            for exc_type, exceptions in exception_patterns.items():
                if len(exceptions) >= 3:  # Threshold for pattern detection
                    opportunities.append({
                        'source_type': 'exception_pattern',
                        'source_file': 'exceptions_ledger.log',
                        'learning_opportunity': f"Recurring exception type '{exc_type}' found {len(exceptions)} times",
                        'confidence_score': min(0.9, len(exceptions) / 10.0),
                        'analysis_notes': f"Exception type: {exc_type}, Count: {len(exceptions)}, Statuses: {Counter([e['status'] for e in exceptions])}",
                        'source_data': {
                            'exception_type': exc_type,
                            'count': len(exceptions),
                            'examples': exceptions[:5],  # First 5 examples
                            'status_distribution': dict(Counter([e['status'] for e in exceptions]))
                        }
                    })
            
            # Analyze queue patterns
            for queue, exc_types in queue_patterns.items():
                if len(exc_types) >= 5:  # Threshold for queue analysis
                    type_counts = Counter(exc_types)
                    most_common = type_counts.most_common(1)[0]
                    
                    opportunities.append({
                        'source_type': 'queue_pattern',
                        'source_file': 'exceptions_ledger.log',
                        'learning_opportunity': f"Queue '{queue}' has high exception volume with dominant type '{most_common[0]}'",
                        'confidence_score': min(0.8, most_common[1] / 10.0),
                        'analysis_notes': f"Queue: {queue}, Total exceptions: {len(exc_types)}, Most common: {most_common[0]} ({most_common[1]} times)",
                        'source_data': {
                            'queue': queue,
                            'total_exceptions': len(exc_types),
                            'type_distribution': dict(type_counts),
                            'most_common_type': most_common[0]
                        }
                    })
        
        except Exception as e:
            print(f"Error analyzing exceptions_ledger.log: {e}")
        
        return opportunities
    
    def _analyze_queue_logs(self) -> List[Dict[str, Any]]:
        """Analyze individual queue log files."""
        opportunities = []
        
        queue_files = [
            "queue_billing_discrepancies.log",
            "queue_date_discrepancies.log", 
            "queue_general_exceptions.log",
            "queue_high_value_approval.log",
            "queue_low_confidence_matches.log",
            "queue_missing_data.log",
            "queue_price_discrepancies.log"
        ]
        
        for queue_file in queue_files:
            queue_path = os.path.join(self.system_logs_dir, queue_file)
            if os.path.exists(queue_path):
                opportunities.extend(self._analyze_single_queue(queue_path, queue_file))
        
        return opportunities
    
    def _analyze_single_queue(self, queue_path: str, queue_name: str) -> List[Dict[str, Any]]:
        """Analyze a single queue log file."""
        opportunities = []
        
        try:
            with open(queue_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count total entries
            lines = content.strip().split('\n')
            if not lines or lines == ['']:
                return opportunities
            
            # Extract invoice IDs and patterns
            invoice_ids = []
            routing_reasons = []
            confidence_scores = []
            
            for line in lines:
                if "INVOICE:" in line:
                    # Extract invoice ID
                    match = re.search(r'INVOICE:\s*([^\s]+)', line)
                    if match:
                        invoice_ids.append(match.group(1))
                
                if "ROUTING_REASON:" in line:
                    # Extract routing reason
                    match = re.search(r'ROUTING_REASON:\s*(.+)', line)
                    if match:
                        routing_reasons.append(match.group(1).strip())
                
                if "confidence:" in line.lower():
                    # Extract confidence scores
                    match = re.search(r'confidence:\s*([0-9.]+)', line.lower())
                    if match:
                        confidence_scores.append(float(match.group(1)))
            
            # Analyze patterns
            if len(invoice_ids) >= 3:  # Threshold for analysis
                # Check for high volume
                if len(invoice_ids) >= 10:
                    opportunities.append({
                        'source_type': 'queue_volume',
                        'source_file': queue_name,
                        'learning_opportunity': f"High volume in {queue_name} queue ({len(invoice_ids)} invoices)",
                        'confidence_score': min(0.8, len(invoice_ids) / 20.0),
                        'analysis_notes': f"Queue: {queue_name}, Invoice count: {len(invoice_ids)}",
                        'source_data': {
                            'queue_name': queue_name,
                            'invoice_count': len(invoice_ids),
                            'sample_invoice_ids': invoice_ids[:5]
                        }
                    })
                
                # Analyze routing reasons
                if routing_reasons:
                    reason_counts = Counter(routing_reasons)
                    most_common_reason = reason_counts.most_common(1)[0]
                    
                    if most_common_reason[1] >= 3:  # Threshold for pattern
                        opportunities.append({
                            'source_type': 'routing_pattern',
                            'source_file': queue_name,
                            'learning_opportunity': f"Common routing reason in {queue_name}: '{most_common_reason[0]}'",
                            'confidence_score': min(0.7, most_common_reason[1] / 5.0),
                            'analysis_notes': f"Most common reason: {most_common_reason[0]} ({most_common_reason[1]} times)",
                            'source_data': {
                                'queue_name': queue_name,
                                'routing_reasons': dict(reason_counts),
                                'most_common_reason': most_common_reason[0]
                            }
                        })
                
                # Analyze confidence scores for low_confidence_matches
                if "low_confidence" in queue_name and confidence_scores:
                    # Filter out None values from confidence scores
                    valid_scores = [score for score in confidence_scores if score is not None]
                    if valid_scores:
                        avg_confidence = sum(valid_scores) / len(valid_scores)
                        low_confidence_count = sum(1 for score in valid_scores if score < 0.7)
                        
                        if avg_confidence < 0.6 or low_confidence_count >= 3:
                            opportunities.append({
                                'source_type': 'confidence_analysis',
                                'source_file': queue_name,
                                'learning_opportunity': f"Low confidence matching in {queue_name} (avg: {avg_confidence:.2f})",
                                'confidence_score': 0.8,
                                'analysis_notes': f"Average confidence: {avg_confidence:.2f}, Low confidence items: {low_confidence_count}",
                                'source_data': {
                                    'queue_name': queue_name,
                                    'average_confidence': avg_confidence,
                                    'low_confidence_count': low_confidence_count,
                                    'confidence_scores': confidence_scores
                                }
                            })
        
        except Exception as e:
            print(f"Error analyzing queue {queue_name}: {e}")
        
        return opportunities
    
    def _analyze_processed_invoices(self) -> List[Dict[str, Any]]:
        """Analyze processed_invoices.log for patterns."""
        opportunities = []
        processed_file = os.path.join(self.system_logs_dir, "processed_invoices.log")
        
        if not os.path.exists(processed_file):
            return opportunities
        
        try:
            with open(processed_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Parse processed invoices
            invoices = []
            for line in lines:
                if line.startswith("PROCESSED:"):
                    try:
                        json_data = line[10:].strip()  # Remove "PROCESSED: " prefix
                        invoice_data = json.loads(json_data)
                        invoices.append(invoice_data)
                    except json.JSONDecodeError:
                        continue
            
            if not invoices:
                return opportunities
            
            # Analyze processing results
            result_counts = Counter([inv.get('processing_result', 'unknown') for inv in invoices])
            queue_counts = Counter([inv.get('routing_queue', 'none') for inv in invoices])
            priority_counts = Counter([inv.get('priority', 'unknown') for inv in invoices])
            
            # Check for high rejection rates
            total_invoices = len(invoices)
            rejected_count = result_counts.get('REJECTED', 0)
            rejection_rate = rejected_count / total_invoices if total_invoices > 0 else 0
            
            if rejection_rate > 0.5:  # More than 50% rejection rate
                opportunities.append({
                    'source_type': 'rejection_rate',
                    'source_file': 'processed_invoices.log',
                    'learning_opportunity': f"High rejection rate: {rejection_rate:.1%} of invoices rejected",
                    'confidence_score': min(0.9, rejection_rate),
                    'analysis_notes': f"Total invoices: {total_invoices}, Rejected: {rejected_count}, Rate: {rejection_rate:.1%}",
                    'source_data': {
                        'total_invoices': total_invoices,
                        'rejected_count': rejected_count,
                        'rejection_rate': rejection_rate,
                        'result_distribution': dict(result_counts)
                    }
                })
            
            # Analyze queue distribution
            if len(queue_counts) > 1:  # Multiple queues used
                most_common_queue = queue_counts.most_common(1)[0]
                if most_common_queue[1] / total_invoices > 0.3:  # More than 30% in one queue
                    opportunities.append({
                        'source_type': 'queue_concentration',
                        'source_file': 'processed_invoices.log',
                        'learning_opportunity': f"High concentration in '{most_common_queue[0]}' queue ({most_common_queue[1]}/{total_invoices})",
                        'confidence_score': 0.6,
                        'analysis_notes': f"Queue distribution: {dict(queue_counts)}",
                        'source_data': {
                            'queue_distribution': dict(queue_counts),
                            'most_common_queue': most_common_queue[0],
                            'concentration_ratio': most_common_queue[1] / total_invoices
                        }
                    })
            
            # Analyze high-value invoices
            high_value_invoices = [inv for inv in invoices if (inv.get('billing_amount') or 0) > 10000]
            if len(high_value_invoices) >= 3:
                high_value_rejection_rate = sum(1 for inv in high_value_invoices if inv.get('processing_result') == 'REJECTED') / len(high_value_invoices)
                
                if high_value_rejection_rate > 0.3:  # More than 30% of high-value invoices rejected
                    opportunities.append({
                        'source_type': 'high_value_rejection',
                        'source_file': 'processed_invoices.log',
                        'learning_opportunity': f"High rejection rate for high-value invoices: {high_value_rejection_rate:.1%}",
                        'confidence_score': 0.7,
                        'analysis_notes': f"High-value invoices: {len(high_value_invoices)}, Rejected: {int(high_value_rejection_rate * len(high_value_invoices))}",
                        'source_data': {
                            'high_value_count': len(high_value_invoices),
                            'high_value_rejection_rate': high_value_rejection_rate,
                            'high_value_invoices': high_value_invoices[:5]  # Sample
                        }
                    })
        
        except Exception as e:
            print(f"Error analyzing processed_invoices.log: {e}")
        
        return opportunities
    
    def _analyze_payments_log(self) -> List[Dict[str, Any]]:
        """Analyze payments.log for patterns."""
        opportunities = []
        payments_file = os.path.join(self.system_logs_dir, "payments.log")
        
        if not os.path.exists(payments_file):
            return opportunities
        
        try:
            with open(payments_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Count payment entries
            payment_lines = [line for line in lines if "payment_item:" in line]
            
            if len(payment_lines) >= 5:  # Threshold for analysis
                # Analyze payment patterns
                opportunities.append({
                    'source_type': 'payment_analysis',
                    'source_file': 'payments.log',
                    'learning_opportunity': f"Payment processing active with {len(payment_lines)} payment items",
                    'confidence_score': 0.5,
                    'analysis_notes': f"Payment items processed: {len(payment_lines)}",
                    'source_data': {
                        'payment_item_count': len(payment_lines),
                        'sample_payments': payment_lines[:3]
                    }
                })
        
        except Exception as e:
            print(f"Error analyzing payments.log: {e}")
        
        return opportunities
    
    def _analyze_memory_sessions(self) -> List[Dict[str, Any]]:
        """Analyze memory session files for patterns."""
        opportunities = []
        
        if not os.path.exists(self.memory_dir):
            return opportunities
        
        try:
            session_files = [f for f in os.listdir(self.memory_dir) if f.endswith('.jsonl')]
            
            if len(session_files) >= 3:  # Threshold for analysis
                # Analyze session patterns
                total_sessions = len(session_files)
                opportunities.append({
                    'source_type': 'session_analysis',
                    'source_file': 'memory/',
                    'learning_opportunity': f"Multiple processing sessions detected ({total_sessions} sessions)",
                    'confidence_score': 0.3,
                    'analysis_notes': f"Session files found: {total_sessions}",
                    'source_data': {
                        'session_count': total_sessions,
                        'session_files': session_files[:5]  # Sample
                    }
                })
        
        except Exception as e:
            print(f"Error analyzing memory sessions: {e}")
        
        return opportunities
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get an overview of the system state based on logs."""
        overview = {
            'total_learning_opportunities': 0,
            'log_files_analyzed': 0,
            'exception_patterns': 0,
            'queue_issues': 0,
            'rejection_rate': 0.0,
            'high_value_issues': 0
        }
        
        opportunities = self.analyze_all_logs()
        overview['total_learning_opportunities'] = len(opportunities)
        
        # Count by type
        for opp in opportunities:
            if opp['source_type'] == 'exception_pattern':
                overview['exception_patterns'] += 1
            elif opp['source_type'] in ['queue_volume', 'routing_pattern', 'confidence_analysis']:
                overview['queue_issues'] += 1
            elif opp['source_type'] == 'rejection_rate':
                overview['rejection_rate'] = opp['source_data'].get('rejection_rate', 0.0)
            elif opp['source_type'] == 'high_value_rejection':
                overview['high_value_issues'] += 1
        
        # Count log files
        log_files = [
            'exceptions_ledger.log',
            'processed_invoices.log',
            'payments.log'
        ]
        queue_files = [f for f in os.listdir(self.system_logs_dir) if f.startswith('queue_')]
        log_files.extend(queue_files)
        
        overview['log_files_analyzed'] = len([f for f in log_files if os.path.exists(os.path.join(self.system_logs_dir, f))])
        
        return overview


def analyze_system_logs(repo_root: str = None) -> List[Dict[str, Any]]:
    """Convenience function to analyze all system logs."""
    analyzer = LogAnalyzer(repo_root)
    return analyzer.analyze_all_logs()


if __name__ == "__main__":
    # Test log analysis
    analyzer = LogAnalyzer()
    opportunities = analyzer.analyze_all_logs()
    
    print(f"Found {len(opportunities)} learning opportunities:")
    for i, opp in enumerate(opportunities, 1):
        print(f"{i}. {opp['learning_opportunity']} (confidence: {opp['confidence_score']:.2f})")
    
    overview = analyzer.get_system_overview()
    print(f"\nSystem Overview: {overview}")
