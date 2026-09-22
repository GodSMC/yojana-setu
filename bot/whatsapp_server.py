"""Local WhatsApp webhook for an HTTPS tunnel. Does not serve the browser demo."""
import os
from urllib.parse import urlsplit

from waitress import serve

from .app import create_app


def main():
    needed = ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_WHATSAPP_NUMBER', 'PUBLIC_BASE_URL')
    missing = [key for key in needed if not os.getenv(key)]
    if missing:
        raise SystemExit('WhatsApp setup is incomplete: ' + ', '.join(missing))
    url = urlsplit(os.environ['PUBLIC_BASE_URL'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
        raise SystemExit('PUBLIC_BASE_URL must be a plain HTTPS origin, without a path or query.')
    if not os.environ['TWILIO_WHATSAPP_NUMBER'].startswith('whatsapp:+'):
        raise SystemExit('TWILIO_WHATSAPP_NUMBER must start with whatsapp:+ followed by the international number.')
    app = create_app({'SERVE_DEMO': False, 'TELEGRAM_WEBHOOK_SECRET': ''})
    port = int(os.getenv('WHATSAPP_LOCAL_PORT', '8001'))
    print('WhatsApp webhook is listening locally. The HTTPS tunnel must stay running.', flush=True)
    print('Webhook: ' + os.environ['PUBLIC_BASE_URL'].rstrip('/') + '/webhooks/whatsapp', flush=True)
    serve(app, host='127.0.0.1', port=port, threads=4)


if __name__ == '__main__':
    main()
