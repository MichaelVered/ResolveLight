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
        
        return exceptions
    
    
    
    def _split_canonical_exception_blocks(self, content: str) -> List[str]:
        """Split content into individual exception blocks using canonical format delimiters."""
        lines = content.strip().split('\n')
        blocks = []
        current_block = []
        in_exception = False
        
        for line in lines:
            if line.strip() == "=== EXCEPTION_START ===":
                # Start of a new exception
                if current_block and in_exception:
                    # Save the previous block
                    blocks.append('\n'.join(current_block))
                current_block = [line]
                in_exception = True
            elif line.strip() == "=== EXCEPTION_END ===":
                # End of current exception
                if in_exception:
                    current_block.append(line)
                    blocks.append('\n'.join(current_block))
                    current_block = []
                    in_exception = False
            elif in_exception:
                current_block.append(line)
        
        return blocks
    
    def _parse_queue_log(self, queue_file: str) -> List[SystemException]:
        """Parse a specific queue log file using canonical format"""
        exceptions = []
        queue_path = os.path.join(self.logs_dir, queue_file)
        
        if not os.path.exists(queue_path):
            return exceptions
            
        queue_name = queue_file.replace("queue_", "").replace(".log", "").upper()
        
        with open(queue_path, 'r') as f:
            content = f.read()
            
        # Parse canonical format with EXCEPTION_START/END delimiters
        if content.strip():
            exception_blocks = self._split_canonical_exception_blocks(content)
            for block in exception_blocks:
                exception = self._parse_canonical_exception_block(block, queue_name)
                if exception:
                    exceptions.append(exception)
        
        return exceptions
    
    def _parse_canonical_exception_block(self, block: str, queue_name: str) -> Optional[SystemException]:
        """Parse a single canonical exception block from a queue log"""
        lines = block.strip().split('\n')
        
        # Initialize fields
        exception_id = ""
        invoice_id = ""
        po_number = ""
        amount = ""
        supplier = ""
        routing_reason = ""
        timestamp = ""
        priority = ""
        exception_type = ""
        status = "OPEN"
        confidence_score = None
        manager_approval_required = False
        context = {}
        suggested_actions = []
        metadata = {}
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Skip delimiters
            if line in ["=== EXCEPTION_START ===", "=== EXCEPTION_END ==="]:
                continue
                
            # Parse header fields
            if ":" in line and not line.startswith("CONTEXT:") and not line.startswith("SUGGESTED_ACTIONS:") and not line.startswith("METADATA:"):
                field_name, field_value = line.split(":", 1)
                field_name = field_name.strip()
                field_value = field_value.strip()
                
                if field_name == "EXCEPTION_ID":
                    exception_id = field_value
                elif field_name == "INVOICE_ID":
                    invoice_id = field_value
                elif field_name == "PO_NUMBER":
                    po_number = field_value
                elif field_name == "AMOUNT":
                    amount = field_value
                elif field_name == "SUPPLIER":
                    supplier = field_value
                elif field_name == "ROUTING_REASON":
                    routing_reason = field_value
                elif field_name == "TIMESTAMP":
                    timestamp = field_value
                elif field_name == "PRIORITY":
                    priority = field_value
                elif field_name == "EXCEPTION_TYPE":
                    exception_type = field_value
                elif field_name == "STATUS":
                    status = field_value
                elif field_name == "CONFIDENCE_SCORE" and field_value != "N/A":
                    try:
                        confidence_score = float(field_value)
                    except ValueError:
                        confidence_score = None
                elif field_name == "MANAGER_APPROVAL_REQUIRED":
                    manager_approval_required = field_value.upper() == "YES"
            
            # Handle sections
            elif line == "CONTEXT:":
                current_section = "context"
                context = {"details": []}
            elif line == "SUGGESTED_ACTIONS:":
                current_section = "suggested_actions"
                suggested_actions = []
            elif line == "METADATA:":
                current_section = "metadata"
                metadata = {}
            elif current_section == "context" and line:
                context["details"].append(line)
            elif current_section == "suggested_actions" and line:
                if line.startswith("- "):
                    suggested_actions.append(line[2:].strip())
                else:
                    suggested_actions.append(line)
            elif current_section == "metadata" and line and ":" in line:
                meta_key, meta_value = line.split(":", 1)
                metadata[meta_key.strip()] = meta_value.strip()
        
        if exception_id and invoice_id:
            # Enhance context with additional parsed information
            enhanced_context = context.copy()
            enhanced_context.update({
                "priority": priority,
                "suggested_actions": suggested_actions,
                "manager_approval_required": manager_approval_required,
                "confidence_score": confidence_score,
                "metadata": metadata
            })
            
            return SystemException(
                exception_id=exception_id,
                invoice_id=invoice_id,
                po_number=po_number,
                amount=amount,
                supplier=supplier,
                exception_type=exception_type or "VALIDATION_FAILED",
                queue=queue_name,
                routing_reason=routing_reason,
                timestamp=timestamp,
                context=enhanced_context,
                raw_data=block,
                status=status
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
