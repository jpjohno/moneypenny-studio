"""Isolated chat-only tester preview. Never constructs owner data connectors.

Register with register_routes(app, secure, settings). The owner authentication
dependencies are supplied only to invitation management routes. Preview cookies
are a separate authority and must never be accepted by owner routes or events.
"""
from __future__ import annotations

import asyncio
from collections import deque
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

COOKIE = "jjrvis_preview"
MAX_DAYS = 7
INVITE_SECONDS = 600
BODY_LIMIT = 12_000
TOKEN = re.compile(r"^[A-Za-z0-9_-]{40,100}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{16,40}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class InviteRequest(StrictModel):
    label: str = Field(default="Private tester", min_length=1, max_length=80)
    days: int = Field(default=2, ge=1, le=MAX_DAYS)


class ConnectRequest(StrictModel):
    invite: str = Field(min_length=40, max_length=100)


class Turn(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=700)


class ChatRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    persona: Literal["moneypenny", "jarvis"] = "moneypenny"
    history: list[Turn] = Field(default_factory=list, max_length=6)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class PreviewStore:
    def __init__(self, path: Path, clock=time.time):
        self.path, self.clock = Path(path), clock
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with self.db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS invites (
                id TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL, label TEXT NOT NULL,
                created REAL NOT NULL, expires REAL NOT NULL, ttl INTEGER NOT NULL,
                used REAL, revoked INTEGER NOT NULL DEFAULT 0)""")
            db.execute("""CREATE TABLE IF NOT EXISTS preview_sessions (
                digest TEXT PRIMARY KEY, invite_id TEXT NOT NULL,
                created REAL NOT NULL, expires REAL NOT NULL,
                FOREIGN KEY(invite_id) REFERENCES invites(id) ON DELETE CASCADE)""")

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=2)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def prune(self, db):
        now = self.clock()
        db.execute("DELETE FROM preview_sessions WHERE expires<=?", (now,))
        db.execute("""DELETE FROM invites WHERE created<?
            AND id NOT IN (SELECT invite_id FROM preview_sessions)""", (now - MAX_DAYS * 86400,))

    def create(self, label, days):
        now, raw, identity = self.clock(), secrets.token_urlsafe(32), secrets.token_urlsafe(16)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            self.prune(db)
            count = db.execute("SELECT COUNT(*) FROM invites WHERE revoked=0 AND (expires>? OR used IS NOT NULL)", (now,)).fetchone()[0]
            if count >= 16:
                raise HTTPException(429, "Preview capacity reached. Revoke an unused invitation first.")
            db.execute("INSERT INTO invites(id,digest,label,created,expires,ttl) VALUES(?,?,?,?,?,?)",
                       (identity, digest(raw), label.strip(), now, now + INVITE_SECONDS, days * 86400))
        return {"id": identity, "invite": raw, "label": label.strip(),
                "expires_at": now + INVITE_SECONDS, "session_days": days}

    def redeem(self, raw):
        if not TOKEN.fullmatch(raw):
            raise HTTPException(401, "This preview invitation is unavailable or expired.")
        now, session = self.clock(), secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            self.prune(db)
            row = db.execute("SELECT * FROM invites WHERE digest=?", (digest(raw),)).fetchone()
            if row is None or row["revoked"] or row["used"] is not None or row["expires"] <= now:
                raise HTTPException(401, "This preview invitation is unavailable or expired.")
            if db.execute("SELECT COUNT(*) FROM preview_sessions").fetchone()[0] >= 8:
                raise HTTPException(429, "The private preview is full. Ask the owner to make room.")
            expiry = min(now + row["ttl"], row["created"] + MAX_DAYS * 86400)
            db.execute("UPDATE invites SET used=? WHERE id=?", (now, row["id"]))
            db.execute("INSERT INTO preview_sessions VALUES(?,?,?,?)", (digest(session), row["id"], now, expiry))
        return session, expiry

    def session(self, raw):
        if not TOKEN.fullmatch(raw):
            return None
        with self.db() as db:
            row = db.execute("""SELECT s.digest,s.expires,i.id AS invite_id
                FROM preview_sessions s JOIN invites i ON i.id=s.invite_id
                WHERE s.digest=? AND s.expires>? AND i.revoked=0""", (digest(raw), self.clock())).fetchone()
        return dict(row) if row else None

    def disconnect(self, raw):
        with self.db() as db:
            db.execute("DELETE FROM preview_sessions WHERE digest=?", (digest(raw),))

    def invitations(self):
        with self.db() as db:
            self.prune(db)
            rows = db.execute("""SELECT i.id,i.label,i.created,i.expires,i.used,i.revoked,
                MAX(s.expires) AS session_expires FROM invites i
                LEFT JOIN preview_sessions s ON s.invite_id=i.id
                GROUP BY i.id ORDER BY i.created DESC LIMIT 32""").fetchall()
        now = self.clock()
        return [{"id": r["id"], "label": r["label"], "created_at": r["created"],
                 "invite_expires_at": r["expires"], "session_expires_at": r["session_expires"],
                 "state": "revoked" if r["revoked"] else "active" if r["session_expires"] and r["session_expires"] > now
                 else "used" if r["used"] is not None else "pending" if r["expires"] > now else "expired"}
                for r in rows]

    def revoke(self, identity):
        if not IDENTIFIER.fullmatch(identity):
            raise HTTPException(404, "Preview invitation not found.")
        with self.db() as db:
            if not db.execute("UPDATE invites SET revoked=1 WHERE id=?", (identity,)).rowcount:
                raise HTTPException(404, "Preview invitation not found.")
            db.execute("DELETE FROM preview_sessions WHERE invite_id=?", (identity,))


class PreviewService:
    def __init__(self, settings, path, *, transport=None, clock=time.time, local_model=None):
        origin = urlsplit(settings.ollama_url)
        if origin.scheme != "http" or origin.hostname not in {"127.0.0.1", "localhost", "::1"} or origin.username or origin.password or origin.path not in {"", "/"} or origin.query or origin.fragment:
            raise ValueError("Preview inference must use the local Ollama service.")
        model = local_model or settings.model
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,160}", model):
            raise ValueError("Select an installed local preview model.")
        self.settings, self.model, self.transport, self.clock = settings, model, transport, clock
        self.store = PreviewStore(path, clock)
        self.gate = asyncio.Semaphore(1)
        self.rate = {}
        self.allowed = {f"http://127.0.0.1:{settings.port}", f"http://localhost:{settings.port}", *settings.origins}

    def boundary(self, request, *, owner=False):
        actual = str(request.base_url).rstrip("/")
        if actual not in self.allowed:
            raise HTTPException(403, "Preview host is not allowed.")
        origin = request.headers.get("origin")
        if request.method in {"GET", "HEAD"}:
            if origin and origin != actual:
                raise HTTPException(403, "Same-origin preview request required.")
        elif origin != actual:
            bearer = request.headers.get("authorization", "")
            if not (owner and not origin and hmac.compare_digest(bearer, "Bearer " + self.settings.token)):
                raise HTTPException(403, "Same-origin preview request required.")

    def authenticate(self, request):
        self.boundary(request)
        session = self.store.session(request.cookies.get(COOKIE, ""))
        if session is None:
            raise HTTPException(401, "Connect a valid private preview invitation to continue.")
        return session

    async def body(self, request, model):
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, "JSON required.")
        length = request.headers.get("content-length", "")
        if length and (not length.isdigit() or int(length) > BODY_LIMIT):
            raise HTTPException(413, "Preview request is too large.")
        value = bytearray()
        async for chunk in request.stream():
            if len(value) + len(chunk) > BODY_LIMIT:
                raise HTTPException(413, "Preview request is too large.")
            value.extend(chunk)
        try:
            result = model.model_validate_json(value)
            if hasattr(result, "question") and not result.question.strip():
                raise ValueError("Empty question")
            if hasattr(result, "label") and not result.label.strip():
                raise ValueError("Empty label")
            return result
        except (ValidationError, ValueError):
            raise HTTPException(422, "Invalid preview request.") from None

    async def chat(self, session, value):
        if self.gate.locked():
            raise HTTPException(429, "The preview is answering a question. Try again shortly.")
        now = self.clock()
        self.rate = {key: times for key, times in self.rate.items() if times and times[-1] > now - 60}
        times = self.rate.setdefault(session["digest"], deque())
        while times and times[0] <= now - 60:
            times.popleft()
        if len(times) >= 8:
            raise HTTPException(429, "Preview limit reached. Wait a minute before another question.")
        times.append(now)
        async with self.gate:
            name = "Moneypenny" if value.persona == "moneypenny" else "Jarvis"
            system = (f"You are {name}, a friendly, concise British assistant in a restricted JJRVIS tester preview. "
                      "This preview provides conversation only. You have no access to the owner's accounts, "
                      "mail, contacts, calendar, home, vehicle, cameras, files, computer controls, trading or other users. "
                      "No tools or live internet are available. Never claim to have read or changed any of them. "
                      "Explain that connecting real services is outside this preview if asked. Do not invent personal facts.")
            payload = {"model": self.model, "stream": False, "keep_alive": "5m",
                       "messages": [{"role": "system", "content": system}]
                       + [turn.model_dump() for turn in value.history]
                       + [{"role": "user", "content": value.question.strip()}],
                       "options": {"num_ctx": 4096, "num_predict": 256, "temperature": .6}}
            try:
                async with asyncio.timeout(35):
                    async with httpx.AsyncClient(timeout=30, trust_env=False, follow_redirects=False, transport=self.transport) as client:
                        async with client.stream("POST", self.settings.ollama_url.rstrip("/") + "/api/chat", json=payload) as response:
                            response.raise_for_status()
                            raw = bytearray()
                            async for part in response.aiter_bytes():
                                if len(raw) + len(part) > 64 * 1024:
                                    raise ValueError("Oversized local response")
                                raw.extend(part)
                answer = json.loads(raw).get("message", {}).get("content", "")
                if not isinstance(answer, str) or not answer.strip() or len(answer) > 12_000:
                    raise ValueError("Invalid local response")
            except (httpx.HTTPError, TimeoutError, ValueError, TypeError, AttributeError):
                raise HTTPException(503, "The selected local preview model is unavailable. No cloud fallback was used.") from None
            # Owner revocation/expiry takes effect even while a generation was running.
            with self.store.db() as db:
                active = db.execute("""SELECT 1 FROM preview_sessions s JOIN invites i ON i.id=s.invite_id
                    WHERE s.digest=? AND s.expires>? AND i.revoked=0""", (session["digest"], self.clock())).fetchone()
            if not active:
                raise HTTPException(401, "This preview session has ended.")
            return {"answer": answer.strip(), "persona": value.persona, "model": self.model,
                    "scope": "chat_only", "actions_executed": False, "external_context_used": False}


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>JJRVIS · Private preview</title><link rel="stylesheet" href="/preview.css"><script src="/preview.js" defer></script></head><body><main><header><p class="eyebrow">JJRVIS / PRIVATE PREVIEW</p><span class="orb" aria-hidden="true"></span><h1>A conversation.<br>A little more human.</h1><p>Meet Moneypenny or Jarvis in this limited preview.</p></header><section id="connect"><h2>Your invitation</h2><p id="connect-copy">Open your private invitation link to begin.</p><button id="connect-button" hidden>Accept private preview</button></section><section id="chat" hidden><div class="chat-toolbar"><label>Speak with <select id="persona"><option value="moneypenny">Moneypenny</option><option value="jarvis">Jarvis</option></select></label><button id="disconnect" class="quiet">End this preview</button></div><div id="messages" aria-live="polite"></div><form id="ask"><label for="question">Your message</label><textarea id="question" rows="3" maxlength="2000" required placeholder="Say hello, ask a question or explore an idea…"></textarea><button id="send">Send message ↗</button></form><p id="expiry" class="muted"></p></section><p id="status" role="status"></p><footer><strong>Conversation only.</strong> Owner accounts, messages, files, home, cameras, cars and trading are unavailable. This preview cannot perform actions or browse the internet.</footer></main></body></html>"""

JS = """'use strict';
const $=id=>document.getElementById(id);let invitation=new URLSearchParams(location.hash.slice(1)).get('invite')||'',history=[];
if(location.hash)window.history.replaceState(null,'','/preview');
async function api(path,body){const response=await fetch(path,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const data=await response.json();if(!response.ok)throw new Error(data.detail||'The preview is unavailable.');return data;}
function locked(message){$('chat').hidden=true;$('connect').hidden=false;$('status').textContent=message||'';history=[];$('messages').replaceChildren();}
async function session(){try{const data=await api('/v1/preview/session');$('chat').hidden=false;$('connect').hidden=true;$('expiry').textContent='Private preview ends '+new Date(data.expires_at*1000).toLocaleString();$('status').textContent='Local conversation · no connected accounts or tools';}catch(error){locked(error.message);}}
function message(role,text){const row=document.createElement('article'),label=document.createElement('small'),body=document.createElement('p');row.className=role;label.textContent=role==='user'?'YOU':$('persona').selectedOptions[0].textContent.toUpperCase();body.textContent=text;row.append(label,body);$('messages').append(row);}
if(invitation){$('connect-copy').textContent='This invitation enables limited chat only. It never grants access to the owner’s workspace.';$('connect-button').hidden=false;}
$('connect-button').onclick=async()=>{const button=$('connect-button');button.disabled=true;try{await api('/v1/preview/connect',{invite:invitation});invitation='';button.hidden=true;await session();}catch(error){$('status').textContent=error.message;}finally{button.disabled=false;}};
$('ask').onsubmit=async event=>{event.preventDefault();const question=$('question').value.trim();if(!question)return;const button=$('send');if(button.disabled)return;button.disabled=true;message('user',question);$('question').value='';$('status').textContent='Thinking with the local model…';try{const data=await api('/v1/preview/chat',{question,persona:$('persona').value,history:history.slice(-6).map(t=>({...t,content:t.content.slice(0,700)}))});message('assistant',data.answer);history.push({role:'user',content:question},{role:'assistant',content:data.answer});history=history.slice(-6);$('status').textContent='Local conversation · no actions performed';}catch(error){$('status').textContent=error.message;}finally{button.disabled=false;$('question').focus();}};
$('disconnect').onclick=async()=>{try{await api('/v1/preview/disconnect',{});locked('Your preview is disconnected.');}catch(error){$('status').textContent=error.message;}};
$('persona').onchange=()=>{history=[];$('messages').replaceChildren();};
session();setInterval(()=>{if(!$('chat').hidden)session();},30000);
"""

CSS = """*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:radial-gradient(ellipse at 75% 10%,#17394a,transparent 55%),#09121b;color:#d8e8ee;font:16px/1.65 system-ui,-apple-system,sans-serif}main{width:min(760px,calc(100% - 36px));margin:50px auto}header{position:relative;padding-bottom:25px}.eyebrow{font:600 10px/1.5 ui-monospace,monospace;letter-spacing:.2em;color:#92b7c5}h1{font-size:clamp(34px,7vw,56px);line-height:1.12;letter-spacing:-.045em;font-weight:450;margin:25px 0 20px}header>p:last-child{color:#94aebc}.orb{float:right;width:80px;height:80px;margin-top:20px;border:1px solid #a7d5df77;border-radius:50%;box-shadow:inset 0 0 24px #81b9c150,0 0 45px #548caa20;background:radial-gradient(circle at 35% 25%,#75a6b7aa,#14384c 50%,#09131f)}section{border:1px solid #6b929e44;border-radius:18px;background:#112431ba;padding:25px}h2{font-size:21px;font-weight:500;margin-top:0}.chat-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}label{display:block;font-size:13px;color:#a5bec8}button,select,textarea{font:inherit;border:1px solid #63879288;border-radius:10px;color:#deedf2;background:#15394c;padding:11px 14px;min-height:44px}button{cursor:pointer;font-size:14px}button:disabled{opacity:.5;cursor:wait}.quiet{background:transparent;color:#9db9c5}select{margin-left:8px;font-size:14px}textarea{display:block;width:100%;resize:vertical;margin:8px 0 12px;background:#0a1b27}#messages{margin:25px 0;max-height:420px;overflow:auto}article{border-top:1px solid #718f9b22;padding-top:15px}article small{font-size:9px;letter-spacing:.15em;color:#9cc3c7}article p{white-space:pre-wrap;overflow-wrap:anywhere;margin-top:7px}.user p{color:#9eb9c9}#status,.muted{font-size:12px;color:#97b4bf}footer{font-size:12px;color:#8ea8b7;padding:20px 7px}footer strong{color:#b8cfd7}button:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #a6d8e5;outline-offset:3px}@media(max-width:500px){main{margin:25px auto}section{padding:18px}.orb{width:55px;height:55px}}
"""


def register_routes(app, secure, settings, *, database_path=None, transport=None, clock=time.time, local_model=None):
    """Register isolated routes; returns service for owner integration and tests."""
    path = database_path or Path(__file__).resolve().parent / ".runtime/tester-preview.sqlite3"
    service = PreviewService(settings, path, transport=transport, clock=clock, local_model=local_model)

    @app.get("/preview", include_in_schema=False)
    async def preview_page(request: Request):
        service.boundary(request)
        return HTMLResponse(HTML, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    @app.get("/preview.js", include_in_schema=False)
    async def preview_script(request: Request):
        service.boundary(request)
        return Response(JS, media_type="text/javascript", headers={"Cache-Control": "no-store"})

    @app.get("/preview.css", include_in_schema=False)
    async def preview_style(request: Request):
        service.boundary(request)
        return Response(CSS, media_type="text/css", headers={"Cache-Control": "no-store"})

    @app.get("/v1/workspace/preview-invites", dependencies=secure)
    async def list_invites(request: Request):
        service.boundary(request, owner=True)
        return {"invites": service.store.invitations(), "scope": "isolated_chat_only", "sends": False}

    @app.post("/v1/workspace/preview-invites", dependencies=secure)
    async def create_invite(request: Request):
        service.boundary(request, owner=True)
        value = await service.body(request, InviteRequest)
        created = service.store.create(value.label, value.days)
        origin = settings.origins[0] if settings.origins else str(request.base_url).rstrip("/")
        created["url"] = origin + "/preview#invite=" + created.pop("invite")
        return {**created, "single_use": True, "scope": "chat_only", "sent": False,
                "warning": "Share only this preview link. Owner pairing links grant owner access."}

    @app.post("/v1/workspace/preview-invites/{identity}/revoke", dependencies=secure)
    async def revoke_invite(identity: str, request: Request):
        service.boundary(request, owner=True)
        service.store.revoke(identity)
        return {"state": "revoked"}

    @app.post("/v1/preview/connect")
    async def connect(request: Request):
        service.boundary(request)
        value = await service.body(request, ConnectRequest)
        session, expiry = service.store.redeem(value.invite)
        response = JSONResponse({"state": "connected", "scope": "chat_only", "expires_at": expiry}, headers={"Cache-Control": "no-store"})
        response.set_cookie(COOKIE, session, httponly=True, samesite="strict", secure=request.url.scheme == "https",
                            max_age=max(1, int(expiry - clock())), path="/")
        return response

    @app.get("/v1/preview/session")
    async def preview_session(request: Request):
        session = service.authenticate(request)
        return JSONResponse({"scope": "chat_only", "expires_at": session["expires"], "model": service.model,
                             "owner_access": False, "external_context": False}, headers={"Cache-Control": "no-store"})

    @app.post("/v1/preview/chat")
    async def preview_chat(request: Request):
        session = service.authenticate(request)
        value = await service.body(request, ChatRequest)
        return JSONResponse(await service.chat(session, value), headers={"Cache-Control": "no-store"})

    @app.post("/v1/preview/disconnect")
    async def disconnect(request: Request):
        service.authenticate(request)
        service.store.disconnect(request.cookies.get(COOKIE, ""))
        response = JSONResponse({"state": "disconnected"}, headers={"Cache-Control": "no-store"})
        response.delete_cookie(COOKIE, path="/")
        return response

    return service
