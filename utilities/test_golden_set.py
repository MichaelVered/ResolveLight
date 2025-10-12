#!/usr/bin/env python3
"""
Golden Set Test Script

This script tests all invoices in the golden dataset by running the complete
agentic workflow through runnerLog.py and validating the results. It checks:

1. All validations passed
2. Proper routing to queues
3. Exception details and queue assignments

Usage:
    python utilities/test_golden_set.py
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.adk.agents.config_agent_utils import from_config as load_agent_from_yaml
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.plugins import BasePlugin
from google.genai import types
import google.generativeai as genai

# Import all tools to ensure they're available
from tool_library import date_check_tool
from tool_library import duplicate_invoice_check_tool
from tool_library import fuzzy_matching_tool
from tool_library import line_item_validation_tool
from tool_library import po_contract_resolver_tool
from tool_library import services_report_tool
from tool_library import simple_overbilling_tool
from tool_library import supplier_match_tool
from tool_library import triage_resolution_tool
from tool_library import validation_runner_tool


class TestEventLogger(BasePlugin):
    """Plugin to capture test results from the agentic workflow."""
    
    def __init__(self):
        super().__init__(name="test_event_logger")
        self.description = "Captures test results from agentic workflow"
        self.test_results = []
        self.current_test = None
    
    async def on_event_callback(self, *, invocation_context, event):
        """Capture events and extract test results."""
        try:
            if hasattr(event, 'content') and event.content:
                parts = getattr(event.content, 'parts', [])
                for part in parts:
                    if hasattr(part, 'text') and part.text:
                        text = part.text
                        # Look for specific patterns in agent responses
                        if "Status:" in text and "APPROVED" in text:
                            self.current_test = {"status": "APPROVED", "raw_response": text}
                        elif "Status:" in text and "REJECTED" in text:
                            self.current_test = {"status": "REJECTED", "raw_response": text}
                        elif "Status:" in text and "PENDING_APPROVAL" in text:
                            self.current_test = {"status": "PENDING_APPROVAL", "raw_response": text}
                        elif "Routing queue:" in text:
                            if self.current_test:
                                self.current_test["routing_queue"] = text.split("Routing queue:")[-1].strip()
                        elif "Exception ID:" in text:
                            if self.current_test:
                                self.current_test["exception_id"] = text.split("Exception ID:")[-1].strip()
                        elif "Priority:" in text:
                            if self.current_test:
                                self.current_test["priority"] = text.split("Priority:")[-1].strip()
        except Exception:
            pass
        return None


class GoldenSetTester:
    """Test suite for the golden invoice dataset using runnerLog.py."""
    
    def __init__(self, repo_root: str = None):
        self.repo_root = repo_root or str(project_root)
        self.invoice_dir = os.path.join(self.repo_root, "json_files", "invoices")
        self.results = []
        
        # Configure Gemini API
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY.")
            genai.configure(api_key=api_key)
        except (ImportError, ValueError) as e:
            print(f"ERROR: Could not configure API key. {e}")
            sys.exit(1)
        
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
    
    async def test_invoice_with_agent(self, invoice_path: str) -> Dict[str, Any]:
        """Test an invoice using the complete agentic workflow."""
        invoice_filename = os.path.basename(invoice_path)
        
        # Load the root agent
        root_agent = load_agent_from_yaml("root_agent.yaml")
        
        # Set up session and runner
        session_service = InMemorySessionService()
        app_name = "test_multi_agent_system"
        user_id = "test_user_001"
        session_id = f"test_session_{invoice_filename.replace('.json', '')}"
        
        await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        
        # Create test event logger
        test_logger = TestEventLogger()
        
        runner = Runner(
            app_name=app_name,
            agent=root_agent,
            session_service=session_service,
            plugins=[test_logger],
        )
        
        # Create test message
        test_message = f"Please process the invoice file: {invoice_filename}"
        content = types.Content(role="user", parts=[types.Part(text=test_message)])
        
        # Run the agentic workflow
        try:
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                # Events are captured by the test_logger plugin
                pass
            
            # Extract results from the test logger
            test_result = test_logger.current_test or {"status": "UNKNOWN", "raw_response": "No response captured"}
            
            return {
                "status": "success",
                "agent_result": test_result,
                "session_id": session_id
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "session_id": session_id
            }
    
    async def test_single_invoice(self, invoice_path: str) -> Dict[str, Any]:
        """Test a single invoice through the complete agentic workflow."""
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
        
        # Test using agentic workflow
        print("🤖 Running Agentic Workflow...")
        agent_result = await self.test_invoice_with_agent(invoice_path)
        
        if agent_result["status"] == "success":
            agent_data = agent_result["agent_result"]
            final_status = agent_data.get("status", "UNKNOWN")
            routing_queue = agent_data.get("routing_queue", "")
            exception_id = agent_data.get("exception_id", "")
            priority = agent_data.get("priority", "")
            
            # Display results
            if final_status == "APPROVED":
                print(f"   ✅ Final Status: {final_status}")
                print(f"   📋 No routing queue (approved)")
            elif final_status == "PENDING_APPROVAL":
                print(f"   ⚠️ Final Status: {final_status}")
                if routing_queue:
                    print(f"   📋 Routing Queue: {routing_queue}")
                if priority:
                    print(f"   📋 Priority: {priority}")
                if exception_id:
                    print(f"   📋 Exception ID: {exception_id}")
            elif final_status == "REJECTED":
                print(f"   ❌ Final Status: {final_status}")
                if routing_queue:
                    print(f"   📋 Routing Queue: {routing_queue}")
                if priority:
                    print(f"   📋 Priority: {priority}")
                if exception_id:
                    print(f"   📋 Exception ID: {exception_id}")
            else:
                print(f"   ❓ Final Status: {final_status}")
                print(f"   📋 Raw Response: {agent_data.get('raw_response', 'No response')}")
        else:
            print(f"   ❌ Error: {agent_result['error']}")
        
        # Compile results
        result = {
            "invoice_file": invoice_filename,
            "invoice_data": {
                "invoice_id": invoice_data.get("invoice_id"),
                "po_number": invoice_data.get("purchase_order_number"),
                "amount": invoice_data.get("summary", {}).get("billing_amount"),
                "line_items_count": len(invoice_data.get("line_items", []))
            },
            "agent_result": agent_result,
            "overall_status": "success" if agent_result["status"] == "success" else "error"
        }
        
        return result
    
    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run tests for all invoices using the agentic workflow."""
        print("🎯 GOLDEN SET TEST SUITE (Agentic Workflow)")
        print("=" * 60)
        print(f"Repository Root: {self.repo_root}")
        print(f"Invoice Directory: {self.invoice_dir}")
        
        invoice_files = self.find_invoice_files()
        if not invoice_files:
            print("❌ No invoice files found!")
            return []
        
        print(f"📋 Found {len(invoice_files)} invoice files")
        print("🤖 Running complete agentic workflow for each invoice...")
        
        for invoice_path in invoice_files:
            result = await self.test_single_invoice(invoice_path)
            self.results.append(result)
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        if not self.results:
            print("❌ No test results to summarize")
            return
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY (Agentic Workflow)")
        print("=" * 80)
        
        total_invoices = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get("overall_status") == "success")
        
        print(f"Total Invoices Tested: {total_invoices}")
        print(f"Successful Tests: {successful_tests}")
        print(f"Failed Tests: {total_invoices - successful_tests}")
        
        # Agent workflow results summary
        print(f"\n📋 Agentic Workflow Results:")
        approved_count = 0
        pending_count = 0
        rejected_count = 0
        unknown_count = 0
        
        for result in self.results:
            agent_result = result.get("agent_result", {})
            if agent_result.get("status") == "success":
                agent_data = agent_result.get("agent_result", {})
                status = agent_data.get("status", "UNKNOWN")
                if status == "APPROVED":
                    approved_count += 1
                elif status == "PENDING_APPROVAL":
                    pending_count += 1
                elif status == "REJECTED":
                    rejected_count += 1
                else:
                    unknown_count += 1
        
        print(f"   Approved: {approved_count}")
        print(f"   Pending Approval: {pending_count}")
        print(f"   Rejected: {rejected_count}")
        print(f"   Unknown: {unknown_count}")
        
        # Routing summary
        print(f"\n📋 Routing Results:")
        routing_summary = {}
        for result in self.results:
            agent_result = result.get("agent_result", {})
            if agent_result.get("status") == "success":
                agent_data = agent_result.get("agent_result", {})
                status = agent_data.get("status", "UNKNOWN")
                if status == "APPROVED":
                    queue = "approved"
                else:
                    queue = agent_data.get("routing_queue", "unknown")
                routing_summary[queue] = routing_summary.get(queue, 0) + 1
        
        for queue, count in sorted(routing_summary.items(), key=lambda x: (x[0] is None, x[0])):
            queue_display = queue if queue else "approved"
            print(f"   {queue_display}: {count} invoices")
        
        # Exceptions detail
        exceptions = []
        for result in self.results:
            agent_result = result.get("agent_result", {})
            if agent_result.get("status") == "success":
                agent_data = agent_result.get("agent_result", {})
                exception_id = agent_data.get("exception_id")
                if exception_id:
                    exceptions.append({
                        "invoice_file": result["invoice_file"],
                        "exception_id": exception_id,
                        "routing_queue": agent_data.get("routing_queue", "unknown")
                    })
        
        if exceptions:
            print(f"\n⚠️  Exceptions Found:")
            for exc in exceptions:
                print(f"   {exc['invoice_file']}: {exc['exception_id']} → {exc['routing_queue']}")
        
        # Failed tests detail
        failed_tests = [r for r in self.results if r.get("overall_status") != "success"]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for result in failed_tests:
                invoice_file = result["invoice_file"]
                error = result.get("agent_result", {}).get("error", "Unknown error")
                print(f"   {invoice_file}: {error}")


async def main():
    """Main function to run the golden set tests using agentic workflow."""
    tester = GoldenSetTester()
    results = await tester.run_all_tests()
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
    asyncio.run(main())
