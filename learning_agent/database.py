"""
Database operations for the learning agent system.
Handles SQLite database creation, initialization, and data operations.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class LearningDatabase:
    """Manages the learning agent SQLite database operations."""
    
    def __init__(self, db_path: str = "learning_data/learning.db"):
        """Initialize database connection and ensure directory exists."""
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
        """Initialize database with schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Create tables if they don't exist (don't clear existing data)
        self._create_tables_if_not_exist()
        self.conn.commit()
    
    def _drop_tables(self):
        """Drop all existing tables."""
        cursor = self.conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS learning_plans")
        cursor.execute("DROP TABLE IF EXISTS human_feedback")
        cursor.execute("DROP TABLE IF EXISTS learning_records")
        cursor.execute("DROP TABLE IF EXISTS system_exceptions")
        cursor.execute("DROP TABLE IF EXISTS flexible_exceptions")
    
    def _create_tables_if_not_exist(self):
        """Create database tables with proper schema if they don't exist."""
        cursor = self.conn.cursor()
        
        # Create learning_plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'MEDIUM',
                status TEXT DEFAULT 'DRAFT',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expert_feedback TEXT,
                implementation_notes TEXT
            )
        """)
        
        # Create human_feedback table with enhanced schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS human_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                invoice_id VARCHAR(100),
                original_agent_decision VARCHAR(50),
                human_correction VARCHAR(50),
                routing_queue VARCHAR(100),
                feedback_text TEXT,
                expert_name VARCHAR(100),
                feedback_type VARCHAR(50),
                supporting_evidence JSON,
                learning_record_id INTEGER,
                conversation_id VARCHAR(100),
                is_initial_feedback BOOLEAN DEFAULT TRUE,
                parent_feedback_id INTEGER,
                llm_questions TEXT,
                human_responses TEXT,
                feedback_summary TEXT,
                conversation_status VARCHAR(20) DEFAULT 'active',
                quality_score REAL DEFAULT 0.0,
                FOREIGN KEY (learning_record_id) REFERENCES learning_records(id),
                FOREIGN KEY (parent_feedback_id) REFERENCES human_feedback(id)
            )
        """)
        
        # Create learning_records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                learning_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Create system_exceptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_exceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_id TEXT UNIQUE NOT NULL,
                invoice_id TEXT NOT NULL,
                po_number TEXT,
                amount TEXT,
                supplier TEXT,
                exception_type TEXT NOT NULL,
                queue TEXT NOT NULL,
                routing_reason TEXT,
                timestamp TEXT,
                context TEXT,
                raw_data TEXT,
                status TEXT DEFAULT 'OPEN',
                expert_reviewed BOOLEAN DEFAULT FALSE,
                expert_feedback TEXT,
                expert_name TEXT,
                human_correction TEXT,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Run migrations for existing databases
        self._run_migrations()

    def _create_tables(self):
        """Create database tables with proper schema."""
        cursor = self.conn.cursor()
        
        # learning_records: Raw learning opportunities from log analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_type VARCHAR(50) NOT NULL,
                source_file VARCHAR(200),
                source_data JSON,
                learning_opportunity TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'pending',
                analysis_notes TEXT
            )
        """)
        
        # human_feedback: Human corrections and expert input
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS human_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                invoice_id VARCHAR(100),
                original_agent_decision VARCHAR(50),
                human_correction VARCHAR(50),
                routing_queue VARCHAR(100),
                feedback_text TEXT,
                expert_name VARCHAR(100),
                feedback_type VARCHAR(50),
                supporting_evidence JSON,
                learning_record_id INTEGER,
                conversation_id VARCHAR(100),
                is_initial_feedback BOOLEAN DEFAULT TRUE,
                parent_feedback_id INTEGER,
                llm_questions TEXT,
                human_responses TEXT,
                feedback_summary TEXT,
                conversation_status VARCHAR(20) DEFAULT 'active',
                quality_score REAL DEFAULT 0.0,
                conversation_history TEXT,
                FOREIGN KEY (learning_record_id) REFERENCES learning_records(id),
                FOREIGN KEY (parent_feedback_id) REFERENCES human_feedback(id)
            )
        """)
        
        # learning_plans: Generated improvement plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                plan_type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                source_learning_records TEXT,
                suggested_changes JSON NOT NULL,
                impact_analysis JSON,
                priority VARCHAR(20) DEFAULT 'medium',
                status VARCHAR(20) DEFAULT 'draft',
                implementation_notes TEXT,
                approved_by VARCHAR(100),
                approved_at TIMESTAMP,
                llm_reasoning TEXT
            )
        """)
        
        # system_exceptions: System exceptions for expert review
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_exceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exception_id VARCHAR(100) UNIQUE NOT NULL,
                invoice_id VARCHAR(100) NOT NULL,
                po_number VARCHAR(100),
                amount VARCHAR(50),
                supplier VARCHAR(200),
                exception_type VARCHAR(50) NOT NULL,
                queue VARCHAR(50) NOT NULL,
                routing_reason TEXT,
                timestamp VARCHAR(50),
                context JSON,
                raw_data TEXT,
                status VARCHAR(20) DEFAULT 'OPEN',
                expert_reviewed BOOLEAN DEFAULT FALSE,
                expert_feedback TEXT,
                expert_name VARCHAR(100),
                reviewed_at TIMESTAMP,
                human_correction VARCHAR(50)
            )
        """)
        
        # Run migrations for existing databases
        self._run_migrations()
    
    def _run_migrations(self):
        """Run database migrations for schema updates."""
        cursor = self.conn.cursor()
        
        # Migration: Add raw_data column to system_exceptions table
        try:
            cursor.execute("ALTER TABLE system_exceptions ADD COLUMN raw_data TEXT DEFAULT ''")
            print("Added raw_data column to system_exceptions table")
        except Exception as e:
            # Column might already exist, which is fine
            if "duplicate column name" not in str(e).lower():
                print(f"Migration note: {e}")
        
        # Migration: Add new fields to human_feedback table for enhanced feedback collection
        new_fields = [
            ("conversation_id", "VARCHAR(100)"),
            ("is_initial_feedback", "BOOLEAN DEFAULT TRUE"),
            ("parent_feedback_id", "INTEGER"),
            ("llm_questions", "TEXT"),
            ("human_responses", "TEXT"),
            ("feedback_summary", "TEXT"),
            ("conversation_status", "VARCHAR(20) DEFAULT 'active'"),
            ("quality_score", "REAL DEFAULT 0.0"),
            ("conversation_history", "TEXT")
        ]
        
        # Check if we need to add the new schema fields (for old databases)
        try:
            cursor.execute("SELECT invoice_id FROM human_feedback LIMIT 1")
            # If this succeeds, we have the new schema
            has_new_schema = True
        except:
            # If this fails, we have the old schema and need to add the missing fields
            has_new_schema = False
        
        if not has_new_schema:
            # Add the missing fields from the new schema
            missing_fields = [
                ("invoice_id", "VARCHAR(100)"),
                ("original_agent_decision", "VARCHAR(50)"),
                ("human_correction", "VARCHAR(50)"),
                ("routing_queue", "VARCHAR(100)"),
                ("feedback_text", "TEXT"),
                ("supporting_evidence", "JSON"),
                ("learning_record_id", "INTEGER")
            ]
            
            for field_name, field_definition in missing_fields:
                try:
                    cursor.execute(f"ALTER TABLE human_feedback ADD COLUMN {field_name} {field_definition}")
                    print(f"Added {field_name} column to human_feedback table")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"Migration note for {field_name}: {e}")
        
        # Add the enhanced feedback fields
        for field_name, field_definition in new_fields:
            try:
                cursor.execute(f"ALTER TABLE human_feedback ADD COLUMN {field_name} {field_definition}")
                print(f"Added {field_name} column to human_feedback table")
            except Exception as e:
                # Column might already exist, which is fine
                if "duplicate column name" not in str(e).lower():
                    print(f"Migration note for {field_name}: {e}")
        
        self.conn.commit()
    
    def store_learning_record(self, source_type: str, source_file: str, 
                            source_data: Dict[str, Any], learning_opportunity: str,
                            confidence_score: float = 0.0, analysis_notes: str = "") -> int:
        """Store a learning record from log analysis."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO learning_records 
            (source_type, source_file, source_data, learning_opportunity, confidence_score, analysis_notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source_type, source_file, json.dumps(source_data), learning_opportunity, 
              confidence_score, analysis_notes))
        self.conn.commit()
        return cursor.lastrowid
    
    def store_human_feedback(self, invoice_id: str, original_decision: str, 
                           human_correction: str, routing_queue: str = None,
                           feedback_text: str = "", expert_name: str = "",
                           feedback_type: str = "", supporting_evidence: Dict[str, Any] = None,
                           learning_record_id: int = None, conversation_id: str = None,
                           is_initial_feedback: bool = True, parent_feedback_id: int = None,
                           llm_questions: str = "", human_responses: str = "",
                           feedback_summary: str = "", conversation_status: str = "active",
                           quality_score: float = 0.0) -> int:
        """Store human feedback and corrections."""
        cursor = self.conn.cursor()
        
        # Check if we have the old schema (with feedback_id) or new schema
        try:
            cursor.execute("SELECT feedback_id FROM human_feedback LIMIT 1")
            has_old_schema = True
        except:
            has_old_schema = False
        
        if has_old_schema:
            # Use old schema with feedback_id
            import uuid
            feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
            cursor.execute("""
                INSERT INTO human_feedback 
                (feedback_id, feedback_type, content, expert_name, invoice_id, original_agent_decision, 
                 human_correction, routing_queue, feedback_text, supporting_evidence, learning_record_id,
                 conversation_id, is_initial_feedback, parent_feedback_id, llm_questions,
                 human_responses, feedback_summary, conversation_status, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (feedback_id, feedback_type, feedback_text, expert_name, invoice_id, original_decision,
                  human_correction, routing_queue, feedback_text, 
                  json.dumps(supporting_evidence or {}), learning_record_id,
                  conversation_id, is_initial_feedback, parent_feedback_id, llm_questions,
                  human_responses, feedback_summary, conversation_status, quality_score))
        else:
            # Use new schema
            cursor.execute("""
                INSERT INTO human_feedback 
                (invoice_id, original_agent_decision, human_correction, routing_queue,
                 feedback_text, expert_name, feedback_type, supporting_evidence, learning_record_id,
                 conversation_id, is_initial_feedback, parent_feedback_id, llm_questions,
                 human_responses, feedback_summary, conversation_status, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_id, original_decision, human_correction, routing_queue,
                  feedback_text, expert_name, feedback_type, 
                  json.dumps(supporting_evidence or {}), learning_record_id,
                  conversation_id, is_initial_feedback, parent_feedback_id, llm_questions,
                  human_responses, feedback_summary, conversation_status, quality_score))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def store_learning_plan(self, plan_type: str, title: str, description: str,
                          source_learning_records: List[int], suggested_changes: Dict[str, Any],
                          impact_analysis: Dict[str, Any] = None, priority: str = "medium",
                          llm_reasoning: str = "") -> int:
        """Store a generated learning plan."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO learning_plans 
            (plan_type, title, description, source_learning_records, suggested_changes,
             impact_analysis, priority, llm_reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (plan_type, title, description, json.dumps(source_learning_records),
              json.dumps(suggested_changes), json.dumps(impact_analysis or {}),
              priority, llm_reasoning))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_learning_records(self, status: str = None) -> List[Dict[str, Any]]:
        """Get learning records, optionally filtered by status."""
        cursor = self.conn.cursor()
        if status:
            cursor.execute("SELECT * FROM learning_records WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM learning_records ORDER BY created_at DESC")
        
        records = []
        for row in cursor.fetchall():
            record = dict(row)
            record['source_data'] = json.loads(record['source_data']) if record['source_data'] else {}
            records.append(record)
        return records
    
    def get_human_feedback(self, learning_record_id: int = None) -> List[Dict[str, Any]]:
        """Get human feedback, optionally filtered by learning record."""
        cursor = self.conn.cursor()
        if learning_record_id:
            cursor.execute("SELECT * FROM human_feedback WHERE learning_record_id = ? ORDER BY created_at DESC", (learning_record_id,))
        else:
            cursor.execute("SELECT * FROM human_feedback ORDER BY created_at DESC")
        
        feedback = []
        for row in cursor.fetchall():
            item = dict(row)
            item['supporting_evidence'] = json.loads(item['supporting_evidence']) if item['supporting_evidence'] else {}
            feedback.append(item)
        return feedback
    
    def get_feedback_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all feedback items in a conversation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM human_feedback 
            WHERE conversation_id = ? 
            ORDER BY created_at ASC
        """, (conversation_id,))
        
        feedback = []
        for row in cursor.fetchall():
            item = dict(row)
            item['supporting_evidence'] = json.loads(item['supporting_evidence']) if item['supporting_evidence'] else {}
            feedback.append(item)
        return feedback
    
    def get_active_conversations(self) -> List[Dict[str, Any]]:
        """Get all active feedback conversations."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT conversation_id, invoice_id, expert_name, created_at, conversation_status
            FROM human_feedback 
            WHERE conversation_status = 'active' AND is_initial_feedback = TRUE
            ORDER BY created_at DESC
        """)
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append(dict(row))
        return conversations
    
    def update_feedback_conversation(self, feedback_id: int, llm_questions: str = None,
                                   human_responses: str = None, feedback_summary: str = None,
                                   conversation_status: str = None, quality_score: float = None) -> bool:
        """Update a feedback conversation with LLM questions, responses, or summary."""
        cursor = self.conn.cursor()
        
        updates = []
        params = []
        
        if llm_questions is not None:
            updates.append("llm_questions = ?")
            params.append(llm_questions)
        
        if human_responses is not None:
            updates.append("human_responses = ?")
            params.append(human_responses)
        
        if feedback_summary is not None:
            updates.append("feedback_summary = ?")
            params.append(feedback_summary)
        
        if conversation_status is not None:
            updates.append("conversation_status = ?")
            params.append(conversation_status)
        
        if quality_score is not None:
            updates.append("quality_score = ?")
            params.append(quality_score)
        
        if not updates:
            return False
        
        params.append(feedback_id)
        query = f"UPDATE human_feedback SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, params)
        success = cursor.rowcount > 0
        self.conn.commit()
        
        return success
    
    def get_learning_plans(self, status: str = None) -> List[Dict[str, Any]]:
        """Get learning plans, optionally filtered by status."""
        cursor = self.conn.cursor()
        if status:
            cursor.execute("SELECT * FROM learning_plans WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM learning_plans ORDER BY created_at DESC")
        
        plans = []
        for row in cursor.fetchall():
            plan = dict(row)
            plan['source_learning_records'] = json.loads(plan['source_learning_records']) if plan['source_learning_records'] else []
            plan['suggested_changes'] = json.loads(plan['suggested_changes']) if plan['suggested_changes'] else {}
            plan['impact_analysis'] = json.loads(plan['impact_analysis']) if plan['impact_analysis'] else {}
            plans.append(plan)
        return plans
    
    def update_learning_plan_status(self, plan_id: int, status: str, approved_by: str = None):
        """Update learning plan status and approval info."""
        cursor = self.conn.cursor()
        if approved_by:
            cursor.execute("""
                UPDATE learning_plans 
                SET status = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (status, approved_by, plan_id))
        else:
            cursor.execute("UPDATE learning_plans SET status = ? WHERE id = ?", (status, plan_id))
        self.conn.commit()
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM learning_records")
        learning_records_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM human_feedback")
        human_feedback_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM learning_plans")
        learning_plans_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM learning_plans WHERE status = 'draft'")
        draft_plans_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM learning_plans WHERE status = 'approved'")
        approved_plans_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM system_exceptions")
        exceptions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM system_exceptions WHERE expert_reviewed = FALSE")
        pending_exceptions_count = cursor.fetchone()[0]
        
        return {
            'learning_records': learning_records_count,
            'human_feedback': human_feedback_count,
            'learning_plans': learning_plans_count,
            'draft_plans': draft_plans_count,
            'approved_plans': approved_plans_count,
            'system_exceptions': exceptions_count,
            'pending_exceptions': pending_exceptions_count
        }
    
    def store_system_exception(self, exception_data: Dict[str, Any]) -> int:
        """Store a system exception for expert review."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO system_exceptions 
            (exception_id, invoice_id, po_number, amount, supplier, exception_type, 
             queue, routing_reason, timestamp, context, raw_data, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exception_data['exception_id'],
            exception_data['invoice_id'],
            exception_data.get('po_number', ''),
            exception_data.get('amount', ''),
            exception_data.get('supplier', ''),
            exception_data['exception_type'],
            exception_data['queue'],
            exception_data.get('routing_reason', ''),
            exception_data.get('timestamp', ''),
            json.dumps(exception_data.get('context', {})),
            exception_data.get('raw_data', ''),
            exception_data.get('status', 'OPEN')
        ))
        
        conn.commit()
        exception_id = cursor.lastrowid
        conn.close()
        return exception_id
    
    def get_pending_exceptions(self) -> List[Dict[str, Any]]:
        """Get all pending exceptions that need expert review."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM system_exceptions 
            WHERE expert_reviewed = FALSE 
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_exception_by_id(self, exception_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific exception by its ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM system_exceptions WHERE exception_id = ?", (exception_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def update_exception_review(self, exception_id: str, expert_name: str, 
                              expert_feedback: str, human_correction: str) -> bool:
        """Update an exception with expert review feedback."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE system_exceptions 
            SET expert_reviewed = TRUE, expert_feedback = ?, expert_name = ?, 
                human_correction = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE exception_id = ?
        """, (expert_feedback, expert_name, human_correction, exception_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def sync_exceptions_from_logs(self) -> int:
        """Sync exceptions from log files to database."""
        from .exception_parser import ExceptionParser
        
        parser = ExceptionParser()
        exceptions = parser.parse_all_exceptions()
        
        synced_count = 0
        for exc in exceptions:
            exception_data = {
                'exception_id': exc.exception_id,
                'invoice_id': exc.invoice_id,
                'po_number': exc.po_number,
                'amount': exc.amount,
                'supplier': exc.supplier,
                'exception_type': exc.exception_type,
                'queue': exc.queue,
                'routing_reason': exc.routing_reason,
                'timestamp': exc.timestamp,
                'context': exc.context,
                'raw_data': exc.raw_data,
                'status': exc.status
            }
            
            try:
                self.store_system_exception(exception_data)
                synced_count += 1
            except Exception as e:
                print(f"Error syncing exception {exc.exception_id}: {e}")
        
        return synced_count

    def get_related_data(self, invoice_id: str) -> Dict[str, Any]:
        """Get related data based on what's explicitly stated in the log files."""
        import json
        import os
        import re
        from pathlib import Path
        
        result = {
            "invoice": None,
            "po_item": None,
            "contract": None,
            "data_mismatches": []
        }
        
        # Find invoice file - always try to find this
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        invoice_dirs = [
            os.path.join(repo_root, "json_files", "bronze_invoices"),
            os.path.join(repo_root, "json_files", "golden_invoices"),
            os.path.join(repo_root, "json_files", "silver_invoices")
        ]
        
        invoice_data = None
        for invoice_dir in invoice_dirs:
            if os.path.exists(invoice_dir):
                for file in os.listdir(invoice_dir):
                    if file.endswith('.json'):
                        try:
                            with open(os.path.join(invoice_dir, file), 'r') as f:
                                data = json.load(f)
                                if data.get('invoice_id') == invoice_id:
                                    invoice_data = data
                                    break
                        except:
                            continue
                if invoice_data:
                    break
        
        if invoice_data:
            result["invoice"] = invoice_data
            
            # Check log files for PO information
            po_number = self._extract_po_from_logs(invoice_id)
            if po_number:
                # Find PO file
                po_data = self._find_po_data(po_number, repo_root)
                if po_data:
                    result["po_item"] = po_data
                    
                    # Find related contract
                    contract_id = po_data.get('contract_id')
                    if contract_id:
                        contract_data = self._find_contract_data(contract_id, repo_root)
                        if contract_data:
                            result["contract"] = contract_data
        
        return result
    
    def _extract_po_from_logs(self, invoice_id: str) -> str:
        """Extract PO number from log files for the given invoice."""
        import os
        import re
        
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(repo_root, "system_logs")
        
        if not os.path.exists(log_dir):
            return None
            
        for log_file in os.listdir(log_dir):
            if log_file.endswith('.log'):
                log_path = os.path.join(log_dir, log_file)
                try:
                    with open(log_path, 'r') as f:
                        content = f.read()
                        # Look for pattern: INVOICE: INV-XXX-XXX (PO: PO-XXX, Amount: $X,XXX.XX)
                        pattern = rf'INVOICE:\s+{re.escape(invoice_id)}\s+\(PO:\s+([^,]+),'
                        match = re.search(pattern, content)
                        if match:
                            return match.group(1).strip()
                except:
                    continue
        return None
    
    def _find_po_data(self, po_number: str, repo_root: str) -> dict:
        """Find PO data by PO number."""
        import json
        import os
        
        po_dirs = [
            "/Users/michaelzimmerman/projects/ResolveLight/json_files/POs",
            os.path.join(repo_root, "json_files", "golden_invoices"),
            os.path.join(repo_root, "json_files", "silver_invoices")
        ]
        
        for po_dir in po_dirs:
            if os.path.exists(po_dir):
                for file in os.listdir(po_dir):
                    if file.endswith('.json'):
                        try:
                            with open(os.path.join(po_dir, file), 'r') as f:
                                po_data = json.load(f)
                                # Check if this PO file contains our PO number
                                if self._po_contains_number(po_data, po_number):
                                    # If it's a file with multiple POs, find the specific one
                                    if 'purchase_orders' in po_data and isinstance(po_data['purchase_orders'], list):
                                        for po in po_data['purchase_orders']:
                                            if isinstance(po, dict) and po.get('po_number') == po_number:
                                                return po
                                    else:
                                        return po_data
                        except:
                            continue
        return None
    
    def _find_contract_data(self, contract_id: str, repo_root: str) -> dict:
        """Find contract data by contract ID."""
        import json
        import os
        
        contract_dirs = [
            "/Users/michaelzimmerman/projects/ResolveLight/json_files/contracts",
            os.path.join(repo_root, "json_files", "golden_invoices"),
            os.path.join(repo_root, "json_files", "silver_invoices")
        ]
        
        for contract_dir in contract_dirs:
            if os.path.exists(contract_dir):
                for file in os.listdir(contract_dir):
                    if file.endswith('.json'):
                        try:
                            with open(os.path.join(contract_dir, file), 'r') as f:
                                contract_data = json.load(f)
                                if contract_data.get('contract_id') == contract_id:
                                    return contract_data
                        except:
                            continue
        return None
    
    def _po_contains_number(self, po_data: dict, po_number: str) -> bool:
        """Check if a PO data structure contains the given PO number."""
        if isinstance(po_data, dict):
            # Check if this is a single PO object
            for key in ['po_number', 'purchase_order_number', 'po_id', 'id']:
                if po_data.get(key) == po_number:
                    return True
            
            # Check if this is a file containing multiple POs in an array
            if 'purchase_orders' in po_data and isinstance(po_data['purchase_orders'], list):
                for po in po_data['purchase_orders']:
                    if isinstance(po, dict) and po.get('po_number') == po_number:
                        return True
        return False

    def append_to_conversation_history(self, conversation_id: str, content: str, content_type: str) -> bool:
        """Append content to conversation history."""
        try:
            cursor = self.conn.cursor()
            
            # Get current conversation history
            cursor.execute("""
                SELECT conversation_history FROM human_feedback 
                WHERE conversation_id = ? AND is_initial_feedback = TRUE
            """, (conversation_id,))
            result = cursor.fetchone()
            
            # Append new content
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_content = f"{content_type.upper()}: {content}\n"
            
            updated_history = (result[0] if result and result[0] else "") + new_content
            
            # Update the record
            cursor.execute("""
                UPDATE human_feedback 
                SET conversation_history = ?
                WHERE conversation_id = ? AND is_initial_feedback = TRUE
            """, (updated_history, conversation_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error appending to conversation history: {e}")
            return False

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def initialize_database(db_path: str = "learning_data/learning.db") -> LearningDatabase:
    """Initialize and return a new database instance."""
    return LearningDatabase(db_path)


if __name__ == "__main__":
    # Test database initialization
    db = initialize_database()
    print("Database initialized successfully!")
    print("Database stats:", db.get_database_stats())
    db.close()
