#!/usr/bin/env python3
"""
Demo script to showcase all the improvements to the job scraper.
This will test the specific sites mentioned in the requirements.
"""

import os
import logging
from extractors.dynamic_sites import fetch_dynamic_jobs
from storage_enhanced import init_enhanced_db, upsert_jobs_enhanced, get_job_statistics
from notifier_enhanced import send_test_notification
from job_filter import add_pilot_score, filter_pilot_jobs

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_dynamic_site_improvements():
    """Test the improved dynamic site scraping"""
    
    logger.info("🚀 TESTING DYNAMIC SITE IMPROVEMENTS")
    logger.info("=" * 60)
    
    # Test the specific problematic sites mentioned in requirements
    problem_sites = [
        {
            'name': 'Binter Canarias',
            'url': 'https://trabajaconnosotros.bintercanarias.com/jobs',
            'config': {
                'company': 'Binter Canarias',
                'wait_for': '.job-offer, .job-item, .job-card',
                'selectors': {
                    'item': '.job-offer, .job-item, .job-card, .career-item, .position',
                    'title': '.job-title, h3, .title, [data-job-title]',
                    'location': '.job-location, .location, .city',
                    'url': 'a::attr(href)'
                }
            }
        },
        {
            'name': 'Air Europa (Bizneo)',
            'url': 'https://jobs.aireuropa.bizneo.cloud/jobs',
            'config': {
                'company': 'Air Europa',
                'wait_for': '.job-offer, .job-item, .job-card',
                'selectors': {
                    'item': '.job-offer, .job-item, .job-card, .career-item, .position',
                    'title': '.job-title, h3, .title, [data-job-title]',
                    'location': '.job-location, .location, .city',
                    'url': 'a::attr(href)'
                }
            }
        },
        {
            'name': 'Wizz Air (SuccessFactors)',
            'url': 'https://careers.wizzair.com/go/Pilot-Jobs/5258601/',
            'config': {
                'company': 'Wizz Air',
                'wait_for': '.job-listing, .job-item, .job-card',
                'selectors': {
                    'item': '.job-listing, .job-item, .job-card, .position, .career-item',
                    'title': '.job-title, h3, .title, [data-job-title]',
                    'location': '.job-location, .location, .city',
                    'url': 'a::attr(href)'
                }
            }
        }
    ]
    
    all_jobs = []
    
    for site in problem_sites:
        logger.info(f"\n🔍 Testing: {site['name']}")
        logger.info(f"   URL: {site['url']}")
        
        try:
            jobs = fetch_dynamic_jobs(site['url'], site['config'])
            
            # Add pilot scores
            jobs = [add_pilot_score(job) for job in jobs]
            
            # Filter for pilot jobs
            pilot_jobs = filter_pilot_jobs(jobs)
            
            logger.info(f"   ✅ SUCCESS: Found {len(jobs)} total jobs, {len(pilot_jobs)} pilot-related")
            
            # Show examples
            for i, job in enumerate(pilot_jobs[:3]):
                title = job.get('title', 'No title')[:50]
                location = job.get('location', 'No location')[:30]
                score = job.get('pilot_score', 0)
                logger.info(f"      {i+1}. [{score}/10] {title} - {location}")
            
            if len(pilot_jobs) > 3:
                logger.info(f"      ... and {len(pilot_jobs) - 3} more pilot jobs")
            
            all_jobs.extend(pilot_jobs)
            
        except Exception as e:
            logger.error(f"   ❌ FAILED: {e}")
    
    logger.info(f"\n📊 SUMMARY: Found {len(all_jobs)} total pilot jobs from problematic sites")
    return all_jobs

