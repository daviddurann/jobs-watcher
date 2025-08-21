# main.py
import os, sys, yaml
from typing import List, Dict
from storage import init_db, upsert_jobs
from notifier import notify_changes
from extractors import fetch_one

def load_config(path="config.yml") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run(config_path="config.yml", db_path="jobs.db"):
    cfg = load_config(config_path)
    telegram_cfg = cfg.get("telegram", {})
    targets = cfg.get("targets", [])

    conn = init_db(db_path)

    all_jobs: List[Dict] = []
    for t in targets:
        try:
            jobs = fetch_one(t)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[WARN] Error en {t.get('company') or t.get('source')}: {e}", file=sys.stderr)

    opened, closed = upsert_jobs(conn, all_jobs)
    print(f"Detectados: {len(opened)} abiertos, {len(closed)} cerrados")

    notify_changes(opened, closed, telegram_cfg)

if __name__ == "__main__":
    config_path = os.getenv("CONFIG_PATH", "config.yml")
    db_path = os.getenv("DB_PATH", "jobs.db")
    run(config_path, db_path)
