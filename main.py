# main.py
import os, sys, yaml
from typing import List, Dict
from storage import init_db, upsert_jobs
from notifier import notify_changes
from extractors import fetch_one
from job_filter import filter_pilot_jobs

def load_config(path="config_enhanced.yml") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run(config_path="config_enhanced.yml", db_path="jobs.db"):
    cfg = load_config(config_path)
    telegram_cfg = cfg.get("telegram", {})
    targets = cfg.get("targets", [])
    filtering_cfg = cfg.get("filtering", {})

    conn = init_db(db_path)

    all_jobs: List[Dict] = []
    successful_sources = 0
    total_sources = len(targets)

    for i, t in enumerate(targets):
        try:
            print(f"[{i+1}/{total_sources}] Fetching from {t.get('company', 'Unknown')} ({t.get('source')})...")
            jobs = fetch_one(t)

            # Apply pilot job filtering if enabled
            if filtering_cfg.get("pilot_jobs_only", False):
                jobs = filter_pilot_jobs(jobs)

            # Apply minimum pilot score if set
            min_score = filtering_cfg.get("minimum_pilot_score", 0)
            if min_score > 0:
                jobs = [job for job in jobs if job.get('pilot_score', 0) >= min_score]

            all_jobs.extend(jobs)
            successful_sources += 1
            print(f"  → Found {len(jobs)} pilot-related jobs")

        except Exception as e:
            print(f"[WARN] Error en {t.get('company') or t.get('source')}: {e}", file=sys.stderr)

    print(f"\n=== SUMMARY ===")
    print(f"Sources processed: {successful_sources}/{total_sources}")
    print(f"Total pilot jobs found: {len(all_jobs)}")

    opened, closed = upsert_jobs(conn, all_jobs)
    print(f"Changes detected: {len(opened)} new, {len(closed)} closed")

    # Send notifications
    if opened or closed:
        notify_changes(opened, closed, telegram_cfg)
        print(f"Notifications sent via Telegram")
    else:
        print("No changes to notify")

if __name__ == "__main__":
    config_path = os.getenv("CONFIG_PATH", "config_enhanced.yml")
    db_path = os.getenv("DB_PATH", "jobs.db")
    run(config_path, db_path)
