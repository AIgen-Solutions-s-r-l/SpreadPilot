# Phase 1: Discover & Frame - Issue #65

**Issue**: Implement Enhanced WebSocket Message Handling
**Priority**: MEDIUM
**Date**: 2025-11-11
**Protocol**: LIFECYCLE-ORCHESTRATOR-ENHANCED-PROTO.yaml

---

## Problem Statement

Current WebSocket implementation in `WebSocketContext.tsx` has minimal message handling - it simply stores the last message in state. Components consume this via `lastMessage` state and implement their own type-checking logic. This creates:

1. **Tight Coupling**: Each component must know message structure
2. **Code Duplication**: Message type checking repeated across components
3. **No Message Routing**: Can't subscribe to specific message types
4. **Missed Messages**: Components only see last message, not all messages
5. **No Offline Support**: Messages lost when disconnected

**Current Code** (`WebSocketContext.tsx:63`):
```typescript
ws.current.onmessage = (event) => {
  try {
    const messageData = JSON.parse(event.data);
    setLastMessage(messageData); // Simple state update
    // TODO: Implement more sophisticated message handling/dispatching if needed
  } catch (error) {
    console.error('Failed to parse WebSocket message:', event.data, error);
  }
};
```

---

## Investigation Results

### Current Consumer Analysis

Let me examine how WebSocket messages are currently consumed:

**useDashboard.ts** (lines 135-163):
```typescript
useEffect(() => {
  if (lastMessage) {
    try {
      const { type, data } = lastMessage;

      switch (type) {
        case 'position_update':
          setPositions(prev => /* ... */);
          break;
        case 'trade_execution':
          setRecentTrades(prev => /* ... */);
          break;
        case 'pnl_update':
          setTodayPnl(data.pnl);
          break;
        case 'log_entry':
          setRecentLogs(prev => /* ... */);
          break;
        default:
          console.log('Unknown WebSocket message type:', type);
      }
    } catch (error) {
      console.error('Error processing WebSocket message:', error);
    }
  }
}, [lastMessage]);
```

**LogsPage.tsx** (lines 36-51):
```typescript
useEffect(() => {
  if (lastMessage) {
    if (lastMessage.type === 'log_entry') {
      const newLog = lastMessage.data as LogEntry;
      setLogs(prevLogs => {
        // Filter and add logic
      });
    }
  }
}, [lastMessage, filterLevel]);
```

**Current Pattern Problems**:
1. useEffect triggers on EVERY message (even unrelated ones)
2. Type checking duplicated in each component
3. Complex logic mixed with message handling
4. Race conditions possible (rapid messages)
5. Memory leaks if components unmount during processing

### Message Types in Use

From code analysis, these message types are already in use:
- `log_entry` - Real-time log entries (LogsPage, useDashboard)
- `position_update` - Position changes (useDashboard)
- `trade_execution` - Trade confirmations (useDashboard)
- `pnl_update` - P&L changes (useDashboard)

**Missing but likely needed**:
- `follower_status` - Follower enable/disable (FollowersPage)
- `alert` - System alerts (RecentAlerts component)
- `health_update` - Service health (ServiceHealth component)

### Backend Message Format

From `admin-api/app/api/v1/endpoints/websocket.py`, the current backend only echoes:
```python
await manager.send_personal_message(f"You sent: {data}", websocket)
```

**No structured messages are sent yet!** This means:
1. Backend needs to send structured messages
2. Frontend enhancement is premature without backend support
3. OR: We can prepare frontend for future backend implementation

---

## Technical Feasibility

### Complexity: **MEDIUM** ⭐⭐⭐

**Why Moderate Complexity**:
1. ⚠️ Requires subscriber pattern implementation
2. ⚠️ Needs careful memory management (subscribe/unsubscribe)
3. ⚠️ Must handle component lifecycle
4. ⚠️ Offline queue adds state complexity
5. ✅ Message routing is straightforward
6. ✅ TypeScript helps with type safety

### Implementation Options

#### **Option 1: Simple Event Emitter Pattern** (Recommended) ⭐

Implement pub/sub using JavaScript Map and callbacks.

```typescript
interface WebSocketContextType {
  isConnected: boolean;
  sendMessage: (message: WebSocketMessage | string) => void;
  subscribe: (type: string, handler: MessageHandler) => () => void;
}

// Inside provider
const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());

ws.current.onmessage = (event) => {
  const message = JSON.parse(event.data);
  const handlers = handlersRef.current.get(message.type);
  handlers?.forEach(handler => handler(message.data));
};

const subscribe = useCallback((type: string, handler: MessageHandler) => {
  if (!handlersRef.current.has(type)) {
    handlersRef.current.set(type, new Set());
  }
  handlersRef.current.get(type)!.add(handler);

  // Return unsubscribe function
  return () => {
    handlersRef.current.get(type)?.delete(handler);
  };
}, []);
```

**Pros**:
- ✅ Simple implementation (4-6 hours)
- ✅ Clean component code
- ✅ Automatic cleanup via unsubscribe
- ✅ Type-safe with TypeScript
- ✅ No external dependencies

