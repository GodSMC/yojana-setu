"""Run Telegram locally without public hosting: python -m bot.telegram_polling."""
import os
import time
from dotenv import load_dotenv
from .app import create_app
from .channels import TelegramAPIError, telegram_call, telegram_payload


def process_update(token, store, update, call=telegram_call):
    callback = update.get('callback_query') or {}
    msg = callback.get('message') or update.get('message') or {}
    chat = msg.get('chat', {})
    if chat.get('type') != 'private':
        return
    text = callback.get('data') or msg.get('text') or '/voice'
    reply = store.handle('telegram', str(chat['id']), str(update['update_id']), text[:2000])
    if callback:
        try:
            call(token, 'answerCallbackQuery', {'callback_query_id': callback['id']})
        except RuntimeError:
            # A stale callback spinner must never prevent sending the actual reply.
            pass
    payload = telegram_payload(chat['id'], reply)
    payload.pop('method', None)
    try:
        call(token, 'sendMessage', payload)
    except TelegramAPIError as exc:
        if exc.code in (400, 403):
            print(f'Skipped an undeliverable Telegram reply (error {exc.code}).', flush=True)
            return
        raise


def main():
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise SystemExit('Set TELEGRAM_BOT_TOKEN in .env first.')
    store = create_app().extensions['store']
    while True:
        try:
            bot_id = telegram_call(token, 'getMe', {})['id']
            telegram_call(token, 'deleteWebhook', {'drop_pending_updates': False})
            break
        except RuntimeError as exc:
            print(str(exc), flush=True)
            time.sleep(10)
    offset = store.get_offset(bot_id)
    print('Yojana Setu is listening on Telegram. Ctrl+C stops the bot.', flush=True)
    while True:
        try:
            updates = telegram_call(token, 'getUpdates', {'offset': offset, 'timeout': 25, 'allowed_updates': ['message', 'callback_query']})
            for update in updates:
                process_update(token, store, update)
                offset = update['update_id'] + 1
                store.set_offset(bot_id, offset)
            store.purge()
        except RuntimeError as exc:
            print(str(exc), flush=True)
            time.sleep(getattr(exc, 'retry_after', 5))


if __name__ == '__main__':
    main()
