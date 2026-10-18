"""Per-account direct mail connections, separate from the Mac Mail database.

Connections are made only by an explicit user action. TLS hosts and accounts are
server-owned. Readers never send mail or change read flags. Provider sign-in is
not presented as completed until the expected account has been verified.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, parseaddr
from pathlib import Path
from urllib.parse import quote
import asyncio
import imaplib
import json
import os
import re
import secrets
import ssl
import tempfile
import threading
import time
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from workspace_data import ACCOUNT, MAIL_CACHE

HERE = Path(__file__).resolve().parent
SCOPES = ["User.Read", "Mail.Read"]
IMAP_HOSTS = {"gmail": "imap.gmail.com", "icloud": "imap.mail.me.com"}
PROVIDER_LINKS = {
    "gmail": ("https://mail.google.com/", "https://myaccount.google.com/apppasswords"),
    "icloud": ("https://www.icloud.com/mail/", "https://account.apple.com/"),
    "microsoft365": ("https://outlook.office.com/mail/", "https://microsoft.com/devicelogin"),
    "hotmail": ("https://outlook.live.com/mail/", "https://microsoft.com/devicelogin"),
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd, tmp = tempfile.mkstemp(prefix=".account-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class AppPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_password: SecretStr = Field(min_length=16, max_length=64)


class AddAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address: str = Field(min_length=3, max_length=254)
    provider: Literal["gmail", "icloud", "microsoft365", "hotmail"]


class CloudMailAccounts:
    def __init__(self, native, legacy_mail, root=None):
        self.native = native
        self.legacy = legacy_mail
        self.root = Path(root or HERE / ".runtime/cloud-mail")
        self.jobs = {}
        self.last_checks = {}
        self.lock = threading.RLock()
        self.read_locks = {}

    def account(self, account_id):
        account = next((a for a in self.entries() if a["id"] == account_id and a.get("enabled")), None)
        if not account:
            raise HTTPException(404, "This mailbox has not been added to this workspace")
        domain = account["address"].lower().split("@")[-1]
        provider = "gmail" if domain in {"gmail.com", "googlemail.com"} else "icloud" if domain in {"me.com", "icloud.com", "mac.com"} else "hotmail" if domain in {"hotmail.com", "outlook.com", "live.com"} else "microsoft365"
        return {"id": account["id"], "address": account["address"], "provider": account.get("provider", provider)}

    def entries(self):
        path = self.root / "accounts.json"
        try:
            added = json.loads(path.read_text()) if not path.is_symlink() else []
        except FileNotFoundError:
            added = []
        except (OSError, ValueError):
            raise HTTPException(503, "Saved account list could not be read")
        return self.native.accounts() + added

    def add_account(self, request):
        address = request.address.strip().lower()
        if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", address):
            raise HTTPException(400, "Enter a valid email address")
        with self.lock:
            entries = self.entries()
            existing = next((a for a in entries if a["address"].lower() == address), None)
            if existing:
                return self.account(existing["id"])
            if len(entries) >= 50:
                raise HTTPException(400, "This workspace supports up to 50 mail accounts")
            row = {"id": "cloud_" + secrets.token_hex(12), "address": address, "provider": request.provider, "enabled": True}
            native_ids = {a["id"] for a in self.native.accounts()}
            private_json(self.root / "accounts.json", [a for a in entries if a["id"] not in native_ids] + [row])
            return self.account(row["id"])

    def path(self, account):
        # account() restricts IDs to the registered accounts; additionally never
        # let a future registry entry turn an identifier into a filesystem path.
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", account["id"]):
            raise HTTPException(400, "Account identifier is invalid")
        return self.root / (account["id"] + ".json")

    def saved(self, account):
        path = self.path(account)
        try:
            if path.is_symlink():
                return None
            value = json.loads(path.read_text())
            return value if value.get("address", "").lower() == account["address"].lower() else None
        except (OSError, ValueError):
            return None

    def status(self):
        rows = []
        for entry in self.entries():
            if not entry.get("enabled"):
                continue
            account = self.account(entry["id"])
            saved = self.saved(account)
            legacy = account["address"].lower() == ACCOUNT
            check = self.last_checks.get(account["id"], {})
            rows.append({**account, "state": check.get("state") or ("saved_sign_in" if saved or legacy else "sign_in_needed"),
                         "checked_at": check.get("checked_at"), "detail": check.get("detail") or ("Existing Microsoft sign-in. Open the inbox to check it now." if legacy else "Sign-in saved. Open the inbox to check server access." if saved else "Complete this account's sign-in to read directly from its provider."),
                         "method": "app_password" if account["provider"] in IMAP_HOSTS else "microsoft_device",
                         "webmail_url": PROVIDER_LINKS[account["provider"]][0],
                         "sign_in_url": PROVIDER_LINKS[account["provider"]][1],
                         "can_open": bool(saved or legacy), "can_send": False,
                         "scope": "read_only", "source": "provider_cloud"})
        return {"accounts": rows, "checked_at": stamp()}

    def _imap(self, account, password):
        connection = imaplib.IMAP4_SSL(IMAP_HOSTS[account["provider"]], port=993, ssl_context=ssl.create_default_context(), timeout=15)
        try:
            connection.login(account["address"], password)
            state, counts = connection.select("INBOX", readonly=True)
            if state != "OK" or not counts or not counts[0].isdigit():
                raise ValueError("Inbox unavailable")
            connection._jjrvis_message_count = int(counts[0])
            return connection
        except Exception:
            try:
                connection.logout()
            except Exception:
                pass
            raise

    def connect_password(self, account_id, password):
        account = self.account(account_id)
        if account["provider"] not in IMAP_HOSTS:
            raise HTTPException(400, "Use Microsoft sign-in for this account")
        password = re.sub(r"[\s-]", "", password)
        if not re.fullmatch(r"[a-zA-Z0-9]{16}", password):
            raise HTTPException(400, "Enter the 16-character app-specific password, not the account password")
        if account["provider"] == "icloud":
            password = "-".join(password[i:i+4] for i in range(0, 16, 4))
        try:
            connection = self._imap(account, password)
            connection.logout()
        except Exception:
            raise HTTPException(503, "The provider did not accept this connection. Check the account's app-specific password and mail access settings. Nothing was saved.")
        private_json(self.path(account), {"address": account["address"], "provider": account["provider"], "app_password": password, "connected_at": stamp()})
        self.last_checks[account_id] = {"state": "connected", "checked_at": stamp(), "detail": "Inbox access verified directly with the mail provider."}
        return {"state": "connected", "account": account["address"], "checked_at": stamp()}

    def _ms_app(self, account, *, existing=False):
        import msal
        import requests
        saved = self.saved(account)
        raw = json.loads(MAIL_CACHE.read_text())
        # Reuse this app's already configured registration, never a third party's.
        configured = next(a for a in raw.get("Account", {}).values() if a.get("username", "").lower() == ACCOUNT)
        credential = next(t for t in raw.get("AccessToken", {}).values() if t.get("home_account_id") == configured["home_account_id"])
        client_id = credential["client_id"]
        cache = msal.SerializableTokenCache()
        if existing and saved:
            cache.deserialize(saved["cache"])
        class BoundedSession(requests.Session):
            def request(self, *args, **kwargs):
                kwargs["timeout"] = (5, 15)
                return super().request(*args, **kwargs)
        session = BoundedSession()
        session.trust_env = False
        authority = "https://login.microsoftonline.com/common"
        # This registration already belongs to Junomo's organisation. Its
        # device-code endpoint cannot infer that tenant from /common. Use the
        # same trusted realm as the working mailbox for other Junomo accounts;
        # do not route unrelated organisations or personal accounts into it.
        if account["provider"] == "microsoft365" and account["address"].lower().split("@")[-1] == ACCOUNT.split("@")[-1]:
            realm = configured.get("realm", "")
            if not isinstance(realm, str) or not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", realm):
                session.close()
                raise ValueError("Microsoft organisation configuration is unavailable")
            authority = "https://login.microsoftonline.com/" + realm
        return msal.PublicClientApplication(client_id, authority=authority, token_cache=cache, http_client=session), cache, session

    def start_microsoft(self, account_id):
        account = self.account(account_id)
        if account["provider"] in IMAP_HOSTS:
            raise HTTPException(400, "Use the account's app-password connection")
        with self.lock:
            self.jobs = {k:v for k,v in self.jobs.items() if v["expires_at"] > time.time()}
            if any(j["account_id"] == account_id and j["state"] == "pending" for j in self.jobs.values()):
                raise HTTPException(409, "Sign-in is already waiting in this workspace")
            if len(self.jobs) >= 10:
                raise HTTPException(429, "Too many sign-in requests. Let the existing requests expire.")
            try:
                app, cache, session = self._ms_app(account)
                flow = app.initiate_device_flow(scopes=SCOPES)
                if "user_code" not in flow:
                    session.close()
                    codes = set(re.findall(r"AADSTS\d+", str(flow.get("error_description", ""))))
                    if codes.intersection({"AADSTS50059", "AADSTS50194", "AADSTS90133"}):
                        raise HTTPException(503, "This Microsoft application is not configured for this account's sign-in route. Your existing connected mailboxes are unchanged.")
                    raise ValueError("Flow unavailable")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(503, "Microsoft sign-in could not start. The configured application must permit this account type and device sign-in.")
            job_id = secrets.token_urlsafe(32)
            job = {"account_id":account_id, "state":"pending", "expires_at":time.time()+min(int(flow.get("expires_in",900)),900), "detail":"Finish Microsoft sign-in for " + account["address"]}
            self.jobs[job_id] = job
        def finish():
            try:
                result = app.acquire_token_by_device_flow(flow)
                if "access_token" not in result:
                    raise ValueError("Sign-in incomplete")
                response = session.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization":"Bearer " + result["access_token"]}, params={"$select":"mail,userPrincipalName"}, allow_redirects=False)
                response.raise_for_status()
                identity = {str(v).lower() for v in response.json().values()}
                if account["address"].lower() not in identity:
                    job.update(state="failed", detail="You signed in to a different account. Nothing was saved; start again with " + account["address"])
                    return
                # Verify mailbox access as well as identity before persisting.
                inbox = session.get("https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages", headers={"Authorization":"Bearer " + result["access_token"]}, params={"$top":1,"$select":"id"}, allow_redirects=False)
                inbox.raise_for_status()
                private_json(self.path(account), {"address":account["address"], "provider":account["provider"], "cache":cache.serialize(), "connected_at":stamp()})
                job.update(state="connected", detail="Account identity and inbox access verified.")
                self.last_checks[account_id] = {"state":"connected", "checked_at":stamp(), "detail":job["detail"]}
            except Exception:
                job.update(state="failed", detail="Microsoft sign-in was not completed or this account is not permitted by the application. Nothing was saved.")
        threading.Thread(target=finish, daemon=True).start()
        return {"job_id":job_id, "state":"pending", "user_code":flow["user_code"], "verification_uri":"https://microsoft.com/devicelogin", "expires_in":min(int(flow.get("expires_in",900)),900), "account":account["address"]}

    def sign_in_status(self, job_id):
        job = self.jobs.get(job_id)
        if not job or job["expires_at"] <= time.time():
            raise HTTPException(410, "Sign-in request expired. Start again.")
        return {k:job[k] for k in ("state", "account_id", "detail")}

    def _graph_read(self, account, message_id=None):
        if account["address"].lower() == ACCOUNT and not self.saved(account):
            return self.legacy.message(message_id) if message_id else self.legacy.inbox()
        app, cache, session = self._ms_app(account, existing=True)
        identities = app.get_accounts(username=account["address"])
        if not identities:
            raise ValueError("Sign-in needed")
        token = app.acquire_token_silent_with_error(SCOPES, account=identities[0]) or {}
        if "access_token" not in token:
            raise ValueError("Sign-in needed")
        headers = {"Authorization":"Bearer " + token["access_token"], "Prefer":'outlook.body-content-type="text"'}
        base = "https://graph.microsoft.com/v1.0/me/"
        path = "messages/" + quote(message_id, safe="") if message_id else "mailFolders/inbox/messages"
        fields = "id,conversationId,subject,from,receivedDateTime,isRead,hasAttachments,bodyPreview,webLink" + (",body,toRecipients" if message_id else "")
        params = {"$select":fields}
        if not message_id:
            params.update({"$top":50,"$orderby":"receivedDateTime desc"})
        response = session.get(base+path, headers=headers, params=params, allow_redirects=False, stream=True)
        try:
            response.raise_for_status()
            payload = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                payload.extend(chunk)
                if len(payload) > 2_000_000:
                    raise HTTPException(413, "Open this large message in its mail app to view the full content")
            data = json.loads(payload)
        finally:
            response.close()
        def row(d):
            return {"id":d["id"], "conversation_id":d.get("conversationId"), "subject":d.get("subject", ""), "sender":d.get("from",{}).get("emailAddress",{}).get("address", ""), "received_at":d.get("receivedDateTime"), "is_read":d.get("isRead"), "has_attachments":d.get("hasAttachments"), "preview":d.get("bodyPreview", ""), "body":d.get("body",{}).get("content", "")[:80000], "web_link":d.get("webLink"), "account":account["address"], "mode":"live_read_only"}
        if cache.has_state_changed:
            private_json(self.path(account), {"address":account["address"],"provider":account["provider"],"cache":cache.serialize(),"connected_at":stamp()})
        return row(data) if message_id else {"state":"connected", "mode":"live_read_only", "account":account["address"], "messages":[row(x) for x in data.get("value",[])], "checked_at":stamp()}

    def _imap_read(self, account, message_id=None):
        saved = self.saved(account)
        if not saved:
            raise HTTPException(409, "Connect this account first")
        connection = self._imap(account, saved["app_password"])
        try:
            validity = (connection.response("UIDVALIDITY")[1] or [b""])[0].decode()
            if not validity.isdigit():
                raise ValueError("Inbox identity unavailable")
            if message_id:
                match = re.fullmatch(r"(\d+):(\d+)", message_id)
                if not match or match[1] != validity:
                    raise HTTPException(409, "This inbox has changed. Refresh it before opening this message.")
                uid = match[2]
                state, size_info = connection.uid("fetch", uid, "(RFC822.SIZE)")
                found = re.search(rb"RFC822.SIZE (\d+)", b" ".join(x for x in size_info if isinstance(x,bytes)))
                if state != "OK" or not found:
                    raise HTTPException(404, "Message is no longer available")
                if int(found[1]) > 2_000_000:
                    raise HTTPException(413, "Open this large message in its mail app to view the full message and attachments")
                state, response = connection.uid("fetch", uid, "(UID FLAGS BODY.PEEK[])")
            else:
                count = connection._jjrvis_message_count
                if not count:
                    return {"state":"connected","mode":"live_read_only","account":account["address"],"messages":[],"checked_at":stamp()}
                # Read only the latest 50 sequence positions, with at most 32 KiB
                # of headers each. Do not retrieve an unbounded SEARCH ALL list.
                state, response = connection.fetch(f"{max(1,count-49)}:{count}", "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID IN-REPLY-TO REFERENCES)]<0.32768>)")
            if state != "OK":
                raise ValueError("Messages unavailable")
            rows = []
            for item in response:
                if not isinstance(item,tuple):
                    continue
                meta, body = item
                uid = re.search(rb"UID (\d+)",meta)
                if not uid:
                    continue
                message = BytesParser(policy=policy.default).parsebytes(body)
                try:
                    received = parsedate_to_datetime(str(message.get("Date", ""))).isoformat()
                except (TypeError, ValueError):
                    received = None
                references = str(message.get("References", "")).split()
                rows.append({"id":validity+":"+uid[1].decode(), "subject":str(message.get("Subject", "")), "sender":parseaddr(str(message.get("From", "")))[1], "received_at":received, "is_read":b"\\Seen" in meta, "internet_message_id":str(message.get("Message-ID", "")), "conversation_id":references[0] if references else str(message.get("In-Reply-To") or message.get("Message-ID") or ""), "account":account["address"], "mode":"live_read_only", "body_scope":"full_message" if message_id else "headers_only"})
                if message_id:
                    part = message.get_body(preferencelist=("plain",)) if message.is_multipart() else message
                    rows[-1]["body"] = str(part.get_content())[:80000] if part and part.get_content_type()=="text/plain" else "This message contains an HTML layout. Open it in the provider's mail app for the original formatting."
                    rows[-1]["has_attachments"] = any(p.get_content_disposition()=="attachment" for p in message.walk())
            if message_id:
                if not rows:
                    raise HTTPException(404,"Message is no longer available")
                return rows[0]
            return {"state":"connected","mode":"live_read_only","account":account["address"],"messages":list(reversed(rows)),"checked_at":stamp()}
        finally:
            try:
                connection.logout()
            except Exception:
                pass

    def read(self, account_id, message_id=None):
        account = self.account(account_id)
        with self.lock:
            guard = self.read_locks.setdefault(account_id, threading.Lock())
        with guard:
            return self._read_checked(account, message_id)

    def _read_checked(self, account, message_id=None):
        account_id = account["id"]
        try:
            result = self._imap_read(account,message_id) if account["provider"] in IMAP_HOSTS else self._graph_read(account,message_id)
            if result.get("state") == "unavailable":
                raise ValueError("Provider unavailable")
            self.last_checks[account_id] = {"state":"connected", "checked_at":stamp(), "detail":"Read directly from the mail provider. Opening here does not change read flags."}
            return result
        except HTTPException:
            raise
        except Exception:
            self.last_checks[account_id] = {"state":"unavailable", "checked_at":stamp(), "detail":"The provider could not be read. Reconnect this account or try again."}
            raise HTTPException(503, self.last_checks[account_id]["detail"])


def register_routes(app, secure, native, legacy_mail):
    service = CloudMailAccounts(native, legacy_mail)
    @app.get("/v1/workspace/mail-accounts", dependencies=secure)
    async def accounts():
        return service.status()
    @app.post("/v1/workspace/mail-accounts", dependencies=secure)
    async def add_account(request:AddAccountRequest):
        return service.add_account(request)
    @app.post("/v1/workspace/mail-accounts/{account_id}/app-password", dependencies=secure)
    async def connect_password(account_id:str, request:AppPasswordRequest):
        return await asyncio.to_thread(service.connect_password, account_id, request.app_password.get_secret_value())
    @app.post("/v1/workspace/mail-accounts/{account_id}/microsoft", dependencies=secure)
    async def connect_microsoft(account_id:str):
        return await asyncio.to_thread(service.start_microsoft,account_id)
    @app.get("/v1/workspace/mail-sign-ins/{job_id}", dependencies=secure)
    async def sign_in_status(job_id:str):
        return service.sign_in_status(job_id)
    @app.get("/v1/workspace/mail-accounts/{account_id}/messages", dependencies=secure)
    async def messages(account_id:str, message_id:str|None=None):
        return await asyncio.to_thread(service.read,account_id,message_id)
    return service
