import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import xml.etree.ElementTree as ET

import pytest
from twilio.request_validator import RequestValidator

from bot.app import create_app
from bot.engine import DATA, SCHEMES, evaluate, parse, respond
from bot.storage import Store

ROOT = Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / 'tests/conversations.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case', CASES, ids=lambda c:c['name'])
def test_conversations(case):
    state = None
    for message in case['inputs']:
        state, reply = respond(state, message)
    for key in ('status', 'scheme', 'kind', 'field'):
        if key in case:
            assert reply[key] == case[key]


def test_missing_data_never_passes():
    for scheme in SCHEMES.values():
        assert evaluate(scheme, {})[0] == 'review'


@pytest.mark.parametrize('value', ['NaN','Infinity','-1','1e8','0x10','12.5','121','<script>'])
def test_age_rejects_invalid_values(value):
    assert parse(DATA['fields']['age'], value) is None


def test_store_persistence_replay_and_delete(tmp_path):
    path = tmp_path / 'bot.db'
    store = Store(path, 'a'*32)
    store.handle('telegram','123','1','pension')
    first = store.handle('telegram','123','2','Punjab')
    assert first['field'] == 'age'
    assert store.handle('telegram','123','2','Punjab') == first
    other = Store(path,'a'*32)
    assert other.handle('telegram','123','3','60')['field'] == 'bpl'
    assert other.handle('whatsapp','123','4','pension')['field'] == 'state'
    other.handle('telegram','123','5','/delete')
    assert other.handle('telegram','123','6','pension')['field'] == 'state'
    with sqlite3.connect(path) as db:
        assert not db.execute("SELECT id FROM sessions WHERE id='123'").fetchone()
        db.execute('UPDATE sessions SET updated=?', (time.time()-8*86400,))
    other.purge()
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM sessions').fetchone()[0] == 0


@pytest.fixture
def client(tmp_path):
    return create_app({'TESTING':True, 'DATABASE_PATH':str(tmp_path/'test.db'), 'SESSION_SECRET':'x'*32,
                       'TELEGRAM_WEBHOOK_SECRET':'telegram-secret', 'TWILIO_AUTH_TOKEN':'twilio-secret',
                       'PUBLIC_BASE_URL':'https://bot.example'}).test_client()


def test_telegram_auth_and_retries(client):
    payload = {'update_id':1,'message':{'chat':{'id':123,'type':'private'},'text':'pension'}}
    assert client.post('/webhooks/telegram',json=payload).status_code == 403
    headers = {'X-Telegram-Bot-Api-Secret-Token':'telegram-secret'}
    r=client.post('/webhooks/telegram',json=payload,headers=headers)
    assert r.status_code == 200 and r.json['method'] == 'sendMessage'
    assert client.post('/webhooks/telegram',json=payload,headers=headers).json == r.json
    payload['update_id']=2
    payload['message']['text']='Delhi'
    assert 'age' in client.post('/webhooks/telegram',json=payload,headers=headers).json['text']


def test_telegram_callback_and_group_privacy(client):
    headers={'X-Telegram-Bot-Api-Secret-Token':'telegram-secret'}
    payload={'update_id':4,'callback_query':{'data':'pension','message':{'chat':{'id':1,'type':'private'}}}}
    assert client.post('/webhooks/telegram',json=payload,headers=headers).status_code == 200
    payload={'update_id':5,'message':{'chat':{'id':2,'type':'group'},'text':'pension'}}
    assert 'private chat' in client.post('/webhooks/telegram',json=payload,headers=headers).json['text']
    assert client.post('/webhooks/telegram',json={'update_id':1,'callback_query':'bad'},headers=headers).status_code == 400


def test_whatsapp_validation_and_flow(client):
    url='https://bot.example/webhooks/whatsapp'
    payload={'From':'whatsapp:+911111111111','MessageSid':'SM1','Body':'pension'}
    assert client.post('/webhooks/whatsapp',data=payload).status_code == 403
    for i, text in enumerate(['pension','Delhi','60','yes']):
        payload.update(MessageSid=f'SM{i}',Body=text)
        signature=RequestValidator('twilio-secret').compute_signature(url,payload)
        r=client.post('/webhooks/whatsapp',data=payload,headers={'X-Twilio-Signature':signature})
        assert r.status_code == 200
        parts=[n.text for n in ET.fromstring(r.data).findall('.//Body')]
        assert all(len(p)<=1500 for p in parts)
    assert 'basic criteria' in r.text


def test_whatsapp_button_and_query_signature(client):
    payload={'From':'whatsapp:+911111111111','MessageSid':'SMQ','Body':'Old-age Pension','ButtonPayload':'pension'}
    signature=RequestValidator('twilio-secret').compute_signature('https://bot.example/webhooks/whatsapp?a=1',payload)
    r=client.post('/webhooks/whatsapp?a=1',data=payload,headers={'X-Twilio-Signature':signature})
    assert r.status_code == 200 and 'state' in r.text


def test_health_assets_and_traversal(client):
    assert client.get('/healthz').json['status']=='ok'
    assert client.get('/').status_code==200
    assert client.get('/schemes.json').json['schemes']
    assert client.get('/app.mjs').mimetype == 'text/javascript'
    assert client.get('/engine.mjs').mimetype == 'text/javascript'
    assert client.get('/../.env').status_code==404
    assert client.get('/bot/app.py').status_code==404


def test_production_needs_secret(tmp_path):
    with pytest.raises(RuntimeError):
        create_app({'APP_ENV':'production','SESSION_SECRET':'','DATABASE_PATH':str(tmp_path/'x.db')})


def test_python_browser_parity():
    node=shutil.which('node')
    if not node:
        pytest.skip('Node is not installed; browser tests run separately in CI')
    output=subprocess.check_output([node,str(ROOT/'tests/parity.mjs')],cwd=ROOT,text=True,encoding='utf-8')
    actual=json.loads(output)
    expected=[]
    for case in CASES:
        state=None
        turns=[]
        for text in case['inputs']:
            state,reply=respond(state,text)
            turns.append({'state':state,'reply':reply})
        expected.append(turns)
    assert actual==expected
