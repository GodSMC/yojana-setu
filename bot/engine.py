"""Pure conversation logic. No API calls, randomness or model-generated claims."""
import copy
import json
import math
import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / 'web'
DATA = json.loads((WEB / 'schemes.json').read_text(encoding='utf-8'))
UI = json.loads((WEB / 'ui.json').read_text(encoding='utf-8'))
SCHEMES = {s['id']: s for s in DATA['schemes']}


def normalise(value):
    return str(value).strip().lower().translate(str.maketrans('०१२३४५६७८९', '0123456789'))


def initial(lang='en'):
    return {'lang': lang, 'profile': {}, 'scheme': None, 'pending': None, 'options': []}


def evaluate(scheme, profile):
    missing = [f for f in scheme['fields'] if f not in profile or profile[f] == 'unknown']
    failures = []
    for r in scheme['rules']:
        v = profile.get(r['field'])
        if v is None or v == 'unknown':
            continue
        if r['op'] == 'marks':
            if profile.get('sc_st') in (None, 'unknown'):
                continue
            passed = v >= (50 if profile['sc_st'] == 'yes' else r['value'])
        elif r['op'] == 'eq':
            passed = v == r['value']
        elif r['op'] == 'lte':
            passed = v <= r['value']
        elif r['op'] == 'gte':
            passed = v >= r['value']
        else:
            raise ValueError('Unsupported rule operator')
        if not passed:
            failures.append(r['reason'])
    return ('unlikely' if failures else 'review' if missing else 'possible'), failures


def parse(field, raw):
    value = normalise(raw)
    if value in ('unknown', 'not sure', "don't know", 'पता नहीं', 'नहीं पता'):
        return 'unknown'
    if field['type'] == 'choice':
        for i, option in enumerate(field['options'], 1):
            aliases = [normalise(v) for v in option] + [str(i)]
            if option[0] == 'yes':
                aliases += ['haan', 'han', 'ha', 'हां']
            if option[0] == 'no':
                aliases += ['nahi', 'nahin']
            if value in aliases:
                return option[0]
    elif field['type'] == 'number':
        value = value.replace(',', '').replace('₹', '').strip().removesuffix('%').strip()
        if not re.fullmatch(r'\d+(?:\.\d+)?', value):
            return None
        n = float(value)
        if math.isfinite(n) and field['min'] <= n <= field['max'] and (not field.get('integer') or n.is_integer()):
            return int(n) if n.is_integer() else n
    elif field['type'] == 'state':
        if value in DATA['state_aliases']:
            return DATA['state_aliases'][value]
        return next((s for s in DATA['states'] if s.lower() == value), None)
    return None


def respond(saved, text):
    s = copy.deepcopy(saved or initial('hi' if re.search('[\u0900-\u097f]', text) else 'en'))
    raw = normalise(text)
    lang = s['lang']

    def t(key):
        return UI[key][s['lang']]

    def result(kind, body, options=None, links=None, **extra):
        opts = options or []
        s['options'] = opts
        return s, {'kind': kind, 'text': body, 'options': opts, 'links': links or [], 'lang': s['lang'], **extra}

    def link(label, url):
        return {'label': label, 'url': url}

    def scheme_options():
        return [{'label': x['icon'] + ' ' + x['name'][s['lang']], 'value': x['id']} for x in DATA['schemes']]

    def menu(prefix=''):
        s['scheme'] = s['pending'] = None
        return result('menu', (prefix + '\n\n' if prefix else '') + t('welcome') + '\n\n' + t('saved'), scheme_options())

    def advance():
        scheme = SCHEMES[s['scheme']]
        for key in scheme['fields']:
            if key not in s['profile']:
                s['pending'] = key
                field = DATA['fields'][key]
                opts = [{'value': o[0], 'label': o[1 if s['lang'] == 'en' else 2]} for o in field.get('options', [])]
                return result('question', field['question'][s['lang']], opts,
                              field=key, scheme=scheme['id'], progress={'done': sum(f in s['profile'] for f in scheme['fields']), 'total': len(scheme['fields'])})
        return assessment()

    def assessment():
        scheme = SCHEMES[s['scheme']]
        status, reasons = evaluate(scheme, s['profile'])
        s['pending'] = None
        lines = [scheme['name'][s['lang']], t(status)]
        lines += [r[s['lang']] for r in reasons]
        if status == 'review':
            lines.append(t('unknown'))
        lines += [scheme['benefit'][s['lang']], scheme['scope'][s['lang']], scheme['documents'][s['lang']], t('disclaimer')]
        return result('assessment', '\n\n'.join(lines),
                      [{'label': t('menu'), 'value': '/menu'}, {'label': t('edit'), 'value': '/edit'}],
                      [link(t('official'), scheme['apply']), link(t('source'), scheme['source']), link(t('csc'), DATA['csc_url'])],
                      status=status, scheme=scheme['id'])

    if raw in ('/delete', '/reset', 'delete'):
        s = initial(lang)
        return menu(t('deleted'))
    if raw in ('/privacy', 'privacy'):
        return result('info', t('privacy'), [{'label': t('menu'), 'value': '/menu'}])
    if raw in ('/voice',):
        return result('info', t('voice'), [{'label': t('menu'), 'value': '/menu'}])
    if raw in ('/help', 'help', '/csc', 'csc', 'मदद', 'सहायता'):
        return result('help', t('help'), [{'label': t('menu'), 'value': '/menu'}], [link(t('csc'), DATA['csc_url']), link('myScheme', 'https://www.myscheme.gov.in/')])
    if raw in ('/language', '/hi', '/en', 'hindi', 'हिंदी', 'english'):
        s['lang'] = ('hi' if s['lang'] == 'en' else 'en') if raw == '/language' else ('hi' if raw in ('/hi', 'hindi', 'हिंदी') else 'en')
        return advance() if s['scheme'] and s['pending'] else menu()
    if raw in ('/edit', 'edit'):
        s['profile'] = {}
        return advance() if s['scheme'] else menu()
    if raw in ('/back', 'back') and s['scheme']:
        fields = SCHEMES[s['scheme']]['fields']
        index = fields.index(s['pending']) if s['pending'] else len(fields)
        if index:
            s['profile'].pop(fields[index - 1], None)
        return advance()
    if raw in ('/start', '/menu', 'menu', 'hi', 'hello', 'namaste', 'नमस्ते', ''):
        return menu()

    # Button payloads are unambiguous. Bare numbers only select a menu when no question is active.
    selected = raw if raw in SCHEMES else None
    if not selected and not s['pending']:
        if raw in ('1', '2', '3') and s['options'] == scheme_options():
            selected = DATA['schemes'][int(raw) - 1]['id']
        else:
            matches = [x['id'] for x in DATA['schemes'] if any(k in raw for k in x['keywords'])]
            if len(matches) == 1:
                selected = matches[0]
    if selected:
        s['scheme'] = selected
        return advance()
    if s['pending']:
        field = DATA['fields'][s['pending']]
        value = parse(field, text)
        if value is None:
            state, reply = advance()
            reply['text'] = t('invalid') + '\n\n' + reply['text']
            return state, reply
        s['profile'][s['pending']] = value
        return assessment() if value == 'unknown' else advance()
    return result('fallback', t('fallback'), scheme_options(), [link(t('csc'), DATA['csc_url']), link('myScheme', 'https://www.myscheme.gov.in/')])
