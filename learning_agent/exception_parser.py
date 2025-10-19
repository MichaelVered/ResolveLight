"""
Exception Parser for ResolveLight Learning Agent
Parses system logs to extract exceptions for expert review
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class SystemException:
    """Represents a system exception that needs expert review"""
    exception_id: str
    invoice_id: str
    po_number: str
    amount: str
    supplier: str
    exception_type: str
    queue: str
    routing_reason: str
    timestamp: str
    context: Dict
    raw_data: str = ""
    status: str = "OPEN"
    expert_reviewed: bool = False
    expert_feedback: Optional[str] = None

class ExceptionParser:
    """Parses system logs to extract exceptions for expert review"""
    
    def __init__(self, logs_dir: str = "system_logs"):
        self.logs_dir = logs_dir
        
    def parse_all_exceptions(self) -> List[SystemException]:
        """Parse all exception logs and return list of exceptions"""
        exceptions = []
        
        # Parse main exceptions ledger
        exceptions.extend(self._parse_exceptions_ledger())
        
        # Parse queue-specific logs
        queue_files = [
            "queue_missing_data.log",
            "queue_low_confidence_matches.log", 
            "queue_price_discrepancies.log",
            "queue_supplier_mismatch.log",
            "queue_billing_discrepancies.log",
            "queue_date_discrepancies.log",
            "queue_high_value_approval.log",
            "queue_general_exceptions.log"
        ]
        
        for queue_file in queue_files:
            exceptions.extend(self._parse_queue_log(queue_file))
        
        # Deduplicate by exception_id, preferring queue log data over ledger data
        seen_ids = {}
        for exc in exceptions:
            if exc.exception_id not in seen_ids:
                seen_ids[exc.exception_id] = exc
            else:
                # If we already have this exception, prefer the one with more data
                existing = seen_ids[exc.exception_id]
                # Prioritize entries with raw_data, then other detailed fields
                if exc.raw_data or (exc.po_number or exc.amount or exc.supplier):
                    # This exception has more data, use it instead
                    seen_ids[exc.exception_id] = exc
        
        deduplicated = list(seen_ids.values())
            
        return deduplicated
    
    def _parse_exceptions_ledger(self) -> List[SystemException]:
        """Parse the main exceptions ledger"""
        exceptions = []
        ledger_path = os.path.join(self.logs_dir, "exceptions_ledger.log")
        
        if not os.path.exists(ledger_path):
            return exceptions
            
        with open(ledger_path, 'r') as f:
            for line in f:
                if line.strip():
                    exception = self._parse_ledger_line(line.strip())
                    if exception:
                        exceptions.append(exception)
        
        return exceptions
    
    def _parse_ledger_line(self, line: str) -> Optional[SystemException]:
        """Parse a single line from the exceptions ledger"""
        # Pattern: [EXCEPTION] [timestamp] id=ID status=STATUS type=TYPE invoice_id=INVOICE queue=QUEUE
        pattern = r'\[EXCEPTION\] \[([^\]]+)\] id=([^\s]+) status=([^\s]+) type=([^\s]+) invoice_id=([^\s]+) queue=([^\s]+)'
        match = re.match(pattern, line)
        
        if match:
            timestamp, exc_id, status, exc_type, invoice_id, queue = match.groups()
            
            # Try to get raw data from the corresponding queue log file
            raw_data = self._get_raw_data_from_queue_log(exc_id, queue)
            
            return SystemException(
                exception_id=exc_id,
                invoice_id=invoice_id,
                po_number="",  # Will be filled from queue logs
                amount="",     # Will be filled from queue logs
                supplier="",   # Will be filled from queue logs
                exception_type=exc_type,
                queue=queue,
                routing_reason="",  # Will be filled from queue logs
                timestamp=timestamp,
                context={},
                raw_data=raw_data
            )
        return None
    
    def _get_raw_data_from_queue_log(self, exception_id: str, queue: str) -> str:
        """Get raw data from the corresponding queue log file for a given exception ID."""
        queue_file = f"queue_{queue.lower()}.log"
        queue_path = os.path.join(self.logs_dir, queue_file)
        
        if not os.path.exists(queue_path):
            return ""
            
        try:
            with open(queue_path, 'r') as f:
                content = f.read()
                # Check if this exception ID is in this file
                if f"EXCEPTION_ID: {exception_id}" in content:
                    return content.strip()
        except Exception:
            pass
        
        return ""
    
    def _extract_exception_raw_data(self, block: str, exception_id: str) -> str:
        """Extract only the raw data for a specific exception from a block that may contain multiple exceptions."""
        lines = block.strip().split('\n')
        exception_lines = []
        in_exception = False
        
        for line in lines:
            if line.startswith("EXCEPTION_ID:") and exception_id in line:
                in_exception = True
                exception_lines = [line]
            elif in_exception:
                if line.startswith("EXCEPTION_ID:") and exception_id not in line:
                    # This is a different exception, stop collecting
                    break
                elif line.strip():  # Only add non-empty lines
                    exception_lines.append(line)
        
        return '\n'.join(exception_lines) if exception_lines else block.strip()
    
    def _split_exception_blocks(self, content: str) -> List[str]:
        """Split content into individual exception blocks."""
        lines = content.strip().split('\n')
        blocks = []
        current_block = []
        
        for line in lines:
            if line.startswith("QUEUE:") and current_block:
                # Start of a new exception, save the previous one
                blocks.append('\n'.join(current_block))
                current_block = [line]
            else:
                current_block.append(line)
        
        # Add the last block
        if current_block:
            blocks.append('\n'.join(current_block))
        
        return blocks
    
    def _parse_queue_log(self, queue_file: str) -> List[SystemException]:
        """Parse a specific queue log file"""
        exceptions = []
        queue_path = os.path.join(self.logs_dir, queue_file)
        
        if not os.path.exists(queue_path):
            return exceptions
            
        queue_name = queue_file.replace("queue_", "").replace(".log", "").upper()
        
        with open(queue_path, 'r') as f:
            content = f.read()
            
        # Split content by exception blocks (each starts with "QUEUE:")
        if content.strip():
            exception_blocks = self._split_exception_blocks(content)
            for block in exception_blocks:
                exception = self._parse_queue_block(block, queue_name)
                if exception:
                    exceptions.append(exception)
        
        return exceptions
    
    def _parse_queue_block(self, block: str, queue_name: str) -> Optional[SystemException]:
        """Parse a single exception block from a queue log"""
        lines = block.strip().split('\n')
        
        # Extract key information
        exception_id = ""
        invoice_id = ""
        po_number = ""
        amount = ""
        supplier = ""
        routing_reason = ""
        timestamp = ""
        priority = ""
        suggested_actions = []
        manager_approval_required = False
        context = {}
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("EXCEPTION_ID:"):
                exception_id = line.split(":", 1)[1].strip()
            elif line.startswith("INVOICE:"):
                # Parse: INVOICE: INV-AEG-2025-001 (PO: PO-AEG-GA001, Amount: $6,000.00)
                invoice_part = line.split(":", 1)[1].strip()
                invoice_id = invoice_part.split("(")[0].strip()
                
                # Extract PO and amount from parentheses
                if "(" in invoice_part and ")" in invoice_part:
                    paren_content = invoice_part.split("(")[1].split(")")[0]
                    if "PO:" in paren_content:
                        po_number = paren_content.split("PO:")[1].split(",")[0].strip()
                    if "Amount:" in paren_content:
                        amount = paren_content.split("Amount:")[1].strip()
            elif line.startswith("ROUTING_REASON:"):
                routing_reason = line.split(":", 1)[1].strip()
            elif line.startswith("TIMESTAMP:"):
                timestamp = line.split(":", 1)[1].strip()
            elif line.startswith("SUPPLIER:"):
                supplier = line.split(":", 1)[1].strip()
            elif line.startswith("PRIORITY:"):
                priority = line.split(":", 1)[1].strip()
            elif line.startswith("MANAGER_APPROVAL_REQUIRED:"):
                manager_approval_required = line.split(":", 1)[1].strip().upper() == "YES"
            elif line.startswith("CONTEXT:"):
                # Parse context section
                context_lines = []
                in_context = True
                for context_line in lines[lines.index(line)+1:]:
                    if context_line.strip() and not context_line.startswith("  -"):
                        break
                    if context_line.strip():
                        context_lines.append(context_line.strip())
                context = {"details": context_lines}
            elif line.startswith("SUGGESTED_ACTIONS:"):
                # Parse suggested actions
                action_lines = []
                for action_line in lines[lines.index(line)+1:]:
                    if action_line.strip() and action_line.startswith("  -"):
                        action_lines.append(action_line.strip()[2:].strip())
                    elif action_line.strip() and not action_line.startswith("  -"):
                        break
                suggested_actions = action_lines
        
        if exception_id and invoice_id:
            # Extract only the relevant section for this exception
            raw_data = self._extract_exception_raw_data(block, exception_id)
            
            # Enhance context with additional parsed information
            enhanced_context = context.copy()
            enhanced_context.update({
                "priority": priority,
                "suggested_actions": suggested_actions,
                "manager_approval_required": manager_approval_required
            })
            
            return SystemException(
                exception_id=exception_id,
                invoice_id=invoice_id,
                po_number=po_number,
                amount=amount,
                supplier=supplier,
                exception_type="VALIDATION_FAILED",  # Default, could be enhanced
                queue=queue_name,
                routing_reason=routing_reason,
                timestamp=timestamp,
                context=enhanced_context,
                raw_data=raw_data
            )
        
        return None
    
    def get_pending_exceptions(self) -> List[SystemException]:
        """Get all exceptions that haven't been reviewed by experts yet"""
        all_exceptions = self.parse_all_exceptions()
        return [exc for exc in all_exceptions if not exc.expert_reviewed]
    
    def get_exception_by_id(self, exception_id: str) -> Optional[SystemException]:
        """Get a specific exception by ID"""
        all_exceptions = self.parse_all_exceptions()
        for exc in all_exceptions:
            if exc.exception_id == exception_id:
                return exc
        return None

def get_exception_summary() -> Dict:
    """Get a summary of all exceptions for the dashboard"""
    parser = ExceptionParser()
    all_exceptions = parser.parse_all_exceptions()
    pending = parser.get_pending_exceptions()
    
    # Group by queue
    by_queue = {}
    for exc in all_exceptions:
        queue = exc.queue
        if queue not in by_queue:
            by_queue[queue] = {"total": 0, "pending": 0, "reviewed": 0}
        by_queue[queue]["total"] += 1
        if exc.expert_reviewed:
            by_queue[queue]["reviewed"] += 1
        else:
            by_queue[queue]["pending"] += 1
    
    return {
        "total_exceptions": len(all_exceptions),
        "pending_exceptions": len(pending),
        "reviewed_exceptions": len(all_exceptions) - len(pending),
        "by_queue": by_queue
    }
