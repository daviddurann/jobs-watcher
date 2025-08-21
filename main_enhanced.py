# main_enhanced.py
"""
Enhanced job tracker with improved dynamic site support, better deduplication,
and status management.
"""

import os, sys, yaml, time, logging
from typing import List, Dict
from datetime import datetime
from storage_enhanced import (
    init_enhanced_db, upsert_jobs_enhanced, start_scraping_run, 
    finish_scraping_run, get_job_statistics, cleanup_old_data
)
from notifier_enhanced import notify_changes_enhanced
from extractors import fetch_one
from job_filter import filter_pilot_jobs
import traceback
import json

# Configure enhanced logging
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

def test_problematic_sites(targets: List[Dict]) -> List[Dict]:
    """Test the specific sites mentioned in the requirements"""
    problem_sites = [
        "trabajaconnosotros.bintercanarias.com",
        "jobs.aireuropa.bizneo.cloud", 
        "careers.wizzair.com"
    ]
    
    tested_targets = []
    for target in targets:
        url = target.get('url', '')
        if any(site in url for site in problem_sites):
            tested_targets.append(target)
    
    return tested_targets

def run_enhanced(config_path="config_enhanced.yml", db_path="jobs.db"):
    start_time = datetime.now()
    logger.info(f"🚀 Starting ENHANCED job tracker run at {start_time}")

    cfg = load_config(config_path)
    telegram_cfg = cfg.get("telegram", {})
    targets = cfg.get("targets", [])
    filtering_cfg = cfg.get("filtering", {})

    # Initialize enhanced database
    conn = init_enhanced_db(db_path)
    run_id = start_scraping_run(conn)

    all_jobs: List[Dict] = []
    successful_sources = 0
    failed_sources = 0
    total_sources = len(targets)

    # Enhanced statistics tracking
    error_stats = {}
    region_stats = {}
    source_type_stats = {}
    
    # Test problematic sites first to verify improvements
    problem_targets = test_problematic_sites(targets)
    if problem_targets:
        logger.info(f"🎯 Testing {len(problem_targets)} previously problematic sites first...")
        
        for target in problem_targets:
            logger.info(f"🔍 Testing: {target['company']} ({target['url']})")
            try:
                jobs = fetch_one(target)
                logger.info(f"  ✅ SUCCESS: Found {len(jobs)} jobs from {target['company']}")
                if jobs:
                    for job in jobs[:3]:  # Show first 3 jobs as examples
                        logger.info(f"    📋 {job.get('title', 'No title')} - {job.get('location', 'No location')}")
            except Exception as e:
                logger.error(f"  ❌ FAILED: {target['company']} - {e}")

    # Process all targets
    for i, target in enumerate(targets):
        company_name = target.get('company', 'Unknown')
        source_type = target.get('source', 'unknown')

        try:
            logger.info(f"[{i+1}/{total_sources}] Fetching from {company_name} ({source_type})...")

            start_source_time = time.time()
            jobs = fetch_one(target)
            source_duration = time.time() - start_source_time

            # Enhanced filtering
            original_count = len(jobs)
            
            # Apply pilot job filtering if enabled
            if filtering_cfg.get("pilot_jobs_only", False):
                jobs = filter_pilot_jobs(jobs)

            # Apply minimum pilot score if set
            min_score = filtering_cfg.get("minimum_pilot_score", 0)
            if min_score > 0:
                jobs = [job for job in jobs if job.get('pilot_score', 0) >= min_score]

            filtered_count = len(jobs)
            all_jobs.extend(jobs)
            successful_sources += 1

            # Track enhanced statistics
            region = target.get('region', 'Unknown')
            if region not in region_stats:
                region_stats[region] = {'successful': 0, 'failed': 0, 'jobs': 0, 'filtered_jobs': 0}
            region_stats[region]['successful'] += 1
            region_stats[region]['jobs'] += original_count
            region_stats[region]['filtered_jobs'] += filtered_count

            # Track by source type
            if source_type not in source_type_stats:
                source_type_stats[source_type] = {'successful': 0, 'failed': 0, 'jobs': 0}
            source_type_stats[source_type]['successful'] += 1
            source_type_stats[source_type]['jobs'] += filtered_count

            if original_count != filtered_count:
                logger.info(f"  ✅ Found {original_count} jobs, {filtered_count} pilot-related (filtered) in {source_duration:.2f}s")
            else:
                logger.info(f"  ✅ Found {filtered_count} pilot-related jobs in {source_duration:.2f}s")

        except Exception as e:
            failed_sources += 1
            error_type = type(e).__name__
            if error_type not in error_stats:
                error_stats[error_type] = []
            error_stats[error_type].append({
                'company': company_name,
                'source': source_type,
                'error': str(e)[:200]  # Truncate long errors
            })

            # Track regional failure statistics
            region = target.get('region', 'Unknown')
            if region not in region_stats:
                region_stats[region] = {'successful': 0, 'failed': 0, 'jobs': 0, 'filtered_jobs': 0}
            region_stats[region]['failed'] += 1

            # Track source type failures
            if source_type not in source_type_stats:
                source_type_stats[source_type] = {'successful': 0, 'failed': 0, 'jobs': 0}
            source_type_stats[source_type]['failed'] += 1

            logger.error(f"  ❌ Error in {company_name}: {e}")
            
            # Log full traceback for debugging in debug mode
            if os.getenv('DEBUG'):
                logger.debug(f"Full traceback: {traceback.format_exc()}")

        # Add respectful delay
        time.sleep(1)

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    # Enhanced job processing with better change detection
    logger.info("📊 Processing job changes...")
    opened, closed, updated = upsert_jobs_enhanced(conn, all_jobs)
    
    # Get database statistics
    db_stats = get_job_statistics(conn)

    # Log comprehensive execution summary
    logger.info(f"\n=== 🎯 ENHANCED EXECUTION SUMMARY ===")
    logger.info(f"⏱️  Execution time: {total_duration:.2f} seconds")
    logger.info(f"📡 Sources processed: {successful_sources}/{total_sources} ({failed_sources} failed)")
    logger.info(f"📈 Success rate: {(successful_sources/total_sources*100):.1f}%")
    logger.info(f"🔍 Total jobs found: {len(all_jobs)}")
    logger.info(f"🆕 New jobs: {len(opened)}")
    logger.info(f"🔄 Updated jobs: {len(updated)}")
    logger.info(f"🔴 Closed jobs: {len(closed)}")
    logger.info(f"📊 Currently open jobs: {db_stats['currently_open']}")
    logger.info(f"📚 Total jobs in database: {db_stats['total_jobs_ever']}")

    # Log error statistics with details
    if error_stats:
        logger.info(f"\n=== 🚨 ERROR BREAKDOWN ===")
        for error_type, errors in sorted(error_stats.items(), key=lambda x: len(x[1]), reverse=True):
            logger.info(f"{error_type}: {len(errors)} occurrences")
            # Show first few examples
            for error_detail in errors[:3]:
                logger.info(f"  • {error_detail['company']} ({error_detail['source']}): {error_detail['error']}")

    # Log regional statistics
    if region_stats:
        logger.info(f"\n=== 🌍 REGIONAL BREAKDOWN ===")
        for region, stats in sorted(region_stats.items()):
            total_sources_region = stats['successful'] + stats['failed']
            success_rate = (stats['successful']/total_sources_region*100) if total_sources_region > 0 else 0
            logger.info(f"{region}: {stats['successful']}/{total_sources_region} sources ({success_rate:.1f}%), {stats['filtered_jobs']} filtered jobs")

    # Log source type statistics
    if source_type_stats:
        logger.info(f"\n=== 🔧 SOURCE TYPE BREAKDOWN ===")
        for source_type, stats in sorted(source_type_stats.items(), key=lambda x: x[1]['jobs'], reverse=True):
            total_sources_type = stats['successful'] + stats['failed']
            success_rate = (stats['successful']/total_sources_type*100) if total_sources_type > 0 else 0
            logger.info(f"{source_type}: {stats['successful']}/{total_sources_type} sources ({success_rate:.1f}%), {stats['jobs']} jobs")

    # Finish scraping run tracking
    run_stats = {
        'total_sources': total_sources,
        'successful_sources': successful_sources,
        'failed_sources': failed_sources,
        'total_jobs_found': len(all_jobs),
        'new_jobs': len(opened),
        'closed_jobs': len(closed),
        'errors': error_stats
    }
    finish_scraping_run(conn, run_id, run_stats)

    # Enhanced notifications - only send changes
    if opened or closed or updated:
        try:
            notify_changes_enhanced(opened, closed, updated, telegram_cfg, db_stats)
            logger.info(f"📱 Notifications sent: {len(opened)} new, {len(closed)} closed, {len(updated)} updated")
        except Exception as e:
            logger.error(f"Failed to send Telegram notifications: {e}")
            if os.getenv('DEBUG'):
                logger.debug(f"Notification error traceback: {traceback.format_exc()}")
    else:
        logger.info("📱 No job changes to notify")

    # Cleanup old data periodically (every 7 days)
    import random
    if random.random() < 0.14:  # ~14% chance = roughly once per week
        logger.info("🧹 Performing periodic cleanup...")
        deleted_jobs, deleted_runs = cleanup_old_data(conn)
        if deleted_jobs > 0 or deleted_runs > 0:
            logger.info(f"🧹 Cleaned up {deleted_jobs} old jobs and {deleted_runs} old runs")

    logger.info(f"✅ Enhanced job tracker run completed at {end_time}")
    
    # Close database connection
    conn.close()

    return {
        'success': True,
        'stats': run_stats,
        'db_stats': db_stats,
        'duration': total_duration
    }

if __name__ == "__main__":
    # Handle command line arguments
    import sys
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = os.getenv("CONFIG_PATH", "config_enhanced.yml")

    db_path = os.getenv("DB_PATH", "jobs.db")
    
    try:
        result = run_enhanced(config_path, db_path)
        if result['success']:
            logger.info("🎉 Job tracking completed successfully!")
        else:
            logger.error("❌ Job tracking completed with errors")
            sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Fatal error in job tracker: {e}")
        if os.getenv('DEBUG'):
            logger.error(f"Fatal error traceback: {traceback.format_exc()}")
        sys.exit(1)