# Auto send message to Telegram channel via web request
import requests
from env._secrete import telegram_bot_token, telegram_chat_id

def send_msg_to_telegram(msg, chat_id=telegram_chat_id, token=telegram_bot_token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"  # You can use "HTML" if preferred
    }
    response = requests.post(url, data=payload)
    print(response)