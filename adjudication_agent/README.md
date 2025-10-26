# Adjudication Agent

## Overview

The Adjudication Agent is a standalone system that reviews exceptions against the learning playbook and makes APPROVED/REJECTED decisions with clear justification.

## Design

The agent follows this workflow:

1. **Load Exceptions**: Parse all exceptions from system logs
2. **Display**: Show numbered list of exceptions for user selection
3. **Load Playbook**: Load and filter the learning playbook entries
4. **Adjudicate**: Use LLM to compare exception against playbook rules
5. **Decision**: Return APPROVED or REJECTED with justification

## Key Components

### Files

- `adjudication_agent.yaml` - ADK agent configuration with detailed instructions
- `exception_parser.py` - Parses exception logs from system_logs directory
- `playbook_loader.py` - Loads and filters learning playbook entries
- `adjudication_tool.py` - Tool for ADK agent integration (for multi-agent use)
- `adjudication_runner.py` - Standalone runner for manual adjudication
- `__init__.py` - Package initialization
- `run_adjudication.sh` - Convenience script to run the agent

### Decision Logic

The agent makes decisions based on three scenarios:

1. **Playbook Rules Match**: 
   - Calculate if exception meets playbook criteria (e.g., thresholds)
   - If criteria match → APPROVED
   - If criteria don't match → REJECTED (explains why it fails)

2. **No Relevant Playbook Rules**:
   - No learned guidance available
   - → REJECTED (original exception stands)

3. **Edge Cases**:
   - Handles partial matches carefully
   - Applies learned rules strictly
   - Never invents rules - only uses playbook

## Usage

### Standalone Mode

```bash
# Option 1: Run directly
python3 adjudication_agent/adjudication_runner.py

# Option 2: Use convenience script
./adjudication_agent/run_adjudication.sh
```

### Workflow

1. Script loads all exceptions from `system_logs/queue_*.log`
2. Displays numbered list with key information
3. User selects an exception by number
4. Agent:
   - Loads the learning playbook
   - Filters entries by exception type
   - Queries LLM with exception and relevant playbook rules
   - Makes decision: APPROVED or REJECTED
   - Provides detailed justification

### Expected Output

```
ADJUDICATION AGENT - Standalone Runner
================================================================================

Loading exceptions from system logs...

EXCEPTIONS FOUND:
================================================================================

1. Exception ID: EXC-6AE46763D4F7
   Type: PRICE_DISCREPANCY
   Invoice: INV-ZEP-2025-100 | PO: PO-2025-305A
   Amount: $6,270.00
   Queue: price_discrepancies

Enter exception number (1-2): 1

Loading adjudication agent and playbook...
Loaded 4 entries from playbook.

ADJUDICATING EXCEPTION...
================================================================================

FINAL JUDGMENT:
==============
DECISION: APPROVED

JUSTIFICATION:
The playbook contains a rule for price discrepancies with documented discount in the notes field.
This exception matches the learned pattern where:
- Invoice contains "notes" field with discount explanation
- Unit price is lower than PO (5% discount in this case)
- Based on Entry 3: The expert approved similar discounts documented in notes

The learned rule states: "Discounts in notes field are acceptable when clearly documented"
Therefore, this exception should be APPROVED.

==============
```

## Integration with ResolveLight

### As Standalone Tool
Currently designed to run independently outside the ResolveLight pipeline.

### Future: As ADK Agent
The agent is configured for ADK integration:
- YAML config with tools reference
- Can be integrated into multi-agent system
- Could be added to `root_agent.yaml` as a sub-agent

## Configuration

### API Key
Set in `.env` file in parent directory:
```
GOOGLE_API_KEY=your_key_here
```

Or as environment variable:
```bash
export GOOGLE_API_KEY=your_key_here
```

### Model
Currently uses `gemini-2.0-flash-exp` (configurable in YAML)

## Testing

To test the adjudication agent:

1. Ensure you have exceptions in `system_logs/` directory
2. Ensure you have playbook entries in `learning_playbooks/learning_playbook.jsonl`
3. Run the agent: `python3 adjudication_agent/adjudication_runner.py`
4. Select an exception and review the decision

## Example Playbook Entry Format

The agent expects playbook entries with:
- `exception_type`: Type of exception (must match exception's EXCEPTION_TYPE)
- `expert_feedback`: Human expert's decision rationale
- `learning_insights`: What was learned
- `corrective_actions`: How the system should handle similar cases

See `learning_playbooks/learning_playbook.jsonl` for examples.

