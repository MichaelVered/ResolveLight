import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

from .validation_runner_tool import run_validations
from .po_contract_resolver_tool import resolve_invoice_to_po_and_contract
from .fuzzy_matching_tool import fuzzy_resolve_invoice_to_po_and_contract


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_logs_dir(repo_root: str) -> str:
    logs_dir = os.path.join(repo_root, "system_logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def _append_line(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def _log_processed_invoice(invoice_data: Dict[str, Any], processing_result: str, logs_dir: str, additional_info: Dict[str, Any] = None) -> None:
    """
    Log every processed invoice to processed_invoices.log for comprehensive audit trail.
    
    Args:
        invoice_data: Invoice data dictionary
        processing_result: Final processing result (APPROVED, PENDING_APPROVAL, REJECTED)
        logs_dir: Directory containing log files
        additional_info: Additional information like exception_id, routing_queue, etc.
    """
    processed_log = os.path.join(logs_dir, "processed_invoices.log")
    
    # Check if this invoice has already been processed to avoid duplicates
    invoice_id = invoice_data.get("invoice_id", "<unknown>")
    if os.path.exists(processed_log):
        try:
            with open(processed_log, "r", encoding="utf-8") as f:
                content = f.read()
                if f'"invoice_id": "{invoice_id}"' in content:
                    # Invoice already processed, skip logging
                    return
        except Exception:
            # If we can't read the file, continue with logging
            pass
    
    # Extract key invoice information
    invoice_id = invoice_data.get("invoice_id", "<unknown>")
    # Handle both supplier and supplier_info structures
    supplier_info = invoice_data.get("supplier_info", invoice_data.get("supplier", {}))
    supplier_name = supplier_info.get("name", "<unknown>")
    vendor_id = supplier_info.get("vendor_id", "<unknown>")
    # Use invoice_id as invoice_number if invoice_number field doesn't exist
    invoice_number = invoice_data.get("invoice_number", invoice_data.get("invoice_id", "<unknown>"))
    billing_amount = float(invoice_data.get("summary", {}).get("billing_amount", 0))
    po_number = invoice_data.get("purchase_order_number", "<unknown>")
    line_items_count = len(invoice_data.get("line_items", []))
    issue_date = invoice_data.get("issue_date", "<unknown>")
    
    # Create the processed invoice record
    processed_record = {
        "timestamp": _ts(),
        "invoice_id": invoice_id,
        "supplier_name": supplier_name,
        "vendor_id": vendor_id,
        "invoice_number": invoice_number,
        "billing_amount": billing_amount,
        "po_number": po_number,
        "processing_result": processing_result,
        "line_items_count": line_items_count,
        "issue_date": issue_date
    }
    
    # Add additional information if provided
    if additional_info:
        processed_record.update(additional_info)
    
    # Log to processed_invoices.log
    log_entry = f"PROCESSED: {json.dumps(processed_record)}"
    _append_line(processed_log, log_entry)


def _format_fail_reasons(tool_results: List[Dict[str, Any]]) -> List[str]:
    reasons: List[str] = []
    for r in tool_results or []:
        if r.get("status") == "FAIL":
            tool = r.get("tool", "tool")
            exc = r.get("exceptions") or []
            # Handle both string and dict exceptions
            exc_strs = []
            for e in exc:
                if isinstance(e, dict):
                    exc_strs.append(str(e))
                else:
                    exc_strs.append(str(e))
            msg = f"{tool}: " + ", ".join(exc_strs) if exc_strs else f"{tool}: <no details>"
            reasons.append(msg)
    return reasons


def _determine_routing_queue(tool_results: List[Dict[str, Any]], invoice_data: Dict[str, Any], matching_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine the appropriate routing queue based on validation failures and confidence scores.
    
    Args:
        tool_results: Results from validation tools
        invoice_data: Invoice data
        matching_details: Details from fuzzy matching
    
    Returns:
        Dict with queue information and routing decision
    """
    routing_info = {
        "queue_name": "general_exceptions",
        "priority": "normal",
        "routing_reason": "General validation failure",
        "requires_manager_approval": False,
        "confidence_score": 0.0,
        "specific_issues": []
    }
    
    
    # Check for missing data issues
    dependency_tool = next((r for r in tool_results if r.get("tool") == "dependency_check"), None)
    if dependency_tool and dependency_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "missing_data",
            "priority": "high",
            "routing_reason": "Missing PO or contract data",
            "requires_manager_approval": True,
            "specific_issues": ["missing_po", "missing_contract"]
        })
        return routing_info
    
    # Check for low confidence matching
    po_confidence = matching_details.get("po_match", {}).get("confidence", 0.0)
    supplier_confidence = matching_details.get("supplier_match", {}).get("confidence", 0.0)
    overall_confidence = matching_details.get("overall_confidence", 0.0)
    
    if overall_confidence < 0.7:  # Low confidence threshold
        routing_info.update({
            "queue_name": "low_confidence_matches",
            "priority": "high",
            "routing_reason": f"Low confidence matching ({overall_confidence:.1%})",
            "requires_manager_approval": True,
            "confidence_score": overall_confidence,
            "specific_issues": ["low_po_confidence", "low_supplier_confidence"]
        })
        return routing_info
    
    # Check for line item validation failures
    line_item_tool = next((r for r in tool_results if r.get("tool") == "line_item_validation_tool"), None)
    if line_item_tool and line_item_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "price_discrepancies",
            "priority": "high",
            "routing_reason": "Line item validation failed",
            "requires_manager_approval": True,
            "specific_issues": ["price_mismatch", "quantity_mismatch"]
        })
        return routing_info
    
    # Check for supplier matching issues
    supplier_tool = next((r for r in tool_results if r.get("tool") == "supplier_match_tool"), None)
    if supplier_tool and supplier_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "supplier_mismatch",
            "priority": "medium",
            "routing_reason": "Supplier information mismatch",
            "requires_manager_approval": False,
            "specific_issues": ["supplier_name_mismatch", "vendor_id_mismatch"]
        })
        return routing_info
    
    # Check for billing/overbilling issues
    billing_tool = next((r for r in tool_results if r.get("tool") == "simple_overbilling_tool"), None)
    if billing_tool and billing_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "billing_discrepancies",
            "priority": "high",
            "routing_reason": "Billing amount exceeds PO or arithmetic error",
            "requires_manager_approval": True,
            "specific_issues": ["overbilling", "arithmetic_error"]
        })
        return routing_info
    
    # Check for date issues
    date_tool = next((r for r in tool_results if r.get("tool") == "date_check_tool"), None)
    if date_tool and date_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "date_discrepancies",
            "priority": "medium",
            "routing_reason": "Date validation failed",
            "requires_manager_approval": False,
            "specific_issues": ["date_mismatch", "payment_terms_error"]
        })
        return routing_info
    
    # Check invoice value for high-value routing
    invoice_amount = float(invoice_data.get("summary", {}).get("billing_amount", 0))
    if invoice_amount > 10000:  # High-value threshold
        routing_info.update({
            "queue_name": "high_value_approval",
            "priority": "high",
            "routing_reason": f"High-value invoice (${invoice_amount:,.2f})",
            "requires_manager_approval": True,
            "specific_issues": ["high_value"]
        })
        return routing_info
    
    return routing_info


def _generate_validation_details(tool_results: List[Dict[str, Any]], invoice_data: Dict[str, Any] = None, contract_data: Dict[str, Any] = None, po_item: Dict[str, Any] = None) -> str:
    """
    Generate structured VALIDATION_DETAILS section from tool results.
    
    Args:
        tool_results: List of validation tool results
        invoice_data: Invoice data dictionary
        contract_data: Contract data dictionary
        po_item: Purchase order item data dictionary
    
    Returns:
        Multi-line string with validation details or empty string if no failures
    """
    validation_details = []
    
    for tool_result in tool_results:
        tool_name = tool_result.get("tool", "unknown_tool")
        tool_status = tool_result.get("status")
        
        # Only process failed tools
        if tool_status != "FAIL":
            continue
        
        exceptions = tool_result.get("exceptions", [])
        
        # Handle different tool types
        if tool_name == "line_item_validation_tool":
            for exc in exceptions:
                if isinstance(exc, dict) and exc.get("discrepancies"):
                    item_id = exc.get("item_id", "unknown")
                    description = exc.get("description", "N/A")
                    
                    for disc in exc.get("discrepancies", []):
                        if disc.get("status") == "FAIL":
                            field = disc.get("field", "unknown_field")
                            inv_value = disc.get("invoice_value")
                            exp_value = disc.get("po_value") or disc.get("calculated_value")
                            
                            # Format difference
                            if "difference" in disc:
                                diff = disc.get("difference")
                                if isinstance(diff, (int, float)):
                                    diff_str = f"{diff:,.2f}"
                                else:
                                    diff_str = str(diff)
                            elif "excess" in disc:
                                excess = disc.get("excess")
                                pct = disc.get("percentage_excess", 0)
                                diff_str = f"{excess} ({pct}% excess)"
                            else:
                                diff_str = "N/A"
                            
                            # Determine failed rule and comparison method
                            failed_rule_map = {
                                "unit_price": "unit_price_match",
                                "quantity": "quantity_validation",
                                "line_total": "line_total_calculation"
                            }
                            failed_rule = failed_rule_map.get(field, f"{field}_validation")
                            comparison_method = "exact_match" if field != "quantity" else "upper_bound_validation"
                            
                            # Format failure reason
                            if field == "unit_price":
                                if isinstance(inv_value, (int, float)) and isinstance(exp_value, (int, float)):
                                    diff_val = abs(inv_value - exp_value)
                                    pct = (diff_val / exp_value * 100) if exp_value != 0 else 0
                                    reason = f"Unit price exceeds PO unit price by ${diff_val:.2f} ({pct:.2f}%)"
                                    threshold = "100% exact match required"
                                else:
                                    reason = f"Unit price mismatch: Invoice {inv_value} vs PO {exp_value}"
                                    threshold = "N/A"
                            elif field == "quantity":
                                if "excess" in disc:
                                    excess = disc.get("excess")
                                    pct = disc.get("percentage_excess", 0)
                                    reason = f"Quantity exceeds PO quantity by {excess} units ({pct}%)"
                                    threshold = "Invoice quantity must not exceed PO quantity"
                                else:
                                    reason = f"Quantity mismatch: Invoice {inv_value} vs PO {exp_value}"
                                    threshold = "N/A"
                            elif field == "line_total":
                                reason = f"Line total calculation error: ${inv_value} vs expected ${exp_value}"
                                threshold = "Line total must equal unit_price × quantity (within rounding)"
                            else:
                                reason = f"Validation failed for {field}: {inv_value} vs {exp_value}"
                                threshold = "N/A"
                            
                            validation_details.append(f"Tool: {tool_name}")
                            validation_details.append(f"Field: {field}")
                            validation_details.append(f"FAILED_RULE: {failed_rule}")
                            validation_details.append(f"INVOICE_VALUE: {inv_value}")
                            validation_details.append(f"EXPECTED_VALUE: {exp_value}")
                            validation_details.append(f"DIFFERENCE: {diff_str}")
                            validation_details.append(f"COMPARISON_METHOD: {comparison_method}")
                            validation_details.append(f"THRESHOLD: {threshold}")
                            validation_details.append(f"FAILURE_REASON: {reason}")
                            validation_details.append("")  # Empty line between blocks
        
        elif tool_name == "supplier_match_tool":
            # Supplier mismatch - handle detailed exception information
            if exceptions:
                for exc in exceptions:
                    # Check if this is a detailed exception dict or legacy string
                    if isinstance(exc, dict):
                        # New detailed exception format
                        exc_type = exc.get("type", "supplier_name_mismatch")
                        invoice_value = exc.get("invoice_value", "Unknown")
                        expected_value = exc.get("expected_value", "Unknown")
                        invoice_details = exc.get("invoice_value_details", "")
                        expected_details = exc.get("expected_value_details", "")
                        difference = exc.get("difference", "N/A")
                        comparison_method = exc.get("comparison_method", "exact_match")
                        threshold = exc.get("threshold", "N/A")
                        
                        # Determine field and rule based on exception type
                        if "vendor_id" in exc_type:
                            field = "supplier_vendor_id"
                            failed_rule = "supplier_vendor_id_match"
                        elif "bill_to" in exc_type:
                            field = "bill_to_name"
                            failed_rule = "bill_to_match"
                        else:
                            field = "supplier_name"
                            failed_rule = "supplier_match"
                        
                        # Create detailed failure reason
                        failure_reason = f"Supplier mismatch: '{invoice_value}' vs '{expected_value}'. {difference}. Method: {comparison_method}, Threshold: {threshold}"
                        
                        validation_details.append("Tool: supplier_match_tool")
                        validation_details.append(f"Field: {field}")
                        validation_details.append(f"FAILED_RULE: {failed_rule}")
                        validation_details.append(f"INVOICE_VALUE: {invoice_value}")
                        validation_details.append(f"EXPECTED_VALUE: {expected_value}")
                        validation_details.append(f"INVOICE_DETAILS: {invoice_details}")
                        validation_details.append(f"EXPECTED_DETAILS: {expected_details}")
                        validation_details.append(f"DIFFERENCE: {difference}")
                        validation_details.append(f"COMPARISON_METHOD: {comparison_method}")
                        validation_details.append(f"THRESHOLD: {threshold}")
                        validation_details.append(f"FAILURE_REASON: {failure_reason}")
                        validation_details.append("")
                    else:
                        # Legacy string format - extract from invoice/contract data
                        invoice_supplier = "Unknown"
                        contract_supplier = "Unknown"
                        
                        if invoice_data:
                            inv_supplier_info = invoice_data.get("supplier_info", {})
                            if isinstance(inv_supplier_info, dict):
                                invoice_supplier = inv_supplier_info.get("name", "Unknown")
                            elif isinstance(inv_supplier_info, str):
                                invoice_supplier = inv_supplier_info
                        
                        if contract_data:
                            parties = contract_data.get("parties", {})
                            con_supplier = parties.get("supplier", {})
                            if isinstance(con_supplier, dict):
                                contract_supplier = con_supplier.get("name", "Unknown")
                        
                        # Check what specific mismatches occurred
                        failed_rule = "supplier_match"
                        field = "supplier_name"
                        failure_reason = f"Supplier name mismatch between invoice and PO: '{invoice_supplier}' vs '{contract_supplier}'"
                        
                        if "vendor_id" in str(exc).lower():
                            field = "supplier_vendor_id"
                            failed_rule = "supplier_vendor_id_match"
                            failure_reason = "Supplier vendor ID mismatch between invoice and PO"
                        
                        validation_details.append("Tool: supplier_match_tool")
                        validation_details.append(f"Field: {field}")
                        validation_details.append(f"FAILED_RULE: {failed_rule}")
                        validation_details.append(f"INVOICE_VALUE: {invoice_supplier}")
                        validation_details.append(f"EXPECTED_VALUE: {contract_supplier}")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append("COMPARISON_METHOD: exact_match")
                        validation_details.append("THRESHOLD: 100% exact match required")
                        validation_details.append(f"FAILURE_REASON: {failure_reason}")
                        validation_details.append("")
        
        elif tool_name == "simple_overbilling_tool":
            # Billing issues - handle new detailed exception format
            if exceptions:
                for exc in exceptions:
                    if isinstance(exc, dict):
                        exc_type = exc.get("type", "")
                        if exc_type == "billing_amount_mismatch":
                            validation_details.append("Tool: simple_overbilling_tool")
                            validation_details.append("Field: billing_amount")
                            validation_details.append("FAILED_RULE: billing_arithmetic_validation")
                            validation_details.append(f"INVOICE_VALUE: ${exc.get('invoice_billing_amount', 'Unknown')}")
                            validation_details.append(f"EXPECTED_VALUE: ${exc.get('calculated_total', 'Unknown')} (subtotal ${exc.get('invoice_subtotal', 0)} + tax ${exc.get('invoice_tax', 0)})")
                            validation_details.append(f"DIFFERENCE: ${exc.get('difference', 'N/A')}")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: {exc.get('message', 'Billing amount calculation mismatch')}")
                            validation_details.append("")
                        elif exc_type == "invoice_exceeds_po":
                            validation_details.append("Tool: simple_overbilling_tool")
                            validation_details.append("Field: total_amount")
                            validation_details.append("FAILED_RULE: invoice_amount_validation")
                            validation_details.append(f"INVOICE_VALUE: ${exc.get('invoice_total', 'Unknown')}")
                            validation_details.append(f"EXPECTED_VALUE: ${exc.get('po_total_value', 'Unknown')} (PO total)")
                            validation_details.append(f"DIFFERENCE: ${exc.get('excess', 'N/A')} ({exc.get('percentage_excess', 0)}% excess)")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: Invoice total exceeds PO total by ${exc.get('excess', 0)} ({exc.get('percentage_excess', 0)}%)")
                            validation_details.append("")
                    else:
                        # Legacy string format
                        validation_details.append("Tool: simple_overbilling_tool")
                        validation_details.append("Field: billing_amount")
                        validation_details.append("FAILED_RULE: billing_validation")
                        validation_details.append("INVOICE_VALUE: Unknown")
                        validation_details.append("EXPECTED_VALUE: Unknown")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append(f"FAILURE_REASON: {str(exc)}")
                        validation_details.append("")
        
        elif tool_name == "content_validation_tool":
            # Content validation issues - handle new detailed exception format
            if exceptions:
                for exc in exceptions:
                    if isinstance(exc, dict):
                        exc_type = exc.get("type", "")
                        if exc_type == "content_mismatch":
                            validation_details.append("Tool: content_validation_tool")
                            validation_details.append(f"Field: item_{exc.get('item_id', 'unknown')}_description")
                            validation_details.append("FAILED_RULE: content_similarity_validation")
                            validation_details.append(f"INVOICE_VALUE: '{exc.get('invoice_description', 'N/A')}'")
                            validation_details.append(f"EXPECTED_VALUE: '{exc.get('po_description', 'N/A')}'")
                            validation_details.append(f"DIFFERENCE: Similarity score {exc.get('similarity_score', 'N/A')} (below threshold {exc.get('threshold', 'N/A')})")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: Content mismatch for item {exc.get('item_id', 'N/A')}: descriptions don't match")
                            validation_details.append("")
                        elif exc_type == "suspicious_content":
                            validation_details.append("Tool: content_validation_tool")
                            validation_details.append(f"Field: item_{exc.get('item_id', 'unknown')}_description")
                            validation_details.append("FAILED_RULE: content_safety_validation")
                            validation_details.append(f"INVOICE_VALUE: '{exc.get('description', 'N/A')}'")
                            validation_details.append("EXPECTED_VALUE: Clean business description")
                            validation_details.append(f"DIFFERENCE: Contains suspicious keyword: '{exc.get('suspicious_keyword', 'N/A')}'")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: Suspicious content detected in item {exc.get('item_id', 'N/A')}")
                            validation_details.append("")
                        elif exc_type == "missing_line_items":
                            validation_details.append("Tool: content_validation_tool")
                            validation_details.append("Field: line_items")
                            validation_details.append("FAILED_RULE: content_completeness_validation")
                            validation_details.append(f"INVOICE_VALUE: {exc.get('invoice_line_items_count', 0)} line items")
                            validation_details.append(f"EXPECTED_VALUE: {exc.get('expected', 'At least 1 line item')}")
                            validation_details.append("DIFFERENCE: N/A")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: Missing required line items")
                            validation_details.append("")
                    else:
                        # Legacy string format
                        validation_details.append("Tool: content_validation_tool")
                        validation_details.append("Field: content_match")
                        validation_details.append("FAILED_RULE: content_validation")
                        validation_details.append("INVOICE_VALUE: N/A")
                        validation_details.append("EXPECTED_VALUE: N/A")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append(f"FAILURE_REASON: {str(exc)}")
                        validation_details.append("")
        
        elif tool_name == "date_check_tool":
            # Date issues - handle new detailed exception format
            if exceptions:
                for exc in exceptions:
                    if isinstance(exc, dict):
                        exc_type = exc.get("type", "")
                        
                        if exc_type == "invoice_issue_out_of_contract_window":
                            validation_details.append("Tool: date_check_tool")
                            validation_details.append("Field: issue_date")
                            validation_details.append("FAILED_RULE: date_range_validation")
                            validation_details.append(f"INVOICE_VALUE: {exc.get('invoice_issue_date', 'N/A')}")
                            validation_details.append(f"EXPECTED_VALUE: {exc.get('expected_range', 'N/A')}")
                            validation_details.append(f"DIFFERENCE: {exc.get('days_out_of_range', 'N/A')} days outside window")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: Invoice issue date ({exc.get('invoice_issue_date', 'N/A')}) is outside contract window ({exc.get('expected_range', 'N/A')}) by {exc.get('days_out_of_range', 'N/A')} days")
                            validation_details.append("")
                        
                        elif exc_type == "due_date_not_net30":
                            validation_details.append("Tool: date_check_tool")
                            validation_details.append("Field: due_date")
                            validation_details.append("FAILED_RULE: payment_terms_validation")
                            validation_details.append(f"INVOICE_VALUE: {exc.get('invoice_due_date', 'N/A')}")
                            validation_details.append(f"EXPECTED_VALUE: {exc.get('expected_due_date', 'N/A')} (issue date + 30 days)")
                            validation_details.append(f"DIFFERENCE: {exc.get('days_difference', 'N/A')} days")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: Due date ({exc.get('invoice_due_date', 'N/A')}) should be Net 30 from issue date ({exc.get('invoice_issue_date', 'N/A')})")
                            validation_details.append("")
                        
                        elif exc_type == "invoice_issue_before_po_effective_date":
                            validation_details.append("Tool: date_check_tool")
                            validation_details.append("Field: issue_date")
                            validation_details.append("FAILED_RULE: po_date_validation")
                            validation_details.append(f"INVOICE_VALUE: {exc.get('invoice_issue_date', 'N/A')}")
                            validation_details.append(f"EXPECTED_VALUE: {exc.get('po_effective_date', 'N/A')} or later")
                            validation_details.append(f"DIFFERENCE: {exc.get('days_before', 'N/A')} days before PO effective date")
                            validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                            validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                            validation_details.append(f"FAILURE_REASON: Invoice issue date ({exc.get('invoice_issue_date', 'N/A')}) is {exc.get('days_before', 'N/A')} days before PO effective date ({exc.get('po_effective_date', 'N/A')})")
                            validation_details.append("")
                        
                        elif "parse_error" in exc_type:
                            validation_details.append("Tool: date_check_tool")
                            validation_details.append("Field: date_parsing")
                            validation_details.append("FAILED_RULE: date_format_validation")
                            validation_details.append(f"INVOICE_VALUE: {exc.get('issue_date', exc.get('due_date', exc.get('effective_date', exc.get('end_date', 'N/A'))))}")
                            validation_details.append(f"EXPECTED_VALUE: YYYY-MM-DD format")
                            validation_details.append(f"DIFFERENCE: N/A")
                            validation_details.append(f"COMPARISON_METHOD: format_validation")
                            validation_details.append(f"THRESHOLD: {exc.get('required_format', 'YYYY-MM-DD')}")
                            validation_details.append(f"FAILURE_REASON: Date parsing error: {exc.get('error', 'Unknown error')}")
                            validation_details.append("")
                    else:
                        # Legacy string format
                        validation_details.append("Tool: date_check_tool")
                        validation_details.append("Field: date_validation")
                        validation_details.append("FAILED_RULE: date_validation")
                        validation_details.append("INVOICE_VALUE: N/A")
                        validation_details.append("EXPECTED_VALUE: N/A")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append(f"FAILURE_REASON: {str(exc)}")
                        validation_details.append("")
        
        elif tool_name == "currency_validation_tool":
            # Currency validation issues - handle new detailed exception format
            if exceptions:
                for exc in exceptions:
                    if isinstance(exc, dict):
                        validation_details.append("Tool: currency_validation_tool")
                        validation_details.append("Field: currency")
                        validation_details.append(f"FAILED_RULE: {exc.get('type', 'currency_validation')}")
                        validation_details.append(f"INVOICE_VALUE: {exc.get('invoice_currency', 'N/A')}")
                        validation_details.append(f"EXPECTED_VALUE: {exc.get('supported_currencies', exc.get('contract_currency', exc.get('expected_format', 'N/A')))}")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                        validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                        validation_details.append(f"FAILURE_REASON: {exc.get('type', 'Currency validation failed')} - {exc.get('invoice_currency', 'Unknown currency')}")
                        validation_details.append("")
                    else:
                        # Legacy string format
                        validation_details.append("Tool: currency_validation_tool")
                        validation_details.append("Field: currency")
                        validation_details.append("FAILED_RULE: currency_validation")
                        validation_details.append("INVOICE_VALUE: Unknown")
                        validation_details.append("EXPECTED_VALUE: USD")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append(f"FAILURE_REASON: {str(exc)}")
                        validation_details.append("")
        
        elif tool_name == "payment_terms_validation_tool":
            # Payment terms validation issues - handle new detailed exception format
            if exceptions:
                for exc in exceptions:
                    if isinstance(exc, dict):
                        validation_details.append("Tool: payment_terms_validation_tool")
                        validation_details.append("Field: payment_terms")
                        validation_details.append(f"FAILED_RULE: {exc.get('type', 'payment_terms_validation')}")
                        validation_details.append(f"INVOICE_VALUE: {exc.get('invoice_terms', 'N/A')}")
                        validation_details.append(f"EXPECTED_VALUE: {exc.get('supported_terms', exc.get('contract_terms', exc.get('expected_format', 'N/A')))}")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append(f"COMPARISON_METHOD: {exc.get('comparison_method', 'N/A')}")
                        validation_details.append(f"THRESHOLD: {exc.get('threshold', 'N/A')}")
                        validation_details.append(f"FAILURE_REASON: {exc.get('type', 'Payment terms validation failed')} - {exc.get('invoice_terms', 'Unknown terms')}")
                        validation_details.append("")
                    else:
                        # Legacy string format
                        validation_details.append("Tool: payment_terms_validation_tool")
                        validation_details.append("Field: payment_terms")
                        validation_details.append("FAILED_RULE: payment_terms_validation")
                        validation_details.append("INVOICE_VALUE: Unknown")
                        validation_details.append("EXPECTED_VALUE: Net 30")
                        validation_details.append("DIFFERENCE: N/A")
                        validation_details.append(f"FAILURE_REASON: {str(exc)}")
                        validation_details.append("")
    
    return "\n".join(validation_details)


def _create_queue_specific_log_entry(queue_info: Dict[str, Any], invoice_data: Dict[str, Any], exception_id: str, tool_results: List[Dict[str, Any]], contract_data: Dict[str, Any] = None, po_item: Dict[str, Any] = None) -> str:
    """
    Create a queue-specific log entry in canonical format for human reviewers.
    """
    queue_name = queue_info["queue_name"]
    priority = queue_info["priority"]
    routing_reason = queue_info["routing_reason"]
    
    inv_id = invoice_data.get("invoice_id", "<unknown>")
    po_num = invoice_data.get("purchase_order_number", "<unknown>")
    amount = float(invoice_data.get("summary", {}).get("billing_amount", 0))
    # Handle both supplier and supplier_info structures
    supplier_info = invoice_data.get("supplier_info", invoice_data.get("supplier", {}))
    supplier = supplier_info.get("name", "<unknown>")
    
    # Map queue names to exception types
    exception_type_map = {
        "missing_data": "MISSING_DATA",
        "low_confidence_matches": "LOW_CONFIDENCE", 
        "price_discrepancies": "PRICE_DISCREPANCY",
        "supplier_mismatch": "SUPPLIER_MISMATCH",
        "billing_discrepancies": "BILLING_DISCREPANCY",
        "date_discrepancies": "DATE_DISCREPANCY",
        "high_value_approval": "HIGH_VALUE_APPROVAL",
        "general_exceptions": "GENERAL"
    }
    exception_type = exception_type_map.get(queue_name, "GENERAL")
    
    # Generate validation details  
    validation_details = _generate_validation_details(tool_results, invoice_data, contract_data, po_item)
    
    # Create detailed context based on queue type
    context_details = []
    
    if queue_name == "low_confidence_matches":
        context_details.append("MATCHING CONFIDENCE:")
        context_details.append(f"  - Overall confidence: {queue_info.get('confidence_score', 0):.1%}")
        context_details.append("  - Review matching logic and consider manual verification")
    
    elif queue_name == "price_discrepancies":
        line_item_tool = next((r for r in tool_results if r.get("tool") == "line_item_validation_tool"), None)
        if line_item_tool:
            context_details.append("LINE ITEM DISCREPANCIES:")
            for exc in line_item_tool.get("exceptions", []):
                if exc.get("discrepancies"):
                    context_details.append(f"  - Item {exc.get('item_id')}: {exc.get('description')}")
                    for disc in exc.get("discrepancies", []):
                        if disc.get("status") == "FAIL":
                            context_details.append(f"    * {disc.get('field')}: {disc.get('invoice_value')} vs PO {disc.get('po_value')}")
    
    elif queue_name == "billing_discrepancies":
        billing_tool = next((r for r in tool_results if r.get("tool") == "simple_overbilling_tool"), None)
        if billing_tool:
            context_details.append("BILLING ISSUES:")
            for exc in billing_tool.get("exceptions", []):
                context_details.append(f"  - {exc}")
    
    elif queue_name == "supplier_mismatch":
        context_details.append("SUPPLIER MISMATCH:")
        context_details.append("  - Supplier information mismatch")
        context_details.append("  - Verify supplier details and PO matching")
    
    elif queue_name == "date_discrepancies":
        context_details.append("DATE ISSUES:")
        context_details.append("  - Date validation failed")
        context_details.append("  - Check invoice dates, payment terms, and PO dates")
    
    elif queue_name == "high_value_approval":
        context_details.append("HIGH VALUE INVOICE:")
        context_details.append(f"  - Invoice amount: ${amount:,.2f}")
        context_details.append("  - Requires manager approval due to high value")
    
    elif queue_name == "missing_data":
        context_details.append("MISSING DATA:")
        context_details.append("  - Required PO or contract data not found")
        context_details.append("  - Verify data availability and matching criteria")
    
    else:  # general_exceptions
        context_details.append("  - General validation failure")
    
    # Create canonical format log entry
    log_entry = f"""=== EXCEPTION_START ===
VERSION: 1.0
EXCEPTION_ID: {exception_id}
STATUS: REJECTED
QUEUE: {queue_name}
PRIORITY: {priority.upper()}
EXCEPTION_TYPE: {exception_type}
TIMESTAMP: {_ts()}
INVOICE_ID: {inv_id}
PO_NUMBER: {po_num}
AMOUNT: ${amount:,.2f}
SUPPLIER: {supplier}
ROUTING_REASON: {routing_reason}
CONFIDENCE_SCORE: {queue_info.get('confidence_score', 'N/A')}
MANAGER_APPROVAL_REQUIRED: {'YES' if queue_info.get('requires_manager_approval', False) else 'NO'}
"""
    
    # Add VALIDATION_DETAILS section if available
    if validation_details:
        log_entry += f"\nVALIDATION_DETAILS:\n{validation_details}\n"
    
    log_entry += f"""
CONTEXT:
{chr(10).join(context_details)}

SUGGESTED_ACTIONS:
  - Review the specific issues listed above
  - Contact supplier if data discrepancies found
  - Verify PO and contract details if matching issues
  - Approve manually if all checks pass after review

METADATA:
  tool_version: 1.0.0
  system_version: 2.1.0
  processing_time: N/A
=== EXCEPTION_END ==="""
    
    return log_entry


def triage_and_route(invoice_filename: str, repo_root: str | None = None) -> Dict[str, Any]:
    """
    Enhanced triage and routing with granular queue management.
    
    This function:
    1. Performs duplicate detection
    2. Uses fuzzy matching for better resolution
    3. Runs comprehensive validation
    4. Routes to specific queues based on failure types
    5. Creates detailed context for human reviewers
    
    Args:
        invoice_filename: Path to invoice file
        repo_root: Root directory of the project
    
    Returns:
        Dict with routing results and actions taken
    """
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    logs_dir = _ensure_logs_dir(root)
    
    # Step 1: Skip duplicate check to make flow stateless
    # duplicate_check = check_for_duplicates(invoice_filename, repo_root=root)
    # if duplicate_check.get("status") == "FAIL":
    #     # Handle duplicate immediately - REMOVED FOR STATELESS FLOW
    #     pass
    
    # Step 2: Use fuzzy matching for better resolution
    resolution = fuzzy_resolve_invoice_to_po_and_contract(invoice_filename, repo_root=root)
    invoice = resolution.get("invoice") if isinstance(resolution.get("invoice"), dict) else {}
    po_item = resolution.get("po_item") if isinstance(resolution.get("po_item"), dict) else {}
    contract = resolution.get("contract") if isinstance(resolution.get("contract"), dict) else {}
    matching_details = resolution.get("matching_details", {})
    
    # Step 3: Run comprehensive validation
    report = run_validations(invoice_filename, repo_root=root)
    validation = report.get("validation")
    tool_results = report.get("tool_results") or []
    
    actions: List[str] = []
    
    if validation == "PASS":
        # Check if we need manager approval for high-value invoices
        invoice_amount = float(invoice.get("summary", {}).get("billing_amount", 0))
        overall_confidence = matching_details.get("overall_confidence", 1.0)
        
        if invoice_amount > 10000 or overall_confidence < 0.9:
            # Route to high-value approval queue even if validation passes
            exception_id = f"EXC-{uuid.uuid4().hex[:12].upper()}"
            queue_info = {
                "queue_name": "high_value_approval",
                "priority": "high",
                "routing_reason": f"High-value invoice (${invoice_amount:,.2f}) or low confidence ({overall_confidence:.1%})",
                "requires_manager_approval": True
            }
            
            # High-value approval logging
            approval_log = os.path.join(logs_dir, "queue_high_value_approval.log")
            log_entry = _create_queue_specific_log_entry(queue_info, invoice, exception_id, tool_results, contract, po_item)
            _append_line(approval_log, log_entry)
            
            # Log to processed_invoices.log for audit trail
            additional_info = {
                "exception_id": exception_id,
                "routing_queue": "high_value_approval",
                "priority": "high",
                "requires_manager_approval": True
            }
            _log_processed_invoice(invoice, "PENDING_APPROVAL", logs_dir, additional_info)
            
            return {
                "status": "PENDING_APPROVAL",
                "exception_id": exception_id,
                "routing_queue": "high_value_approval",
                "priority": "high",
                "actions": ["PENDING → Routed to manager approval queue"],
                "logs": {"approval_queue_log": approval_log}
            }
        else:
            # Standard approval
            inv_id = invoice.get("invoice_id", "<unknown>")
            po_num = invoice.get("purchase_order_number", "<unknown>")
            
            payments_log = os.path.join(logs_dir, "payments.log")
            _append_line(payments_log, f"[INFO] [{_ts()}] Invoice {inv_id} approved. Routing to Payment System.")
            
            # Log each line item as approved payment
            for li in invoice.get("line_items", []) or []:
                item_id = li.get("item_id")
                desc = li.get("description")
                total = li.get("line_total")
                _append_line(
                    payments_log,
                    f"    payment_item: invoice_id={inv_id}, po_number={po_num}, item_id={item_id}, description={desc}, amount={total}"
                )
            
            actions.append("APPROVED → Payments logged")
            
            # Log to processed_invoices.log for audit trail
            _log_processed_invoice(invoice, "APPROVED", logs_dir)
            
            return {
                "status": "APPROVED",
                "actions": actions,
                "logs": {"payments_log": payments_log}
            }
    
    # Step 4: Handle validation failures with granular routing
    inv_id = invoice.get("invoice_id", "<unknown>")
    exception_id = f"EXC-{uuid.uuid4().hex[:12].upper()}"
    
    # Determine routing queue based on failure types
    queue_info = _determine_routing_queue(tool_results, invoice, matching_details)
    queue_name = queue_info["queue_name"]
    priority = queue_info["priority"]
    
    # Create queue-specific log file
    queue_log = os.path.join(logs_dir, f"queue_{queue_name}.log")
    log_entry = _create_queue_specific_log_entry(queue_info, invoice, exception_id, tool_results, contract, po_item)
    _append_line(queue_log, log_entry)
    
    # Also log to general exceptions ledger for audit trail
    exceptions_log = os.path.join(logs_dir, "exceptions_ledger.log")
    _append_line(exceptions_log, f"[EXCEPTION] [{_ts()}] id={exception_id} status=REJECTED type=VALIDATION_FAILED invoice_id={inv_id} queue={queue_name}")
    
    # Log rejection for audit trail
    
    # Log to processed_invoices.log for audit trail
    additional_info = {
        "exception_id": exception_id,
        "routing_queue": queue_name,
        "priority": priority,
        "requires_manager_approval": queue_info["requires_manager_approval"],
        "routing_reason": queue_info["routing_reason"]
    }
    _log_processed_invoice(invoice, "REJECTED", logs_dir, additional_info)
    
    actions.append(f"REJECTED → Routed to {queue_name} queue")
    return {
        "status": "REJECTED",
        "exception_id": exception_id,
        "routing_queue": queue_name,
        "priority": priority,
        "requires_manager_approval": queue_info["requires_manager_approval"],
        "actions": actions,
        "logs": {
            "queue_log": queue_log,
            "exceptions_log": exceptions_log
        }
    }


def triage_and_route_tool(invoice_filename: str) -> str:
    """Wrapper for ADK – returns a concise, human-readable summary string."""
    res = triage_and_route(invoice_filename)
    status = res.get("status")
    if status == "APPROVED":
        return f"APPROVED: routed to payments. Log: {res['logs']['payments_log']}"
    return f"REJECTED: exception_id={res.get('exception_id')} logs: {json.dumps(res.get('logs'))}"


