"""
Flask web GUI for the learning agent system.
Provides interfaces for human feedback collection and learning plan review.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from learning_agent.database import LearningDatabase
from learning_agent.log_analyzer import LogAnalyzer


app = Flask(__name__)
app.secret_key = 'learning_agent_secret_key_2024'

# Initialize database
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learning_data", "learning.db")
db = LearningDatabase(db_path)


@app.route('/')
def dashboard():
    """Main dashboard showing system overview and learning plans."""
    # Get database statistics
    stats = db.get_database_stats()
    
    # Get recent learning plans
    recent_plans = db.get_learning_plans()[:10]  # Last 10 plans
    
    # Get recent learning records
    recent_records = db.get_learning_records()[:10]  # Last 10 records
    
    # Get recent human feedback
    recent_feedback = db.get_human_feedback()[:10]  # Last 10 feedback items
    
    return render_template('dashboard.html', 
                         stats=stats,
                         recent_plans=recent_plans,
                         recent_records=recent_records,
                         recent_feedback=recent_feedback)


@app.route('/learning_plans')
def learning_plans():
    """Learning plans management page."""
    status_filter = request.args.get('status', '')
    plans = db.get_learning_plans(status_filter) if status_filter else db.get_learning_plans()
    
    return render_template('learning_plans.html', plans=plans, current_filter=status_filter)


@app.route('/learning_plans/<int:plan_id>')
def learning_plan_detail(plan_id):
    """Detailed view of a specific learning plan."""
    plans = db.get_learning_plans()
    plan = next((p for p in plans if p['id'] == plan_id), None)
    
    if not plan:
        flash('Learning plan not found', 'error')
        return redirect(url_for('learning_plans'))
    
    # Get source learning records
    source_record_ids = plan.get('source_learning_records', [])
    source_records = []
    for record_id in source_record_ids:
        records = db.get_learning_records()
        record = next((r for r in records if r['id'] == record_id), None)
        if record:
            source_records.append(record)
    
    return render_template('learning_plan_detail.html', plan=plan, source_records=source_records)


@app.route('/learning_plans/<int:plan_id>/approve', methods=['POST'])
def approve_learning_plan(plan_id):
    """Approve a learning plan."""
    approved_by = request.form.get('expert_name', 'Unknown Expert')
    db.update_learning_plan_status(plan_id, 'approved', approved_by)
    flash(f'Learning plan {plan_id} approved by {approved_by}', 'success')
    return redirect(url_for('learning_plan_detail', plan_id=plan_id))


@app.route('/learning_plans/<int:plan_id>/reject', methods=['POST'])
def reject_learning_plan(plan_id):
    """Reject a learning plan."""
    reason = request.form.get('rejection_reason', 'No reason provided')
    db.update_learning_plan_status(plan_id, 'rejected')
    flash(f'Learning plan {plan_id} rejected: {reason}', 'warning')
    return redirect(url_for('learning_plan_detail', plan_id=plan_id))


@app.route('/feedback')
def feedback():
    """Human feedback collection page."""
    # Get recent processed invoices for feedback
    recent_records = db.get_learning_records()[:20]
    
    return render_template('feedback.html', recent_records=recent_records)


@app.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    """Submit human feedback."""
    try:
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
            'additional_notes': request.form.get('additional_notes', '')
        }
        
        # Store feedback
        feedback_id = db.store_human_feedback(
            invoice_id=invoice_id,
            original_decision=original_decision,
            human_correction=human_correction,
            routing_queue=routing_queue,
            feedback_text=feedback_text,
            expert_name=expert_name,
            feedback_type=feedback_type,
            supporting_evidence=supporting_evidence
        )
        
        flash(f'Feedback submitted successfully (ID: {feedback_id})', 'success')
        return redirect(url_for('feedback'))
        
    except Exception as e:
        flash(f'Error submitting feedback: {str(e)}', 'error')
        return redirect(url_for('feedback'))


@app.route('/learning_records')
def learning_records():
    """Learning records page."""
    status_filter = request.args.get('status', '')
    records = db.get_learning_records(status_filter) if status_filter else db.get_learning_records()
    
    return render_template('learning_records.html', records=records, current_filter=status_filter)


@app.route('/learning_records/<int:record_id>')
def learning_record_detail(record_id):
    """Detailed view of a specific learning record."""
    records = db.get_learning_records()
    record = next((r for r in records if r['id'] == record_id), None)
    
    if not record:
        flash('Learning record not found', 'error')
        return redirect(url_for('learning_records'))
    
    # Get related human feedback
    related_feedback = db.get_human_feedback(record_id)
    
    return render_template('learning_record_detail.html', record=record, related_feedback=related_feedback)


@app.route('/api/learning_records/<int:record_id>/feedback', methods=['POST'])
def add_feedback_to_record(record_id):
    """Add feedback to a specific learning record."""
    try:
        data = request.get_json()
        
        feedback_id = db.store_human_feedback(
            invoice_id=data.get('invoice_id', ''),
            original_decision=data.get('original_decision', ''),
            human_correction=data.get('human_correction', ''),
            routing_queue=data.get('routing_queue', ''),
            feedback_text=data.get('feedback_text', ''),
            expert_name=data.get('expert_name', ''),
            feedback_type=data.get('feedback_type', ''),
            supporting_evidence=data.get('supporting_evidence', {}),
            learning_record_id=record_id
        )
        
        return jsonify({'success': True, 'feedback_id': feedback_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint for database statistics."""
    stats = db.get_database_stats()
    return jsonify(stats)


@app.route('/api/learning_plans')
def api_learning_plans():
    """API endpoint for learning plans."""
    status = request.args.get('status', '')
    plans = db.get_learning_plans(status) if status else db.get_learning_plans()
    return jsonify(plans)


@app.route('/api/learning_records')
def api_learning_records():
    """API endpoint for learning records."""
    status = request.args.get('status', '')
    records = db.get_learning_records(status) if status else db.get_learning_records()
    return jsonify(records)


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


if __name__ == '__main__':
    print("🌐 Starting Learning Agent Web GUI...")
    print("📊 Dashboard: http://localhost:5000")
    print("📝 Learning Plans: http://localhost:5000/learning_plans")
    print("💬 Feedback: http://localhost:5000/feedback")
    print("📋 Learning Records: http://localhost:5000/learning_records")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
