"""
Exception Parser for Adjudication Agent
Parses exception logs and extracts structured data.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional


class ExceptionParser:
    """Parses exception logs into structured data."""
    
    @staticmethod
    def parse_exception_log(log_file: Path) -> List[Dict]:
        """Parse all exceptions from a log file."""
        exceptions = []
        current_exception = None
        current_section = None
        current_validation_block = None
        validation_blocks = []
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.rstrip('\n')
                    
                    if line.strip() == "=== EXCEPTION_START ===":
                        current_exception = {}
                        current_section = "HEADER"
                        validation_blocks = []
                        current_validation_block = None
                    elif line.strip() == "=== EXCEPTION_END ===":
                        if current_exception is not None:
                            # Store any pending validation block
                            if current_validation_block and len(current_validation_block) > 0:
                                validation_blocks.append(current_validation_block)
                            if validation_blocks:
                                current_exception['VALIDATION_DETAILS'] = validation_blocks
                            exceptions.append(current_exception)
                            current_exception = None
                            current_section = None
                            validation_blocks = []
                            current_validation_block = None
                    elif current_exception is not None:
                        if line.strip() == "VALIDATION_DETAILS:":
                            current_section = "VALIDATION_DETAILS"
                            if current_validation_block and len(current_validation_block) > 0:
                                validation_blocks.append(current_validation_block)
                            current_validation_block = {}
                        elif line.strip() in ["CONTEXT:", "SUGGESTED_ACTIONS:", "METADATA:"]:
                            # Transition out of VALIDATION_DETAILS
                            if current_section == "VALIDATION_DETAILS" and current_validation_block and len(current_validation_block) > 0:
                                validation_blocks.append(current_validation_block)
                                current_validation_block = None
                            current_section = line.strip().replace(":", "").lower()
                            current_exception[current_section] = ""
                        elif current_section == "HEADER" and ":" in line:
                            field, value = line.split(":", 1)
                            field = field.strip()
                            value = value.strip()
                            current_exception[field] = value
                        elif current_section == "VALIDATION_DETAILS":
                            if ":" in line:
                                field, value = line.split(":", 1)
                                field = field.strip()
                                value = value.strip()
                                current_validation_block[field] = value
                            elif line.strip() == "" and current_validation_block and len(current_validation_block) > 0:
                                # Empty line indicates end of current validation block
                                validation_blocks.append(current_validation_block)
                                current_validation_block = {}
                        elif current_section and current_section in current_exception:
                            current_exception[current_section] += line + "\n"
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error parsing {log_file}: {e}")
        
        return exceptions
    
    @staticmethod
    def get_all_exceptions(system_logs_dir: Path) -> List[Dict]:
        """Get all exceptions from all log files in system_logs directory.
        
        This method scans ALL .log files in the directory and tries to parse exceptions
        from each. Files that don't contain exception markers (EXCEPTION_START/EXCEPTION_END)
        will return an empty list and be skipped. This makes the parser future-proof for
        any new exception queue files added to the system_logs directory.
        """
        all_exceptions = []
        
        # Find all log files in the directory
        log_files = list(system_logs_dir.glob("*.log"))
        
        for log_file in log_files:
            # Try to parse exceptions from this file
            # The parser will return an empty list if the file doesn't contain
            # EXCEPTION_START/EXCEPTION_END markers
            exceptions = ExceptionParser.parse_exception_log(log_file)
            
            # Only add if this file actually contains exceptions
            if exceptions:
                all_exceptions.extend(exceptions)
        
        return all_exceptions
    
    @staticmethod
    def format_exception(exception: Dict) -> str:
        """Format exception for display or agent prompt."""
        formatted = f"""EXCEPTION DETAILS:

EXCEPTION_ID: {exception.get('EXCEPTION_ID', 'N/A')}
EXCEPTION_TYPE: {exception.get('EXCEPTION_TYPE', 'N/A')}
STATUS: {exception.get('STATUS', 'N/A')}
QUEUE: {exception.get('QUEUE', 'N/A')}
PRIORITY: {exception.get('PRIORITY', 'N/A')}
TIMESTAMP: {exception.get('TIMESTAMP', 'N/A')}
INVOICE_ID: {exception.get('INVOICE_ID', 'N/A')}
PO_NUMBER: {exception.get('PO_NUMBER', 'N/A')}
AMOUNT: {exception.get('AMOUNT', 'N/A')}
SUPPLIER: {exception.get('SUPPLIER', 'N/A')}
ROUTING_REASON: {exception.get('ROUTING_REASON', 'N/A')}
MANAGER_APPROVAL_REQUIRED: {exception.get('MANAGER_APPROVAL_REQUIRED', 'N/A')}"""

        # Add VALIDATION_DETAILS if present
        if 'VALIDATION_DETAILS' in exception and exception['VALIDATION_DETAILS']:
            formatted += "\n\nVALIDATION_DETAILS:\n"
            for i, block in enumerate(exception['VALIDATION_DETAILS'], 1):
                formatted += f"\nBlock {i}:\n"
                for key, value in block.items():
                    formatted += f"  {key}: {value}\n"

        formatted += f"""

CONTEXT:
{exception.get('CONTEXT', 'N/A')}

SUGGESTED_ACTIONS:
{exception.get('SUGGESTED_ACTIONS', 'N/A')}

METADATA:
{exception.get('METADATA', 'N/A')}"""
        return formatted

