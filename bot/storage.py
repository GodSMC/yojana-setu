"""Atomic conversations and retry deduplication. Raw channel IDs are never stored."""
import hashlib
import hmac
import json
import sqlite3
import time
from pathlib import Path

from .engine import respond


class Store:
    def __init__(self, path, secret):
        self.path, self.secret = str(path), secret.encode()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, user TEXT NOT NULL, response TEXT NOT NULL, created REAL NOT NULL);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def key(self, raw):
        return hmac.new(self.secret, raw.encode(), hashlib.sha256).hexdigest()

    def handle(self, channel, user, event, text):
        uid = self.key(f'{channel}:{user}')
        eid = self.key(f'{channel}:{user}:{event}')
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM sessions WHERE updated < ?', (now - 7 * 86400,))
            db.execute('DELETE FROM receipts WHERE created < ?', (now - 86400,))
            existing = db.execute('SELECT response FROM receipts WHERE id=?', (eid,)).fetchone()
            if existing:
                return json.loads(existing[0])
            row = db.execute('SELECT state FROM sessions WHERE id=?', (uid,)).fetchone()
            state, reply = respond(json.loads(row[0]) if row else None, text)
            deleting = text.strip().lower() in ('/delete', '/reset', 'delete')
            if deleting:
                db.execute('DELETE FROM sessions WHERE id=?', (uid,))
                db.execute('DELETE FROM receipts WHERE user=?', (uid,))
            else:
                db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?,?)', (uid, json.dumps(state), now))
            # Delete receipts contain only the generic deletion acknowledgement, never old answers.
            db.execute('INSERT INTO receipts VALUES (?,?,?,?)', (eid, uid, json.dumps(reply), now))
        return reply

    def purge(self):
        now = time.time()
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE updated < ?', (now - 7 * 86400,))
            db.execute('DELETE FROM receipts WHERE created < ?', (now - 86400,))
