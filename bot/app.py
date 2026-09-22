import hmac
import os
import secrets
import textwrap
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from .channels import telegram_payload, whatsapp_text
from .storage import Store

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(MAX_CONTENT_LENGTH=64 * 1024,
                      DATABASE_PATH=os.getenv('DATABASE_PATH', str(ROOT / 'data/setu.db')),
                      SESSION_SECRET=os.getenv('SESSION_SECRET', ''),
                      TELEGRAM_WEBHOOK_SECRET=os.getenv('TELEGRAM_WEBHOOK_SECRET', ''),
                      TWILIO_AUTH_TOKEN=os.getenv('TWILIO_AUTH_TOKEN', ''),
                      PUBLIC_BASE_URL=os.getenv('PUBLIC_BASE_URL', '').rstrip('/'),
                      APP_ENV=os.getenv('APP_ENV', 'development'))
    if config:
        app.config.update(config)
    if not app.config['SESSION_SECRET']:
        if app.config['APP_ENV'] == 'production':
            raise RuntimeError('Set SESSION_SECRET before running in production.')
        secret_path = Path(app.config['DATABASE_PATH']).parent / '.session-secret'
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32), encoding='ascii')
        app.config['SESSION_SECRET'] = secret_path.read_text(encoding='ascii').strip()
    if app.config['APP_ENV'] == 'production' and len(app.config['SESSION_SECRET']) < 32:
        raise RuntimeError('SESSION_SECRET must contain at least 32 characters.')
    store = Store(app.config['DATABASE_PATH'], app.config['SESSION_SECRET'])
    app.extensions['store'] = store

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        return response

    @app.get('/healthz')
    def health():
        store.purge()
        return jsonify(status='ok', app='yojana-setu')

    @app.post('/webhooks/telegram')
    def telegram():
        secret = app.config['TELEGRAM_WEBHOOK_SECRET']
        if not secret or not hmac.compare_digest(request.headers.get('X-Telegram-Bot-Api-Secret-Token', ''), secret):
            return jsonify(error='Unauthorised'), 403
        update = request.get_json(silent=True)
        if not isinstance(update, dict) or not isinstance(update.get('update_id'), int):
            return jsonify(error='Invalid update'), 400
        callback = update.get('callback_query') or {}
        if not isinstance(callback, dict):
            return jsonify(error='Invalid callback'), 400
        msg = callback.get('message') or update.get('message') or {}
        if not isinstance(msg, dict) or not msg.get('chat'):
            return jsonify(ok=True)
        chat = msg['chat']
        if not isinstance(chat, dict) or not isinstance(chat.get('id'), int):
            return jsonify(error='Invalid chat'), 400
        if chat.get('type') != 'private':
            return jsonify(method='sendMessage', chat_id=chat['id'], text='Please open a private chat with this bot to check personal scheme criteria.')
        text = callback.get('data') or msg.get('text') or '/voice'
        if not isinstance(text, str) or len(text) > 2000:
            return jsonify(error='Invalid message'), 400
        reply = store.handle('telegram', str(chat['id']), str(update['update_id']), text)
        return jsonify(telegram_payload(chat['id'], reply))

    @app.post('/webhooks/whatsapp')
    def whatsapp():
        token, base = app.config['TWILIO_AUTH_TOKEN'], app.config['PUBLIC_BASE_URL']
        if not token or not base or urlsplit(base).scheme != 'https':
            return jsonify(error='WhatsApp is not configured'), 503
        suffix = ('?' + request.query_string.decode('ascii')) if request.query_string else ''
        url = base + '/webhooks/whatsapp' + suffix
        if not RequestValidator(token).validate(url, request.form, request.headers.get('X-Twilio-Signature', '')):
            return jsonify(error='Unauthorised'), 403
        sender, event = request.form.get('From', ''), request.form.get('MessageSid', '')
        if not sender.startswith('whatsapp:') or not event:
            return jsonify(error='Invalid message'), 400
        text = request.form.get('ButtonPayload') or request.form.get('Body') or '/voice'
        if len(text) > 2000:
            return jsonify(error='Message too long'), 400
        reply = store.handle('whatsapp', sender, event, text)
        response = MessagingResponse()
        # TwiML supports text directly. Optional native menu buttons use a pre-created Content SID.
        sid = os.getenv('TWILIO_MENU_' + reply['lang'].upper() + '_SID')
        if sid and reply['kind'] == 'menu' and os.getenv('TWILIO_ACCOUNT_SID') and os.getenv('TWILIO_WHATSAPP_NUMBER'):
            from twilio.rest import Client
            from twilio.http.http_client import TwilioHttpClient
            try:
                Client(os.environ['TWILIO_ACCOUNT_SID'], token, http_client=TwilioHttpClient(timeout=8)).messages.create(
                    from_=os.environ['TWILIO_WHATSAPP_NUMBER'], to=sender, content_sid=sid)
                return str(response), 200, {'Content-Type': 'application/xml'}
            except Exception:
                # Preserve the usable numbered menu if the optional template fails.
                pass
        for part in textwrap.wrap(whatsapp_text(reply), width=1500, replace_whitespace=False, drop_whitespace=True):
            response.message(part)
        return str(response), 200, {'Content-Type': 'application/xml'}

    @app.get('/')
    def index():
        return send_from_directory(ROOT / 'web', 'index.html')

    @app.get('/<path:filename>')
    def static_file(filename):
        # Windows registry MIME mappings can incorrectly classify JS modules as plain text.
        mime = 'text/javascript' if filename.endswith(('.mjs', '.js')) else None
        return send_from_directory(ROOT / 'web', filename, mimetype=mime)

    return app


if __name__ == '__main__':
    from waitress import serve
    serve(create_app(), host='0.0.0.0', port=int(os.getenv('PORT', '8000')), threads=4)
