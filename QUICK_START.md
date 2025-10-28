# 🚀 Quick Start Guide - Human-Driven Learning Agent

## **Prerequisites**

1. **API Key**: The system automatically reads from the `.env` file in the project's parent directory
   ```bash
   # Your .env file should contain:
   GEMINI_API_KEY=AIzaSyDD_oBIy1Zj-c9ZVZ0ObtJ0uUFujpvop3w
   ```

2. **Dependencies**: Install required packages
   ```bash
   pip install -r requirements_learning.txt
   ```

## **🚀 Start the System**

### **Option 1: One-Command Start**
```bash
cd ResolveLight
./start_learning_system.sh
```

### **Option 2: Manual Start**

1. **Start Web GUI**:
   ```bash
   python web_gui/human_driven_app.py
   ```

2. **Open Browser**: Go to http://localhost:5001

## **📝 How to Use**

### **Step 1: Add Expert Feedback**
1. Click "Add Expert Feedback" or go to http://localhost:5001/feedback
2. Fill out the form:
   - **Invoice ID**: Specific invoice that was processed incorrectly
   - **Original Decision**: What the system decided (APPROVED/REJECTED)
   - **Your Correction**: What it should have been
   - **Expert Name**: Your name
   - **Feedback Type**: Choose from dropdown
   - **Detailed Feedback**: Explain why the agent was wrong
3. Submit the feedback

### **Step 2: Generate Learning Plans**
```bash
python run_human_driven_learning.py
```

### **Step 3: Review Learning Plans**
1. Go to "Learning Plans" in the web GUI
2. Review each AI-generated optimization plan
3. Approve or reject based on your expertise

### **Step 4: Implement Changes**
- The learning agent provides specific, code-level changes
- Implement approved plans in your ResolveLight system

## **🎯 Workflow Summary**

```
Expert Reviews Exception → Adds Feedback → AI Generates Plan → Expert Approves Plan → Implement Changes
```

## **📊 What You'll See**

- **Dashboard**: Overview of feedback and learning plans
- **Expert Feedback**: Add corrections and explanations  
- **Learning Plans**: Review AI-generated optimization suggestions
- **Feedback History**: See all your expert input

## **💡 Pro Tips**

1. **Be Specific**: Include invoice IDs and detailed explanations
2. **Add Context**: Explain business rules and why the agent was wrong
3. **Multiple Examples**: The more feedback, the better the learning
4. **Review Carefully**: Make sure AI suggestions make sense for your business

## **🔧 Troubleshooting**

- **API Key Error**: Make sure `.env` file exists in the project's parent directory
- **Port 5001 in Use**: Kill other processes or use different port
- **No Learning Plans**: Add expert feedback first

## **📁 Key Files**

- `web_gui/human_driven_app.py` - Web interface (port 5001)
- `run_human_driven_learning.py` - Generate learning plans
- `learning_agent/human_driven_learning_agent.py` - Core learning logic
- `learning_data/learning.db` - SQLite database

The system is now ready to learn from your domain expertise! 🎯
