# storage.py
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Tuple

SCHEMA = """
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
                                             is_open INTEGER NOT NULL,
                                             closed_at TEXT,
                                             pilot_score INTEGER DEFAULT 0,
                                             description TEXT,
                                             UNIQUE (source, external_id)
             ); \
         """

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def init_db(path="jobs.db"):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(SCHEMA)

    # Paso adicional: agregar columna pilot_score si no existe
    cur = conn.execute("PRAGMA table_info(jobs)")
    columns = [row[1] for row in cur.fetchall()]  # nombres de columnas
    if "pilot_score" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN pilot_score INTEGER DEFAULT 0")
        print("→ Columna 'pilot_score' agregada a la tabla 'jobs'")

    conn.commit()
    return conn


def snapshot_open_jobs(conn) -> Dict[Tuple[str,str], Dict]:
    cur = conn.execute("SELECT source, external_id FROM jobs WHERE is_open=1")
    return {(row[0], row[1]): {} for row in cur.fetchall()}

def upsert_jobs(conn, jobs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Devuelve (opened, closed) para notificar.
    - opened: nuevas aperturas detectadas en esta corrida
    - closed: cierres detectados por desaparición
    """
    seen_now = set()
    opened = []

    now = now_iso()
    for j in jobs:
        key = (j["source"], j["external_id"])
        seen_now.add(key)
        cur = conn.execute("SELECT id, is_open FROM jobs WHERE source=? AND external_id=?", key)
        row = cur.fetchone()
        if row is None:
            # Nuevo
            conn.execute("""
                         INSERT INTO jobs (source, company, external_id, title, location, url, department, remote,
                                           posted_at, updated_at, first_seen, last_seen, is_open, closed_at, pilot_score, description)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, ?)
                         """, (
                             j.get("source"), j.get("company"), j.get("external_id"), j.get("title"), j.get("location"),
                             j.get("url"), j.get("department"), j.get("remote"),
                             j.get("posted_at"), j.get("updated_at"), now, now, j.get("pilot_score", 0), j.get("description", "")
                         ))
            opened.append(j)
        else:
            # Existe: refresca last_seen y campos básicos
            conn.execute("""
                         UPDATE jobs SET title=?, location=?, url=?, department=?, remote=?,
                                         posted_at=?, updated_at=?, last_seen=?, company=?, pilot_score=?, description=?
                         WHERE source=? AND external_id=?
                         """, (
                             j.get("title"), j.get("location"), j.get("url"), j.get("department"), j.get("remote"),
                             j.get("posted_at"), j.get("updated_at"), now, j.get("company"), j.get("pilot_score", 0), j.get("description", ""),
                             j["source"], j["external_id"]
                         ))

    # Cierres: lo que estaba abierto y no se vio ahora
    prev_open = snapshot_open_jobs(conn)
    closed = []
    to_close = [k for k in prev_open.keys() if k not in seen_now]
    for (source, external_id) in to_close:
        conn.execute("""
                     UPDATE jobs SET is_open=0, closed_at=? WHERE source=? AND external_id=?
                     """, (now, source, external_id))
        # Buscar datos para notificación
        cur = conn.execute("""
                           SELECT company, title, location, url FROM jobs WHERE source=? AND external_id=?
                           """, (source, external_id))
        c = cur.fetchone()
        closed.append({
            "source": source,
            "external_id": external_id,
            "company": c[0],
            "title": c[1],
            "location": c[2],
            "url": c[3],
        })

    conn.commit()
    return opened, closed
