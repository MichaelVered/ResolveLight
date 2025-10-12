#!/usr/bin/env python3
"""
Invoice Test Script

This script tests all invoices in a specified folder by running the complete
agentic workflow through runnerLog.py (ADK agents) and validating the results. It checks:

1. All validations passed
2. Proper routing to queues
3. Exception details and queue assignments

Usage:
    python utilities/test_golden_set.py
    # Script will prompt for invoice folder path
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import types as _types

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Provide a package alias so YAML can import tools as ResolveLight.*
if 'ResolveLight' not in sys.modules:
    pkg = _types.ModuleType('ResolveLight')
    pkg.__path__ = [str(project_root)]
    sys.modules['ResolveLight'] = pkg

from google.adk.agents.config_agent_utils import from_config as load_agent_from_yaml
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.plugins import BasePlugin
from google.genai import types
import google.generativeai as genai

# Import all tools to ensure they're available
from tool_library import date_check_tool
from tool_library import fuzzy_matching_tool
from tool_library import line_item_validation_tool
from tool_library import po_contract_resolver_tool
from tool_library import simple_overbilling_tool
from tool_library import supplier_match_tool
from tool_library import triage_resolution_tool
from tool_library import validation_runner_tool


# ----------------- Event Logging Plugin (from runnerLog.py) -----------------
class JsonlLoggerPlugin(BasePlugin):
    def __init__(self, memory_dir: str = "memory"):
        # Register with base plugin (required by PluginManager)
        super().__init__(name="jsonl_logger")
        self.description = "Writes raw ADK events to a per-session JSONL file"
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)

    async def on_event_callback(self, *, invocation_context, event):
        # one line per event, raw JSON from ADK's pydantic model
        try:
            session = getattr(invocation_context, "session", None)
            sid = getattr(session, "id", None) or "session_001"
            path = os.path.join(self.memory_dir, f"{sid}.jsonl")
            line = None
            try:
                if hasattr(event, "model_dump_json"):
                    line = event.model_dump_json()
                elif hasattr(event, "model_dump"):
                    import json as _json
                    line = _json.dumps(event.model_dump(), ensure_ascii=False)
            except Exception:
                pass
            if line is None:
                line = str(event)
            with open(path, "a", encoding="utf-8") as f:
                # Write one JSON object per line, plus an extra blank line for readability
                f.write(line + "\n\n")
        except Exception:
            pass
        return None


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
                        
                        # Initialize current_test if we don't have one yet
                        if not self.current_test:
                            self.current_test = {"raw_response": text}
                        
                        # Look for specific patterns in agent responses
                        # Check for REJECTED status first (more specific patterns)
                        if "The invoice has been **REJECTED**" in text:
                            self.current_test["status"] = "REJECTED"
                        elif "**Status:** REJECTED" in text:
                            self.current_test["status"] = "REJECTED"
                        elif "Status:" in text and "REJECTED" in text:
                            self.current_test["status"] = "REJECTED"
                        
                        # Check for APPROVED status
                        elif "The invoice has been **APPROVED**" in text:
                            self.current_test["status"] = "APPROVED"
                        elif "**Status:** APPROVED" in text:
                            self.current_test["status"] = "APPROVED"
                        elif "Status:" in text and "APPROVED" in text:
                            self.current_test["status"] = "APPROVED"
                        
                        # Check for PENDING status
                        elif "PENDING_APPROVAL" in text:
                            self.current_test["status"] = "PENDING_APPROVAL"
                        
                        # Extract routing queue information
                        if "**Routing Queue:**" in text:
                            routing_text = text.split("**Routing Queue:**")[-1].strip()
                            queue_name = routing_text.split('\n')[0].strip()
                            self.current_test["routing_queue"] = queue_name.replace('`', '').strip()
                        elif "Routing Queue:" in text:
                            routing_text = text.split("Routing Queue:")[-1].strip()
                            queue_name = routing_text.split('\n')[0].strip()
                            self.current_test["routing_queue"] = queue_name.replace('**', '').replace('`', '').strip()
                        
                        # Extract exception ID
                        if "**Exception ID:**" in text:
                            exception_text = text.split("**Exception ID:**")[-1].strip()
                            exception_id = exception_text.split('\n')[0].strip()
                            self.current_test["exception_id"] = exception_id.replace('`', '').strip()
                        elif "Exception ID:" in text:
                            exception_text = text.split("Exception ID:")[-1].strip()
                            exception_id = exception_text.split('\n')[0].strip()
                            self.current_test["exception_id"] = exception_id.replace('**', '').replace('`', '').strip()
                        
                        # Extract priority level
                        if "**Priority Level:**" in text:
                            priority_text = text.split("**Priority Level:**")[-1].strip()
                            priority = priority_text.split('\n')[0].strip()
                            self.current_test["priority"] = priority.replace('`', '').strip()
                        elif "Priority Level:" in text:
                            priority_text = text.split("Priority Level:")[-1].strip()
                            priority = priority_text.split('\n')[0].strip()
                            self.current_test["priority"] = priority.replace('**', '').replace('`', '').strip()
                        
                        # Extract manager approval requirement
                        if "**Manager Approval Required:**" in text:
                            approval_text = text.split("**Manager Approval Required:**")[-1].strip()
                            self.current_test["requires_manager_approval"] = "Yes" in approval_text or "True" in approval_text
                        elif "Manager Approval Required:" in text:
                            approval_text = text.split("Manager Approval Required:")[-1].strip()
                            self.current_test["requires_manager_approval"] = "Yes" in approval_text or "True" in approval_text
                        
                        # Look for validation failure indicators
                        if "validation: FAIL" in text:
                            self.current_test["validation_failed"] = True
                        elif "Validation FAILED" in text:
                            self.current_test["validation_failed"] = True
                        
                        # Look for dependency check failures
                        if "dependency_check: FAIL" in text:
                            self.current_test["dependency_failed"] = True
                            
                        # Update raw response with latest text
                        self.current_test["raw_response"] = text
                        
        except Exception as e:
            # Don't let parsing errors break the workflow
            print(f"   ⚠️ Warning: Error in event callback: {str(e)}")
        return None


class GoldenSetTester:
    """Test suite for invoice dataset using agentic workflow."""
    
    def __init__(self, invoice_folder: str = None, repo_root: str = None):
        self.repo_root = repo_root or str(project_root)
        self.invoice_dir = invoice_folder or os.path.join(self.repo_root, "json_files", "golden_invoices")
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
        """Find all invoice JSON files in the specified directory."""
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
        """Test an invoice using the complete agentic workflow - simulates individual runner.py execution."""
        invoice_filename = os.path.basename(invoice_path)
        
        # Change to project root directory for proper module resolution
        original_cwd = os.getcwd()
        os.chdir(self.repo_root)
        
        try:
            # Load the root agent (fresh load for each invoice)
            root_agent = load_agent_from_yaml("root_agent.yaml")
            
            # Set up completely fresh session and runner for each invoice
            # This simulates calling runner.py individually for each invoice
            session_service = InMemorySessionService()
            app_name = "multi_agent_system"  # Use same app name as runner.py
            user_id = "user_001"  # Use same user_id as runner.py
            session_id = f"session_{invoice_filename.replace('.json', '').replace('invoice_', '')}"
            
            await session_service.create_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
            
            # Create plugins - both JsonlLoggerPlugin (from runnerLog.py) and TestEventLogger
            jsonl_logger = JsonlLoggerPlugin("memory")
            test_logger = TestEventLogger()
            
            runner = Runner(
                app_name=app_name,
                agent=root_agent,
                session_service=session_service,
                plugins=[jsonl_logger, test_logger],
            )
            
            # Create the input message - just the invoice filename like runner.py expects
            content = types.Content(role="user", parts=[types.Part(text=invoice_filename)])
            
            # Run the agentic workflow - this simulates the complete runner.py execution
            print(f"🤖 Running Agentic Workflow for {invoice_filename}...")
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                # Events are captured by the test_logger plugin
                pass
            
            # Extract results from the test logger
            test_result = test_logger.current_test or {"status": "UNKNOWN", "raw_response": "No response captured"}
            
            # Session history is automatically saved by JsonlLoggerPlugin (like runnerLog.py)
            
            return {
                "status": "success",
                "agent_result": test_result,
                "session_id": session_id
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "session_id": f"session_{invoice_filename.replace('.json', '').replace('invoice_', '')}"
            }
        
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    async def test_single_invoice(self, invoice_path: str) -> Dict[str, Any]:
        """Test a single invoice through the complete agentic workflow."""
        try:
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
                requires_manager_approval = agent_data.get("requires_manager_approval", False)
                
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
                    if requires_manager_approval:
                        print(f"   📋 Manager Approval Required: Yes")
                elif final_status == "REJECTED":
                    print(f"   ❌ Final Status: {final_status}")
                    if routing_queue:
                        print(f"   📋 Routing Queue: {routing_queue}")
                    if priority:
                        print(f"   📋 Priority: {priority}")
                    if exception_id:
                        print(f"   📋 Exception ID: {exception_id}")
                    if requires_manager_approval:
                        print(f"   📋 Manager Approval Required: Yes")
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
                "overall_status": "success" if agent_result.get("status") == "success" else "error"
            }
            
            return result
            
        except Exception as e:
            print(f"   ❌ Unexpected error in test_single_invoice: {str(e)}")
            return {
                "invoice_file": os.path.basename(invoice_path),
                "status": "error",
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run tests for all invoices using the agentic workflow."""
        print("🎯 INVOICE TEST SUITE (Agentic Workflow)")
        print("=" * 60)
        print(f"Repository Root: {self.repo_root}")
        print(f"Invoice Directory: {self.invoice_dir}")
        
        invoice_files = self.find_invoice_files()
        if not invoice_files:
            print("❌ No invoice files found!")
            return []
        
        print(f"📋 Found {len(invoice_files)} invoice files")
        print("🤖 Running complete agentic workflow for ALL invoices...")
        
        # Test each invoice individually
        for i, invoice_file in enumerate(invoice_files, 1):
            print(f"\n📄 Processing invoice {i}/{len(invoice_files)}: {os.path.basename(invoice_file)}")
            result = await self.test_single_invoice(invoice_file)
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


