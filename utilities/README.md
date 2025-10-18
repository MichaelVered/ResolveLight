# Utilities

This folder contains utility scripts for testing and maintenance of the ResolveLight project.

## Test Scripts

### `test_golden_set.py`

A comprehensive test suite that validates the entire agentic workflow against the golden dataset using the complete runnerLog.py architecture.

**Purpose:**
- Tests all invoices in the golden dataset through the complete agentic workflow
- Uses the actual ADK agents, runners, and sessions (same as runnerLog.py)
- Validates end-to-end user experience instead of individual tools
- Provides detailed reporting on agentic workflow results

**Usage:**
```bash
python utilities/test_golden_set.py
```

**What it tests:**
1. **Complete Agentic Workflow**: Full end-to-end process through ADK agents
2. **Agent Responses**: Captures actual agent status, routing, and exception decisions
3. **Real User Experience**: Tests the same workflow users would experience
4. **Event Logging**: Uses TestEventLogger plugin to capture agent responses

**Technical Architecture:**
- Uses Google ADK (agents, runners, sessions, plugins)
- Integrates with runnerLog.py architecture
- Async/await pattern for proper agentic workflow execution
- Real-time event capture and result parsing

**Example Output:**
```
🎯 GOLDEN SET TEST SUITE (Agentic Workflow)
============================================================
📋 Found 11 invoice files
🤖 Running complete agentic workflow for each invoice...

🔍 Testing: invoice_Aegis_PO-2025-304A.json
============================================================
🤖 Running Agentic Workflow...
   ✅ Final Status: APPROVED
   📋 No routing queue (approved)

🔍 Testing: invoice_Nexus_PO-2025-NEX-001.json
============================================================
🤖 Running Agentic Workflow...
   ⚠️ Final Status: PENDING_APPROVAL
   📋 Routing Queue: high_value_approval
   📋 Priority: high
   📋 Exception ID: EXC-C7E8E2D996E0

📊 TEST SUMMARY (Agentic Workflow)
================================================================================
Total Invoices Tested: 11
Successful Tests: 11
Failed Tests: 0

📋 Agentic Workflow Results:
   Approved: 10
   Pending Approval: 1
   Rejected: 0
   Unknown: 0

📋 Routing Results:
   approved: 10 invoices
   high_value_approval: 1 invoices

⚠️  Exceptions Found:
   invoice_Nexus_PO-2025-NEX-001.json: EXC-C7E8E2D996E0 → high_value_approval

🎉 All tests passed!
```

**Exit Codes:**
- `0`: All tests passed
- `1`: One or more tests failed

**Key Features:**
- **End-to-End Testing**: Tests complete agentic workflow as users experience it
- **Real Agent Responses**: Captures actual agent decisions and routing
- **Event-Driven Architecture**: Uses ADK plugins for real-time result capture
- **Comprehensive Reporting**: Shows agentic workflow results and routing decisions
- **Golden Dataset Validation**: Ensures synthetic data works with agentic workflow

**Benefits over Direct Tool Testing:**
- Tests the actual user experience (agentic workflow)
- Validates complete end-to-end process
- Captures real agent responses and routing decisions
- More realistic testing than direct tool calls
- Tests agent prompts and tool orchestration

This script is essential for:
- Validating changes to the agentic workflow
- Ensuring the golden dataset works with agents
- Testing agent prompts and tool orchestration
- Monitoring the health of the complete system
- Validating end-to-end user experience

## Batch Processing Scripts

### `process_bronze_invoices.py`

A batch processing script that runs the complete agentic workflow across all bronze invoices using the runnerLog.py architecture.

**Purpose:**
- Processes all invoices in the bronze_invoices directory
- Uses the same agentic workflow as the main system
- Provides comprehensive logging and tracking
- Simulates real-world batch processing scenarios

**Usage:**
```bash
python utilities/process_bronze_invoices.py
```

**Features:**
- **Sequential Processing**: Processes each invoice individually through the complete workflow
- **Comprehensive Logging**: Maintains detailed logs for each invoice processed
- **Exception Tracking**: Captures and logs all exceptions and routing decisions
- **Progress Monitoring**: Real-time progress updates during batch processing
- **Audit Trail**: Complete audit trail for compliance and debugging

### `process_bronze_invoices_quiet.py`

A quiet version of the batch processing script designed for automated runs and background processing.

**Purpose:**
- Same functionality as `process_bronze_invoices.py` but with minimal console output
- Ideal for automated runs, cron jobs, or background processing
- Detailed output redirected to log files
- Non-interactive operation

**Usage:**
```bash
python utilities/process_bronze_invoices_quiet.py
```

**Key Differences from Interactive Version:**
- Minimal console output (only essential progress updates)
- Detailed logging to files
- Non-interactive operation
- Suitable for automated environments

## Log Management

### System Logs Preservation

Both batch processing scripts are designed to preserve system logs across multiple runs:

- **System Logs**: Preserved and accumulated across runs (exceptions_ledger.log, payments.log, etc.)
- **Session Memory**: Cleared between runs for clean agent interactions
- **Learning Database**: Cleared between runs for fresh learning data
- **Queue Logs**: Accumulated to track all exceptions and routing decisions

This ensures that:
- Historical data is preserved for analysis
- Each run starts with a clean agent state
- Complete audit trail is maintained
- System performance is optimized
