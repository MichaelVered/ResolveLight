# Enhanced Human Feedback Collection System

## Overview

The Enhanced Human Feedback Collection System is designed to collect high-quality, actionable feedback from domain experts through an intelligent LLM-guided questioning process. This system focuses on extracting concrete business rules, thresholds, and conditions that can be used to improve the ResolveLight system's decision-making capabilities.

## Key Features

### 1. **LLM-Guided Questioning**
- Automatically generates specific, actionable questions based on human feedback
- Focuses on extracting concrete business rules and thresholds
- Asks about scope of application, conditions, exceptions, and business logic
- Guides experts to provide actionable information

### 2. **Conversation Management**
- Tracks complete feedback conversations with unique conversation IDs
- Stores initial feedback, LLM questions, human responses, and summaries
- Maintains conversation status (active, ready_for_learning, completed)
- Links related feedback items in conversation threads

### 3. **Intelligent Summarization**
- Summarizes complete feedback conversations for the next learning stage
- Extracts business rules, system improvements, and actionable changes
- Assesses feedback quality and completeness
- Prepares structured data for learning plan generation

### 4. **Enhanced Database Schema**
- New fields for conversation tracking and LLM interaction
- Support for multi-turn conversations
- Quality scoring and status tracking
- Structured storage of questions, responses, and summaries

## System Architecture

### Database Schema

The `human_feedback` table has been enhanced with new fields:

```sql
-- New fields added to human_feedback table
conversation_id VARCHAR(100)           -- Unique conversation identifier
is_initial_feedback BOOLEAN            -- Whether this is the initial feedback
parent_feedback_id INTEGER             -- Links to parent feedback in conversation
llm_questions TEXT                     -- JSON array of LLM-generated questions
human_responses TEXT                   -- JSON array of human responses
feedback_summary TEXT                  -- JSON summary of the conversation
conversation_status VARCHAR(20)        -- active, ready_for_learning, completed
quality_score REAL                     -- 0.0-1.0 quality assessment
```

### LLM Service

The `FeedbackLLMService` provides two main functions:

1. **Question Generation** (`generate_feedback_questions`)
   - Analyzes human feedback to identify areas needing clarification
   - Generates 3-5 specific, actionable questions
   - Focuses on extracting concrete business rules and thresholds

2. **Conversation Summarization** (`summarize_feedback_conversation`)
   - Summarizes complete feedback conversations
   - Extracts business rules and system improvements
   - Assesses feedback quality and completeness
   - Prepares structured data for learning plan generation

### Web Interface

The enhanced feedback form (`enhanced_feedback.html`) provides:

- **Initial Feedback Form**: Standard feedback collection
- **LLM Chat Interface**: Dynamic questioning and response collection
- **Conversation Tracking**: Visual chat-like interface for multi-turn conversations
- **Summary Display**: Shows extracted business rules and system improvements

## Usage Flow

### 1. Initial Feedback Submission
1. Expert fills out the initial feedback form
2. System generates a unique conversation ID
3. LLM analyzes the feedback and generates specific questions
4. Questions are displayed in a chat interface

### 2. LLM-Guided Questioning
1. Expert answers each question in sequence
2. System stores responses and tracks conversation progress
3. Expert can skip remaining questions if desired
4. All responses are linked to the conversation

### 3. Conversation Summarization
1. LLM summarizes the complete conversation
2. Extracts business rules, thresholds, and system improvements
3. Assesses feedback quality and completeness
4. Stores structured summary for next learning stage

### 4. Completion
1. Expert reviews the summary
2. Marks conversation as completed
3. Feedback is ready for learning plan generation (next stage)

## API Endpoints

### New Endpoints

- `POST /feedback/submit_initial` - Submit initial feedback and generate questions
- `POST /feedback/submit_response` - Submit human response to LLM questions
- `POST /feedback/generate_summary` - Generate conversation summary
- `POST /feedback/complete` - Mark conversation as completed

### Updated Endpoints

- `GET /feedback` - Now uses enhanced feedback template
- `GET /feedback_history` - Shows conversation status and quality scores

## Database Methods

### New Methods in LearningDatabase

- `get_feedback_conversation(conversation_id)` - Get all items in a conversation
- `get_active_conversations()` - Get all active feedback conversations
- `update_feedback_conversation()` - Update conversation with LLM data

### Enhanced Methods

- `store_human_feedback()` - Now supports conversation tracking and LLM data

## Configuration

### Environment Variables

The system requires the same API key configuration as the existing learning agent:

```bash
GOOGLE_API_KEY=your_gemini_api_key
# or
GEMINI_API_KEY=your_gemini_api_key
```

### Database Migration

The system automatically runs database migrations to add the new fields. No manual intervention is required.

## Testing

Run the test script to verify the system works correctly:

```bash
python test_enhanced_feedback.py
```

This will test:
- Database migrations
- LLM service functionality
- Web route configuration

## Next Steps

This enhanced feedback collection system is designed to work with the next stage of the learning system, which will:

1. Use the summarized feedback to generate learning plans
2. Extract specific business rules and implement system improvements
3. Apply the learned rules to improve future decision-making

## Files Modified

### New Files
- `learning_agent/feedback_llm_service.py` - LLM service for questioning and summarization
- `web_gui/templates/enhanced_feedback.html` - Enhanced feedback form with chat interface
- `test_enhanced_feedback.py` - Test script for the enhanced system
- `ENHANCED_FEEDBACK_README.md` - This documentation

### Modified Files
- `learning_agent/database.py` - Enhanced schema and new methods
- `web_gui/human_driven_app.py` - New routes and updated functionality

## Key Benefits

1. **Higher Quality Feedback**: LLM-guided questioning extracts more actionable information
2. **Structured Data**: Conversations are properly organized and summarized
3. **Better Learning**: Rich, structured feedback enables better learning plan generation
4. **User Experience**: Chat-like interface makes the process more engaging
5. **Scalability**: Conversation tracking supports complex multi-turn interactions

The enhanced feedback system provides a solid foundation for the next stage of the learning system, ensuring that human expertise is captured in a structured, actionable format that can drive meaningful system improvements.
