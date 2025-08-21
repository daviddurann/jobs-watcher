# main.py
import os, sys, yaml, time, logging
from typing import List, Dict
from datetime import datetime
from storage import init_db, upsert_jobs
from notifier import notify_changes
from extractors import fetch_one
from job_filter import filter_pilot_jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config(path="config_enhanced.yml") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run(config_path="config_enhanced.yml", db_path="jobs.db"):
    start_time = datetime.now()
    logger.info(f"Starting job tracker run at {start_time}")

    cfg = load_config(config_path)
    telegram_cfg = cfg.get("telegram", {})
    targets = cfg.get("targets", [])
    filtering_cfg = cfg.get("filtering", {})

    conn = init_db(db_path)

    all_jobs: List[Dict] = []
    successful_sources = 0
    failed_sources = 0
    total_sources = len(targets)

    # Statistics tracking
    error_stats = {}
    region_stats = {}

    for i, t in enumerate(targets):
        company_name = t.get('company', 'Unknown')
        source_type = t.get('source', 'unknown')

        try:
            logger.info(f"[{i+1}/{total_sources}] Fetching from {company_name} ({source_type})...")

            start_source_time = time.time()
            jobs = fetch_one(t)
            source_duration = time.time() - start_source_time

            # Apply pilot job filtering if enabled
            if filtering_cfg.get("pilot_jobs_only", False):
                jobs = filter_pilot_jobs(jobs)

            # Apply minimum pilot score if set
            min_score = filtering_cfg.get("minimum_pilot_score", 0)
            if min_score > 0:
                jobs = [job for job in jobs if job.get('pilot_score', 0) >= min_score]

            all_jobs.extend(jobs)
            successful_sources += 1

            # Track regional statistics
            region = t.get('region', 'Unknown')
            if region not in region_stats:
                region_stats[region] = {'successful': 0, 'failed': 0, 'jobs': 0}
            region_stats[region]['successful'] += 1
            region_stats[region]['jobs'] += len(jobs)

            logger.info(f"  ✅ Found {len(jobs)} pilot-related jobs in {source_duration:.2f}s")

        except Exception as e:
            failed_sources += 1
            error_type = type(e).__name__
            if error_type not in error_stats:
                error_stats[error_type] = 0
            error_stats[error_type] += 1

            # Track regional failure statistics
            region = t.get('region', 'Unknown')
            if region not in region_stats:
                region_stats[region] = {'successful': 0, 'failed': 0, 'jobs': 0}
            region_stats[region]['failed'] += 1

            logger.error(f"  ❌ Error in {company_name}: {e}")

        # Add small delay to be respectful to websites
        time.sleep(1)

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    logger.info(f"\n=== EXECUTION SUMMARY ===")
    logger.info(f"Execution time: {total_duration:.2f} seconds")
    logger.info(f"Sources processed: {successful_sources}/{total_sources} ({failed_sources} failed)")
    logger.info(f"Success rate: {(successful_sources/total_sources*100):.1f}%")
    logger.info(f"Total pilot jobs found: {len(all_jobs)}")

    # Log error statistics
    if error_stats:
        logger.info(f"\n=== ERROR BREAKDOWN ===")
        for error_type, count in sorted(error_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"{error_type}: {count} occurrences")

    # Log regional statistics
    if region_stats:
        logger.info(f"\n=== REGIONAL BREAKDOWN ===")
        for region, stats in sorted(region_stats.items()):
            total_sources_region = stats['successful'] + stats['failed']
            success_rate = (stats['successful']/total_sources_region*100) if total_sources_region > 0 else 0
            logger.info(f"{region}: {stats['successful']}/{total_sources_region} sources ({success_rate:.1f}%), {stats['jobs']} jobs")

    opened, closed = upsert_jobs(conn, all_jobs)
    logger.info(f"Database changes: {len(opened)} new jobs, {len(closed)} closed jobs")

    # Send notifications
    if opened or closed:
        try:
            notify_changes(opened, closed, telegram_cfg)
            logger.info(f"Notifications sent via Telegram: {len(opened)} new, {len(closed)} closed")
        except Exception as e:
            logger.error(f"Failed to send Telegram notifications: {e}")
    else:
        logger.info("No job changes to notify")

    logger.info(f"Job tracker run completed at {end_time}")

if __name__ == "__main__":
    # Handle command line arguments
    import sys
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = os.getenv("CONFIG_PATH", "config_enhanced.yml")

    db_path = os.getenv("DB_PATH", "jobs.db")
    run(config_path, db_path)
