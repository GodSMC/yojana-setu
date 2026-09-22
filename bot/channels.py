"""Platform formatting and bounded API calls."""
import requests


class TelegramAPIError(RuntimeError):
    """Expose status metadata, never token-bearing URLs or user messages."""
    def __init__(self, method, code, retry_after=5):
        self.method, self.code = method, code
        self.retry_after = max(1, min(int(retry_after), 3600))
        super().__init__(f'Telegram {method} returned error {code}.')


def telegram_payload(chat_id, reply):
    rows = [[{'text': x['label'], 'callback_data': x['value']}] for x in reply['options']]
    rows += [[{'text': x['label'], 'url': x['url']}] for x in reply['links']]
    return {'method': 'sendMessage', 'chat_id': chat_id, 'text': reply['text'],
            'reply_markup': {'inline_keyboard': rows}, 'link_preview_options': {'is_disabled': True}}


def whatsapp_text(reply):
    text = reply['text']
    for i, option in enumerate(reply['options'], 1):
        value = option['value']
        selector = str(i) if reply['kind'] in ('menu', 'question', 'fallback') else value
        text += f'\n{selector}. {option["label"]}'
    for link in reply['links']:
        text += f'\n{link["label"]}: {link["url"]}'
    return text


def telegram_call(token, method, payload, timeout=35):
    try:
        response = requests.post(f'https://api.telegram.org/bot{token}/{method}', json=payload, timeout=timeout)
        data = response.json()
        if not response.ok or not data.get('ok'):
            raise TelegramAPIError(method, data.get('error_code', response.status_code),
                                   data.get('parameters', {}).get('retry_after', 5))
        return data['result']
    except (requests.RequestException, ValueError):
        # Avoid logging request URLs, which contain the bot token.
        raise RuntimeError('Telegram could not be reached. Check network and credentials.') from None
