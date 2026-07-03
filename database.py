"""
Database Module - SQLite storage for leads and history
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path


class LeadDatabase:
    """SQLite database for storing lead information"""
    
    def __init__(self, db_path='leads.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Leads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    type TEXT,
                    location TEXT,
                    ranking_position INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Analysis results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    seo_score INTEGER,
                    issues TEXT,
                    strengths TEXT,
                    recommendations TEXT,
                    pagespeed_data TEXT,
                    contact_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads (id)
                )
            ''')
            
            # Outreach tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS outreach (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    contact_email TEXT,
                    contact_phone TEXT,
                    email_draft TEXT,
                    last_contacted TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads (id)
                )
            ''')
            
            # Add email_draft column if it doesn't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE outreach ADD COLUMN email_draft TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Search history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    location TEXT,
                    results_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_lead(self, lead_data):
        """Add or update a lead"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if lead exists
            cursor.execute('SELECT id FROM leads WHERE url = ?', (lead_data['url'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE leads 
                    SET title = ?, type = ?, location = ?, ranking_position = ?, updated_at = ?
                    WHERE url = ?
                ''', (
                    lead_data.get('title'),
                    lead_data.get('type'),
                    lead_data.get('location'),
                    lead_data.get('ranking_position'),
                    datetime.now().isoformat(),
                    lead_data['url']
                ))
                lead_id = existing[0]
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO leads (url, title, type, location, ranking_position)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    lead_data['url'],
                    lead_data.get('title'),
                    lead_data.get('type'),
                    lead_data.get('location'),
                    lead_data.get('ranking_position')
                ))
                lead_id = cursor.lastrowid
            
            conn.commit()
            return lead_id
    
    def save_analysis(self, lead_id, analysis_data):
        """Save analysis results for a lead"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get score - try both 'seo_score' and 'score' keys
            seo_score = analysis_data.get('seo_score') or analysis_data.get('score')
            
            cursor.execute('''
                INSERT INTO analysis (lead_id, seo_score, issues, strengths, recommendations, pagespeed_data, contact_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead_id,
                seo_score,
                json.dumps(analysis_data.get('issues', [])),
                json.dumps(analysis_data.get('strengths', [])),
                json.dumps(analysis_data.get('recommendations', [])),
                json.dumps(analysis_data.get('pagespeed', {})),
                json.dumps(analysis_data.get('contacts', {}))
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_outreach(self, lead_id, status, notes=None):
        """Update outreach status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if outreach record exists
            cursor.execute('SELECT id FROM outreach WHERE lead_id = ?', (lead_id,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE outreach 
                    SET status = ?, last_contacted = ?, notes = COALESCE(?, notes)
                    WHERE lead_id = ?
                ''', (status, datetime.now().isoformat(), notes, lead_id))
            else:
                cursor.execute('''
                    INSERT INTO outreach (lead_id, status, notes)
                    VALUES (?, ?, ?)
                ''', (lead_id, status, notes))
            
            conn.commit()
    
    def save_email_draft(self, lead_id, email_draft):
        """Save generated email draft for a lead"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if outreach record exists
            cursor.execute('SELECT id FROM outreach WHERE lead_id = ?', (lead_id,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE outreach 
                    SET email_draft = ?
                    WHERE lead_id = ?
                ''', (json.dumps(email_draft), lead_id))
            else:
                cursor.execute('''
                    INSERT INTO outreach (lead_id, status, email_draft)
                    VALUES (?, 'pending', ?)
                ''', (lead_id, json.dumps(email_draft)))
            
            conn.commit()
    
    def get_email_draft(self, lead_id):
        """Get email draft for a lead"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email_draft FROM outreach WHERE lead_id = ?', (lead_id,))
            row = cursor.fetchone()
            
            if row and row[0]:
                return json.loads(row[0])
            return None
    
    def get_lead(self, lead_id):
        """Get lead by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'url': row[1],
                    'title': row[2],
                    'type': row[3],
                    'location': row[4],
                    'ranking_position': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
    
    def get_lead_by_url(self, url):
        """Get lead by URL"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM leads WHERE url = ?', (url,))
            row = cursor.fetchone()
            
            if row:
                return self.get_lead(row[0])
            return None
    
    def get_all_leads(self, lead_type=None):
        """Get all leads, optionally filtered by type"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if lead_type:
                cursor.execute('SELECT * FROM leads WHERE type = ? ORDER BY created_at DESC', (lead_type,))
            else:
                cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            
            return [{
                'id': row[0],
                'url': row[1],
                'title': row[2],
                'type': row[3],
                'location': row[4],
                'ranking_position': row[5],
                'created_at': row[6],
                'updated_at': row[7]
            } for row in rows]
    
    def get_latest_analysis(self, lead_id):
        """Get latest analysis for a lead"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM analysis 
                WHERE lead_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (lead_id,))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'lead_id': row[1],
                    'seo_score': row[2],
                    'issues': json.loads(row[3]) if row[3] else [],
                    'strengths': json.loads(row[4]) if row[4] else [],
                    'recommendations': json.loads(row[5]) if row[5] else [],
                    'pagespeed_data': json.loads(row[6]) if row[6] else {},
                    'contact_info': json.loads(row[7]) if row[7] else {},
                    'created_at': row[8]
                }
            return None
    
    def get_outreach_status(self, lead_id):
        """Get outreach status for a lead"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM outreach WHERE lead_id = ?', (lead_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'lead_id': row[1],
                    'status': row[2],
                    'contact_email': row[3],
                    'contact_phone': row[4],
                    'last_contacted': row[5],
                    'notes': row[6],
                    'created_at': row[7]
                }
            return None
    
    def log_search(self, query, location, results_count):
        """Log a search query"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO search_history (query, location, results_count)
                VALUES (?, ?, ?)
            ''', (query, location, results_count))
            conn.commit()
    
    def get_stats(self):
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute('SELECT COUNT(*) FROM leads')
            stats['total_leads'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM leads WHERE type = ?', ('solar',))
            stats['solar_leads'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM leads WHERE type = ?', ('pool',))
            stats['pool_leads'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM outreach WHERE status = ?', ('contacted',))
            stats['contacted'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM outreach WHERE status = ?', ('responded',))
            stats['responded'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM outreach WHERE status = ?', ('closed',))
            stats['closed'] = cursor.fetchone()[0]
            
            return stats
    
    def export_to_json(self, output_path='leads_export.json'):
        """Export all leads to JSON"""
        leads = self.get_all_leads()
        
        export = {
            'exported_at': datetime.now().isoformat(),
            'total_leads': len(leads),
            'leads': []
        }
        
        for lead in leads:
            analysis = self.get_latest_analysis(lead['id'])
            outreach = self.get_outreach_status(lead['id'])
            
            export['leads'].append({
                **lead,
                'analysis': analysis,
                'outreach': outreach
            })
        
        with open(output_path, 'w') as f:
            json.dump(export, f, indent=2)
        
        return output_path
