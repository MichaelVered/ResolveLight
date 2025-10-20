"""
Human-Driven Learning Agent Web GUI
Focuses on expert feedback collection and learning plan generation.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from learning_agent.database import LearningDatabase
from learning_agent.flexible_database import FlexibleDatabase
from learning_agent.flexible_exception_parser import FlexibleExceptionParser
from learning_agent.human_driven_learning_agent import HumanDrivenLearningAgent
from learning_agent.feedback_llm_service import FeedbackLLMService

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from projects directory
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
    load_dotenv(env_path)
except ImportError:
    pass


app = Flask(__name__)
app.secret_key = 'learning_agent_secret_key_2024'

# Database path - create connections only when needed
db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning_data", "learning.db"))


@app.route('/')
def dashboard():
    """Main dashboard showing system exceptions for expert review."""
    # Create a new database connection for this request
    local_db = LearningDatabase(db_path)
    
    # Sync exceptions from logs first
    try:
        synced_count = local_db.sync_exceptions_from_logs()
        if synced_count > 0:
            print(f"Synced {synced_count} exceptions from logs")
    except Exception as e:
        print(f"Error syncing exceptions: {e}")
    
    # Get database statistics
    stats = local_db.get_database_stats()
    
    # Get pending exceptions for review
    pending_exceptions = local_db.get_pending_exceptions()
    
    # Get active feedback conversations
    active_conversations = local_db.get_active_conversations()[:10]  # Last 10 conversations
    
    local_db.close()
    
    return render_template('human_driven_dashboard.html', 
                         stats=stats, 
                         pending_exceptions=pending_exceptions, 
                         active_conversations=active_conversations)


@app.route('/feedback')
def feedback():
    """Human feedback collection page - the main entry point."""
    # Create a new database connection for this request
    local_db = LearningDatabase(db_path)
    
    # Get recent feedback for context
    recent_feedback = local_db.get_human_feedback()[:20]
    
    local_db.close()
    
    return render_template('enhanced_feedback.html', recent_feedback=recent_feedback)


@app.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    """Submit human feedback - this is the core learning input."""
    try:
        # Create a new database connection for this request
        local_db = LearningDatabase(db_path)
        
        invoice_id = request.form.get('invoice_id', '')
        original_decision = request.form.get('original_decision', '')
        human_correction = request.form.get('human_correction', '')
        routing_queue = request.form.get('routing_queue', '')
        feedback_text = request.form.get('feedback_text', '')
        expert_name = request.form.get('expert_name', '')
        feedback_type = request.form.get('feedback_type', '')
        
        # Get supporting evidence
        supporting_evidence = {
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', ''),
            'additional_notes': request.form.get('additional_notes', ''),
            'expert_confidence': request.form.get('expert_confidence', 'high')
        }
        
        # Store feedback
        feedback_id = local_db.store_human_feedback(
            invoice_id=invoice_id,
            original_decision=original_decision,
            human_correction=human_correction,
            routing_queue=routing_queue,
            feedback_text=feedback_text,
            expert_name=expert_name,
            feedback_type=feedback_type,
            supporting_evidence=supporting_evidence
        )
        
        local_db.close()
        
        flash(f'Expert feedback submitted successfully (ID: {feedback_id})', 'success')
        return redirect(url_for('feedback'))
        
    except Exception as e:
        flash(f'Error submitting feedback: {str(e)}', 'error')
        return redirect(url_for('feedback'))


@app.route('/feedback/submit_initial', methods=['POST'])
def submit_initial_feedback():
    """Submit initial feedback and generate LLM questions."""
    try:
        # Create a new database connection for this request
        local_db = LearningDatabase(db_path)
        
        # Generate conversation ID
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        
        invoice_id = request.form.get('invoice_id', '')
        original_decision = request.form.get('original_decision', '')
        human_correction = request.form.get('human_correction', '')
        routing_queue = request.form.get('routing_queue', '')
        feedback_text = request.form.get('feedback_text', '')
        expert_name = request.form.get('expert_name', '')
        feedback_type = request.form.get('feedback_type', '')
        
        # Get supporting evidence
        supporting_evidence = {
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', ''),
            'additional_notes': request.form.get('additional_notes', ''),
            'expert_confidence': request.form.get('expert_confidence', 'high')
        }
        
        # Store initial feedback
        feedback_id = local_db.store_human_feedback(
            invoice_id=invoice_id,
            original_decision=original_decision,
            human_correction=human_correction,
            routing_queue=routing_queue,
            feedback_text=feedback_text,
            expert_name=expert_name,
            feedback_type=feedback_type,
            supporting_evidence=supporting_evidence,
            conversation_id=conversation_id,
            is_initial_feedback=True
        )
        
        # Generate LLM questions
        llm_service = FeedbackLLMService()
        feedback_data = {
            'invoice_id': invoice_id,
            'original_agent_decision': original_decision,
            'human_correction': human_correction,
            'routing_queue': routing_queue,
            'feedback_text': feedback_text,
            'expert_name': expert_name,
            'feedback_type': feedback_type
        }
        
        llm_result = llm_service.generate_feedback_questions(feedback_data)
        questions = llm_result.get('questions', [])
        
        # Store LLM questions
        if questions:
            local_db.update_feedback_conversation(
                feedback_id=feedback_id,
                llm_questions=json.dumps(questions)
            )
        
        local_db.close()
        llm_service.close()
        
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'feedback_id': feedback_id,
            'questions': questions,
            'reasoning': llm_result.get('reasoning', ''),
            'expected_outcome': llm_result.get('expected_outcome', '')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/feedback/submit_response', methods=['POST'])
def submit_human_response():
    """Submit human response to LLM questions."""
    try:
        data = request.get_json()
        
        local_db = LearningDatabase(db_path)
        
        # Get the conversation
        conversation = local_db.get_feedback_conversation(data['conversation_id'])
        if not conversation:
            return jsonify({'success': False, 'message': 'Conversation not found'}), 404
        
        # Store the human response
        response_id = local_db.store_human_feedback(
            invoice_id=conversation[0]['invoice_id'],
            original_decision=conversation[0]['original_agent_decision'],
            human_correction=conversation[0]['human_correction'],
            routing_queue=conversation[0]['routing_queue'],
            feedback_text=data['response'],
            expert_name=conversation[0]['expert_name'],
            feedback_type='follow_up_response',
            conversation_id=data['conversation_id'],
            is_initial_feedback=False,
            parent_feedback_id=data['feedback_id']
        )
        
        local_db.close()
        
        return jsonify({
            'success': True,
            'response_id': response_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/feedback/generate_summary', methods=['POST'])
def generate_feedback_summary():
    """Generate summary of the feedback conversation."""
    try:
        data = request.get_json()
        
        llm_service = FeedbackLLMService()
        summary_result = llm_service.summarize_feedback_conversation(data['conversation_id'])
        
        if 'error' in summary_result:
            return jsonify({
                'success': False,
                'message': summary_result['error']
            }), 500
        
        # Store the summary
        local_db = LearningDatabase(db_path)
        conversation = local_db.get_feedback_conversation(data['conversation_id'])
        if conversation:
            # Update the initial feedback with the summary
            local_db.update_feedback_conversation(
                feedback_id=conversation[0]['id'],
                feedback_summary=json.dumps(summary_result),
                conversation_status='ready_for_learning'
            )
        
        local_db.close()
        llm_service.close()
        
        # Format summary for display
        summary_text = f"""
        <strong>Business Rules Extracted:</strong> {len(summary_result.get('business_rules', []))}<br>
        <strong>System Improvements:</strong> {len(summary_result.get('system_improvements', []))}<br>
        <strong>Overall Quality:</strong> {summary_result.get('feedback_quality', {}).get('overall_quality', 'Unknown')}<br>
        <br>
        <strong>Summary:</strong><br>
        {summary_result.get('summary', 'No summary available')}
        """
        
        return jsonify({
            'success': True,
            'summary': summary_text,
            'full_summary': summary_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/feedback/complete', methods=['POST'])
def complete_feedback_conversation():
    """Mark feedback conversation as completed."""
    try:
        data = request.get_json()
        
        local_db = LearningDatabase(db_path)
        conversation = local_db.get_feedback_conversation(data['conversation_id'])
        
        if conversation:
            local_db.update_feedback_conversation(
                feedback_id=conversation[0]['id'],
                conversation_status='completed'
            )
        
        local_db.close()
        
        return jsonify({
            'success': True,
            'message': 'Feedback conversation completed successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# Learning plan generation removed - will be implemented in next stage


# Learning plans routes removed - will be implemented in next stage


@app.route('/feedback_history')
def feedback_history():
    """View all human feedback history."""
    local_db = LearningDatabase(db_path)
    feedback_items = local_db.get_human_feedback()
    local_db.close()
    
    return render_template('human_driven_feedback_history.html', feedback_items=feedback_items)


@app.route('/api/stats')
def api_stats():
    """API endpoint for database statistics."""
    local_db = LearningDatabase(db_path)
    stats = local_db.get_database_stats()
    local_db.close()
    return jsonify(stats)


@app.template_filter('json_pretty')
def json_pretty(value):
    """Jinja2 filter to pretty-print JSON."""
    if isinstance(value, str):
        try:
            return json.dumps(json.loads(value), indent=2)
        except:
            return value
    return json.dumps(value, indent=2)


@app.template_filter('datetime_format')
def datetime_format(value):
    """Jinja2 filter to format datetime."""
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return value
    return value


@app.route('/sync_exceptions', methods=['POST'])
def sync_exceptions():
    """Sync exceptions from log files to database."""
    try:
        local_db = LearningDatabase(db_path)
        synced_count = local_db.sync_exceptions_from_logs()
        local_db.close()
        
        return jsonify({
            'success': True,
            'count': synced_count,
            'message': f'Synced {synced_count} exceptions from logs'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/exception/<exception_id>')
def get_exception(exception_id):
    """Get details of a specific exception."""
    try:
        local_db = LearningDatabase(db_path)
        exception = local_db.get_exception_by_id(exception_id)
        
        if exception:
            # Get related data (invoice, PO, contract)
            related_data = local_db.get_related_data(exception['invoice_id'])
            local_db.close()
            
            return jsonify({
                'success': True,
                'exception': exception,
                'related_data': related_data
            })
        else:
            local_db.close()
            return jsonify({
                'success': False,
                'message': 'Exception not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/submit_exception_review', methods=['POST'])
def submit_exception_review():
    """Submit expert review for an exception."""
    try:
        data = request.get_json()
        
        local_db = LearningDatabase(db_path)
        
        # Update the exception with expert review
        success = local_db.update_exception_review(
            exception_id=data['exception_id'],
            expert_name=data['expert_name'],
            expert_feedback=data['expert_feedback'],
            human_correction=data.get('human_correction', 'APPROVED')
        )
        
        # Also store as human feedback for learning and trigger enhanced feedback flow
        if success:
            # Generate conversation ID for enhanced feedback
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            
            # Store initial feedback
            expert_decision = data.get('expert_decision', 'APPROVE')
            original_decision = 'REJECTED' if expert_decision == 'REJECT' else 'APPROVED'
            human_correction = data.get('human_correction', expert_decision)
            
            feedback_id = local_db.store_human_feedback(
                invoice_id=data.get('invoice_id', ''),
                original_decision=original_decision,
                human_correction=human_correction,
                routing_queue=data.get('queue', ''),
                feedback_text=data['expert_feedback'],
                expert_name=data['expert_name'],
                feedback_type='exception_correction',
                conversation_id=conversation_id,
                is_initial_feedback=True
            )
            
            # Generate LLM questions for enhanced feedback
            llm_service = FeedbackLLMService()
            feedback_data = {
                'invoice_id': data.get('invoice_id', ''),
                'original_agent_decision': original_decision,
                'human_correction': human_correction,
                'routing_queue': data.get('queue', ''),
                'feedback_text': data['expert_feedback'],
                'expert_name': data['expert_name'],
                'feedback_type': 'exception_correction'
            }
            
            llm_result = llm_service.generate_feedback_questions(feedback_data)
            questions = llm_result.get('questions', [])
            
            # Store LLM questions
            if questions:
                local_db.update_feedback_conversation(
                    feedback_id=feedback_id,
                    llm_questions=json.dumps(questions)
                )
            
            llm_service.close()
            
            # Return enhanced feedback data
            return jsonify({
                'success': True,
                'message': 'Exception review submitted successfully!',
                'enhanced_feedback': True,
                'conversation_id': conversation_id,
                'feedback_id': feedback_id,
                'questions': questions,
                'reasoning': llm_result.get('reasoning', ''),
                'expected_outcome': llm_result.get('expected_outcome', '')
            })
        
        local_db.close()
        
        # This code will never be reached due to the return above
        # Keeping it for fallback in case the enhanced feedback flow fails
        return jsonify({
            'success': True,
            'message': 'Exception review submitted successfully'
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# Flexible Exception Endpoints
@app.route('/flexible_exceptions')
def flexible_exceptions():
    """Get flexible exceptions for review."""
    try:
        local_flexible_db = FlexibleDatabase(db_path)
        exceptions = local_flexible_db.get_pending_flexible_exceptions()
        stats = local_flexible_db.get_flexible_database_stats()
        local_flexible_db.close()
        
        return render_template('flexible_exceptions.html', 
                             exceptions=exceptions, 
                             stats=stats)
    except Exception as e:
        return f"Error loading flexible exceptions: {str(e)}", 500


@app.route('/flexible_exception/<exception_id>')
def get_flexible_exception(exception_id):
    """Get details of a specific flexible exception."""
    try:
        local_flexible_db = FlexibleDatabase(db_path)
        exception = local_flexible_db.get_flexible_exception_by_id(exception_id)
        
        if exception:
            # Get related data (reuse existing logic)
            local_db = LearningDatabase(db_path)
            related_data = local_db.get_related_data(exception['invoice_id'])
            local_db.close()
            local_flexible_db.close()
            
            return jsonify({
                'success': True,
                'exception': exception,
                'related_data': related_data
            })
        else:
            local_flexible_db.close()
            return jsonify({
                'success': False,
                'message': 'Exception not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/submit_flexible_exception_review', methods=['POST'])
def submit_flexible_exception_review():
    """Submit expert review for a flexible exception."""
    try:
        data = request.get_json()
        exception_id = data.get('exception_id')
        expert_name = data.get('expert_name')
        expert_feedback = data.get('expert_feedback')
        human_correction = data.get('human_correction')
        
        if not all([exception_id, expert_name, expert_feedback]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        local_flexible_db = FlexibleDatabase(db_path)
        success = local_flexible_db.update_flexible_exception_review(
            exception_id, expert_name, expert_feedback, human_correction)
        local_flexible_db.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Exception review submitted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update exception review'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/sync_flexible_exceptions', methods=['POST'])
def sync_flexible_exceptions():
    """Sync flexible exceptions from logs."""
    try:
        local_flexible_db = FlexibleDatabase(db_path)
        synced_count = local_flexible_db.sync_flexible_exceptions_from_logs()
        local_flexible_db.close()
        
        return jsonify({
            'success': True,
            'message': f'Synced {synced_count} flexible exceptions from logs',
            'synced_count': synced_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/exception_schema_analysis')
def exception_schema_analysis():
    """Get exception schema analysis."""
    try:
        local_flexible_db = FlexibleDatabase(db_path)
        analysis = local_flexible_db.get_exception_schema_analysis()
        local_flexible_db.close()
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


if __name__ == '__main__':
    print("🌐 Starting Human-Driven Learning Agent Web GUI...")
    print("📊 Dashboard: http://localhost:5001")
    print("💬 Expert Feedback: http://localhost:5001/feedback")
    print("📊 Active Conversations: http://localhost:5001/feedback")
    print("📋 Feedback History: http://localhost:5001/feedback_history")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
