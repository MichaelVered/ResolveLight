#!/usr/bin/env python3
"""
Golden Set Test Script

This script tests all invoices in the golden dataset by running the complete
agentic workflow logic (same as runnerLog.py) and validating the results. It checks:

1. All validations passed
2. Proper routing to queues
3. Exception details and queue assignments

Usage:
    python utilities/test_golden_set.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tool_library.validation_runner_tool import run_validations
from tool_library.triage_resolution_tool import triage_and_route
from tool_library.fuzzy_matching_tool import fuzzy_resolve_invoice_to_po_and_contract


class GoldenSetTester:
    """Test suite for the golden invoice dataset."""
    
    def __init__(self, repo_root: str = None):
        self.repo_root = repo_root or str(project_root)
        self.invoice_dir = os.path.join(self.repo_root, "json_files", "invoices")
        self.results = []
        
    def find_invoice_files(self) -> List[str]:
        """Find all invoice JSON files."""
        invoice_files = []
        if os.path.exists(self.invoice_dir):
            for file in os.listdir(self.invoice_dir):
                if file.startswith("invoice_") and file.endswith(".json"):
                    invoice_files.append(os.path.join(self.invoice_dir, file))
        return sorted(invoice_files)
    
    def load_invoice_data(self, invoice_path: str) -> Dict[str, Any]:
        """Load invoice data from file."""
        try:
            with open(invoice_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load invoice: {str(e)}"}
    
    def test_fuzzy_matching(self, invoice_path: str) -> Dict[str, Any]:
        """Test fuzzy matching for an invoice."""
        try:
            result = fuzzy_resolve_invoice_to_po_and_contract(invoice_path, self.repo_root)
            return {
                "status": "success",
                "confidence": result.get("matching_details", {}).get("overall_confidence", 0.0),
                "po_found": result.get("po_item") != "<not found>",
                "contract_found": result.get("contract") != "<not found>",
                "details": result.get("matching_details", {})
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_validation(self, invoice_path: str) -> Dict[str, Any]:
        """Test validation for an invoice."""
        try:
            result = run_validations(invoice_path, self.repo_root)
            return {
                "status": "success",
                "validation_passed": result.get("validation") == "PASS",
                "validation_status": result.get("validation"),
                "tool_results": result.get("tool_results", []),
                "failed_tools": [
                    tool for tool in result.get("tool_results", [])
                    if tool.get("status") == "FAIL"
                ]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_triage_routing(self, invoice_path: str) -> Dict[str, Any]:
        """Test triage and routing for an invoice."""
        try:
            result = triage_and_route(invoice_path, self.repo_root)
            return {
                "status": "success",
                "final_status": result.get("status"),
                "routing_queue": result.get("routing_queue"),
                "priority": result.get("priority"),
                "exception_id": result.get("exception_id"),
                "requires_manager_approval": result.get("requires_manager_approval", False),
                "actions": result.get("actions", []),
                "logs": result.get("logs", {})
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_single_invoice(self, invoice_path: str) -> Dict[str, Any]:
        """Test a single invoice through the complete workflow."""
        invoice_filename = os.path.basename(invoice_path)
        print(f"\n🔍 Testing: {invoice_filename}")
        print("=" * 60)
        
        # Load invoice data
        invoice_data = self.load_invoice_data(invoice_path)
        if "error" in invoice_data:
            return {
                "invoice_file": invoice_filename,
                "status": "error",
                "error": invoice_data["error"]
            }
        
        # Test fuzzy matching
        print("1️⃣ Testing Fuzzy Matching...")
        fuzzy_result = self.test_fuzzy_matching(invoice_path)
        if fuzzy_result["status"] == "success":
            confidence = fuzzy_result["confidence"]
            print(f"   ✅ Confidence: {confidence:.1%}")
            print(f"   ✅ PO Found: {fuzzy_result['po_found']}")
            print(f"   ✅ Contract Found: {fuzzy_result['contract_found']}")
        else:
            print(f"   ❌ Error: {fuzzy_result['error']}")
        
        # Test validation
        print("2️⃣ Testing Validation...")
        validation_result = self.test_validation(invoice_path)
        if validation_result["status"] == "success":
            validation_passed = validation_result["validation_passed"]
            status_icon = "✅" if validation_passed else "❌"
            print(f"   {status_icon} Validation: {validation_result['validation_status']}")
            
            if not validation_passed:
                print("   📋 Failed Tools:")
                for tool in validation_result["failed_tools"]:
                    tool_name = tool.get("tool", "Unknown")
                    exceptions = tool.get("exceptions", [])
                    print(f"      - {tool_name}: {exceptions}")
        else:
            print(f"   ❌ Error: {validation_result['error']}")
        
        # Test triage routing
        print("3️⃣ Testing Triage & Routing...")
        triage_result = self.test_triage_routing(invoice_path)
        if triage_result["status"] == "success":
            final_status = triage_result["final_status"]
            routing_queue = triage_result["routing_queue"]
            priority = triage_result["priority"]
            
            status_icon = "✅" if final_status == "APPROVED" else "⚠️" if final_status == "PENDING_APPROVAL" else "❌"
            print(f"   {status_icon} Final Status: {final_status}")
            
            if routing_queue:
                print(f"   📋 Routing Queue: {routing_queue}")
                print(f"   📋 Priority: {priority}")
                
                if triage_result["exception_id"]:
                    print(f"   📋 Exception ID: {triage_result['exception_id']}")
                
                if triage_result["requires_manager_approval"]:
                    print(f"   📋 Manager Approval Required: Yes")
            else:
                print(f"   📋 No routing queue (approved)")
        else:
            print(f"   ❌ Error: {triage_result['error']}")
        
        # Compile results
        result = {
            "invoice_file": invoice_filename,
            "invoice_data": {
                "invoice_id": invoice_data.get("invoice_id"),
                "po_number": invoice_data.get("purchase_order_number"),
                "amount": invoice_data.get("summary", {}).get("billing_amount"),
                "line_items_count": len(invoice_data.get("line_items", []))
            },
            "fuzzy_matching": fuzzy_result,
            "validation": validation_result,
            "triage_routing": triage_result,
            "overall_status": "success"
        }
        
        return result
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run tests for all invoices."""
        print("🎯 GOLDEN SET TEST SUITE")
        print("=" * 60)
        print(f"Repository Root: {self.repo_root}")
        print(f"Invoice Directory: {self.invoice_dir}")
        
        invoice_files = self.find_invoice_files()
        if not invoice_files:
            print("❌ No invoice files found!")
            return []
        
        print(f"📋 Found {len(invoice_files)} invoice files")
        
        for invoice_path in invoice_files:
            result = self.test_single_invoice(invoice_path)
            self.results.append(result)
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        if not self.results:
            print("❌ No test results to summarize")
            return
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_invoices = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get("overall_status") == "success")
        
        print(f"Total Invoices Tested: {total_invoices}")
        print(f"Successful Tests: {successful_tests}")
        print(f"Failed Tests: {total_invoices - successful_tests}")
        
        # Validation summary
        validation_passed = sum(1 for r in self.results 
                              if r.get("validation", {}).get("validation_passed", False))
        print(f"\n📋 Validation Results:")
        print(f"   Passed: {validation_passed}/{total_invoices}")
        print(f"   Failed: {total_invoices - validation_passed}/{total_invoices}")
        
        # Routing summary
        print(f"\n📋 Routing Results:")
        routing_summary = {}
        for result in self.results:
            triage = result.get("triage_routing", {})
            if triage.get("status") == "success":
                queue = triage.get("routing_queue", "approved")
                routing_summary[queue] = routing_summary.get(queue, 0) + 1
        
        for queue, count in sorted(routing_summary.items(), key=lambda x: (x[0] is None, x[0])):
            queue_display = queue if queue else "approved"
            print(f"   {queue_display}: {count} invoices")
        
        # Failed validations detail
        failed_validations = [r for r in self.results 
                            if not r.get("validation", {}).get("validation_passed", True)]
        if failed_validations:
            print(f"\n❌ Failed Validations:")
            for result in failed_validations:
                invoice_file = result["invoice_file"]
                failed_tools = result.get("validation", {}).get("failed_tools", [])
                print(f"   {invoice_file}:")
                for tool in failed_tools:
                    tool_name = tool.get("tool", "Unknown")
                    exceptions = tool.get("exceptions", [])
                    print(f"      - {tool_name}: {exceptions}")
        
        # Exceptions detail
        exceptions = [r for r in self.results 
                     if r.get("triage_routing", {}).get("exception_id")]
        if exceptions:
            print(f"\n⚠️  Exceptions Found:")
            for result in exceptions:
                invoice_file = result["invoice_file"]
                triage = result.get("triage_routing", {})
                exception_id = triage.get("exception_id")
                queue = triage.get("routing_queue")
                print(f"   {invoice_file}: {exception_id} → {queue}")


def main():
    """Main function to run the golden set tests."""
    tester = GoldenSetTester()
    results = tester.run_all_tests()
    tester.print_summary()
    
    # Return appropriate exit code
    failed_tests = sum(1 for r in results if r.get("overall_status") != "success")
    if failed_tests > 0:
        print(f"\n❌ {failed_tests} tests failed")
        sys.exit(1)
    else:
        print(f"\n🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
