"""
Flexible Database Adapter for ResolveLight
Handles flexible exception schemas and dynamic field storage.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from .flexible_exception_parser import FlexibleException


class FlexibleDatabase:
    """Database adapter that can handle flexible exception schemas."""
    
    def __init__(self, db_path: str = "learning_data/learning.db"):
        """Initialize database with flexible schema."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = None
        self._init_database()
    
    def get_connection(self):
        """Get a new database connection for thread safety."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database with flexible schema and clear existing data."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Clear existing data and recreate tables
        self._drop_tables()
        self._create_flexible_exceptions_table()
        self.conn.commit()

    def _drop_tables(self):
        """Drop all existing tables."""
        cursor = self.conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS flexible_exceptions")
        cursor.execute("DROP TABLE IF EXISTS learning_plans")
        cursor.execute("DROP TABLE IF EXISTS human_feedback")
        cursor.execute("DROP TABLE IF EXISTS learning_records")
        cursor.execute("DROP TABLE IF EXISTS system_exceptions")

    def _create_flexible_exceptions_table(self):
        """Create flexible exceptions table that can store any schema."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE flexible_exceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_id TEXT UNIQUE NOT NULL,
                invoice_id TEXT NOT NULL,
                queue TEXT NOT NULL,
                timestamp TEXT,
                priority TEXT,
                status TEXT DEFAULT 'OPEN',
                
                -- Flexible JSON storage for any fields
                structured_fields TEXT,  -- JSON of key-value pairs
                unstructured_text TEXT,  -- JSON array of text lines
                context TEXT,           -- JSON of additional context
                raw_data TEXT,          -- JSON of original raw data
                
                -- Expert review fields
                expert_reviewed BOOLEAN DEFAULT FALSE,
                expert_feedback TEXT,
                expert_name TEXT,
                human_correction TEXT,
                reviewed_at TIMESTAMP,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exception_id ON flexible_exceptions(exception_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_id ON flexible_exceptions(invoice_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue ON flexible_exceptions(queue)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expert_reviewed ON flexible_exceptions(expert_reviewed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON flexible_exceptions(status)")

    def store_flexible_exception(self, exception: FlexibleException) -> int:
        """Store a flexible exception with any schema."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO flexible_exceptions 
            (exception_id, invoice_id, queue, timestamp, priority, status,
             structured_fields, unstructured_text, context, raw_data,
             expert_reviewed, expert_feedback, expert_name, human_correction, reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exception.exception_id,
            exception.invoice_id,
            exception.queue,
            exception.timestamp,
            exception.priority,
            exception.status,
            json.dumps(exception.structured_fields),
            json.dumps(exception.unstructured_text),
            json.dumps(exception.context),
            json.dumps(exception.raw_data),
            exception.expert_reviewed,
            exception.expert_feedback,
            exception.expert_name,
            exception.human_correction,
            exception.reviewed_at
        ))
        
        conn.commit()
        exception_id = cursor.lastrowid
        conn.close()
        return exception_id

    def get_flexible_exception_by_id(self, exception_id: str) -> Optional[Dict[str, Any]]:
        """Get a flexible exception by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM flexible_exceptions WHERE exception_id = ?", (exception_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_flexible_dict(row)
        return None

    def get_pending_flexible_exceptions(self) -> List[Dict[str, Any]]:
        """Get all pending flexible exceptions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flexible_exceptions 
            WHERE expert_reviewed = FALSE 
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_flexible_dict(row) for row in rows]

    def _row_to_flexible_dict(self, row) -> Dict[str, Any]:
        """Convert database row to flexible dictionary."""
        result = dict(row)
        
        # Parse JSON fields
        for field in ['structured_fields', 'unstructured_text', 'context', 'raw_data']:
            if result[field]:
                try:
                    result[field] = json.loads(result[field])
                except:
                    result[field] = {}
            else:
                result[field] = {}
        
        return result

    def update_flexible_exception_review(self, exception_id: str, expert_name: str, 
                                       expert_feedback: str, human_correction: str) -> bool:
        """Update flexible exception with expert review."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE flexible_exceptions 
            SET expert_reviewed = TRUE, expert_feedback = ?, expert_name = ?, 
                human_correction = ?, reviewed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE exception_id = ?
        """, (expert_feedback, expert_name, human_correction, exception_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def sync_flexible_exceptions_from_logs(self) -> int:
        """Sync flexible exceptions from logs."""
        from .flexible_exception_parser import FlexibleExceptionParser
        
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(repo_root, "system_logs")
        parser = FlexibleExceptionParser(logs_dir)
        exceptions = parser.parse_all_exceptions()
        
        synced_count = 0
        for exc in exceptions:
            try:
                self.store_flexible_exception(exc)
                synced_count += 1
            except Exception as e:
                print(f"Error syncing flexible exception {exc.exception_id}: {e}")
        
        return synced_count

    def get_flexible_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for flexible exceptions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM flexible_exceptions")
        total_exceptions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM flexible_exceptions WHERE expert_reviewed = FALSE")
        pending_exceptions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM flexible_exceptions WHERE expert_reviewed = TRUE")
        reviewed_exceptions = cursor.fetchone()[0]
        
        # Queue breakdown
        cursor.execute("""
            SELECT queue, COUNT(*) as count 
            FROM flexible_exceptions 
            GROUP BY queue 
            ORDER BY count DESC
        """)
        queue_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Field usage analysis
        cursor.execute("SELECT structured_fields FROM flexible_exceptions WHERE structured_fields IS NOT NULL")
        field_usage = {}
        for row in cursor.fetchall():
            try:
                fields = json.loads(row[0])
                for field in fields.keys():
                    field_usage[field] = field_usage.get(field, 0) + 1
            except:
                continue
        
        conn.close()
        
        return {
            'total_exceptions': total_exceptions,
            'pending_exceptions': pending_exceptions,
            'reviewed_exceptions': reviewed_exceptions,
            'queue_breakdown': queue_breakdown,
            'field_usage': field_usage,
            'common_fields': sorted(field_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        }

    def search_flexible_exceptions(self, query: str, field: str = None) -> List[Dict[str, Any]]:
        """Search flexible exceptions by content."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if field:
            # Search in specific field
            cursor.execute("""
                SELECT * FROM flexible_exceptions 
                WHERE structured_fields LIKE ? OR unstructured_text LIKE ? OR context LIKE ?
                ORDER BY created_at DESC
            """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        else:
            # Search in all text fields
            cursor.execute("""
                SELECT * FROM flexible_exceptions 
                WHERE exception_id LIKE ? OR invoice_id LIKE ? OR 
                      structured_fields LIKE ? OR unstructured_text LIKE ? OR context LIKE ?
                ORDER BY created_at DESC
            """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_flexible_dict(row) for row in rows]

    def get_exception_schema_analysis(self) -> Dict[str, Any]:
        """Analyze exception schemas to understand data patterns."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT structured_fields, queue FROM flexible_exceptions")
        rows = cursor.fetchall()
        
        schema_analysis = {
            'total_exceptions': len(rows),
            'field_frequency': {},
            'queue_schemas': {},
            'field_combinations': {},
            'data_types': {}
        }
        
        for row in rows:
            try:
                fields = json.loads(row[0])
                queue = row[1]
                
                # Track field frequency
                for field in fields.keys():
                    schema_analysis['field_frequency'][field] = schema_analysis['field_frequency'].get(field, 0) + 1
                
                # Track queue-specific schemas
                if queue not in schema_analysis['queue_schemas']:
                    schema_analysis['queue_schemas'][queue] = set()
                schema_analysis['queue_schemas'][queue].update(fields.keys())
                
                # Track field combinations
                field_combo = tuple(sorted(fields.keys()))
                schema_analysis['field_combinations'][field_combo] = schema_analysis['field_combinations'].get(field_combo, 0) + 1
                
                # Track data types
                for field, value in fields.items():
                    if field not in schema_analysis['data_types']:
                        schema_analysis['data_types'][field] = set()
                    schema_analysis['data_types'][field].add(type(value).__name__)
                
            except:
                continue
        
        # Convert sets to lists for JSON serialization
        for queue in schema_analysis['queue_schemas']:
            schema_analysis['queue_schemas'][queue] = list(schema_analysis['queue_schemas'][queue])
        
        for field in schema_analysis['data_types']:
            schema_analysis['data_types'][field] = list(schema_analysis['data_types'][field])
        
        conn.close()
        return schema_analysis

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
