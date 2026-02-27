"""OAuth 2.0 endpoints for Claude.ai custom connector authentication."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from ._shared import mcp

# In-memory stores (single Railway instance, acceptable for personal server)
_auth_codes: dict[str, dict] = {}  # code -> {client_id, code_challenge, expires}

# Pre-shared OAuth credentials — only clients with matching values can authenticate.
# Set these in Railway env vars; leave empty for local dev (auth bypassed).
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")


def _get_server_url(request: Request) -> str:
    """Derive the public server URL from the request."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}"


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_metadata(request: Request) -> JSONResponse:
    """RFC 8414 - OAuth 2.0 Authorization Server Metadata."""
    base = _get_server_url(request)
    return JSONResponse({
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": ["S256"],
    })


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def resource_metadata(request: Request) -> JSONResponse:
    """RFC 9728 - OAuth 2.0 Protected Resource Metadata."""
    base = _get_server_url(request)
    return JSONResponse({
        "resource": f"{base}/mcp",
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
    })


@mcp.custom_route("/register", methods=["POST"])
async def register_client(request: Request) -> JSONResponse:
    """Dynamic client registration is disabled — use pre-shared credentials."""
    return JSONResponse({"error": "registration_not_supported"}, status_code=403)


@mcp.custom_route("/authorize", methods=["GET"])
async def authorize(request: Request) -> RedirectResponse:
    """Authorization endpoint - auto-approves (single-user personal server)."""
    params = request.query_params
    redirect_uri = params.get("redirect_uri", "")
    state = params.get("state", "")
    code_challenge = params.get("code_challenge", "")
    client_id = params.get("client_id", "")
    response_type = params.get("response_type", "")

    if response_type != "code":
        return RedirectResponse(
            f"{redirect_uri}?error=unsupported_response_type&state={state}",
            status_code=302,
        )

    # Validate client_id against pre-shared credential
    if OAUTH_CLIENT_ID and client_id != OAUTH_CLIENT_ID:
        return RedirectResponse(
            f"{redirect_uri}?error=unauthorized_client&state={state}",
            status_code=302,
        )

    # Generate authorization code
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "code_challenge": code_challenge,
        "redirect_uri": redirect_uri,
        "expires": time.time() + 300,  # 5 minute expiry
    }

    return RedirectResponse(
        f"{redirect_uri}?code={code}&state={state}",
        status_code=302,
    )


@mcp.custom_route("/token", methods=["POST"])
async def token_exchange(request: Request) -> JSONResponse:
    """Token endpoint - exchanges authorization code for access token (with PKCE)."""
    try:
        body = await request.body()
        # Support both form-encoded and JSON
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            params = json.loads(body)
        else:
            from urllib.parse import parse_qs
            raw = parse_qs(body.decode())
            params = {k: v[0] for k, v in raw.items()}
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    grant_type = params.get("grant_type", "")
    code = params.get("code", "")
    code_verifier = params.get("code_verifier", "")
    client_id = params.get("client_id", "")
    client_secret = params.get("client_secret", "")

    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    # Validate client credentials against pre-shared values
    if OAUTH_CLIENT_ID and client_id != OAUTH_CLIENT_ID:
        return JSONResponse({"error": "invalid_client", "error_description": "Unknown client_id"}, status_code=401)
    if OAUTH_CLIENT_SECRET and client_secret != OAUTH_CLIENT_SECRET:
        return JSONResponse({"error": "invalid_client", "error_description": "Bad client_secret"}, status_code=401)

    # Look up and consume the auth code
    code_data = _auth_codes.pop(code, None)
    if not code_data:
        return JSONResponse({"error": "invalid_grant", "error_description": "Code not found or already used"}, status_code=400)

    if code_data["expires"] < time.time():
        return JSONResponse({"error": "invalid_grant", "error_description": "Code expired"}, status_code=400)

    # Verify client_id matches the one that requested the auth code
    if client_id and code_data.get("client_id") and client_id != code_data["client_id"]:
        return JSONResponse({"error": "invalid_grant", "error_description": "client_id mismatch"}, status_code=400)

    # PKCE verification (S256)
    if code_data["code_challenge"] and code_verifier:
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if computed != code_data["code_challenge"]:
            return JSONResponse({"error": "invalid_grant", "error_description": "PKCE verification failed"}, status_code=400)

    # Return the MCP_AUTH_TOKEN as the access token
    auth_token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not auth_token:
        return JSONResponse({"error": "server_error", "error_description": "MCP_AUTH_TOKEN not configured"}, status_code=500)

    return JSONResponse({
        "access_token": auth_token,
        "token_type": "Bearer",
    })
