"""
Flexible Exception Parser for ResolveLight
Handles varying exception log schemas and unstructured data dynamically.
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class FlexibleException:
    """Flexible exception data structure that can handle any schema."""
    exception_id: str
    invoice_id: str
    queue: str
    timestamp: str
    raw_data: Dict[str, Any]  # Store all parsed data
    structured_fields: Dict[str, Any]  # Key-value pairs
    unstructured_text: List[str]  # Free-form text lines
    context: Dict[str, Any]  # Additional context
    priority: Optional[str] = None
    status: str = "OPEN"
    expert_reviewed: bool = False
    expert_feedback: Optional[str] = None
    expert_name: Optional[str] = None
    human_correction: Optional[str] = None
    reviewed_at: Optional[str] = None


class FlexibleExceptionParser:
    """Flexible parser that adapts to different exception log schemas."""
    
    def __init__(self, logs_dir: str = "system_logs"):
        self.logs_dir = logs_dir
        
        # Common field patterns for different log formats
        self.field_patterns = {
            'exception_id': [
                r'EXCEPTION_ID:\s*(.+)',
                r'ID:\s*(.+)',
                r'Exception ID:\s*(.+)',
                r'ExceptionId:\s*(.+)',
                r'id=([^\s]+)',
                r'"exception_id":\s*"([^"]+)"',
                r"'exception_id':\s*'([^']+)'"
            ],
            'invoice_id': [
                r'INVOICE:\s*([^(]+)',
                r'Invoice:\s*(.+)',
                r'Invoice ID:\s*(.+)',
                r'InvoiceId:\s*(.+)',
                r'invoice_id=([^\s]+)',
                r'"invoice_id":\s*"([^"]+)"',
                r"'invoice_id':\s*'([^']+)'"
            ],
            'po_number': [
                r'PO:\s*([^,)]+)',
                r'PO Number:\s*(.+)',
                r'Purchase Order:\s*(.+)',
                r'po_number=([^\s,)]+)',
                r'"purchase_order_number":\s*"([^"]+)"',
                r"'purchase_order_number':\s*'([^']+)'"
            ],
            'amount': [
                r'Amount:\s*([^,)]+)',
                r'Total:\s*(.+)',
                r'Value:\s*(.+)',
                r'amount=([^\s,)]+)',
                r'"amount":\s*"([^"]+)"',
                r"'amount':\s*'([^']+)'"
            ],
            'supplier': [
                r'SUPPLIER:\s*(.+)',
                r'Vendor:\s*(.+)',
                r'Company:\s*(.+)',
                r'supplier=([^\s,)]+)',
                r'"supplier":\s*"([^"]+)"',
                r"'supplier':\s*'([^']+)'"
            ],
            'priority': [
                r'PRIORITY:\s*(.+)',
                r'Level:\s*(.+)',
                r'Urgency:\s*(.+)',
                r'priority=([^\s,)]+)',
                r'"priority":\s*"([^"]+)"',
                r"'priority':\s*'([^']+)'"
            ],
            'reason': [
                r'REASON:\s*(.+)',
                r'Description:\s*(.+)',
                r'Issue:\s*(.+)',
                r'routing_reason=([^\s,)]+)',
                r'"routing_reason":\s*"([^"]+)"',
                r"'routing_reason':\s*'([^']+)'"
            ],
            'timestamp': [
                r'TIMESTAMP:\s*(.+)',
                r'Time:\s*(.+)',
                r'Date:\s*(.+)',
                r'timestamp=([^\s,)]+)',
                r'"timestamp":\s*"([^"]+)"',
                r"'timestamp':\s*'([^']+)'"
            ]
        }
        
        # Section patterns for structured data
        self.section_patterns = {
            'context': [r'CONTEXT:', r'Details:', r'Additional Info:'],
            'suggested_actions': [r'SUGGESTED_ACTIONS:', r'Actions:', r'Recommendations:'],
            'manager_approval': [r'MANAGER_APPROVAL_REQUIRED:', r'Approval Required:', r'Manager Review:'],
            'line_items': [r'LINE_ITEMS:', r'Items:', r'Products:'],
            'validation_errors': [r'VALIDATION_ERRORS:', r'Errors:', r'Issues:']
        }

    def parse_all_exceptions(self) -> List[FlexibleException]:
        """Parse all exception logs with flexible schema detection."""
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
        
        # Deduplicate by exception_id, preferring more complete data
        return self._deduplicate_exceptions(exceptions)

    def _parse_exceptions_ledger(self) -> List[FlexibleException]:
        """Parse the main exceptions ledger with flexible format detection."""
        exceptions = []
        ledger_path = os.path.join(self.logs_dir, "exceptions_ledger.log")
        
        if not os.path.exists(ledger_path):
            return exceptions
            
        with open(ledger_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    exception = self._parse_ledger_line(line.strip(), line_num)
                    if exception:
                        exceptions.append(exception)
        
        return exceptions

    def _parse_ledger_line(self, line: str, line_num: int) -> Optional[FlexibleException]:
        """Parse a single line from the exceptions ledger with flexible format detection."""
        # Try different ledger formats
        patterns = [
            # Format: [EXCEPTION] [timestamp] id=ID status=STATUS type=TYPE invoice_id=INVOICE queue=QUEUE
            r'\[EXCEPTION\]\s*\[([^\]]+)\]\s*id=([^\s]+)\s*status=([^\s]+)\s*type=([^\s]+)\s*invoice_id=([^\s]+)\s*queue=([^\s]+)',
            # Format: EXCEPTION_ID:ID INVOICE_ID:INVOICE STATUS:STATUS TYPE:TYPE QUEUE:QUEUE TIMESTAMP:TIME
            r'EXCEPTION_ID:([^\s]+)\s+INVOICE_ID:([^\s]+)\s+STATUS:([^\s]+)\s+TYPE:([^\s]+)\s+QUEUE:([^\s]+)\s+TIMESTAMP:([^\s]+)',
            # JSON format
            r'\{.*"exception_id".*\}',
            # CSV format
            r'[^,]+,[^,]+,[^,]+,[^,]+,[^,]+'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) >= 6:  # Standard format
                    timestamp, exc_id, status, exc_type, invoice_id, queue = groups[:6]
                elif len(groups) == 6:  # Alternative format
                    exc_id, invoice_id, status, exc_type, queue, timestamp = groups
                else:
                    continue
                
                return FlexibleException(
                    exception_id=exc_id,
                    invoice_id=invoice_id,
                    queue=queue,
                    timestamp=timestamp,
                    raw_data={'line': line, 'line_number': line_num},
                    structured_fields={
                        'status': status,
                        'type': exc_type,
                        'timestamp': timestamp
                    },
                    unstructured_text=[line],
                    context={'source': 'ledger', 'line_number': line_num}
                )
        
        # Try JSON parsing
        try:
            data = json.loads(line)
            if 'exception_id' in data and 'invoice_id' in data:
                return self._create_exception_from_dict(data, 'ledger')
        except:
            pass
        
        return None

    def _parse_queue_log(self, queue_file: str) -> List[FlexibleException]:
        """Parse a specific queue log file with flexible format detection."""
        exceptions = []
        queue_path = os.path.join(self.logs_dir, queue_file)
        
        if not os.path.exists(queue_path):
            return exceptions
            
        queue_name = queue_file.replace("queue_", "").replace(".log", "").upper()
        
        with open(queue_path, 'r') as f:
            content = f.read()
            
        if content.strip():
            exception = self._parse_flexible_content(content, queue_name)
            if exception:
                exceptions.append(exception)
        
        return exceptions

    def _parse_flexible_content(self, content: str, queue_name: str) -> Optional[FlexibleException]:
        """Parse content with flexible schema detection."""
        lines = content.strip().split('\n')
        
        # Initialize structured data
        structured_fields = {}
        unstructured_text = []
        context = {}
        sections = {}
        
        # Extract key fields using flexible patterns
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            unstructured_text.append(line)
            
            # Try to extract structured fields
            for field_name, patterns in self.field_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        structured_fields[field_name] = value
                        break
            
            # Check for section headers
            for section_name, section_patterns in self.section_patterns.items():
                for pattern in section_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        sections[section_name] = []
                        break
        
        # Parse sections
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new section
            section_found = False
            for section_name, section_patterns in self.section_patterns.items():
                for pattern in section_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        current_section = section_name
                        sections[current_section] = []
                        section_found = True
                        break
                if section_found:
                    break
            
            # Add line to current section
            if current_section and not section_found:
                if line.startswith('-') or line.startswith('*') or line.startswith('•'):
                    sections[current_section].append(line[1:].strip())
                else:
                    sections[current_section].append(line)
        
        # Extract essential fields
        exception_id = structured_fields.get('exception_id', '')
        invoice_id = structured_fields.get('invoice_id', '')
        
        if not exception_id or not invoice_id:
            return None
        
        # Create context from sections
        context.update(sections)
        context['queue'] = queue_name
        context['source'] = 'queue_log'
        
        return FlexibleException(
            exception_id=exception_id,
            invoice_id=invoice_id,
            queue=queue_name,
            timestamp=structured_fields.get('timestamp', datetime.now().isoformat()),
            raw_data={'content': content, 'lines': lines},
            structured_fields=structured_fields,
            unstructured_text=unstructured_text,
            context=context,
            priority=structured_fields.get('priority'),
            status=structured_fields.get('status', 'OPEN')
        )

    def _create_exception_from_dict(self, data: Dict[str, Any], source: str) -> FlexibleException:
        """Create exception from dictionary data."""
        return FlexibleException(
            exception_id=data.get('exception_id', ''),
            invoice_id=data.get('invoice_id', ''),
            queue=data.get('queue', 'UNKNOWN'),
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            raw_data=data,
            structured_fields=data,
            unstructured_text=[],
            context={'source': source},
            priority=data.get('priority'),
            status=data.get('status', 'OPEN')
        )

    def _deduplicate_exceptions(self, exceptions: List[FlexibleException]) -> List[FlexibleException]:
        """Deduplicate exceptions, preferring more complete data."""
        seen_ids = {}
        
        for exc in exceptions:
            if exc.exception_id not in seen_ids:
                seen_ids[exc.exception_id] = exc
            else:
                # Prefer the exception with more structured data
                existing = seen_ids[exc.exception_id]
                if len(exc.structured_fields) > len(existing.structured_fields):
                    seen_ids[exc.exception_id] = exc
                elif len(exc.structured_fields) == len(existing.structured_fields):
                    # Prefer queue log data over ledger data
                    if exc.context.get('source') == 'queue_log' and existing.context.get('source') == 'ledger':
                        seen_ids[exc.exception_id] = exc
        
        return list(seen_ids.values())

    def get_exception_summary(self) -> Dict[str, Any]:
        """Get a summary of all exceptions with flexible field analysis."""
        exceptions = self.parse_all_exceptions()
        
        # Analyze field usage across all exceptions
        field_usage = {}
        queue_stats = {}
        
        for exc in exceptions:
            queue = exc.queue
            if queue not in queue_stats:
                queue_stats[queue] = {'total': 0, 'fields': set()}
            
            queue_stats[queue]['total'] += 1
            queue_stats[queue]['fields'].update(exc.structured_fields.keys())
            
            for field in exc.structured_fields.keys():
                field_usage[field] = field_usage.get(field, 0) + 1
        
        return {
            'total_exceptions': len(exceptions),
            'field_usage': field_usage,
            'queue_stats': {k: {'total': v['total'], 'fields': list(v['fields'])} for k, v in queue_stats.items()},
            'common_fields': sorted(field_usage.items(), key=lambda x: x[1], reverse=True)
        }

