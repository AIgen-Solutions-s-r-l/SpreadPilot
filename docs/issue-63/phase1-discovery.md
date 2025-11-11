# Phase 1: Discover & Frame - Issue #63

**Issue**: Implement WebSocket Authentication
**Priority**: MEDIUM-HIGH (Security)
**Date**: 2025-11-11
**Protocol**: LIFECYCLE-ORCHESTRATOR-ENHANCED-PROTO.yaml

---

## Problem Statement

WebSocket connections to `/dashboard` endpoint are **not authenticated**. Anyone with network access can connect and receive real-time trading data without authentication.

### Current Security Gap

**Frontend** (`frontend/src/contexts/WebSocketContext.tsx:34-36`):
```typescript
// TODO: Potentially add token to URL query params or handle auth differently if needed
const connectionUrl = url; // Using plain URL for now
ws.current = new WebSocket(connectionUrl);
```

**Backend** (`admin-api/app/api/v1/endpoints/websocket.py:47-49`):
```python
@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)  # NO AUTH CHECK!
```

---

## Investigation Results

### ✅ Infrastructure Already Exists!

**From Issue #59** (v2.0.0 - Frontend Authentication):
- ✅ JWT token generation (`create_access_token()`)
- ✅ JWT token validation (`get_current_user()`)
- ✅ Token storage in frontend (localStorage)
- ✅ Token available in `useAuth()` hook
- ✅ JWT secret configured

**Required**: Connect WebSocket to existing auth infrastructure

---

## Security Risk Assessment

### Current Vulnerabilities

**MEDIUM-HIGH** severity:

1. **Unauthorized Data Access**
   - Real-time positions visible without auth
   - P&L data exposed
   - Trade executions visible
   - Follower information accessible

2. **Data Exposure Scope**
   - Trading positions and strategies
   - Financial performance data
   - System status and health
   - User activity

3. **Compliance Risk**
   - No audit trail for WebSocket access
   - Cannot demonstrate access controls
   - Regulatory exposure

4. **Attack Surface**
   - Anyone on network can connect
   - No rate limiting per user
   - Cannot block malicious actors

### Why Not Critical?

- Dashboard requires authentication (HTTP API protected)
- WebSocket provides real-time updates but not control
- Internal admin dashboard (not public-facing)
- Still **MUST FIX** for production security

---

## Technical Feasibility

### Complexity: **LOW** ⭐⭐

**Why Relatively Easy**:
1. ✅ JWT infrastructure exists
2. ✅ Token available in frontend
3. ✅ FastAPI WebSocket supports query params
4. ✅ Clear implementation pattern

### Implementation Options

#### **Option 1: Query Parameter** (RECOMMENDED) ⭐

**Frontend**:
```typescript
const connectionUrl = token
  ? `${url}?token=${token}`
  : url;
```

**Backend**:
```python
@router.websocket("/dashboard")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None)
):
    # Validate token before accept()
    user = await validate_ws_token(token)
    await manager.connect(websocket, user)
```

**Pros**:
- ✅ Simple implementation
- ✅ Works with standard WebSocket
- ✅ Easy to test
- ✅ Clear error messages

**Cons**:
- ⚠️ Token in URL (logged in some systems)
- ⚠️ Visible in browser dev tools

**Security Note**: Acceptable for admin dashboard over HTTPS

#### **Option 2: Sec-WebSocket-Protocol** (Alternative)

**Frontend**:
```typescript
const ws = new WebSocket(url, [`Bearer.${token}`]);
```

**Backend**:
```python
# Parse from Sec-WebSocket-Protocol header
```

**Pros**:
- ✅ Token not in URL
- ✅ Standard WebSocket header

**Cons**:
- ❌ More complex parsing
- ❌ Less obvious implementation
- ❌ Header format not standardized

#### **Option 3: Initial Message** (Not Recommended)

Send token as first message after connection.

**Cons**:
- ❌ Window of unauthenticated connection
- ❌ More complex state management
- ❌ Race conditions possible

---

## Recommended Approach

### ✅ **Option 1: Query Parameter with JWT Validation**

**Rationale**:
1. Simplest to implement and test
2. Leverages existing JWT infrastructure
3. Clear error handling
4. Standard pattern for WebSocket auth
5. Acceptable security for admin dashboard

**Effort**: 4-6 hours

---

## Implementation Plan

### Frontend Changes (2 hours)

1. **Update WebSocketContext.tsx** (30 min)
   - Pass token as query parameter
   - Handle token refresh/expiration
   - Reconnect on 401

2. **Add reconnection logic** (30 min)
   - Exponential backoff
   - Token refresh before reconnect

3. **Error handling** (1 hour)
   - Display auth errors to user
   - Redirect to login on persistent failure

### Backend Changes (2 hours)

1. **Create token validator** (1 hour)
   - Reuse JWT decode logic from auth.py
   - WebSocket-specific error responses

2. **Update websocket.py** (30 min)
   - Add token parameter
   - Validate before accept()
   - Close on invalid token

3. **Add user context** (30 min)
   - Track authenticated user per connection
   - Log user activity

### Testing (2 hours)

1. **Manual testing** (1 hour)
   - Valid token connection
   - Invalid token rejection
   - Expired token handling
   - No token rejection

2. **Integration testing** (1 hour)
   - Token refresh during connection
   - Reconnection flow
   - Multiple concurrent connections

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Token expiration during connection | MEDIUM | LOW | Implement reconnection with refresh |
| Breaking existing connections | NONE | NONE | Current connections don't work anyway |
| Performance impact | LOW | LOW | Token validation is fast (<1ms) |
| Implementation complexity | LOW | LOW | Clear pattern, existing infrastructure |

**Overall Risk**: **LOW** ✅

---

## Dependencies

- ✅ **Issue #59 Complete**: Frontend authentication implemented (v2.0.0)
- ✅ JWT infrastructure available
- ✅ Token management in place

**No Blocking Dependencies**

---

## Success Metrics

- ✅ WebSocket connections require valid JWT token
- ✅ Invalid/missing tokens rejected before connection established
- ✅ Token expiration handled gracefully with reconnection
- ✅ User activity logged for audit trail
- ✅ No unauthorized access possible

---

## Quality Gates Status

- ✅ **Problem validated**: Security gap confirmed
- ✅ **Technical feasibility confirmed**: Straightforward implementation
- ✅ **Risk assessment complete**: Low risk, clear approach
- ✅ **Dependencies resolved**: Auth infrastructure exists

---

## Tech Lead Sign-off

**Decision**: ✅ **APPROVED - PROCEED TO IMPLEMENTATION**

**Comments**:
> Clear security gap that must be addressed. Fortunately, JWT infrastructure from Issue #59 makes this straightforward. Query parameter approach is appropriate for admin dashboard. Recommend prioritizing this as it's both a security issue and a quick win (4-6 hours).

---

**Phase 1 Deliverables**:
- ✅ Security vulnerability documented
- ✅ Infrastructure assessed (exists!)
- ✅ Implementation approach selected (Query Parameter)
- ✅ Effort estimated (4-6 hours)
- ✅ Risk assessed (LOW)

**Phase Completion**: 2025-11-11

**Next Phase**: Phase 2 - Design the Solution
