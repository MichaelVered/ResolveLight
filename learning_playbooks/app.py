"""
Flask web GUI for viewing and managing learning playbook entries.
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from parser import parse_learning_playbook, save_to_jsonl, load_from_jsonl

app = Flask(__name__)
app.secret_key = 'learning_playbook_secret_key_2024'

# Paths
BASE_DIR = Path(__file__).parent
FORMATTED_FILE = BASE_DIR / 'learning_playbook_formatted.txt'
JSONL_FILE = BASE_DIR / 'learning_playbook.jsonl'


def get_learning_entries():
    """Load learning entries from JSONL file."""
    return load_from_jsonl(str(JSONL_FILE))


def sync_from_formatted():
    """Sync learning entries from formatted text file."""
    try:
        entries = parse_learning_playbook(str(FORMATTED_FILE))
        save_to_jsonl(entries, str(JSONL_FILE))
        return entries
    except Exception as e:
        raise Exception(f"Error syncing from formatted file: {str(e)}")


@app.route('/')
def dashboard():
    """Main dashboard showing all learning entries."""
    entries = get_learning_entries()
    
    # Get statistics
    stats = {
        'total_entries': len(entries),
        'active_entries': len([e for e in entries if e.get('status') == 'ACTIVE']),
        'exception_types': len(set(e.get('exception_type', '') for e in entries if e.get('exception_type'))),
        'experts': len(set(e.get('expert_name', '') for e in entries if e.get('expert_name')))
    }
    
    return render_template('dashboard.html', entries=entries, stats=stats)


@app.route('/sync', methods=['POST'])
def sync():
    """Sync learning entries from formatted text file."""
    try:
        entries = sync_from_formatted()
        flash(f'Successfully synced {len(entries)} learning entries from formatted file', 'success')
    except Exception as e:
        flash(f'Error syncing: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/entry/<int:entry_number>')
def entry_detail(entry_number):
    """Detailed view of a specific learning entry."""
    entries = get_learning_entries()
    entry = next((e for e in entries if e.get('entry_number') == entry_number), None)
    
    if not entry:
        flash('Learning entry not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('entry_detail.html', entry=entry)


@app.route('/api/entries')
def api_entries():
    """API endpoint for learning entries."""
    entries = get_learning_entries()
    return jsonify(entries)


@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics."""
    entries = get_learning_entries()
    stats = {
        'total_entries': len(entries),
        'active_entries': len([e for e in entries if e.get('status') == 'ACTIVE']),
        'exception_types': len(set(e.get('exception_type', '') for e in entries if e.get('exception_type'))),
        'experts': len(set(e.get('expert_name', '') for e in entries if e.get('expert_name')))
    }
    return jsonify(stats)


if __name__ == '__main__':
    print("🌐 Starting Learning Playbook Web GUI...")
    print("📊 Dashboard: http://localhost:5002")
    print("📋 Entries: http://localhost:5002/")
    
    app.run(debug=True, host='0.0.0.0', port=5002)

