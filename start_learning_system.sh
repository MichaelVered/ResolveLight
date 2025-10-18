#!/bin/bash

# ResolveLight Learning Agent Startup Script
# This script starts the human-driven learning agent and web GUI

echo "🚀 Starting ResolveLight Human-Driven Learning Agent System"
echo "=========================================================="
echo "This system learns from expert feedback, not autonomous log analysis."
echo ""

# Check if .env file exists
if [ -f "../.env" ]; then
    echo "✅ Found .env file with API key"
    echo ""
    
    # Run human-driven learning agent
    python run_human_driven_learning.py --verbose
    
    echo ""
    echo "🌐 Starting Human-Driven Web GUI..."
    python web_gui/human_driven_app.py
else
    echo "⚠️  Warning: No .env file found in projects directory."
    echo "   Please create ../.env with your GEMINI_API_KEY"
    echo "   Example: GEMINI_API_KEY=your_api_key_here"
    echo ""
    echo "   Running in test mode (no LLM features)..."
    echo ""
    
    # Run test version
    python test_learning_agent.py
    
    echo ""
    echo "🌐 Starting Web GUI..."
    python web_gui/human_driven_app.py
fi
