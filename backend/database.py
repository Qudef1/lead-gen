"""SQLite database module for storing analysis results"""
import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "leads.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Table for storing analyzed leads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT UNIQUE NOT NULL,
                account_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Table for storing lead profile information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lead_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                first_name TEXT,
                last_name TEXT,
                full_name TEXT,
                company_name TEXT,
                position TEXT,
                location TEXT,
                profile_url TEXT,
                headline TEXT,
                FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
            )
        """)
        
        # Table for storing classification results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                intent TEXT NOT NULL,
                confidence TEXT,
                reasoning TEXT,
                classified_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
            )
        """)
        
        # Table for storing deep analysis results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                lead_profile_json TEXT,
                company_basics_json TEXT,
                company_activity_json TEXT,
                deep_research_json TEXT,
                pain_point_analysis_json TEXT,
                conversation_analysis_json TEXT,
                qualification_json TEXT,
                recommended_action_json TEXT,
                interexy_value_props_json TEXT,
                executive_summary TEXT,
                analyzed_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
            )
        """)
        
        # Table for storing generated messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                messages_json TEXT NOT NULL,
                recommended_top_3_json TEXT,
                strategy_notes TEXT,
                generated_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
            )
        """)
        
        # Table for tracking processing queue
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES leads(conversation_id) ON DELETE CASCADE
            )
        """)
        
        # Index for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_account ON leads(account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_conversation ON leads(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON processing_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_conversation ON processing_queue(conversation_id)")

        # Add last_message_at column if it doesn't exist yet (safe to re-run)
        try:
            cursor.execute("ALTER TABLE leads ADD COLUMN last_message_at TEXT")
        except Exception:
            pass  # column already exists

        conn.commit()
        logger.info("Database initialized successfully")


def save_lead(
    conversation_id: str,
    account_id: int,
    profile: Dict[str, Any]
) -> int:
    """Save or update lead information. Returns lead ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if lead already exists
        cursor.execute("SELECT id FROM leads WHERE conversation_id = ?", (conversation_id,))
        row = cursor.fetchone()
        
        if row:
            lead_id = row['id']
            cursor.execute("UPDATE leads SET updated_at = ? WHERE id = ?", (now, lead_id))
            
            cursor.execute("""
                UPDATE lead_profiles 
                SET first_name = ?, last_name = ?, full_name = ?, 
                    company_name = ?, position = ?, location = ?, 
                    profile_url = ?, headline = ?
                WHERE lead_id = ?
            """, (
                profile.get('firstName', ''),
                profile.get('lastName', ''),
                f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
                profile.get('companyName', ''),
                profile.get('position', ''),
                profile.get('location', ''),
                profile.get('profileUrl', ''),
                profile.get('headline', ''),
                lead_id
            ))
        else:
            cursor.execute("""
                INSERT INTO leads (conversation_id, account_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (conversation_id, account_id, now, now))
            
            lead_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO lead_profiles 
                (lead_id, first_name, last_name, full_name, company_name, 
                 position, location, profile_url, headline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead_id,
                profile.get('firstName', ''),
                profile.get('lastName', ''),
                f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
                profile.get('companyName', ''),
                profile.get('position', ''),
                profile.get('location', ''),
                profile.get('profileUrl', ''),
                profile.get('headline', '')
            ))
        
        conn.commit()
        return lead_id


def save_classification(
    lead_id: int,
    intent: str,
    confidence: str,
    reasoning: str
):
    """Save classification result"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("SELECT id FROM classifications WHERE lead_id = ?", (lead_id,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("""
                UPDATE classifications 
                SET intent = ?, confidence = ?, reasoning = ?, classified_at = ?
                WHERE id = ?
            """, (intent, confidence, reasoning, now, row['id']))
        else:
            cursor.execute("""
                INSERT INTO classifications (lead_id, intent, confidence, reasoning, classified_at)
                VALUES (?, ?, ?, ?, ?)
            """, (lead_id, intent, confidence, reasoning, now))
        
        conn.commit()


def save_analysis(lead_id: int, analysis: Dict[str, Any]):
    """Save deep analysis result"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("SELECT id FROM analyses WHERE lead_id = ?", (lead_id,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("""
                UPDATE analyses SET
                    lead_profile_json = ?,
                    company_basics_json = ?,
                    company_activity_json = ?,
                    deep_research_json = ?,
                    pain_point_analysis_json = ?,
                    conversation_analysis_json = ?,
                    qualification_json = ?,
                    recommended_action_json = ?,
                    interexy_value_props_json = ?,
                    executive_summary = ?,
                    analyzed_at = ?
                WHERE id = ?
            """, (
                json.dumps(analysis.get('lead_profile', {})),
                json.dumps(analysis.get('company_basics', {})),
                json.dumps(analysis.get('company_activity', {})),
                json.dumps(analysis.get('deep_research', {})),
                json.dumps(analysis.get('pain_point_analysis', {})),
                json.dumps(analysis.get('conversation_analysis', {})),
                json.dumps(analysis.get('qualification', {})),
                json.dumps(analysis.get('recommended_action', {})),
                json.dumps(analysis.get('interexy_value_props', {})),
                analysis.get('executive_summary', ''),
                now,
                row['id']
            ))
        else:
            cursor.execute("""
                INSERT INTO analyses (
                    lead_id, lead_profile_json, company_basics_json, 
                    company_activity_json, deep_research_json, 
                    pain_point_analysis_json, conversation_analysis_json,
                    qualification_json, recommended_action_json,
                    interexy_value_props_json, executive_summary, analyzed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead_id,
                json.dumps(analysis.get('lead_profile', {})),
                json.dumps(analysis.get('company_basics', {})),
                json.dumps(analysis.get('company_activity', {})),
                json.dumps(analysis.get('deep_research', {})),
                json.dumps(analysis.get('pain_point_analysis', {})),
                json.dumps(analysis.get('conversation_analysis', {})),
                json.dumps(analysis.get('qualification', {})),
                json.dumps(analysis.get('recommended_action', {})),
                json.dumps(analysis.get('interexy_value_props', {})),
                analysis.get('executive_summary', ''),
                now
            ))
        
        conn.commit()


