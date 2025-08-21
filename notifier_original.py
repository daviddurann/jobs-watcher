# notifier.py
import os
import requests

def _env_or(cfg, path, default=None):
    # permite TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID por env var
    if path == "bot_token":
        return os.getenv("TELEGRAM_BOT_TOKEN") or default
    if path == "chat_id":
        return os.getenv("TELEGRAM_CHAT_ID") or default
    return default

def send_telegram_message(text: str, bot_token: str, chat_id: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()

def notify_changes(opened, closed, telegram_cfg):
    bot_token = _env_or(telegram_cfg, "bot_token", telegram_cfg.get("bot_token"))
    chat_id = _env_or(telegram_cfg, "chat_id", telegram_cfg.get("chat_id"))
    if not bot_token or not chat_id:
        return

    # Un mensaje por evento (más fácil de leer y filtrar)
    for j in opened:
        msg = (
            f"🟢 *ABIERTO* — {j.get('title')}\n"
            f"Empresa: {j.get('company') or j.get('source').title()}\n"
            f"Ubicación: {j.get('location') or 'N/D'}\n"
            f"Link: {j.get('url')}"
        )
        send_telegram_message(msg, bot_token, chat_id)

    for j in closed:
        msg = (
            f"🔴 *CERRADO* — {j.get('title')}\n"
            f"Empresa: {j.get('company') or j.get('source').title()}\n"
            f"Ubicación: {j.get('location') or 'N/D'}\n"
            f"Link (histórico): {j.get('url')}"
        )
        send_telegram_message(msg, bot_token, chat_id)
