# Learning Playbook Web Application

A Flask-based web application for viewing and managing learning playbook entries.

## Features

- **Dashboard View**: Overview of all learning entries with statistics
- **Sync Functionality**: Sync learning entries from the formatted text file
- **Entry List**: Display all learning entries as cards with key information
- **Entry Detail View**: Full detail view for each learning entry
- **Beautiful UI**: Modern, responsive interface using Bootstrap 5

## Getting Started

### Prerequisites

- Python 3.7+
- Flask
- Bootstrap 5 (loaded via CDN)
- Font Awesome (loaded via CDN)

### Installation

No additional installation required - all dependencies are standard Python or loaded via CDN.

### Running the Application

1. Navigate to the `learning_playbooks` directory:
   ```bash
   cd learning_playbooks
   ```

2. Run the Flask application:
   ```bash
   python app.py
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:5002
   ```

### First Time Setup

1. Click the "Sync from Formatted File" button on the dashboard
2. This will parse `learning_playbook_formatted.txt` and create/update `learning_playbook.jsonl`
3. Once synced, all learning entries will be displayed

## Features Overview

### Dashboard

The dashboard provides:
- **Statistics Cards**: Total entries, active entries, exception types, and experts
- **Learning Entries List**: All entries displayed as clickable cards
- **Sync Button**: Re-sync data from the formatted text file

### Entry Cards

Each entry card shows:
- Entry number and status
- Invoice ID, PO Number, Supplier
- Exception type and amount
- Expert name and timestamp
- Feedback preview
- Confidence score
- Link to full details

### Entry Detail View

The detail view displays:
- Complete entry information
- Invoice details
- Expert feedback
- Learning insights
- Decision criteria
- Validation signature
- Key distinguishing factors
- Approval conditions
- Generalization warning

## File Structure

```
learning_playbooks/
├── app.py                           # Flask application
├── parser.py                        # Parser for formatted text files
├── learning_playbook_formatted.txt  # Source formatted file
├── learning_playbook.jsonl          # Parsed JSONL data
├── templates/
│   ├── base.html                   # Base template
│   ├── dashboard.html              # Dashboard view
│   └── entry_detail.html           # Entry detail view
└── README_WEB_APP.md               # This file
```

## How It Works

1. **Parser (`parser.py`)**: 
   - Parses the formatted text file into structured data
   - Extracts all sections and fields from each entry
   - Converts to JSON format

2. **Flask App (`app.py`)**:
   - Serves the web interface
   - Loads data from JSONL file
   - Provides sync functionality
   - Handles routing between views

3. **Templates**:
   - Use Jinja2 templating
   - Bootstrap 5 for styling
   - Font Awesome for icons
   - Responsive design

## API Endpoints

- `GET /` - Dashboard view
- `POST /sync` - Sync from formatted file
- `GET /entry/<number>` - Entry detail view
- `GET /api/entries` - JSON API for all entries
- `GET /api/stats` - JSON API for statistics

## Troubleshooting

### No entries showing up
- Click "Sync from Formatted File" button
- Verify `learning_playbook_formatted.txt` exists and has content

### Parsing errors
- Check the terminal output for error messages
- Verify the formatted file structure matches expected format

### Port already in use
- Change the port in `app.py` (last line)
- Default port is 5002

## Future Enhancements

Potential features for future versions:
- Search and filter functionality
- Export entries to various formats
- Edit entries directly in the web interface
- Add new entries manually
- Compare entries side-by-side
- Tag and categorize entries
- Advanced analytics and reporting