def save_messages(lead_id: int, messages_data: Dict[str, Any]):
    """Save generated messages"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("SELECT id FROM messages WHERE lead_id = ?", (lead_id,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("""
                UPDATE messages SET
                    messages_json = ?,
                    recommended_top_3_json = ?,
                    strategy_notes = ?,
                    generated_at = ?
                WHERE id = ?
            """, (
                json.dumps(messages_data.get('messages', [])),
                json.dumps(messages_data.get('recommended_top_3', [])),
                messages_data.get('notes', ''),
                now,
                row['id']
            ))
        else:
            cursor.execute("""
                INSERT INTO messages (lead_id, messages_json, recommended_top_3_json, strategy_notes, generated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                lead_id,
                json.dumps(messages_data.get('messages', [])),
                json.dumps(messages_data.get('recommended_top_3', [])),
                messages_data.get('notes', ''),
                now
            ))
        
        conn.commit()


def add_to_queue(conversation_id: str, account_id: int) -> Optional[int]:
    """Add conversation to processing queue. Returns queue item ID or None if already queued."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            SELECT id FROM processing_queue 
            WHERE conversation_id = ? AND status IN ('pending', 'processing')
        """, (conversation_id,))
        row = cursor.fetchone()
        
        if row:
            return None
        
        cursor.execute("""
            INSERT INTO processing_queue (conversation_id, account_id, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (conversation_id, account_id, now))
        
        queue_id = cursor.lastrowid
        conn.commit()
        return queue_id


def get_next_pending_queue_item() -> Optional[Dict[str, Any]]:
    """Get next pending item from queue"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM processing_queue 
            WHERE status = 'pending' 
            ORDER BY created_at ASC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_queue_status(queue_id: int, status: str, error: Optional[str] = None):
    """Update queue item status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        if status == 'processing':
            cursor.execute("""
                UPDATE processing_queue 
                SET status = ?, started_at = ?
                WHERE id = ?
            """, (status, now, queue_id))
        elif status == 'completed':
            cursor.execute("""
                UPDATE processing_queue 
                SET status = ?, completed_at = ?
                WHERE id = ?
            """, (status, now, queue_id))
        elif status == 'error':
            cursor.execute("""
                UPDATE processing_queue 
                SET status = ?, error = ?, completed_at = ?
                WHERE id = ?
            """, (status, error, now, queue_id))
        else:
            cursor.execute("""
                UPDATE processing_queue 
                SET status = ?
                WHERE id = ?
            """, (status, queue_id))
        
        conn.commit()


def get_lead_by_conversation_id(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get complete lead data by conversation ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, lp.* 
            FROM leads l
            JOIN lead_profiles lp ON l.id = lp.lead_id
            WHERE l.conversation_id = ?
        """, (conversation_id,))
        
        lead_row = cursor.fetchone()
        if not lead_row:
            return None
        
        result = dict(lead_row)
        
        cursor.execute("SELECT * FROM classifications WHERE lead_id = ?", (result['id'],))
        class_row = cursor.fetchone()
        if class_row:
            result['classification'] = dict(class_row)
        
        cursor.execute("SELECT * FROM analyses WHERE lead_id = ?", (result['id'],))
        analysis_row = cursor.fetchone()
        if analysis_row:
            result['analysis'] = {
                'lead_profile': json.loads(analysis_row['lead_profile_json']) if analysis_row['lead_profile_json'] else {},
                'company_basics': json.loads(analysis_row['company_basics_json']) if analysis_row['company_basics_json'] else {},
                'company_activity': json.loads(analysis_row['company_activity_json']) if analysis_row['company_activity_json'] else {},
                'deep_research': json.loads(analysis_row['deep_research_json']) if analysis_row['deep_research_json'] else {},
                'pain_point_analysis': json.loads(analysis_row['pain_point_analysis_json']) if analysis_row['pain_point_analysis_json'] else {},
                'conversation_analysis': json.loads(analysis_row['conversation_analysis_json']) if analysis_row['conversation_analysis_json'] else {},
                'qualification': json.loads(analysis_row['qualification_json']) if analysis_row['qualification_json'] else {},
                'recommended_action': json.loads(analysis_row['recommended_action_json']) if analysis_row['recommended_action_json'] else {},
                'interexy_value_props': json.loads(analysis_row['interexy_value_props_json']) if analysis_row['interexy_value_props_json'] else {},
                'executive_summary': analysis_row['executive_summary'],
            }
        
        cursor.execute("SELECT * FROM messages WHERE lead_id = ?", (result['id'],))
        msg_row = cursor.fetchone()
        if msg_row:
            result['messages'] = {
                'messages': json.loads(msg_row['messages_json']),
                'recommended_top_3': json.loads(msg_row['recommended_top_3_json']),
                'notes': msg_row['strategy_notes'],
            }
        
        return result


