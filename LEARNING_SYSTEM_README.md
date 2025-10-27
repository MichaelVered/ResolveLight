# ResolveLight Learning from Human Feedback System

## Overview

The Learning from Human Feedback System automatically processes human expert corrections on system exceptions and generates actionable learning insights and corrective actions. This system focuses on cases where humans said "should be approved but was rejected" to improve the system's decision-making capabilities.

## Architecture

### Core Components

1. **Database Extension** (`learning_agent/database.py`)
   - Added learning fields to `system_exceptions` table
   - Automatic trigger mechanism for approval override cases
   - New methods for learning data management

2. **Learning Insights LLM** (`learning_agent/learning_insights_llm.py`)
   - Uses Gemini 2.0 Flash to generate learning insights
   - Creates decision criteria for adjudication agent
   - Extracts semantic patterns (generalizable concepts) and technical patterns (exact matches)
   - Handles comprehensive context analysis including VALIDATION_DETAILS

3. **Learning Playbook Generator** (`learning_agent/learning_playbook_generator.py`)
   - Generates adjudication playbooks for the adjudication agent
   - JSONL format for easy processing
   - Includes validation signatures and decision criteria
   - Statistics and summary capabilities

4. **Feedback Learning Processor** (`learning_agent/feedback_learning_processor.py`)
   - Main orchestrator for learning workflow
   - Processes individual feedback or batch processing
   - Integrates all components

## Database Schema

### New Fields in `system_exceptions` Table

```sql
ALTER TABLE system_exceptions ADD COLUMN learning_insights TEXT;
ALTER TABLE system_exceptions ADD COLUMN decision_criteria TEXT;  -- Changed from corrective_actions
ALTER TABLE system_exceptions ADD COLUMN learning_timestamp TIMESTAMP;
ALTER TABLE system_exceptions ADD COLUMN learning_agent_version VARCHAR(50);
```

## Workflow

### Automatic Processing

1. **Human provides feedback** → `store_human_feedback()` called
2. **System detects approval override** → `original_decision='REJECTED'` AND `human_correction='APPROVED'`
3. **Learning triggered automatically** → `_trigger_learning_processing()` called
4. **LLM generates insights** → Learning insights and corrective actions created
5. **Database updated** → Learning fields populated in exception record
6. **Playbook updated** → Human-readable entry added to playbook

### Manual Processing

```python
from learning_agent.feedback_learning_processor import FeedbackLearningProcessor

processor = FeedbackLearningProcessor()

# Process specific feedback
processor.process_feedback_learning(feedback_id=123)

# Process all pending
result = processor.process_all_pending_learning()

# Get statistics
stats = processor.get_learning_statistics()
```

## Learning Insights Format

The LLM generates comprehensive learning insights for the adjudication agent:

### Learning Insights
- Clear summary of why exception was approved
- Business rules and patterns extracted from human feedback
- Context-specific insights for similar cases

### Decision Criteria
Structured criteria organized by matching type:

```
VALIDATION PATTERN (EXACT MATCH REQUIRED):
- Tool: [same tool]
- Field: [same field]
- FAILED_RULE: [same rule]

ACCEPTABLE RANGES (EXACT VALUES):
- Thresholds and ranges (e.g., discount ≤ 10%)

SEMANTIC PATTERNS (GENERALIZABLE CONCEPTS):
- Generalizable concepts (e.g., "discount with documented explanation")
- Not exact word matches (e.g., "discount" not "loyalty discount")

MUST HAVE:
- Technical conditions (exact match)
- Semantic conditions (conceptual match)

DO NOT APPROVE IF:
- Different validation pattern
- Threshold exceeded
- No reasonable documented explanation
```

### Key Features
- **Validation Signature**: Captures exact technical pattern that must match
- **Semantic Generalization**: Extracts concepts rather than exact wording
- **Key Distinguishing Factors**: Identifies critical matching criteria
- **Approval Conditions**: Lists specific conditions for approval
- **Generalization Warning**: Prevents over-generalization

