"""
Módulo para manejar la base de datos de jobs
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from threading import Lock

# Lock para operaciones de base de datos
db_lock = Lock()

# Ruta de la base de datos
DB_PATH = Path("data/jobs.db")

def init_db():
    """Inicializa la base de datos"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                config TEXT,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

def create_job(job_id, filename, file_path, config):
    """Crea un nuevo job en la base de datos"""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO jobs (id, filename, file_path, config, status, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, filename, file_path, json.dumps(config), 'queued', 0, now, now))
        
        conn.commit()
        conn.close()

def get_job(job_id):
    """Obtiene un job por su ID"""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            job = dict(row)
            # Parsear JSON
            if job['config']:
                job['config'] = json.loads(job['config'])
            if job['result']:
                job['result'] = json.loads(job['result'])
            return job
        return None

def get_all_jobs(status=None, limit=100):
    """Obtiene todos los jobs, opcionalmente filtrados por estado"""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            job = dict(row)
            # Parsear JSON
            if job['config']:
                job['config'] = json.loads(job['config'])
            if job['result']:
                job['result'] = json.loads(job['result'])
            jobs.append(job)
        
        return jobs

def update_job(job_id, status=None, progress=None, result=None, error=None):
    """Actualiza un job"""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        
        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result))
        
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        params.append(job_id)
        
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()

def delete_old_jobs(days=7):
    """Elimina jobs antiguos"""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        
        cursor.execute(
            "DELETE FROM jobs WHERE created_at < ? AND status IN ('completed', 'failed')",
            (cutoff_date.isoformat(),)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted

