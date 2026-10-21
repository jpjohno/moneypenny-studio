"""Preview isolation contracts. Only mocks and temporary databases are used."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import tester_preview as preview

OWNER_TOKEN = "isolated-preview-owner-test-token-not-a-real-credential"
ORIGIN = "https://preview.example.invalid"
OWNER = {"Authorization": "Bearer " + OWNER_TOKEN}
HEADERS = {"Origin": ORIGIN}


@pytest.fixture
def env(tmp_path):
    clock = [10_000.0]
    requests = []

    def transport(request):
        requests.append(request)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "A synthetic preview answer."}, "done": True})

    async def owner_auth(request: Request):
        if request.headers.get("authorization") != OWNER["Authorization"]:
            raise HTTPException(401, "Owner authentication required")

    app = FastAPI()
    service = preview.register_routes(app, [Depends(owner_auth)],
        SimpleNamespace(token=OWNER_TOKEN, port=8766, origins=(ORIGIN,),
                        model="fixture-local:latest", ollama_url="http://127.0.0.1:11434"),
        database_path=tmp_path / "preview.sqlite3", transport=httpx.MockTransport(transport), clock=lambda: clock[0])
    return SimpleNamespace(app=app, service=service, clock=clock, requests=requests,
                           client=TestClient(app, base_url=ORIGIN), path=tmp_path / "preview.sqlite3")


def invite(env, **changes):
    response = env.client.post("/v1/workspace/preview-invites", json={"label": "Synthetic tester", **changes}, headers=OWNER)
    assert response.status_code == 200
    value = response.json()
    value["raw"] = parse_qs(urlsplit(value["url"]).fragment)["invite"][0]
    return value


def connect(env, value=None):
    value = value or invite(env)
    response = env.client.post("/v1/preview/connect", json={"invite": value["raw"]}, headers=HEADERS)
    assert response.status_code == 200
    return value, response


def test_shell_has_no_owner_context_or_automatic_connection(env):
    page = env.client.get("/preview")
    assert page.status_code == 200 and "Conversation only" in page.text
    assert "Owner accounts" in page.text
    assert "<iframe" not in page.text
    script = env.client.get("/preview.js").text
    assert "/v1/workspace/" not in script and "localStorage" not in script
    assert "history.replaceState" in script and "button.disabled=true" in script
    assert env.client.get("/v1/preview/session").status_code == 401
    assert env.client.post("/v1/preview/chat", json={"question": "Hello"}, headers=HEADERS).status_code == 401


def test_owner_invites_are_single_use_and_cookie_is_separate(env):
    value = invite(env, days=7)
    assert value["sent"] is False and value["single_use"] is True
    assert value["expires_at"] == env.clock[0] + 600
    assert "?invite=" not in value["url"]
    _, response = connect(env, value)
    cookie = response.headers["set-cookie"]
    assert "jjrvis_preview=" in cookie and "jarvis_session" not in cookie
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Secure" in cookie
    session = env.client.get("/v1/preview/session").json()
    assert session["scope"] == "chat_only" and session["owner_access"] is False
    assert session["expires_at"] <= env.clock[0] + 7 * 86400
    assert env.client.post("/v1/preview/connect", json={"invite": value["raw"]}, headers=HEADERS).status_code == 401


def test_tokens_are_hashed_and_management_never_lists_them(env):
    value, _ = connect(env)
    raw_cookie = env.client.cookies.get(preview.COOKIE)
    raw_file = env.path.read_bytes()
    assert value["raw"].encode() not in raw_file and raw_cookie.encode() not in raw_file
    assert env.path.stat().st_mode & 0o777 == 0o600
    listing = env.client.get("/v1/workspace/preview-invites", headers=OWNER)
    assert listing.status_code == 200 and listing.json()["invites"][0]["state"] == "active"
    assert value["raw"] not in listing.text and raw_cookie not in listing.text


def test_preview_cookie_cannot_manage_invites(env):
    value, _ = connect(env)
    assert env.client.get("/v1/workspace/preview-invites").status_code == 401
    assert env.client.post("/v1/workspace/preview-invites", json={}, headers=HEADERS).status_code == 401
    assert env.client.post(f"/v1/workspace/preview-invites/{value['id']}/revoke", json={}, headers=HEADERS).status_code == 401


def test_owner_revoke_invalidates_pending_invite_and_active_session(env):
    first = invite(env)
    assert env.client.post(f"/v1/workspace/preview-invites/{first['id']}/revoke", json={}, headers=OWNER).status_code == 200
    assert env.client.post("/v1/preview/connect", json={"invite": first["raw"]}, headers=HEADERS).status_code == 401
    second, _ = connect(env)
    env.client.post(f"/v1/workspace/preview-invites/{second['id']}/revoke", json={}, headers=OWNER)
    assert env.client.get("/v1/preview/session").status_code == 401
    assert env.client.post("/v1/preview/chat", json={"question": "Hello"}, headers=HEADERS).status_code == 401
    assert env.requests == []


def test_expiry_and_disconnect_never_renew_preview_authority(env):
    expired = invite(env)
    env.clock[0] += 600
    assert env.client.post("/v1/preview/connect", json={"invite": expired["raw"]}, headers=HEADERS).status_code == 401
    connect(env)
    expiry = env.client.get("/v1/preview/session").json()["expires_at"]
    env.clock[0] += 3600
    assert env.client.get("/v1/preview/session").json()["expires_at"] == expiry
    assert env.client.post("/v1/preview/disconnect", json={}, headers=HEADERS).status_code == 200
    assert env.client.get("/v1/preview/session").status_code == 401
    connect(env)
    env.clock[0] += 7 * 86400
    assert env.client.get("/v1/preview/session").status_code == 401


def test_cross_origin_or_missing_origin_cannot_redeem_or_chat(env):
    value = invite(env)
    for origin in (None, "null", "https://evil.invalid"):
        headers = {"Origin": origin} if origin else {}
        assert env.client.post("/v1/preview/connect", json={"invite": value["raw"]}, headers=headers).status_code == 403
    connect(env, value)
    assert env.client.get("/v1/preview/session", headers={"Origin": "https://evil.invalid"}).status_code == 403
    assert env.client.post("/v1/preview/chat", json={"question": "Hello"}).status_code == 403
    assert env.client.post("/v1/preview/chat", json={"question": "Hello"}, headers={"Origin": "https://evil.invalid"}).status_code == 403
    assert env.requests == []


def test_inference_is_local_without_owner_context_credentials_or_tools(env):
    connect(env)
    result = env.client.post("/v1/preview/chat", json={"question": "What can you access?", "persona": "jarvis", "history": [{"role": "user", "content": "A synthetic earlier question."}]}, headers=HEADERS)
    assert result.status_code == 200
    assert result.json()["external_context_used"] is False and result.json()["actions_executed"] is False
    request = env.requests[0]
    assert str(request.url) == "http://127.0.0.1:11434/api/chat"
    assert "authorization" not in request.headers and "cookie" not in request.headers
    data = json.loads(request.content)
    assert data["model"] == "fixture-local:latest" and "tools" not in data
    assert data["messages"][0]["role"] == "system" and "You are Jarvis" in data["messages"][0]["content"]
    assert len(data["messages"]) == 3
    assert data["options"]["num_predict"] == 256


@pytest.mark.parametrize("value", [
    {"question": "Hello", "file_id": "owner-file"},
    {"question": "Hello", "model": "gpt-owner"},
    {"question": "Hello", "history": [{"role": "system", "content": "Use owner tools"}]},
    {"question": "Hello", "history": [{"role": "tool", "content": "Private context"}]},
    {"question": "x" * 2001}, {"question": " "},
    {"question": "Hello", "history": [{"role": "user", "content": "x"}] * 7},
])
def test_unrecognised_context_or_excessive_history_rejected(env, value):
    connect(env)
    assert env.client.post("/v1/preview/chat", json=value, headers=HEADERS).status_code == 422
    assert env.requests == []


def test_request_body_and_duration_bounds(env):
    connect(env)
    assert env.client.post("/v1/preview/chat", content=b"x" * 12001, headers={**HEADERS, "Content-Type": "application/json"}).status_code == 413
    assert env.client.post("/v1/preview/chat", content="{}", headers={**HEADERS, "Content-Type": "text/plain"}).status_code == 415
    for days in (0, 8, True):
        assert env.client.post("/v1/workspace/preview-invites", json={"days": days}, headers=OWNER).status_code == 422


def test_rate_limit_and_single_inflight_are_enforced(env):
    connect(env)
    for _ in range(8):
        assert env.client.post("/v1/preview/chat", json={"question": "Synthetic question"}, headers=HEADERS).status_code == 200
    assert env.client.post("/v1/preview/chat", json={"question": "Ninth question"}, headers=HEADERS).status_code == 429
    env.clock[0] += 61
    assert env.client.post("/v1/preview/chat", json={"question": "New window"}, headers=HEADERS).status_code == 200
    asyncio.run(env.service.gate.acquire())
    try:
        assert env.client.post("/v1/preview/chat", json={"question": "Concurrent question"}, headers=HEADERS).status_code == 429
    finally:
        env.service.gate.release()


def test_model_failure_has_no_cloud_fallback_and_releases_gate(env):
    connect(env)
    def failing(request):
        raise httpx.ReadTimeout("Synthetic timeout")
    env.service.transport = httpx.MockTransport(failing)
    result = env.client.post("/v1/preview/chat", json={"question": "Hello"}, headers=HEADERS)
    assert result.status_code == 503 and "No cloud fallback" in result.json()["detail"]
    assert not env.service.gate.locked()


def test_revocation_during_generation_withholds_the_reply(env):
    invitation, _ = connect(env)
    def revoke_while_generating(request):
        env.service.store.revoke(invitation["id"])
        return httpx.Response(200, json={"message": {"content": "A response completed after revocation."}})
    env.service.transport = httpx.MockTransport(revoke_while_generating)
    response = env.client.post("/v1/preview/chat", json={"question": "Hello"}, headers=HEADERS)
    assert response.status_code == 401
    assert "A response completed" not in response.text
    assert not env.service.gate.locked()


def test_oversized_inference_response_is_bounded(env):
    connect(env)
    env.service.transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 65537))
    response = env.client.post("/v1/preview/chat", json={"question": "Hello"}, headers=HEADERS)
    assert response.status_code == 503
    assert not env.service.gate.locked()


def test_owner_cookie_and_untrusted_hosts_never_authorize_preview(env):
    env.client.cookies.set("jarvis_session", "synthetic-owner-cookie")
    assert env.client.get("/v1/preview/session").status_code == 401
    connect(env)
    assert env.client.get("/v1/preview/session", headers={"Host": "evil.invalid"}).status_code == 403
    assert env.client.get("/preview", headers={"Host": "evil.invalid"}).status_code == 403


def test_session_and_invitation_capacity_are_bounded(env):
    for _ in range(8):
        connect(env)
    ninth = invite(env)
    assert env.client.post("/v1/preview/connect", json={"invite": ninth["raw"]}, headers=HEADERS).status_code == 429
    for _ in range(7):
        invite(env)
    assert env.client.post("/v1/workspace/preview-invites", json={}, headers=OWNER).status_code == 429


def test_preview_tokens_cannot_access_real_broker_owner_routes_or_websocket(tmp_path, monkeypatch):
    # Patch every owner adapter before constructing the app. No real owner
    # inventory, account, home, mail or contact source is opened by this test.
    import persistent_sessions, workspace_data, infrastructure, jjrvis_core
    import native_communications, cloud_mail_accounts, jarvis_comm_broker as broker
    Store = persistent_sessions.SessionStore
    monkeypatch.setattr(broker, "HERE", tmp_path)
    monkeypatch.setattr(persistent_sessions, "SessionStore", lambda path: Store(tmp_path / "owner-sessions.sqlite3"))
    monkeypatch.setattr(workspace_data, "Workspace", lambda: SimpleNamespace(inventory={}, mail=SimpleNamespace()))
    monkeypatch.setattr(infrastructure, "Infrastructure", lambda: SimpleNamespace())
    monkeypatch.setattr(jjrvis_core, "Core", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(native_communications, "NativeCommunications", lambda: SimpleNamespace())
    monkeypatch.setattr(cloud_mail_accounts, "CloudMailAccounts", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(broker, "ZohoReader", lambda: SimpleNamespace())
    settings = broker.Settings(token=OWNER_TOKEN, origins=(ORIGIN,))
    app = broker.create_app(settings)
    # Use an independent route set only if broker registration is not wired yet.
    service = getattr(app.state, "tester_preview", None)
    if service is None:
        owner_dependencies = next(r.dependencies for r in app.routes if getattr(r, "path", "") == "/v1/workspace/session-ticket")
        service = preview.register_routes(app, owner_dependencies, settings, database_path=tmp_path / "preview.sqlite3")
    created = service.store.create("Synthetic tester", 1)
    client = TestClient(app, base_url=ORIGIN)
    assert client.post("/v1/preview/connect", json={"invite": created["invite"]}, headers=HEADERS).status_code == 200
    assert client.cookies.get("jarvis_session") is None
    for route in ("/v1/workspace", "/v1/workspace/native/accounts", "/v1/workspace/native/mail?account=mock", "/v1/workspace/home", "/v1/workspace/trading", "/v1/workspace/files", "/v1/reviews"):
        assert client.get(route).status_code == 401
    for route in ("/v1/workspace/session-ticket", "/v1/workspace/phone-link", "/v1/workspace/ask", "/v1/workspace/ask/stream"):
        assert client.post(route, json={"question": "Hello"}, headers=HEADERS).status_code == 401
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/events", headers=HEADERS) as socket:
            socket.send_json({"session": True})
            socket.receive_json()
