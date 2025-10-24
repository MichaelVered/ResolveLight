# ResolveLight Learning Agent

An intelligent learning system that analyzes ResolveLight agent performance and generates optimization plans based on system logs and human feedback. The system supports both autonomous learning and human-driven learning workflows with a **playbook-based approach** for reversible business rule management.

## 🎯 Overview

The Learning Agent is a standalone system that:
- **Analyzes** system logs to identify learning opportunities
- **Generates** intelligent optimization plans using LLM
- **Collects** human feedback through enhanced web interface
- **Tracks** learning progress and system improvements
- **Supports** both autonomous and human-driven learning modes
- **Enables** reversible business rule changes without code modifications

## 🏗️ Architecture

```
ResolveLight/
├── learning_agent/                    # Core learning agent logic
│   ├── learning_agent.py             # Autonomous learning agent
│   ├── human_driven_learning_agent.py # Human-driven learning agent
│   ├── log_analyzer.py               # Log analysis and pattern detection
│   ├── exception_parser.py           # Exception log parsing
│   ├── flexible_exception_parser.py  # Flexible exception parsing
│   ├── feedback_llm_service.py       # Enhanced feedback collection
│   ├── database.py                   # SQLite database operations
│   └── __init__.py
├── web_gui/                          # Web interface for human feedback
│   ├── app.py                       # Autonomous learning Flask app
│   ├── human_driven_app.py          # Human-driven learning Flask app
│   └── templates/                   # HTML templates
├── learning_data/                   # SQLite database storage
│   └── learning.db
├── run_learning_agent.py            # Autonomous learning script
├── run_human_driven_learning.py     # Human-driven learning script
├── start_learning_system.sh         # Quick start script
├── test_learning_agent.py           # Test script (no LLM required)
└── requirements_learning.txt        # Dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_learning.txt
```

### 2. Set Up API Key (for LLM features)

Create a `.env` file in the parent directory (`projects/.env`):
```bash
GEMINI_API_KEY="your_gemini_api_key_here"
```

### 3. Choose Learning Mode

#### Option A: Human-Driven Learning (Recommended)
```bash
# Start the human-driven learning system
python run_human_driven_learning.py

# Or use the quick start script
./start_learning_system.sh
```

Then open http://localhost:5001 in your browser.

#### Option B: Autonomous Learning
```bash
# Full learning analysis with LLM
python run_learning_agent.py

# Test without LLM (log analysis only)
python test_learning_agent.py

# Verbose output
python run_learning_agent.py --verbose
```

Then open http://localhost:5000 in your browser.

## 📊 Features

### Learning Agent Core
- **Log Analysis**: Automatically analyzes all system logs
- **Pattern Detection**: Identifies recurring issues and inefficiencies
- **LLM Integration**: Uses Gemini to generate intelligent optimization plans
- **Database Storage**: Stores learning records and plans in SQLite

### Web GUI

#### Human-Driven Learning Interface (Port 5001)
- **Exception Review Dashboard**: Review system exceptions from logs
- **Expert Feedback**: Provide corrections and expert input
- **Learning Plans**: Review and approve optimization plans
- **Review History**: Track expert feedback and corrections

#### Autonomous Learning Interface (Port 5000)
- **Dashboard**: System overview and statistics
- **Learning Plans**: Review and approve optimization plans
- **Human Feedback**: Submit corrections and expert input
- **Learning Records**: View detailed analysis results

### Learning Plan Types
The LLM can generate various types of optimization plans:

**Playbook-Based Plans (Reversible):**
- `exception_override_rules`: Override specific exceptions based on conditions
- `threshold_adjustments`: Modify confidence thresholds and limits
- `routing_optimizations`: Improve queue routing logic
- `business_rule_additions`: Add new validation rules
- `supplier_specific_rules`: Create supplier-specific business logic

**Code-Based Plans (Traditional):**
- `prompt_optimization`: Improve agent instructions
- `tool_enhancement`: Modify validation tools
- `fuzzy_matching_improvement`: Enhance matching algorithms
- `data_validation_enhancement`: Better data quality checks
- `exception_handling_improvement`: Better error handling
- `performance_optimization`: Speed/memory improvements

