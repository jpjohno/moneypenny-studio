"""Local persistent follow-ups. Claimed by the visible studio when it can respond."""
from pathlib import Path
import sqlite3
import time
import uuid

PATH=Path(__file__).resolve().parent/'.runtime/reminders.sqlite3'


def connection():
    PATH.parent.mkdir(exist_ok=True)
    conn=sqlite3.connect(PATH,timeout=5)
    conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS reminders (id TEXT PRIMARY KEY, text TEXT NOT NULL, due REAL NOT NULL, state TEXT NOT NULL DEFAULT "pending")')
    return conn


def add(text,delay):
    value={'id':str(uuid.uuid4()),'text':text,'due':time.time()+delay,'state':'pending'}
    with connection() as conn:conn.execute('INSERT INTO reminders(id,text,due) VALUES(?,?,?)',(value['id'],text,value['due']))
    return value


def pending():
    with connection() as conn:return [dict(row) for row in conn.execute('SELECT * FROM reminders WHERE state="pending" ORDER BY due LIMIT 100')]


def claim(identity):
    with connection() as conn:
        result=conn.execute('UPDATE reminders SET state="delivered" WHERE id=? AND state="pending" AND due<=?',(identity,time.time()))
        return result.rowcount==1
