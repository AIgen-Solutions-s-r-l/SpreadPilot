# Phase 2: HLD - Issue #64

**Frontend Console Logging Cleanup Design**
**Approach**: Development-Only Gating with Sanitization

## Design Principles

1. **Security First**: Remove all sensitive data from logs
2. **Development-Friendly**: Preserve debugging in development mode
3. **Zero Production Footprint**: Vite tree-shaking removes DEV-gated code
4. **Minimal Changes**: Simple pattern replacement

---

## Implementation Patterns

### Pattern 1: Remove Debug Logs

**Before**:
```typescript
console.log('Component rendered');
console.log('State updated:', state);
```

**After**:
```typescript
// REMOVED - no value in production or development
```

### Pattern 2: Gate Development Logs

**Before**:
```typescript
console.log('API Request:', endpoint, data);
console.log('API Response:', response);
```

**After**:
```typescript
if (import.meta.env.DEV) {
  console.log('API Request:', endpoint, data);
  console.log('API Response:', response);
}
```

### Pattern 3: Sanitize Sensitive Data

**Before**:
```typescript
console.log('Auth response:', response); // Contains token!
console.log('WebSocket message:', message); // May contain sensitive data
```

**After**:
```typescript
if (import.meta.env.DEV) {
  console.log('Auth successful for user:', response.user?.username);
  // DO NOT log token
}

if (import.meta.env.DEV) {
  console.log('WebSocket message type:', message.type);
  // Log structure, not sensitive content
}
```

### Pattern 4: Keep Error Logging

**Before**:
```typescript
console.error('API Error:', error);
```

**After**:
```typescript
// KEEP - legitimate error logging
console.error('API Error:', error);
```

---

## File-by-File Implementation Plan

### Services Layer (5 files)

#### **api.ts**
- Remove: Request/response debug logs
- Gate: Useful connection/retry logs behind DEV
- Keep: Error logging

#### **followerService.ts, pnlService.ts, logService.ts, tradingActivityService.ts**
- Remove: Debug logs
- Gate: API interaction logs behind DEV
- Keep: Error handling

### Pages (5 files)

#### **All Page Components**
- Remove: Render logs, lifecycle logs
- Gate: Useful state debugging behind DEV
- Keep: Error boundaries

### Hooks (5 files)

#### **useAuth hooks**
- Remove: All auth logs (security critical)
- Keep: Error logging with sanitized messages

#### **Other hooks**
- Remove: Debug logs
- Gate: State update logs behind DEV
- Keep: Error logging

### Contexts (2 files)

#### **WebSocketContext.tsx** (CRITICAL)
```typescript
// Current
console.log('WebSocket Message Received:', messageData);

// After
if (import.meta.env.DEV) {
  console.log('WebSocket Message:', {
    type: messageData.type,
    timestamp: messageData.timestamp,
    // DO NOT log sensitive payload
  });
}
```

#### **AuthContext.tsx** (CRITICAL)
```typescript
// Remove ALL token logging
// Keep only sanitized error messages
```

### Components (3 files)

#### **Dashboard components**
- Remove: Render logs
- Gate: Data update logs behind DEV
- Keep: Error states

---

## ESLint Configuration

**Update**: `frontend/.eslintrc.cjs`

```javascript
module.exports = {
  rules: {
    'no-console': ['error', {
      allow: ['warn', 'error']
    }]
  }
};
```

**Note**: Will require adding `// eslint-disable-next-line no-console` for DEV-gated logs.

**Alternative**: More permissive for now, enforce via pre-commit hook later:

```javascript
module.exports = {
  rules: {
    'no-console': 'warn' // Warn but don't block
  }
};
```

---

## Security Checklist

### Critical: Never Log These

- ✅ JWT tokens
- ✅ Passwords
- ✅ API keys
- ✅ Session IDs
- ✅ Full user objects (may contain email/phone)
- ✅ Trading positions (business sensitive)
- ✅ P&L data (financial sensitive)

### Safe to Log in DEV

- ✅ Usernames (non-sensitive)
- ✅ Request/response types
- ✅ Timestamps
- ✅ Status codes
- ✅ Message types (without payload)

---

## Implementation Order

1. **WebSocketContext.tsx** (30 min)
   - Most critical: handles auth tokens
   - Sanitize message logging

2. **AuthContext.tsx** (30 min)
   - Second most critical: auth flow
   - Remove token logging

3. **Services Layer** (1 hour)
   - api.ts first (base layer)
   - Then domain services

4. **Hooks** (1 hour)
   - Start with useAuth
   - Then data hooks

5. **Pages & Components** (1.5 hours)
   - Less critical
   - Mostly cleanup

6. **ESLint Configuration** (15 min)
   - Add rule
   - Test enforcement

---

## Testing Strategy

### Manual Testing (30 min)

1. **Development Mode**:
   - Run `npm run dev`
   - Verify debug logs appear
   - Verify sensitive data NOT logged

2. **Production Build**:
   - Run `npm run build`
   - Verify bundle size reduction
   - Verify zero console.log in bundle

### Bundle Analysis

```bash
npm run build
grep -r "console.log" dist/
# Should return nothing (tree-shaken)
```

---

## Rollback Plan

If issues arise:
1. Git revert commit
2. Logs are non-functional code, no business logic impact

**Risk**: ZERO

---

## Effort Estimate

- **Implementation**: 4 hours
- **Testing**: 30 minutes
- **Documentation**: 30 minutes
- **Total**: 5 hours

---

**Phase 2 Deliverables**:
- ✅ Detailed implementation patterns
- ✅ File-by-file plan
- ✅ Security checklist
- ✅ ESLint configuration design
- ✅ Testing strategy

**Phase Completion**: 2025-11-11

**Next Phase**: Phase 3 - Build & Validate
