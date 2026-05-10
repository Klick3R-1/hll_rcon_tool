# Internal User API

Optional internal-only API for managing Django/CRCON users from trusted private-network tooling.

## Configuration

The API is disabled unless explicitly enabled:

```env
ENABLE_INTERNAL_USER_API=true
INTERNAL_USER_API_TOKEN=replace-with-a-long-random-token
INTERNAL_USER_API_ALLOWED_IPS=192.168.1.10,192.168.1.20
```

`INTERNAL_USER_API_ALLOWED_IPS` is optional. When set, requests are matched against Django's `REMOTE_ADDR`. If CRCON is behind a reverse proxy, allowlist the proxy address or ensure the proxy/network path preserves the expected source address.

## Safety Model

- Disabled by default.
- Requires `X-Internal-Token` on every request.
- Optionally restricts requests by source IP.
- Uses Django's built-in user and group models.
- Does not create, promote, or modify superusers.
- Does not return password hashes, sessions, API keys, or other auth secrets.
- Disables users instead of deleting them.
- Logs every action with the target username and source IP.

## Endpoints

All requests and responses are JSON.

```text
GET    /api/internal/users/
POST   /api/internal/users/
PATCH  /api/internal/users/<id>/
POST   /api/internal/users/<id>/disable/
POST   /api/internal/users/<id>/set-password/
POST   /api/internal/users/<id>/groups/
```

## Examples

```bash
curl -sS http://crcon.local/api/internal/users/ \
  -H "X-Internal-Token: $INTERNAL_USER_API_TOKEN"

curl -sS -X POST http://crcon.local/api/internal/users/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_USER_API_TOKEN" \
  -d '{
    "username": "newmod",
    "email": "mod@example.com",
    "password": "temporary-password",
    "groups": ["Moderator"],
    "is_staff": true
  }'

curl -sS -X PATCH http://crcon.local/api/internal/users/12/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_USER_API_TOKEN" \
  -d '{"email": "newmod@example.com", "is_staff": true}'

curl -sS -X POST http://crcon.local/api/internal/users/12/groups/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_USER_API_TOKEN" \
  -d '{"add": ["Moderator"], "remove": ["Seed VIP"]}'

curl -sS -X POST http://crcon.local/api/internal/users/12/set-password/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_USER_API_TOKEN" \
  -d '{"password": "new-temporary-password"}'

curl -sS -X POST http://crcon.local/api/internal/users/12/disable/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_USER_API_TOKEN" \
  -d '{"disabled": true}'
```

## Upgrade Notes

The implementation is isolated in `rconweb/internal_user_api/`. Existing CRCON APIs, auth flows, frontend code, and API documentation generation are not modified. Upstream merges should usually only need conflict checks in `rconweb/rconweb/settings.py` and `rconweb/rconweb/urls.py`.
