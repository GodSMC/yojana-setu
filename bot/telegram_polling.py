"""Run Telegram locally without public hosting: python -m bot.telegram_polling."""
import os
import time
from dotenv import load_dotenv
from .app import create_app
from .channels import telegram_call, telegram_payload


def main():
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise SystemExit('Set TELEGRAM_BOT_TOKEN in .env first.')
    store = create_app().extensions['store']
    # Preserve any queued messages. Polling and webhooks cannot run together.
    telegram_call(token, 'deleteWebhook', {'drop_pending_updates': False})
    offset = 0
    print('Yojana Setu is listening on Telegram. Ctrl+C stops the bot.')
    while True:
        try:
            updates = telegram_call(token, 'getUpdates', {'offset': offset, 'timeout': 25, 'allowed_updates': ['message', 'callback_query']})
            for update in updates:
                callback = update.get('callback_query') or {}
                msg = callback.get('message') or update.get('message') or {}
                chat = msg.get('chat', {})
                if chat.get('type') == 'private':
                    text = callback.get('data') or msg.get('text') or '/voice'
                    reply = store.handle('telegram', str(chat['id']), str(update['update_id']), text[:2000])
                    if callback:
                        telegram_call(token, 'answerCallbackQuery', {'callback_query_id': callback['id']})
                    telegram_call(token, 'sendMessage', telegram_payload(chat['id'], reply))
                offset = update['update_id'] + 1
        except RuntimeError as exc:
            print(str(exc))
            time.sleep(5)


if __name__ == '__main__':
    main()
