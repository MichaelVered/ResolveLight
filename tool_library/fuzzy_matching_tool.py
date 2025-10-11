import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from difflib import SequenceMatcher


def normalize_for_fuzzy(value: Optional[str]) -> str:
    """
    Normalize a string for fuzzy matching by:
    - Converting to uppercase
    - Removing extra whitespace
    - Standardizing common separators
    - Keeping alphanumeric characters and common separators
    """
    if not value:
        return ""
    
    # Convert to uppercase and strip whitespace
    normalized = value.upper().strip()
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Standardize common separators (keep them for better matching)
    normalized = re.sub(r'[-_]+', '-', normalized)
    
    return normalized


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings using SequenceMatcher.
    Returns a float between 0.0 and 1.0 (higher = more similar).
    """
    if not str1 or not str2:
        return 0.0
    
    # Normalize both strings
    norm1 = normalize_for_fuzzy(str1)
    norm2 = normalize_for_fuzzy(str2)
    
    # Calculate similarity
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Boost exact matches after normalization
    if norm1 == norm2:
        similarity = 1.0
    
    return similarity


def find_best_po_match(invoice_po: str, po_candidates: List[Dict[str, Any]], min_confidence: float = 0.7) -> Dict[str, Any]:
    """
    Find the best matching PO from candidates using fuzzy matching.
    
    Args:
        invoice_po: PO number from invoice
        po_candidates: List of PO items to match against
        min_confidence: Minimum confidence threshold (0.0 to 1.0)
    
    Returns:
        Dict with match details and confidence score
    """
    if not invoice_po or not po_candidates:
        return {
            "match": None,
            "confidence": 0.0,
            "reasoning": "No PO number or candidates provided",
            "variations": []
        }
    
    best_match = None
    best_confidence = 0.0
    all_matches = []
    
    for po_item in po_candidates:
        po_number = po_item.get("po_number", "")
        confidence = calculate_similarity(invoice_po, po_number)
        
        match_info = {
            "po_item": po_item,
            "po_number": po_number,
            "confidence": confidence,
            "normalized_invoice": normalize_for_fuzzy(invoice_po),
            "normalized_po": normalize_for_fuzzy(po_number)
        }
        
        all_matches.append(match_info)
        
        if confidence > best_confidence:
            best_confidence = confidence
            best_match = po_item
    
    # Filter matches above minimum confidence
    valid_matches = [m for m in all_matches if m["confidence"] >= min_confidence]
    
    if best_match and best_confidence >= min_confidence:
        return {
            "match": best_match,
            "confidence": best_confidence,
            "reasoning": f"Best match found with {best_confidence:.1%} confidence",
            "variations": [m["po_number"] for m in valid_matches],
            "all_matches": valid_matches
        }
    else:
        return {
            "match": None,
            "confidence": best_confidence,
            "reasoning": f"No matches above {min_confidence:.1%} threshold. Best was {best_confidence:.1%}",
            "variations": [],
            "all_matches": all_matches
        }


def find_best_supplier_match(invoice_supplier: str, invoice_vendor_id: str, contract_suppliers: List[Dict[str, Any]], min_confidence: float = 0.8) -> Dict[str, Any]:
    """
    Find the best matching supplier using both name and vendor ID.
    
    Args:
        invoice_supplier: Supplier name from invoice
        invoice_vendor_id: Vendor ID from invoice
        contract_suppliers: List of supplier records to match against
        min_confidence: Minimum confidence threshold
    
    Returns:
        Dict with match details and confidence score
    """
    if not invoice_supplier or not contract_suppliers:
        return {
            "match": None,
            "confidence": 0.0,
            "reasoning": "No supplier name or candidates provided",
            "match_type": "none"
        }
    
    best_match = None
    best_confidence = 0.0
    match_type = "none"
    
    for supplier in contract_suppliers:
        supplier_name = supplier.get("name", "")
        supplier_vendor_id = supplier.get("vendor_id", "")
        
        # Calculate name similarity
        name_confidence = calculate_similarity(invoice_supplier, supplier_name)
        
        # Calculate vendor ID similarity (exact match gets boost)
        vendor_id_confidence = 1.0 if invoice_vendor_id == supplier_vendor_id else 0.0
        
        # Combined confidence (weighted: 70% name, 30% vendor_id)
        combined_confidence = (name_confidence * 0.7) + (vendor_id_confidence * 0.3)
        
        # Boost for exact vendor ID match
        if vendor_id_confidence == 1.0:
            combined_confidence = max(combined_confidence, 0.9)
            match_type = "vendor_id_exact"
        elif name_confidence > 0.9:
            match_type = "name_exact"
        elif combined_confidence > 0.7:
            match_type = "fuzzy_match"
        
        if combined_confidence > best_confidence:
            best_confidence = combined_confidence
            best_match = supplier
    
    if best_match and best_confidence >= min_confidence:
        return {
            "match": best_match,
            "confidence": best_confidence,
            "reasoning": f"Best match found with {best_confidence:.1%} confidence ({match_type})",
            "match_type": match_type,
            "name_confidence": calculate_similarity(invoice_supplier, best_match.get("name", "")),
            "vendor_id_match": invoice_vendor_id == best_match.get("vendor_id", "")
        }
    else:
        return {
            "match": None,
            "confidence": best_confidence,
            "reasoning": f"No matches above {min_confidence:.1%} threshold. Best was {best_confidence:.1%}",
            "match_type": "none"
        }


def fuzzy_resolve_invoice_to_po_and_contract(
    invoice_filename: str,
    repo_root: Optional[str] = None,
    min_po_confidence: float = 0.7,
    min_supplier_confidence: float = 0.8
) -> Dict[str, Union[str, Dict[str, Any]]]:
    """
    Enhanced resolver that uses fuzzy matching to find PO and contract matches.
    
    Args:
        invoice_filename: Path to invoice file
        repo_root: Root directory of the project
        min_po_confidence: Minimum confidence for PO matching
        min_supplier_confidence: Minimum confidence for supplier matching
    
    Returns:
        Dict with invoice, po_item, contract, and matching details
    """
    # Import the existing resolver functions
    from .po_contract_resolver_tool import (
        resolve_directories, find_invoice_path, read_json_file,
        find_contract_by_id, normalize_token
    )
    
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    invoice_dirs, po_dirs, contract_dirs = resolve_directories(root)
    
    result: Dict[str, Union[str, Dict[str, Any]]] = {
        "invoice": "<not found>",
        "po_item": "<not found>",
        "contract": "<not found>",
        "matching_details": {
            "po_match": None,
            "supplier_match": None,
            "overall_confidence": 0.0
        }
    }
    
    # Load invoice
    invoice_path = find_invoice_path(invoice_filename, invoice_dirs)
    invoice_data = read_json_file(invoice_path) if invoice_path else None
    if not invoice_data:
        return result
    result["invoice"] = invoice_data
    
    # Extract PO number and find candidates
    invoice_po = invoice_data.get("purchase_order_number", "")
    if not invoice_po:
        return result
    
    # Collect all PO candidates
    po_candidates = []
    for d in po_dirs:
        try:
            for name in os.listdir(d):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(d, name)
                data = read_json_file(path)
                if not data:
                    continue
                for item in data.get("purchase_orders", []):
                    po_item = dict(item)
                    po_item["_source_file"] = path
                    po_candidates.append(po_item)
        except Exception:
            continue
    
    # Find best PO match using fuzzy matching
    po_match_result = find_best_po_match(invoice_po, po_candidates, min_po_confidence)
    result["matching_details"]["po_match"] = po_match_result
    
    if po_match_result["match"]:
        result["po_item"] = po_match_result["match"]
        
        # Find contract using the matched PO
        contract_id = po_match_result["match"].get("contract_id")
        normalized_cid = normalize_token(contract_id)
        if normalized_cid:
            contract_data = find_contract_by_id(normalized_cid, contract_dirs)
            if contract_data:
                result["contract"] = contract_data
                
                # Perform supplier matching
                invoice_supplier = invoice_data.get("supplier_info", {}).get("name", "")
                invoice_vendor_id = invoice_data.get("supplier_info", {}).get("vendor_id", "")
                
                # Extract supplier from contract
                contract_supplier = contract_data.get("parties", {}).get("supplier", {})
                contract_suppliers = [contract_supplier] if contract_supplier else []
                
                supplier_match_result = find_best_supplier_match(
                    invoice_supplier, invoice_vendor_id, contract_suppliers, min_supplier_confidence
                )
                result["matching_details"]["supplier_match"] = supplier_match_result
    
    # Calculate overall confidence
    po_confidence = po_match_result["confidence"]
    supplier_confidence = result["matching_details"]["supplier_match"]["confidence"] if result["matching_details"]["supplier_match"] else 0.0
    
    # Overall confidence is weighted average (60% PO match, 40% supplier match)
    overall_confidence = (po_confidence * 0.6) + (supplier_confidence * 0.4)
    result["matching_details"]["overall_confidence"] = overall_confidence
    
    return result


def main() -> None:
    """Standalone runner for testing fuzzy matching."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fuzzy matching for invoice resolution")
    parser.add_argument("--invoice", required=True, help="Path to invoice JSON")
    parser.add_argument("--min-po-confidence", type=float, default=0.7, help="Minimum PO confidence threshold")
    parser.add_argument("--min-supplier-confidence", type=float, default=0.8, help="Minimum supplier confidence threshold")
    args = parser.parse_args()
    
    result = fuzzy_resolve_invoice_to_po_and_contract(
        args.invoice,
        min_po_confidence=args.min_po_confidence,
        min_supplier_confidence=args.min_supplier_confidence
    )
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
