# Phase 2: HLD - Issue #65

**Enhanced WebSocket Message Handling Design**
**Approach**: Non-Breaking Subscription Pattern (Additive Enhancement)

## Design Decision

After analyzing the current implementation and backend message format, **I recommend a simpler, non-breaking approach**:

### Why Simpler Approach?

1. **Backend sends structured messages** (`follower_update` confirmed)
2. **Current pattern works** but has duplication
3. **Breaking changes are costly** (need to update all consumers)
4. **3-4 day estimate is too long** for MEDIUM priority
5. **Quick win possible**: Add subscription API alongside existing `lastMessage`

---

## Recommended: Additive Subscription Pattern

### Keep `lastMessage` + Add `subscribe()` Method

**Non-Breaking Design**:
```typescript
interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null; // KEEP existing API
  sendMessage: (message: WebSocketMessage | string) => void;
  subscribe: (type: string, handler: MessageHandler) => () => void; // NEW
}
```

**Benefits**:
- ✅ No breaking changes
- ✅ Existing components continue working
- ✅ New components can use `subscribe()`
- ✅ Gradual migration possible
- ✅ 4-6 hours implementation (vs 3-4 days)

---

## Implementation Design

### 1. Core Message Routing

```typescript
// Type definitions
export type MessageHandler = (data: any) => void;

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp?: string;
}

// Inside WebSocketProvider
const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());

// Update onmessage handler
ws.current.onmessage = (event) => {
  try {
    const messageData = JSON.parse(event.data);

    if (import.meta.env.DEV) {
      console.log('WebSocket Message Received:', { type: messageData.type });
    }

    // Keep existing behavior
    setLastMessage(messageData);

    // NEW: Dispatch to subscribers
    const handlers = handlersRef.current.get(messageData.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(messageData.data);
        } catch (error) {
          console.error(`Error in WebSocket handler for ${messageData.type}:`, error);
        }
      });
    }
  } catch (error) {
    console.error('Failed to parse WebSocket message:', event.data, error);
  }
};
```

### 2. Subscribe Method

```typescript
const subscribe = useCallback((type: string, handler: MessageHandler) => {
  if (import.meta.env.DEV) {
    console.log(`WebSocket: Subscribing to ${type}`);
  }

  // Get or create handler set for this type
  if (!handlersRef.current.has(type)) {
    handlersRef.current.set(type, new Set());
  }

  handlersRef.current.get(type)!.add(handler);

  // Return unsubscribe function
  return () => {
    if (import.meta.env.DEV) {
      console.log(`WebSocket: Unsubscribing from ${type}`);
    }
    handlersRef.current.get(type)?.delete(handler);

    // Cleanup empty sets
    if (handlersRef.current.get(type)?.size === 0) {
      handlersRef.current.delete(type);
    }
  };
}, []);
```

### 3. Message Type Constants

```typescript
// New file: frontend/src/types/websocket.ts
export const WebSocketMessageType = {
  FOLLOWER_UPDATE: 'follower_update',
  LOG_ENTRY: 'log_entry',
  POSITION_UPDATE: 'position_update',
  TRADE_EXECUTION: 'trade_execution',
  PNL_UPDATE: 'pnl_update',
  ALERT: 'alert',
  HEALTH_UPDATE: 'health_update',
} as const;

export type WebSocketMessageType = typeof WebSocketMessageType[keyof typeof WebSocketMessageType];

// Payload type definitions
export interface FollowerUpdateData {
  total: number;
  active: number;
}

export interface LogEntryData {
  level: string;
  message: string;
  timestamp: string;
  service?: string;
}

// Add more as needed...
```

---

## Usage Examples

### New Components (Recommended Pattern)

```typescript
import { useWebSocket } from '@/contexts/WebSocketContext';
import { WebSocketMessageType } from '@/types/websocket';

function MyComponent() {
  const { subscribe } = useWebSocket();
  const [data, setData] = useState(null);

  useEffect(() => {
    // Subscribe to specific message type
    const unsubscribe = subscribe(
      WebSocketMessageType.FOLLOWER_UPDATE,
      (data) => {
        setData(data);
      }
    );

    // Cleanup on unmount
    return unsubscribe;
  }, [subscribe]);

  return <div>{/* render data */}</div>;
}
```

### Existing Components (No Changes Required)

```typescript
// Continues to work as before
const { lastMessage } = useWebSocket();
useEffect(() => {
  if (lastMessage?.type === 'follower_update') {
    // handle
  }
}, [lastMessage]);
```

---

## Migration Strategy

### Phase 1: Add Subscription API (This PR)
- Implement `subscribe()` method
- Keep `lastMessage` unchanged
- Add type constants
- No breaking changes

### Phase 2: Gradual Migration (Future)
- Update components one-by-one to use `subscribe()`
- Remove `lastMessage` usage
- Eventually deprecate (but keep for backwards compat)

### Phase 3: Cleanup (Later, Optional)
- If all components migrated, remove `lastMessage`
- Breaking change in major version

---

## Error Handling

```typescript
// Wrap handler execution in try/catch
handlers.forEach(handler => {
  try {
    handler(messageData.data);
  } catch (error) {
    console.error(`Error in WebSocket handler for ${messageData.type}:`, error);
    // Handler error doesn't affect other handlers
  }
});
```

---

## Memory Management

**Subscription Lifecycle**:
1. Component mounts → `subscribe()` called
2. Handler added to Map
3. Component unmounts → unsubscribe function called
4. Handler removed from Map
5. Empty sets removed automatically

**No Memory Leaks**:
- Unsubscribe function must be called in cleanup
- useEffect cleanup ensures this
- DEV logging helps debug forgotten unsubscribes

---

## Testing Strategy

### Manual Testing
1. Subscribe to message type
2. Backend sends message
3. Handler called with data
4. Unsubscribe
5. Handler not called after unsubscribe
6. Multiple subscribers work
7. Existing `lastMessage` still works

### Integration Testing
- Test component mount/unmount (no leaks)
- Test multiple simultaneous subscriptions
- Test error in one handler doesn't affect others

---

## File Changes

### Modified Files
1. `frontend/src/contexts/WebSocketContext.tsx`
   - Add `handlersRef`
   - Add `subscribe()` method
   - Update `onmessage` to dispatch to handlers
   - Update context type

2. `frontend/src/types/websocket.ts` (NEW)
   - Message type constants
   - Payload type definitions

### Documentation
3. `frontend/README.md`
   - Add WebSocket usage examples
   - Document subscription pattern

---

## Effort Estimate

- **Implementation**: 3 hours
- **Testing**: 1 hour
- **Documentation**: 1 hour
- **Total**: 5 hours

**vs Original Estimate**: 3-4 days (24-32 hours)
**Time Saved**: 19-27 hours (by avoiding breaking changes)

---

## Future Enhancements (Not in Scope)

These can be added later if needed:
- ❌ Offline message queue
- ❌ Message deduplication
- ❌ Retry logic
- ❌ Message persistence
- ❌ Wildcard subscriptions (`*`)

**Keep it simple for now!**

---

**Phase 2 Deliverables**:
- ✅ Non-breaking design
- ✅ Subscription pattern defined
- ✅ Message type constants
- ✅ Error handling strategy
- ✅ Migration path defined
- ✅ Reduced effort (5 hours vs 24-32 hours)

**Phase Completion**: 2025-11-11

**Next Phase**: Phase 3 - Build & Validate