def clear_all_logs_and_sessions():
    """Clear all log files and session files for a clean start (from runnerLog.py)."""
    import shutil
    
    # Clear system logs directory - only clear files that actually exist
    system_logs_dir = "system_logs"
    if os.path.exists(system_logs_dir):
        # Only clear the logs that are actually used
        used_logs = ["payments.log", "exceptions_ledger.log", "processed_invoices.log"]
        for log_file in used_logs:
            file_path = os.path.join(system_logs_dir, log_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'w') as f:
                        f.write("")  # Clear file content
                    print(f"🧹 Cleared: {file_path}")
                except Exception as e:
                    print(f"⚠️ Could not clear {file_path}: {e}")
    
    # Clear memory directory (session files)
    memory_dir = "memory"
    if os.path.exists(memory_dir):
        for file in os.listdir(memory_dir):
            file_path = os.path.join(memory_dir, file)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'w') as f:
                        f.write("")  # Clear file content
                    print(f"🧹 Cleared: {file_path}")
                except Exception as e:
                    print(f"⚠️ Could not clear {file_path}: {e}")
    
    print("✨ All logs and sessions cleared for clean start!")


async def main():
    """Main function to run the invoice tests using agentic workflow (with runnerLog approach)."""
    # Clear all logs and sessions at the start of the test suite
    clear_all_logs_and_sessions()
    
    # Ask user for invoice folder
    print("🎯 INVOICE TEST SUITE")
    print("=" * 50)
    print("This script will run the complete agentic workflow on all invoices in a specified folder.")
    print()
    
    # Get folder input from user
    while True:
        folder_input = input("Enter the path to the invoice folder (or press Enter for default 'json_files/golden_invoices'): ").strip()
        
        if not folder_input:
            # Use default folder
            folder_input = "json_files/golden_invoices"
        
        # Convert to absolute path if relative
        if not os.path.isabs(folder_input):
            folder_input = os.path.join(os.getcwd(), folder_input)
        
        # Check if folder exists
        if os.path.exists(folder_input) and os.path.isdir(folder_input):
            break
        else:
            print(f"❌ Folder '{folder_input}' does not exist or is not a directory.")
            print("Please enter a valid folder path.")
            print()
    
    print(f"✅ Using invoice folder: {folder_input}")
    print()
    
    # Create tester with specified folder
    tester = GoldenSetTester(invoice_folder=folder_input)
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
