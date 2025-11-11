# Phase 2: HLD - Issue #63

**WebSocket Authentication Design**
**Approach**: Query Parameter with JWT Validation

## Backend Changes

```python
# websocket.py
from fastapi import Query, HTTPException
from jose import JWTError, jwt

async def validate_ws_token(token: str | None) -> str:
    """Validate JWT token for WebSocket connection."""
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    try:
        username = await validate_ws_token(token)
        await manager.connect(websocket, username)
        # ... rest of logic
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
```

## Frontend Changes

```typescript
// WebSocketContext.tsx
const { token } = useAuth();
const connectionUrl = token ? `${url}?token=${token}` : url;
```

**Effort**: 4-6 hours