## 🌟 Key Features

### Human-Driven Learning Benefits
- **Pre-populated Data**: All exception information is automatically extracted and presented
- **Financial Expert Focus**: Designed for non-technical financial experts
- **Structured Workflow**: Clear process from exception review to learning plan approval
- **Data Integrity**: Only presents information explicitly found in logs
- **No Interpretation**: System doesn't attempt to fix or interpret missing data
- **Enhanced Feedback Collection**: LLM-driven Q&A to extract actionable business rules
- **Conversation Tracking**: Multi-turn conversations for complete context gathering
- **Reversible Learning**: Business rules can be modified and rolled back instantly

### Exception Review Process
1. **Automatic Parsing**: System extracts all available data from exception logs
2. **Related Data Lookup**: Finds corresponding invoice files when available
3. **Expert Review**: Financial experts review with complete context
4. **Enhanced Feedback Collection**: LLM generates specific questions to extract business rules
5. **Learning Generation**: LLM creates optimization plans based on expert input
6. **Playbook Integration**: Rules are applied through reversible playbook system

### Data Handling Philosophy
- **Log-Only Data**: Only presents information explicitly stated in log files
- **No Data Interpretation**: System doesn't attempt to fix mismatches or find missing links
- **Transparent Display**: Clearly shows "Not found" when data is unavailable
- **Invoice Priority**: Always attempts to find invoice files (most critical data)

## 🧠 Playbook-Based Learning System

### Overview
The playbook system enables **reversible business rule management** without requiring code modifications. This approach allows domain experts to modify system behavior through a rule-based overlay that can be instantly applied or rolled back.

### Key Benefits
- **🔄 Instant Reversibility**: Rules can be enabled/disabled without code deployment
- **👥 Business User Control**: Domain experts can modify rules directly
- **🛡️ Safe Experimentation**: Test rules on subset of invoices before full deployment
- **📊 Audit Trail**: Complete tracking of rule changes and their impact
- **⚡ Rapid Adaptation**: Respond to business changes without development cycles

### Playbook Rule Types

| Rule Type | Description | Example |
|-----------|-------------|---------|
| **Exception Override** | Override specific exceptions based on conditions | "Allow 15% price increases for Supplier A" |
| **Threshold Adjustment** | Modify confidence thresholds and limits | "Lower confidence threshold to 60% for approved suppliers" |
| **Routing Override** | Change queue routing based on conditions | "Route high-value invoices from trusted suppliers to auto-approval" |
| **Business Rule Addition** | Add new validation logic | "Require manager approval for contracts over $50K" |
| **Supplier-Specific Rules** | Create supplier-specific business logic | "Skip duplicate check for Supplier B recurring invoices" |

### Rule Structure
```json
{
  "rule_id": "RULE-001",
  "name": "Supplier A Price Tolerance",
  "type": "exception_override",
  "status": "active",
  "priority": 100,
  "conditions": {
    "supplier_name": "Supplier A",
    "exception_type": "price_discrepancy",
    "price_increase_percent": {"max": 15.0}
  },
  "action": {
    "override_status": "PASS",
    "reason": "Supplier A allows 15% price increases",
    "confidence": 0.95
  },
  "metadata": {
    "created_by": "expert_john_smith",
    "source_feedback": "FB-456",
    "test_cases": ["INV-001", "INV-002"]
  }
}
```

### Rule Application Process
1. **Exception Generated**: ResolveLight generates exception
2. **Playbook Check**: System checks applicable rules
3. **Rule Evaluation**: Conditions are evaluated against invoice data
4. **Action Application**: Matching rules are applied
5. **Result Override**: Exception status/routing is modified
6. **Audit Logging**: All rule applications are logged

## 🔍 How It Works

### Human-Driven Learning Workflow (Recommended)