## Learning Playbook

### Location
`learning_playbooks/learning_playbook.jsonl`

### Format
JSONL (JSON Lines) with human-readable entries:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "exception_id": "EXC-12345",
  "invoice_id": "INV-67890",
  "exception_type": "price_discrepancy",
  "queue": "price_discrepancies",
  "learning_insights": "Price increases up to 15% should be automatically approved for Supplier ABC",
  "corrective_actions": "Priority 1 [HIGH]: Update validation_agent.yaml...",
  "status": "pending_implementation"
}
```

### Human-Readable Format
```bash
python -c "
from learning_agent.learning_playbook_generator import LearningPlaybookGenerator
generator = LearningPlaybookGenerator()
print(generator.format_playbook_for_human())
"
```

## Usage Examples

### Command Line Interface

```bash
# Process all pending learning
python learning_agent/feedback_learning_processor.py --process-all

# Process specific feedback
python learning_agent/feedback_learning_processor.py --feedback-id 123

# Show statistics
python learning_agent/feedback_learning_processor.py --stats

# Test the complete system
python test_learning_system.py
```

### Programmatic Usage

```python
from learning_agent.feedback_learning_processor import FeedbackLearningProcessor
from learning_agent.learning_playbook_generator import LearningPlaybookGenerator

# Initialize processor
processor = FeedbackLearningProcessor()

# Process learning
result = processor.process_all_pending_learning()
print(f"Processed {result['success_count']} feedback entries")

# Generate playbook
generator = LearningPlaybookGenerator()
generator.generate_full_playbook()

# Get playbook summary
summary = generator.get_playbook_summary()
print(f"Playbook has {summary['total_entries']} entries")
```

## Configuration

### Environment Variables
```bash
# Required for LLM functionality
export GOOGLE_API_KEY="your_gemini_api_key"
# OR
export GEMINI_API_KEY="your_gemini_api_key"
```

### Database Migration
The system automatically migrates the database schema when first used. New fields are added to existing tables without data loss.

## File Structure

```
learning_agent/
├── database.py                      # Extended with learning fields
├── learning_insights_llm.py         # LLM service for insights
├── learning_playbook_generator.py   # Playbook generation
├── feedback_learning_processor.py   # Main processor
└── ...

learning_playbooks/
└── learning_playbook.jsonl          # Human-readable playbook

test_learning_system.py              # Complete test suite
LEARNING_SYSTEM_README.md            # This documentation
```

## Testing

Run the complete test suite:

```bash
python test_learning_system.py
```

This tests:
- Database migration
- Learning processor functionality
- Playbook generator
- Complete workflow with sample data

## Future Enhancements

The system is designed for extensibility:

1. **Async Processing** - Move learning processing to background tasks
2. **Learning Validation** - Add human validation of generated insights
3. **Automated Implementation** - Use corrective actions to automatically update system
4. **Learning Analytics** - Track learning effectiveness and system improvement
5. **Multi-Model Support** - Support for different LLM providers
6. **Learning Clustering** - Group similar learning patterns for batch processing

## Troubleshooting

### Common Issues

1. **JSON Parsing Errors**
   - The system handles control characters in LLM responses
   - Check API key configuration if LLM calls fail

2. **Database Migration Issues**
   - Ensure database is writable
   - Check for existing data conflicts

3. **Missing Dependencies**
   - Install required packages: `pip install -r requirements_learning.txt`
   - Ensure Google Generative AI package is installed

### Debug Mode

Enable detailed logging by modifying the processor initialization:

```python
processor = FeedbackLearningProcessor()
# Add debug prints in the code as needed
```

## Contributing

When extending the learning system:

1. Maintain the clean architecture with separate modules
2. Add comprehensive tests for new functionality
3. Update this README with new features
4. Ensure backward compatibility with existing data
5. Follow the established patterns for LLM integration and database operations