def test_enhanced_storage():
    """Test the enhanced storage and deduplication system"""
    
    logger.info("\n🗄️  TESTING ENHANCED STORAGE SYSTEM")
    logger.info("=" * 60)
    
    # Initialize enhanced database
    conn = init_enhanced_db("test_jobs.db")
    
    # Sample job data to test deduplication
    sample_jobs = [
        {
            'source': 'test_dynamic',
            'company': 'Test Airline',
            'external_id': 'test_job_1',
            'title': 'Commercial Pilot - Boeing 737',
            'location': 'Madrid, Spain',
            'url': 'https://example.com/job1',
            'pilot_score': 8
        },
        {
            'source': 'test_dynamic',
            'company': 'Test Airline',
            'external_id': 'test_job_2',
            'title': 'First Officer - Airbus A320',
            'location': 'Barcelona, Spain',
            'url': 'https://example.com/job2',
            'pilot_score': 9
        }
    ]
    
    # First run - should create new jobs
    logger.info("🔄 First run (should create new jobs)...")
    opened1, closed1, updated1 = upsert_jobs_enhanced(conn, sample_jobs)
    logger.info(f"   📈 Opened: {len(opened1)}, Closed: {len(closed1)}, Updated: {len(updated1)}")
    
    # Second run with same jobs - should not create duplicates
    logger.info("🔄 Second run with same jobs (should not duplicate)...")
    opened2, closed2, updated2 = upsert_jobs_enhanced(conn, sample_jobs)
    logger.info(f"   📈 Opened: {len(opened2)}, Closed: {len(closed2)}, Updated: {len(updated2)}")
    
    # Third run with one job removed - should mark as closed
    logger.info("🔄 Third run with one job removed (should close job)...")
    opened3, closed3, updated3 = upsert_jobs_enhanced(conn, sample_jobs[:1])
    logger.info(f"   📈 Opened: {len(opened3)}, Closed: {len(closed3)}, Updated: {len(updated3)}")
    
    # Fourth run with removed job back - should reopen
    logger.info("🔄 Fourth run with job back (should reopen)...")
    opened4, closed4, updated4 = upsert_jobs_enhanced(conn, sample_jobs)
    logger.info(f"   📈 Opened: {len(opened4)}, Closed: {len(closed4)}, Updated: {len(updated4)}")
    
    # Get statistics
    stats = get_job_statistics(conn)
    logger.info(f"\n📊 Database Statistics:")
    logger.info(f"   Total jobs ever: {stats['total_jobs_ever']}")
    logger.info(f"   Currently open: {stats['currently_open']}")
    logger.info(f"   Total closed: {stats['total_closed']}")
    
    conn.close()
    
    return {
        'deduplication_works': len(opened2) == 0,
        'closure_detection_works': len(closed3) > 0,
        'reopening_works': len(opened4) > 0
    }

def test_notification_system():
    """Test the enhanced notification system"""
    
    logger.info("\n📱 TESTING ENHANCED NOTIFICATION SYSTEM")
    logger.info("=" * 60)
    
    # Check if Telegram credentials are available
    telegram_cfg = {
        'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
    }
    
    if not telegram_cfg['bot_token'] or not telegram_cfg['chat_id']:
        logger.warning("⚠️  Telegram credentials not configured, skipping notification test")
        return False
    
    logger.info("🧪 Sending test notification...")
    
    try:
        result = send_test_notification(telegram_cfg)
        if result:
            logger.info("✅ Test notification sent successfully!")
            return True
        else:
            logger.error("❌ Test notification failed")
            return False
    except Exception as e:
        logger.error(f"❌ Notification test error: {e}")
        return False

def main():
    """Run all improvement demonstrations"""
    
    logger.info("🎯 JOB SCRAPER IMPROVEMENTS DEMONSTRATION")
    logger.info("=" * 80)
    logger.info("This demo tests all the requested improvements:")
    logger.info("1. ✈️  Dynamic job board support (Bizneo, SuccessFactors, Oracle)")
    logger.info("2. 🔍 Improved job detection from JavaScript-heavy sites")
    logger.info("3. 🗄️  Enhanced storage with deduplication and status tracking")
    logger.info("4. 📱 Better notification system with change-only updates")
    logger.info("5. 🚨 Enhanced error handling and logging")
    logger.info("=" * 80)
    
    results = {}
    
    # Test 1: Dynamic site improvements
    try:
        pilot_jobs = test_dynamic_site_improvements()
        results['dynamic_sites'] = len(pilot_jobs) > 0
        logger.info(f"✅ Dynamic site test: {'PASSED' if results['dynamic_sites'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"❌ Dynamic site test FAILED: {e}")
        results['dynamic_sites'] = False
    
    # Test 2: Enhanced storage
    try:
        storage_results = test_enhanced_storage()
        results['enhanced_storage'] = all(storage_results.values())
        logger.info(f"✅ Enhanced storage test: {'PASSED' if results['enhanced_storage'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"❌ Enhanced storage test FAILED: {e}")
        results['enhanced_storage'] = False
    
    # Test 3: Notification system
    try:
        results['notifications'] = test_notification_system()
        logger.info(f"✅ Notification test: {'PASSED' if results['notifications'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"❌ Notification test FAILED: {e}")
        results['notifications'] = False
    
    # Summary
    logger.info("\n🎉 FINAL RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
    
    logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎊 ALL IMPROVEMENTS SUCCESSFULLY IMPLEMENTED!")
    else:
        logger.info("⚠️  Some improvements need attention")
    
    # Cleanup
    if os.path.exists("test_jobs.db"):
        os.remove("test_jobs.db")
    
    return results

if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault('TELEGRAM_BOT_TOKEN', '7759383136:AAGXkePLpQ2SMWorMfUwGXc-_Jj9JTdVtL8')
    os.environ.setdefault('TELEGRAM_CHAT_ID', '1661173884')
    
    main()