1. **Exception Parsing**: System automatically parses exception logs and extracts structured data
2. **Expert Review**: Financial experts review exceptions with all relevant information pre-populated
3. **Enhanced Feedback Collection**: LLM generates specific questions to extract actionable business rules
4. **Conversation Tracking**: Multi-turn Q&A to gather complete context and conditions
5. **Learning Plan Generation**: LLM generates playbook rules based on expert feedback
6. **Plan Review**: Experts review and approve playbook rules before activation
7. **Rule Deployment**: Approved rules are activated in the playbook system
8. **Impact Monitoring**: System tracks rule effectiveness and provides feedback

### Autonomous Learning Workflow

1. **Log Analysis**: System analyzes all logs to identify patterns
2. **Learning Opportunity Detection**: Identifies recurring issues and inefficiencies
3. **LLM Plan Generation**: Generates optimization plans automatically
4. **Human Review**: Experts review and approve plans

### Data Sources
The learning agent analyzes:
- `system_logs/exceptions_ledger.log` - Exception patterns
- `system_logs/queue_*.log` - Queue performance issues
- `system_logs/processed_invoices.log` - Rejection rates and patterns
- `system_logs/payments.log` - Payment processing
- `memory/*.jsonl` - Session data

### Exception Data Extraction
The system extracts structured data from logs including:
- Exception ID, type, and status
- Invoice ID and related PO numbers
- Amounts and supplier information
- Routing reasons and context
- Timestamps and priority levels

## 📝 Usage Examples

### Running Learning Analysis

```bash
# Basic analysis
python run_learning_agent.py

# With custom repository path
python run_learning_agent.py --repo-root /path/to/ResolveLight

# With API key
python run_learning_agent.py --api-key your_api_key_here
```

### Web GUI Navigation

#### Human-Driven Learning Interface (Port 5001)
1. **Exception Review** (`/`): Review system exceptions with pre-populated data
2. **Learning Plans** (`/learning_plans`): Review and approve optimization plans
3. **Feedback History** (`/feedback_history`): Track expert feedback and corrections

#### Autonomous Learning Interface (Port 5000)
1. **Dashboard** (`/`): Overview of system status and recent activity
2. **Learning Plans** (`/learning_plans`): Review and approve optimization plans
3. **Human Feedback** (`/feedback`): Submit corrections and expert input
4. **Learning Records** (`/learning_records`): View detailed analysis results

### Adding Human Feedback

1. Go to the Feedback page
2. Fill out the feedback form:
   - Invoice ID
   - Agent's original decision
   - Your correction
   - Detailed explanation
3. Submit the feedback

### Reviewing Learning Plans

1. Go to the Learning Plans page
2. Click on a plan to view details
3. Review the suggested changes
4. Approve or reject the plan

## 🗄️ Database Schema

### learning_records
- Raw learning opportunities from log analysis
- Source type, file, data, confidence score

### human_feedback
- Expert corrections and feedback
- Invoice ID, original decision, human correction

### learning_plans
- Generated optimization plans
- Plan type, suggested changes, impact analysis

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Required for LLM features
- `FLASK_ENV`: Set to 'development' for debug mode

### Database
- SQLite database stored in `learning_data/learning.db`
- Automatically created and initialized
- Cleared and reloaded on each run (configurable)

## 🧪 Testing

### Test Without LLM
```bash
python test_learning_agent.py
```

This tests:
- Log analysis functionality
- Database operations
- Web GUI components

### Test With LLM
```bash
export GOOGLE_API_KEY="your_key"
python run_learning_agent.py --verbose
```

## 📈 Monitoring

### Key Metrics
- Learning opportunities found
- Learning plans generated
- Human feedback collected
- Plan approval rates
- System improvement impact

### Log Files
- All learning activity is logged
- Database provides audit trail
- Web GUI shows real-time statistics

## 🚨 Troubleshooting

### Common Issues

1. **API Key Error**
   ```
   ValueError: API key required
   ```
   Solution: Create `.env` file in parent directory with `GEMINI_API_KEY="your_key"`

