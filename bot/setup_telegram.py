import os
from dotenv import load_dotenv
from .channels import telegram_call


def main():
    load_dotenv()
    token, base, secret = [os.getenv(k, '') for k in ('TELEGRAM_BOT_TOKEN', 'PUBLIC_BASE_URL', 'TELEGRAM_WEBHOOK_SECRET')]
    if not token or not base.startswith('https://') or len(secret) < 32:
        raise SystemExit('Set TELEGRAM_BOT_TOKEN, HTTPS PUBLIC_BASE_URL and a 32+ character TELEGRAM_WEBHOOK_SECRET first.')
    telegram_call(token, 'setWebhook', {'url': base.rstrip('/') + '/webhooks/telegram', 'secret_token': secret,
                                      'allowed_updates': ['message', 'callback_query'], 'max_connections': 1})
    telegram_call(token, 'setMyCommands', {'commands': [
        {'command': 'start', 'description': 'Start / शुरू करें'}, {'command': 'menu', 'description': 'Choose a scheme'},
        {'command': 'language', 'description': 'Hindi / English'}, {'command': 'help', 'description': 'Find human help'},
        {'command': 'edit', 'description': 'Correct my answers'}, {'command': 'delete', 'description': 'Delete my answers'},
        {'command': 'privacy', 'description': 'How answers are stored'}]})
    print('Telegram webhook and menu configured.')


if __name__ == '__main__':
    main()
