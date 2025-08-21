import requests

BOT_TOKEN = "7759383136:AAGXkePLpQ2SMWorMfUwGXc-_Jj9JTdVtL8"
CHAT_ID = "1661173884"

def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, json=payload)
    print(r.json())

if __name__ == "__main__":
    send_message("✅ Hola mundo, tu bot de ofertas de piloto ya funciona 🚀")