2. **Port Already in Use**
   ```
   Address already in use Port 5001 is in use
   ```
   Solution: Kill existing processes with `pkill -f python` or use different port

3. **Database Error**
   ```
   sqlite3.OperationalError: no such table
   ```
   Solution: Database will auto-create on first run

4. **Web GUI Not Starting**
   ```
   ModuleNotFoundError: No module named 'flask'
   ```
   Solution: Install dependencies with `pip install -r requirements_learning.txt`

5. **Exception Not Found Error**
   ```
   Error loading exception details
   ```
   Solution: Ensure database is synced by refreshing the dashboard

6. **SQLite Threading Error**
   ```
   SQLite objects created in a thread can only be used in that same thread
   ```
   Solution: This is handled automatically in the current implementation

### Debug Mode
```bash
# Human-driven learning (recommended)
export FLASK_ENV=development
python web_gui/human_driven_app.py

# Autonomous learning
export FLASK_ENV=development
python web_gui/app.py
```

### Database Reset
If you need to clear the learning database:
```bash
rm learning_data/learning.db
# Database will be recreated on next run
```

## 🗄️ Database Schema

The learning agent uses SQLite with the following tables:

### `system_exceptions`
Stores parsed exception data from logs:
- `exception_id`, `invoice_id`, `po_number`, `amount`
- `supplier`, `exception_type`, `queue`, `routing_reason`
- `timestamp`, `context`, `status`, `expert_reviewed`
- `expert_feedback`, `expert_name`, `reviewed_at`, `human_correction`

### `human_feedback`
Stores expert feedback and corrections:
- `id`, `created_at`, `exception_id`, `expert_name`
- `feedback_type`, `feedback_text`, `correction_action`
- `priority`, `status`, `reviewed_at`

### `learning_plans`
Stores generated optimization plans:
- `id`, `created_at`, `plan_type`, `title`, `description`
- `source_feedback_ids`, `suggested_changes`, `impact_assessment`
- `implementation_effort`, `status`, `approved_by`, `approved_at`

### `learning_records`
Stores learning analysis results:
- `id`, `created_at`, `analysis_type`, `source_data`
- `findings`, `recommendations`, `confidence_score`
- `status`, `processed_at`

## 🔮 Future Enhancements

### Phase 2 Features
- Incremental log analysis (not full reload)
- Automated learning plan implementation
- A/B testing framework
- Advanced analytics and reporting
- Integration with existing agent system

### Phase 3 Features
- Real-time learning
- Automated deployment pipeline
- Machine learning model training
- Performance monitoring dashboard

## 📚 API Reference

### HumanDrivenLearningAgent Class
```python
from learning_agent import HumanDrivenLearningAgent

agent = HumanDrivenLearningAgent(repo_root="/path/to/ResolveLight")
agent.sync_exceptions_from_logs()
exceptions = agent.get_pending_exceptions()
agent.close()
```

### LearningAgent Class (Autonomous)
```python
from learning_agent import LearningAgent

agent = LearningAgent(repo_root="/path/to/ResolveLight", api_key="your_key")
results = agent.run_learning_analysis()
plans = agent.get_learning_plans()
agent.close()
```

### ExceptionParser Class
```python
from learning_agent import ExceptionParser

parser = ExceptionParser("/path/to/ResolveLight")
exceptions = parser.parse_all_exceptions()
```

### LogAnalyzer Class
```python
from learning_agent import LogAnalyzer

analyzer = LogAnalyzer("/path/to/ResolveLight")
opportunities = analyzer.analyze_all_logs()
overview = analyzer.get_system_overview()
```

### Database Class
```python
from learning_agent import LearningDatabase

db = LearningDatabase("learning_data/learning.db")
record_id = db.store_learning_record(...)
plans = db.get_learning_plans()
exceptions = db.get_pending_exceptions()
db.close()
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the ResolveLight system. See the main project license for details.

---

**Note**: The learning agent has read-only access to the ResolveLight system files. It will not modify any existing code or configurations.