def get_all_leads_for_account(account_id: int) -> List[Dict[str, Any]]:
    """Get all leads for a specific account"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, lp.full_name, lp.company_name, lp.position, lp.location, 
                   lp.profile_url, lp.headline,
                   c.intent, c.confidence, c.reasoning,
                   a.executive_summary,
                   m.recommended_top_3_json
            FROM leads l
            JOIN lead_profiles lp ON l.id = lp.lead_id
            LEFT JOIN classifications c ON l.id = c.lead_id
            LEFT JOIN analyses a ON l.id = a.lead_id
            LEFT JOIN messages m ON l.id = m.lead_id
            WHERE l.account_id = ?
            ORDER BY l.created_at DESC
        """, (account_id,))
        
        results = []
        for row in cursor.fetchall():
            lead_data = dict(row)
            
            cursor.execute("SELECT * FROM analyses WHERE lead_id = ?", (lead_data['id'],))
            analysis_row = cursor.fetchone()
            if analysis_row:
                lead_data['analysis'] = {
                    'lead_profile': json.loads(analysis_row['lead_profile_json']) if analysis_row['lead_profile_json'] else {},
                    'company_basics': json.loads(analysis_row['company_basics_json']) if analysis_row['company_basics_json'] else {},
                    'deep_research': json.loads(analysis_row['deep_research_json']) if analysis_row['deep_research_json'] else {},
                    'qualification': json.loads(analysis_row['qualification_json']) if analysis_row['qualification_json'] else {},
                    'executive_summary': analysis_row['executive_summary'],
                }
            
            cursor.execute("SELECT * FROM messages WHERE lead_id = ?", (lead_data['id'],))
            msg_row = cursor.fetchone()
            if msg_row:
                lead_data['messages'] = {
                    'messages': json.loads(msg_row['messages_json']),
                    'recommended_top_3': json.loads(msg_row['recommended_top_3_json']),
                    'notes': msg_row['strategy_notes'],
                }
            
            results.append(lead_data)
        
        return results


def delete_lead(conversation_id: str) -> bool:
    """
    Delete a lead and all associated data (classifications, analyses, messages).
    Returns True if deleted, False if not found.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if lead exists
            cursor.execute("SELECT id FROM leads WHERE conversation_id = ?", (conversation_id,))
            row = cursor.fetchone()

            if not row:
                logger.warning(f"Lead not found for deletion: {conversation_id}")
                return False

            lead_id = row['id']
            logger.info(f"Deleting lead {lead_id} (conversation_id={conversation_id})")

            # Delete in order (foreign key constraints)
            cursor.execute("DELETE FROM messages WHERE lead_id = ?", (lead_id,))
            cursor.execute("DELETE FROM analyses WHERE lead_id = ?", (lead_id,))
            cursor.execute("DELETE FROM classifications WHERE lead_id = ?", (lead_id,))
            cursor.execute("DELETE FROM lead_profiles WHERE lead_id = ?", (lead_id,))
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))

            # Also remove from processing queue
            cursor.execute("DELETE FROM processing_queue WHERE conversation_id = ?", (conversation_id,))

            conn.commit()
            logger.info(f"Deleted lead {conversation_id} and all associated data")
            return True
    except Exception as e:
        logger.error(f"Error deleting lead {conversation_id}: {e}", exc_info=True)
        raise


def get_queue_stats() -> Dict[str, Any]:
    """Get processing queue statistics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        for status in ['pending', 'processing', 'completed', 'error']:
            cursor.execute("SELECT COUNT(*) FROM processing_queue WHERE status = ?", (status,))
            stats[status] = cursor.fetchone()[0]
        
        return stats


def update_last_message_at(conversation_id: str, timestamp_iso: str):
    """Update the last_message_at timestamp for a lead."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE leads SET last_message_at = ? WHERE conversation_id = ?",
            (timestamp_iso, conversation_id)
        )
        conn.commit()


def get_lead_analysis_time(conversation_id: str) -> Optional[str]:
    """Return the analyzed_at ISO timestamp from the analyses table, or None if not yet analyzed."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.analyzed_at
            FROM analyses a
            JOIN leads l ON a.lead_id = l.id
            WHERE l.conversation_id = ?
        """, (conversation_id,))
        row = cursor.fetchone()
        return row['analyzed_at'] if row else None
