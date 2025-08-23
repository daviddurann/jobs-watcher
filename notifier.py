# notifier_enhanced.py
"""
Enhanced notification system with better formatting, rate limiting, and smarter notifications.
"""

import os
import requests
import time
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

def _env_or(cfg, path, default=None):
    """Get config from environment variable or config dict"""
    if path == "bot_token":
        return os.getenv("TELEGRAM_BOT_TOKEN") or cfg.get("bot_token") or default
    if path == "chat_id":
        return os.getenv("TELEGRAM_CHAT_ID") or cfg.get("chat_id") or default
    if path == "group_id":
        return os.getenv("TELEGRAM_GROUP_ID") or cfg.get("group_id") or default
    return default

def send_telegram_message(text: str, bot_token: str, chat_id: str, parse_mode: str = "Markdown"):
    """Send Telegram message with enhanced error handling"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
        "parse_mode": parse_mode
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Telegram send failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to send Telegram message after {max_retries} attempts: {e}")
                raise

    return False

def format_job_message(job: Dict, status: str, pilot_score: int = None) -> str:
    """Format a job for Telegram notification"""

    # Status emoji mapping
    status_emojis = {
        'opened': '🟢',
        'reopened': '🔄',
        'closed': '🔴',
        'updated': '📝'
    }

    # Pilot score emoji
    score_emoji = ""
    if pilot_score is not None:
        if pilot_score >= 8:
            score_emoji = " ✈️✈️✈️"  # High relevance
        elif pilot_score >= 5:
            score_emoji = " ✈️✈️"    # Medium relevance
        elif pilot_score >= 1:
            score_emoji = " ✈️"      # Low relevance

    emoji = status_emojis.get(status, '📋')
    status_text = status.upper()

    title = job.get('title', 'Sin título')
    company = job.get('company', job.get('source', 'Desconocido'))
    location = job.get('location', 'Ubicación no especificada')
    url = job.get('url', '')

    # Clean and format text
    title = title.strip()[:100]  # Limit length
    company = company.strip()[:50]
    location = location.strip()[:50]

    message = f"{emoji} *{status_text}*{score_emoji} — {title}\n"
    message += f"🏢 Empresa: {company}\n"
    message += f"📍 Ubicación: {location}\n"

    if url and url.startswith('http'):
        message += f"🔗 [Ver oferta]({url})"
    elif url:
        message += f"🔗 Enlace: {url}"

    return message

def group_jobs_by_company(jobs: List[Dict]) -> Dict[str, List[Dict]]:
    """Group jobs by company for better notification organization"""
    grouped = {}
    for job in jobs:
        company = job.get('company', job.get('source', 'Unknown'))
        if company not in grouped:
            grouped[company] = []
        grouped[company].append(job)
    return grouped

def create_summary_message(opened: List[Dict], closed: List[Dict], updated: List[Dict], db_stats: Dict) -> str:
    """Create a summary message for bulk notifications"""

    if not (opened or closed or updated):
        return None

    total_changes = len(opened) + len(closed) + len(updated)

    summary = f"📊 *Resumen de Cambios en Empleos Piloto*\n\n"

    if opened:
        summary += f"🟢 Nuevos empleos: {len(opened)}\n"
    if updated:
        summary += f"📝 Empleos actualizados: {len(updated)}\n"
    if closed:
        summary += f"🔴 Empleos cerrados: {len(closed)}\n"

    summary += f"\n📈 Total empleos abiertos: {db_stats.get('currently_open', 0)}"
    summary += f"\n📚 Total empleos en base de datos: {db_stats.get('total_jobs_ever', 0)}"

    # Add top companies with changes
    all_jobs = opened + updated + closed
    if all_jobs:
        companies = {}
        for job in all_jobs:
            company = job.get('company', 'Unknown')
            companies[company] = companies.get(company, 0) + 1

        top_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_companies:
            summary += f"\n\n🏢 *Empresas con más cambios:*\n"
            for company, count in top_companies:
                summary += f"• {company}: {count}\n"

    summary += f"\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')} UTC"

    return summary

def notify_changes_enhanced(opened: List[Dict], closed: List[Dict], updated: List[Dict],
                            telegram_cfg: Dict, db_stats: Dict):
    """Enhanced notification system with smarter grouping and rate limiting"""

    bot_token = _env_or(telegram_cfg, "bot_token")
    chat_id = _env_or(telegram_cfg, "chat_id")
    group_id = _env_or(telegram_cfg, "group_id")

    # Send notifications to both chat_id and group_id if configured
    recipients = []
    if bot_token and chat_id:
        recipients.append(('chat', chat_id))
    if bot_token and group_id:
        recipients.append(('group', group_id))

    if not recipients:
        logger.warning("Telegram credentials not configured, skipping notifications")
        return

    # Rate limiting: don't send too many individual messages
    max_individual_messages = 10
    total_jobs = len(opened) + len(closed) + len(updated)

    if total_jobs == 0:
        logger.info("No job changes to notify")
        return

    # Send notifications to all configured recipients
    for recipient_type, recipient_id in recipients:
        try:
            logger.info(f"📱 Sending notifications to {recipient_type}: {recipient_id}")

            # Always send a summary first
            summary = create_summary_message(opened, closed, updated, db_stats)
            if summary:
                send_telegram_message(summary, bot_token, recipient_id)
                time.sleep(1)  # Rate limiting

            # If there are few changes, send individual messages
            if total_jobs <= max_individual_messages:

                # Send new jobs (highest priority)
                for job in opened:
                    try:
                        pilot_score = job.get('pilot_score', 0)
                        status = 'reopened' if job.get('reopen_count', 0) > 0 else 'opened'
                        message = format_job_message(job, status, pilot_score)
                        send_telegram_message(message, bot_token, recipient_id)
                        time.sleep(0.5)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Failed to send notification for opened job: {e}")

                # Send updated jobs (medium priority)
                for job in updated:
                    try:
                        pilot_score = job.get('pilot_score', 0)
                        message = format_job_message(job, 'updated', pilot_score)
                        send_telegram_message(message, bot_token, recipient_id)
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Failed to send notification for updated job: {e}")

                # Send closed jobs (lower priority)
                for job in closed:
                    try:
                        message = format_job_message(job, 'closed')
                        send_telegram_message(message, bot_token, recipient_id)
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Failed to send notification for closed job: {e}")

            else:
                # Too many changes - send grouped notifications
                logger.info(f"Too many changes ({total_jobs}), sending grouped notifications to {recipient_type}")

                # Group and send only new jobs (most important)
                if opened:
                    grouped_opened = group_jobs_by_company(opened)
                    for company, jobs in grouped_opened.items():
                        try:
                            if len(jobs) == 1:
                                job = jobs[0]
                                pilot_score = job.get('pilot_score', 0)
                                message = format_job_message(job, 'opened', pilot_score)
                            else:
                                # Multiple jobs from same company
                                message = f"🟢 *{len(jobs)} NUEVOS EMPLEOS* — {company}\n"
                                for i, job in enumerate(jobs[:5], 1):  # Show first 5
                                    title = job.get('title', 'Sin título')[:80]
                                    location = job.get('location', 'N/D')[:30]
                                    message += f"{i}. {title} - {location}\n"
                                if len(jobs) > 5:
                                    message += f"... y {len(jobs) - 5} más\n"

                                if jobs[0].get('url'):
                                    message += f"🔗 Ver todos en la empresa"

                            send_telegram_message(message, bot_token, recipient_id)
                            time.sleep(1)

                        except Exception as e:
                            logger.error(f"Failed to send grouped notification for {company}: {e}")

            logger.info(f"Successfully sent notifications to {recipient_type} for {total_jobs} job changes")

        except Exception as e:
            logger.error(f"Failed to send notifications to {recipient_type} {recipient_id}: {e}")
            continue

def send_test_notification(telegram_cfg: Dict) -> bool:
    """Send a test notification to verify Telegram setup"""
    bot_token = _env_or(telegram_cfg, "bot_token")
    chat_id = _env_or(telegram_cfg, "chat_id")
    group_id = _env_or(telegram_cfg, "group_id")

    if not bot_token:
        logger.error("Missing Telegram bot token for test")
        return False

    test_message = (
        "🧪 *Test de Notificaciones*\n\n"
        "✅ Bot configurado correctamente\n"
        "📱 Sistema de notificaciones activo\n\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')} UTC"
    )

    success = True

    # Test chat_id if provided
    if chat_id:
        try:
            send_telegram_message(test_message + f"\n📞 Enviado a Chat ID: {chat_id}", bot_token, chat_id)
            logger.info("✅ Test notification sent successfully to chat_id")
        except Exception as e:
            logger.error(f"❌ Test notification failed for chat_id: {e}")
            success = False

    # Test group_id if provided
    if group_id:
        try:
            send_telegram_message(test_message + f"\n👥 Enviado a Group ID: {group_id}", bot_token, group_id)
            logger.info("✅ Test notification sent successfully to group_id")
        except Exception as e:
            logger.error(f"❌ Test notification failed for group_id: {e}")
            success = False

    if not chat_id and not group_id:
        logger.error("No chat_id or group_id configured for test")
        return False

    return success