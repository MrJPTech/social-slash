"""Bearer token authentication middleware for the /mcp endpoint."""

from __future__ import annotations

from starlette.responses import JSONResponse


class BearerAuthMiddleware:
    """ASGI middleware that requires a Bearer token on the /mcp endpoint.

    Public endpoints (/, /health) are not protected.
    If MCP_AUTH_TOKEN is not set, all requests are allowed.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/mcp":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            expected = f"Bearer {self.token}"
            if auth_header != expected:
                # Derive base URL for resource_metadata link
                host = ""
                for k, v in scope.get("headers", []):
                    if k == b"x-forwarded-host":
                        host = v.decode()
                        break
                    elif k == b"host":
                        host = v.decode()
                scheme = (
                    "https"
                    if any(
                        k == b"x-forwarded-proto" and v == b"https"
                        for k, v in scope.get("headers", [])
                    )
                    else "https"
                )
                base = f"{scheme}://{host}" if host else ""
                res_uri = f"{base}/.well-known/oauth-protected-resource" if base else ""
                www_auth = f'Bearer resource_metadata="{res_uri}"' if res_uri else "Bearer"
                response = JSONResponse(
                    {"error": "Unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": www_auth},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
