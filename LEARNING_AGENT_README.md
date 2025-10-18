# ResolveLight Learning Agent

An intelligent learning system that analyzes ResolveLight agent performance and generates optimization plans based on system logs and human feedback.

## 🎯 Overview

The Learning Agent is a standalone system that:
- **Analyzes** system logs to identify learning opportunities
- **Generates** intelligent optimization plans using LLM
- **Collects** human feedback through a web interface
- **Tracks** learning progress and system improvements

## 🏗️ Architecture

```
ResolveLight/
├── learning_agent/           # Core learning agent logic
│   ├── learning_agent.py     # Main learning agent with LLM integration
│   ├── log_analyzer.py       # Log analysis and pattern detection
│   ├── database.py           # SQLite database operations
│   └── __init__.py
├── web_gui/                  # Web interface for human feedback
│   ├── app.py               # Flask web application
│   └── templates/           # HTML templates
├── learning_data/           # SQLite database storage
│   └── learning.db
├── run_learning_agent.py    # Main script to run learning agent
├── test_learning_agent.py   # Test script (no LLM required)
└── requirements_learning.txt # Dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_learning.txt
```

### 2. Set Up API Key (for LLM features)

```bash
export GOOGLE_API_KEY="your_gemini_api_key_here"
# OR
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### 3. Run Learning Agent

```bash
# Full learning analysis with LLM
python run_learning_agent.py

# Test without LLM (log analysis only)
python test_learning_agent.py

# Verbose output
python run_learning_agent.py --verbose
```

### 4. Start Web GUI

```bash
python web_gui/app.py
```

Then open http://localhost:5000 in your browser.

## 📊 Features

### Learning Agent Core
- **Log Analysis**: Automatically analyzes all system logs
- **Pattern Detection**: Identifies recurring issues and inefficiencies
- **LLM Integration**: Uses Gemini to generate intelligent optimization plans
- **Database Storage**: Stores learning records and plans in SQLite

### Web GUI
- **Dashboard**: System overview and statistics
- **Learning Plans**: Review and approve optimization plans
- **Human Feedback**: Submit corrections and expert input
- **Learning Records**: View detailed analysis results

### Learning Plan Types
The LLM can generate various types of optimization plans:
- `prompt_optimization`: Improve agent instructions
- `tool_enhancement`: Modify validation tools
- `new_validation_rule`: Add business logic
- `fuzzy_matching_improvement`: Enhance matching algorithms
- `confidence_threshold_adjustment`: Tune decision thresholds
- `routing_logic_optimization`: Improve queue routing
- `data_validation_enhancement`: Better data quality checks
- `exception_handling_improvement`: Better error handling
- `business_rule_addition`: Add new business rules
- `performance_optimization`: Speed/memory improvements

## 🔍 How It Works

### 1. Log Analysis
The learning agent analyzes:
- `system_logs/exceptions_ledger.log` - Exception patterns
- `system_logs/queue_*.log` - Queue performance issues
- `system_logs/processed_invoices.log` - Rejection rates and patterns
- `system_logs/payments.log` - Payment processing
- `memory/*.jsonl` - Session data

### 2. Learning Opportunity Detection
Identifies patterns such as:
- High rejection rates
- Recurring exception types
- Queue concentration issues
- Low confidence matching
- High-value invoice problems

### 3. LLM Plan Generation
For each learning opportunity, the LLM:
- Analyzes the root cause
- Determines the best optimization strategy
- Provides specific, code-level changes
- Estimates impact and implementation effort

### 4. Human Review
Experts can:
- Review generated learning plans
- Provide feedback on specific cases
- Approve or reject optimization plans
- Add additional context

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
   Solution: Set `GOOGLE_API_KEY` environment variable

2. **Database Error**
   ```
   sqlite3.OperationalError: no such table
   ```
   Solution: Database will auto-create on first run

3. **Web GUI Not Starting**
   ```
   ModuleNotFoundError: No module named 'flask'
   ```
   Solution: Install dependencies with `pip install -r requirements_learning.txt`

### Debug Mode
```bash
export FLASK_ENV=development
python web_gui/app.py
```

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

### LearningAgent Class
```python
from learning_agent import LearningAgent

agent = LearningAgent(repo_root="/path/to/ResolveLight", api_key="your_key")
results = agent.run_learning_analysis()
plans = agent.get_learning_plans()
agent.close()
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
