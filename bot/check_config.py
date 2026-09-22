"""Check readiness without revealing any secret values."""
import os
from dotenv import load_dotenv


def main():
    load_dotenv()
    groups = {
        'Telegram local polling': ['TELEGRAM_BOT_TOKEN'],
        'Telegram hosted webhook': ['TELEGRAM_BOT_TOKEN', 'PUBLIC_BASE_URL', 'TELEGRAM_WEBHOOK_SECRET', 'SESSION_SECRET'],
        'WhatsApp signed webhook': ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_WHATSAPP_NUMBER', 'PUBLIC_BASE_URL', 'SESSION_SECRET'],
    }
    for name, keys in groups.items():
        missing = [k for k in keys if not os.getenv(k)]
        print(name + ': ' + ('READY TO CONNECT' if not missing else 'missing ' + ', '.join(missing)))


if __name__ == '__main__':
    main()
