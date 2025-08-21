# storage_enhanced.py
"""
Enhanced storage system with better job tracking, deduplication, and status management.
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Enhanced schema with better tracking
ENHANCED_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    company TEXT,
    external_id TEXT NOT NULL,
    title TEXT,
    location TEXT,
    url TEXT,
    department TEXT,
    remote INTEGER,
    posted_at TEXT,
    updated_at TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    is_open INTEGER NOT NULL DEFAULT 1,
    closed_at TEXT,
    pilot_score INTEGER DEFAULT 0,
    description TEXT,
    job_hash TEXT,  -- Hash of job content for change detection
    times_seen INTEGER DEFAULT 1,
    reopen_count INTEGER DEFAULT 0,  -- Track how many times job was reopened
    UNIQUE (source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_source_external_id ON jobs(source, external_id);
CREATE INDEX IF NOT EXISTS idx_jobs_is_open ON jobs(is_open);
CREATE INDEX IF NOT EXISTS idx_jobs_job_hash ON jobs(job_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen);

-- Table to track job status changes for better analytics
CREATE TABLE IF NOT EXISTS job_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    status_change TEXT,  -- 'opened', 'closed', 'reopened'
    changed_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);

-- Table to track scraping runs for analytics
CREATE TABLE IF NOT EXISTS scraping_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_start TEXT NOT NULL,
    run_end TEXT,
    total_sources INTEGER DEFAULT 0,
    successful_sources INTEGER DEFAULT 0,
    failed_sources INTEGER DEFAULT 0,
    total_jobs_found INTEGER DEFAULT 0,
    new_jobs INTEGER DEFAULT 0,
    closed_jobs INTEGER DEFAULT 0,
    errors_summary TEXT  -- JSON string with error details
);
"""

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def init_enhanced_db(path="jobs.db"):
    """Initialize database with enhanced schema"""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(ENHANCED_SCHEMA)
    
    # Migration: add new columns if they don't exist
    cur = conn.execute("PRAGMA table_info(jobs)")
    existing_columns = {row[1] for row in cur.fetchall()}
    
    new_columns = {
        'job_hash': 'TEXT',
        'times_seen': 'INTEGER DEFAULT 1',
        'reopen_count': 'INTEGER DEFAULT 0'
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added column '{col_name}' to jobs table")
    
    conn.commit()
    return conn

def generate_job_hash(job: Dict) -> str:
    """Generate a hash of job content for change detection"""
    # Use key fields to detect meaningful changes
    hash_fields = [
        job.get('title', ''),
        job.get('location', ''),
        job.get('department', ''),
        job.get('description', '')[:500]  # First 500 chars of description
    ]
    
    content = '|'.join(str(field) for field in hash_fields)
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def create_unique_id(job: Dict) -> str:
    """Create a more robust unique ID for jobs"""
    # Use URL if available, otherwise create from key fields
    if job.get('url'):
        return job['url']
    
    # Fallback: create ID from source + company + title
    id_parts = [
        job.get('source', ''),
        job.get('company', ''),
        job.get('title', '')[:100]  # Limit title length
    ]
    
    clean_parts = [part.strip().lower().replace(' ', '_') for part in id_parts if part]
    return '_'.join(clean_parts)

def start_scraping_run(conn) -> int:
    """Start a new scraping run and return run ID"""
    cur = conn.execute(
        "INSERT INTO scraping_runs (run_start) VALUES (?)",
        (now_iso(),)
    )
    conn.commit()
    return cur.lastrowid

def finish_scraping_run(conn, run_id: int, stats: Dict):
    """Finish a scraping run with statistics"""
    conn.execute("""
        UPDATE scraping_runs SET 
            run_end = ?,
            total_sources = ?,
            successful_sources = ?,
            failed_sources = ?,
            total_jobs_found = ?,
            new_jobs = ?,
            closed_jobs = ?,
            errors_summary = ?
        WHERE id = ?
    """, (
        now_iso(),
        stats.get('total_sources', 0),
        stats.get('successful_sources', 0),
        stats.get('failed_sources', 0),
        stats.get('total_jobs_found', 0),
        stats.get('new_jobs', 0),
        stats.get('closed_jobs', 0),
        json.dumps(stats.get('errors', {})),
        run_id
    ))
    conn.commit()

def upsert_jobs_enhanced(conn, jobs: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Enhanced job upsertion with better change detection.
    Returns (opened, closed, updated) for notifications.
    """
    seen_now = set()
    opened = []
    updated = []
    
    now = now_iso()
    
    for job in jobs:
        # Generate better external ID if not present
        if not job.get('external_id'):
            job['external_id'] = create_unique_id(job)
        
        # Generate job hash for change detection
        job_hash = generate_job_hash(job)
        
        key = (job["source"], job["external_id"])
        seen_now.add(key)
        
        # Check if job exists
        cur = conn.execute(
            "SELECT id, is_open, job_hash, times_seen FROM jobs WHERE source=? AND external_id=?", 
            key
        )
        row = cur.fetchone()
        
        if row is None:
            # New job
            conn.execute("""
                INSERT INTO jobs (
                    source, company, external_id, title, location, url, department, remote,
                    posted_at, updated_at, first_seen, last_seen, is_open, closed_at, 
                    pilot_score, description, job_hash, times_seen, reopen_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, ?, ?, 1, 0)
            """, (
                job.get("source"), job.get("company"), job.get("external_id"), 
                job.get("title"), job.get("location"), job.get("url"), 
                job.get("department"), job.get("remote"), job.get("posted_at"), 
                job.get("updated_at"), now, now, job.get("pilot_score", 0), 
                job.get("description", ""), job_hash
            ))
            
            job_id = conn.lastrowid
            
            # Record status change
            conn.execute(
                "INSERT INTO job_status_history (job_id, status_change, changed_at) VALUES (?, 'opened', ?)",
                (job_id, now)
            )
            
            opened.append(job)
            logger.debug(f"New job: {job.get('title')} at {job.get('company')}")
            
        else:
            job_id, is_open, old_hash, times_seen = row
            
            # Check if job was closed and is now reopening
            if not is_open:
                # Job is reopening
                conn.execute("""
                    UPDATE jobs SET 
                        is_open = 1, closed_at = NULL, last_seen = ?, 
                        times_seen = ?, reopen_count = reopen_count + 1,
                        title = ?, location = ?, url = ?, company = ?, 
                        pilot_score = ?, description = ?, job_hash = ?
                    WHERE id = ?
                """, (
                    now, times_seen + 1, job.get("title"), job.get("location"), 
                    job.get("url"), job.get("company"), job.get("pilot_score", 0), 
                    job.get("description", ""), job_hash, job_id
                ))
                
                # Record status change
                conn.execute(
                    "INSERT INTO job_status_history (job_id, status_change, changed_at) VALUES (?, 'reopened', ?)",
                    (job_id, now)
                )
                
                opened.append(job)  # Treat reopened jobs as new
                logger.info(f"Job reopened: {job.get('title')} at {job.get('company')}")
                
            else:
                # Job is still open - update fields and check for changes
                significant_change = old_hash != job_hash
                
                conn.execute("""
                    UPDATE jobs SET 
                        title = ?, location = ?, url = ?, department = ?, remote = ?,
                        posted_at = ?, updated_at = ?, last_seen = ?, company = ?, 
                        pilot_score = ?, description = ?, job_hash = ?, times_seen = ?
                    WHERE id = ?
                """, (
                    job.get("title"), job.get("location"), job.get("url"), 
                    job.get("department"), job.get("remote"), job.get("posted_at"), 
                    job.get("updated_at"), now, job.get("company"), 
                    job.get("pilot_score", 0), job.get("description", ""), 
                    job_hash, times_seen + 1, job_id
                ))
                
                if significant_change:
                    updated.append(job)
                    logger.debug(f"Job updated: {job.get('title')} at {job.get('company')}")

    # Detect closed jobs (were open but not seen in this run)
    prev_open = get_currently_open_jobs(conn)
    closed = []
    
    to_close = [k for k in prev_open.keys() if k not in seen_now]
    
    for (source, external_id) in to_close:
        # Get job details for notification
        cur = conn.execute("""
            SELECT id, company, title, location, url FROM jobs 
            WHERE source=? AND external_id=? AND is_open=1
        """, (source, external_id))
        
        job_row = cur.fetchone()
        if job_row:
            job_id, company, title, location, url = job_row
            
            # Mark as closed
            conn.execute("""
                UPDATE jobs SET is_open=0, closed_at=? WHERE id=?
            """, (now, job_id))
            
            # Record status change
            conn.execute(
                "INSERT INTO job_status_history (job_id, status_change, changed_at) VALUES (?, 'closed', ?)",
                (job_id, now)
            )
            
            closed.append({
                "source": source,
                "external_id": external_id,
                "company": company,
                "title": title,
                "location": location,
                "url": url,
            })
            
            logger.debug(f"Job closed: {title} at {company}")

    conn.commit()
    return opened, closed, updated

def get_currently_open_jobs(conn) -> Dict[Tuple[str, str], Dict]:
    """Get all currently open jobs"""
    cur = conn.execute("SELECT source, external_id FROM jobs WHERE is_open=1")
    return {(row[0], row[1]): {} for row in cur.fetchall()}

def get_job_statistics(conn) -> Dict:
    """Get comprehensive job statistics"""
    stats = {}
    
    # Overall stats
    cur = conn.execute("SELECT COUNT(*) FROM jobs")
    stats['total_jobs_ever'] = cur.fetchone()[0]
    
    cur = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_open=1")
    stats['currently_open'] = cur.fetchone()[0]
    
    cur = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_open=0")
    stats['total_closed'] = cur.fetchone()[0]
    
    # Jobs by source
    cur = conn.execute("""
        SELECT source, COUNT(*) as count, SUM(is_open) as open_count 
        FROM jobs GROUP BY source ORDER BY count DESC
    """)
    stats['by_source'] = [
        {'source': row[0], 'total': row[1], 'open': row[2]} 
        for row in cur.fetchall()
    ]
    
    # Recent activity (last 24 hours)
    cur = conn.execute("""
        SELECT COUNT(*) FROM jobs 
        WHERE first_seen > datetime('now', '-1 day')
    """)
    stats['new_last_24h'] = cur.fetchone()[0]
    
    cur = conn.execute("""
        SELECT COUNT(*) FROM jobs 
        WHERE closed_at > datetime('now', '-1 day')
    """)
    stats['closed_last_24h'] = cur.fetchone()[0]
    
    return stats

def cleanup_old_data(conn, days_to_keep: int = 90):
    """Clean up old job data to prevent database from growing too large"""
    cutoff_date = datetime.now(timezone.utc).isoformat()
    
    # Delete old closed jobs
    cur = conn.execute("""
        DELETE FROM jobs 
        WHERE is_open = 0 AND closed_at < datetime('now', '-{} days')
    """.format(days_to_keep))
    
    deleted_jobs = cur.rowcount
    
    # Clean up old scraping runs
    cur = conn.execute("""
        DELETE FROM scraping_runs 
        WHERE run_start < datetime('now', '-{} days')
    """.format(days_to_keep))
    
    deleted_runs = cur.rowcount
    
    conn.commit()
    
    logger.info(f"Cleaned up {deleted_jobs} old jobs and {deleted_runs} old runs")
    return deleted_jobs, deleted_runs