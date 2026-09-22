"""Create optional in-session WhatsApp quick-reply menu templates."""
import os
import requests
from dotenv import load_dotenv
from .engine import DATA, UI


def main():
    load_dotenv()
    account, token = os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')
    if not account or not token:
        raise SystemExit('Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN first.')
    for lang in ('en', 'hi'):
        body = UI['welcome'][lang] + '\n\n' + UI['saved'][lang]
        payload = {'friendly_name': 'yojana_setu_menu_' + lang, 'language': lang,
                   'types': {'twilio/quick-reply': {'body': body, 'actions': [
                       {'title': s['name'][lang][:20], 'id': s['id']} for s in DATA['schemes']]}}}
        result = requests.post('https://content.twilio.com/v1/Content', auth=(account, token), json=payload, timeout=20)
        if not result.ok:
            raise SystemExit('Twilio could not create the menu. Check your account and Content permissions.')
        print('TWILIO_MENU_' + lang.upper() + '_SID=' + result.json()['sid'])


if __name__ == '__main__':
    main()