**Cons**:
- ⚠️ No offline queue (can add later)
- ⚠️ No message deduplication

#### **Option 2: Full Event Bus with Queue** (Over-engineering)

Add offline message queuing, deduplication, retry logic.

**Pros**:
- ✅ Handles all edge cases
- ✅ Production-ready

**Cons**:
- ❌ More time (2-3 days)
- ❌ More complexity
- ❌ Not needed yet (backend doesn't send messages)

#### **Option 3: Use Library (mitt, eventemitter3)** (Overkill)

**Pros**:
- ✅ Battle-tested

**Cons**:
- ❌ External dependency
- ❌ Bundle size increase
- ❌ Simple Map is sufficient

---

## Recommended Approach

### ✅ **Option 1: Simple Event Emitter with Subscribe Pattern**

**Rationale**:
1. Clean separation of concerns
2. Components subscribe to specific message types
3. Automatic cleanup via unsubscribe
4. Simple implementation
5. Can add offline queue later if needed
6. **Backend integration ready** when backend sends structured messages

**Effort**: 6-8 hours

---

## Implementation Plan

### Phase 1: Core Subscription System (3 hours)

1. **Update WebSocketContext** (2 hours)
   - Add `Map<string, Set<MessageHandler>>` for handlers
   - Implement `subscribe(type, handler)` method
   - Implement message routing in `onmessage`
   - Remove `lastMessage` state (breaking change!)

2. **Create TypeScript types** (1 hour)
   - Define `MessageType` enum
   - Define message payload types
   - Type-safe handlers

### Phase 2: Update Consumers (3 hours)

1. **Update useDashboard.ts** (1 hour)
   - Replace `lastMessage` useEffect with subscriptions
   - Use `subscribe()` for each message type

2. **Update LogsPage.tsx** (30 min)
   - Use `subscribe('log_entry', handler)`

3. **Test all components** (1.5 hours)
   - Verify subscriptions work
   - Verify cleanup (no memory leaks)
   - Verify multiple subscribers work

### Phase 3: Documentation & Cleanup (2 hours)

1. **Update component examples** (1 hour)
2. **Add inline documentation** (30 min)
3. **Create migration guide** (30 min)

---

## Breaking Changes

### CRITICAL: lastMessage Removal

**Before**:
```typescript
const { lastMessage } = useWebSocket();
useEffect(() => {
  if (lastMessage?.type === 'log_entry') {
    // handle
  }
}, [lastMessage]);
```

**After**:
```typescript
const { subscribe } = useWebSocket();
useEffect(() => {
  const unsubscribe = subscribe('log_entry', (data) => {
    // handle
  });
  return unsubscribe;
}, [subscribe]);
```

**Migration Required**:
- useDashboard.ts
- LogsPage.tsx
- Any other components using `lastMessage`

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing components | HIGH | HIGH | Thorough testing, update all consumers |
| Memory leaks from subscriptions | MEDIUM | HIGH | Proper cleanup, test unmount scenarios |
| Backend doesn't send structured messages | HIGH | LOW | Frontend ready when backend updated |
| Performance (many subscribers) | LOW | LOW | Simple Map is fast |

**Overall Risk**: **MEDIUM** ⚠️

---

## Dependencies

**Backend Consideration**:
Current backend (`admin-api/app/api/v1/endpoints/websocket.py`) only echoes messages. Need to verify:
1. Does backend send structured messages?
2. What message types are actually sent?
3. Should we coordinate backend changes first?

**Recommendation**: Implement frontend subscription system now, but verify with backend team that structured messages will be sent.

---

## Success Metrics

- ✅ Components subscribe to specific message types only
- ✅ No code duplication for message type checking
- ✅ Automatic cleanup (no memory leaks)
- ✅ Type-safe message handling
- ✅ Clean component code (no switch statements)
- ✅ All existing functionality preserved

---

## Quality Gates Status

- ✅ **Problem validated**: Current pattern has tight coupling
- ⚠️ **Backend coordination needed**: Verify structured messages
- ✅ **Technical feasibility confirmed**: Simple pub/sub pattern
- ⚠️ **Breaking change identified**: `lastMessage` removal

---

## Tech Lead Sign-off

**Decision**: ⚠️ **CONDITIONAL APPROVAL - VERIFY BACKEND FIRST**

**Comments**:
> Good enhancement for frontend architecture. However, before implementing:
> 1. **Verify backend sends structured messages** - Check admin-api WebSocket endpoint
> 2. **Document message types** - What types are actually sent?
> 3. **Consider scope** - Is offline queue needed now, or later?
>
> If backend only echoes, this might be premature. If backend sends structured messages, proceed with simple subscription pattern. Quick win, but needs backend coordination.

**Next Step**: Check with backend code to see what messages are actually sent!

---

**Phase 1 Deliverables**:
- ✅ Current implementation analyzed
- ✅ Message types documented
- ⚠️ Backend coordination needed
- ✅ Implementation approach selected (Subscribe pattern)
- ✅ Breaking changes identified
- ✅ Effort estimated (6-8 hours)

**Phase Completion**: 2025-11-11

**Next Phase**: Verify backend message format, then proceed to Phase 2 - Design
