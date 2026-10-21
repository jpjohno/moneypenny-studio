"""Named local personas plus an explicitly read-only Open WebUI catalogue.

Only model records are read from the existing local container. No auth tables,
chat history, credentials or tools are copied, and WebUI's database is never written.
"""
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid

PATH = Path(__file__).resolve().parent / '.runtime/personas.sqlite3'
WEBUI_QUERY = '''import sqlite3,json
c=sqlite3.connect("file:/app/backend/data/webui.db?mode=ro",uri=True)
rows=c.execute("SELECT id,name,base_model_id,params,meta FROM model WHERE is_active=1").fetchall()
print(json.dumps([dict(id=r[0],name=r[1],base_model_id=r[2],params=json.loads(r[3] or '{}'),meta=json.loads(r[4] or '{}')) for r in rows]))
c.close()
'''


def connect():
    PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute('CREATE TABLE IF NOT EXISTS personas (id TEXT PRIMARY KEY,name TEXT NOT NULL,model TEXT NOT NULL,system TEXT NOT NULL,settings TEXT NOT NULL,updated REAL NOT NULL)')
    return connection


def local():
    with connect() as db:
        return [dict(id=r['id'],name=r['name'],model=r['model'],system=r['system'],settings=json.loads(r['settings']),source='studio',updated=r['updated'])
                for r in db.execute('SELECT * FROM personas ORDER BY updated DESC')]


def webui():
    try:
        result = subprocess.run(['docker','exec','open-webui','python','-c',WEBUI_QUERY],capture_output=True,text=True,timeout=8,check=True)
        records=json.loads(result.stdout)
        items=[]
        for record in records:
            params=record.get('params') or {};meta=record.get('meta') or {}
            items.append(dict(id='webui:'+record['id'],name=record['name'],model=record.get('base_model_id') or record['id'],
                system=params.get('system',''),settings={'temperature':str(params.get('temperature',.7)),
                'maxTokens':str(params.get('num_predict',params.get('max_tokens',256)))},source='openwebui',
                knowledge_count=len(meta.get('knowledge') or [])))
        return items,None
    except (OSError,subprocess.SubprocessError,ValueError,KeyError,TypeError):
        return [],'Open WebUI catalogue unavailable. Local personas still work.'


def catalogue():
    external,error=webui()
    return {'personas':local()+external,'webui_connected':error is None,'webui_error':error}


def resolve(identity):
    if identity.startswith('webui:'):
        records,error=webui()
        if error:raise ValueError(error)
    else:records=local()
    record=next((r for r in records if r['id']==identity),None)
    if not record:raise ValueError('This saved persona is unavailable. Choose another or save a local copy.')
    if record.get('knowledge_count'):
        raise ValueError('This WebUI persona has attached knowledge. An authenticated WebUI chat connection is required to use those collections; direct Ollama mode cannot retrieve them.')
    return record


def save(value):
    if not isinstance(value,dict):raise ValueError('Invalid persona.')
    for key,limit in [('name',60),('model',150),('system',6000)]:
        if not isinstance(value.get(key),str) or len(value[key])>limit or (key!='system' and not value[key].strip()):raise ValueError('Invalid persona '+key+'.')
    settings=value.get('settings',{})
    if not isinstance(settings,dict) or len(json.dumps(settings))>20000:raise ValueError('Invalid persona settings.')
    # Only update a local record by ID. A WebUI record is saved as a new local copy.
    identity=value.get('id')
    if identity and not str(identity).startswith('webui:'):
        try:uuid.UUID(identity)
        except (ValueError,AttributeError):raise ValueError('Invalid persona identity.')
        if not any(p['id']==identity for p in local()):raise ValueError('Saved persona no longer exists.')
    else:identity=str(uuid.uuid4())
    with connect() as db:
        db.execute('INSERT INTO personas VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,model=excluded.model,system=excluded.system,settings=excluded.settings,updated=excluded.updated',
            (identity,value['name'].strip(),value['model'].strip(),value['system'],json.dumps(settings),time.time()))
    return next(record for record in local() if record['id']==identity)
