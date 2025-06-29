# Frontend API Integration Guide

This document details the frontend's integration with the SpreadPilot backend APIs.

## Overview

The frontend has been enhanced to use live API data instead of mock data. All API calls are now made through a centralized Axios instance with JWT authentication and Zod validation.

## API Client Configuration

### Base Configuration (`src/services/api.ts`)

```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8083/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### JWT Interceptor

The API client automatically attaches JWT tokens to all requests:

```typescript
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  }
);
```

### Error Handling

401 errors automatically redirect to login:

```typescript
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## Service Layer

### Follower Service (`followerService.ts`)

```typescript
// Get all followers with P&L data
export const getFollowers = async (): Promise<Follower[]>

// Enable/disable follower
export const enableFollower = async (followerId: string): Promise<void>
export const disableFollower = async (followerId: string): Promise<void>

// Create new follower
export const createFollower = async (data: CreateFollowerRequest): Promise<Follower>

// Close positions (requires PIN)
export const closeFollowerPosition = async (followerId: string, pin: string): Promise<void>
```

### P&L Service (`pnlService.ts`)

```typescript
// Get today's P&L
export const getTodayPnl = async (): Promise<DailyPnl>

// Get monthly P&L with daily breakdown
export const getMonthlyPnl = async (year?: number, month?: number): Promise<MonthlyPnl>

// Calculate period P&L
export const calculatePeriodPnl = async (days: number): Promise<PeriodPnl>
```

### Log Service (`logService.ts`)

```typescript
// Get logs with filtering
export const getLogs = async (
  limit?: number,
  level?: LogLevel,
  service?: string,
  search?: string
): Promise<LogsResponse>

// Stream logs via WebSocket
export const streamLogs = (onLog: (log: LogEntry) => void): (() => void)
```

## Zod Schema Validation

All API responses are validated using Zod schemas for runtime type safety:

### Follower Schema

```typescript
export const FollowerSchema = z.object({
  id: z.string(),
  enabled: z.boolean(),
  botStatus: z.enum(['RUNNING', 'STOPPED', 'ERROR', 'STARTING']),
  ibGwStatus: z.enum(['CONNECTED', 'DISCONNECTED', 'CONNECTING', 'ERROR']),
  pnlToday: z.number(),
  pnlMonth: z.number(),
  pnlTotal: z.number(),
  timeValue: z.number().optional(),
  positions: z.object({
    count: z.number(),
    value: z.number(),
  }).optional(),
});
```

### P&L Schemas

```typescript
export const DailyPnlSchema = z.object({
  date: z.string(),
  total_pnl: z.number(),
  realized_pnl: z.number(),
  unrealized_pnl: z.number(),
  follower_pnl: z.array(FollowerPnlSchema),
});

export const MonthlyPnlSchema = z.object({
  year: z.number(),
  month: z.number(),
  total_pnl: z.number(),
  daily_breakdown: z.array(DailyBreakdownSchema),
});
```

## Custom Hooks

### useFollowers Hook

Manages follower data with auto-refresh and P&L integration:

```typescript
const { 
  followers,      // Follower array with P&L data
  loading,        // Loading state
  error,          // Error message
  todayPnl,       // Today's aggregated P&L
  monthlyPnl,     // Monthly aggregated P&L
  refresh         // Manual refresh function
} = useFollowers({ autoRefresh: true });
```

### useLogs Hook

Handles log fetching and real-time streaming:

```typescript
const {
  logs,           // Log entries array
  totalCount,     // Total log count
  loading,        // Loading state
  error,          // Error message
  filters,        // Current filters
  refresh,        // Manual refresh
  setFilters      // Update filters
} = useLogs({
  limit: 200,
  streaming: true,
  autoRefresh: false
});
```

### useDashboard Hook

Aggregates dashboard metrics from multiple sources:

```typescript
const {
  metrics,        // Dashboard metrics object
  activeFollowers,// Active follower list
  recentLogs,     // Recent error logs
  pnlHistory,     // P&L trend data
  loading,        // Loading state
  error,          // Error message
  refresh         // Manual refresh
} = useDashboard();
```

## Enhanced Components

### TimeValueBadge

Visual indicator for time value (TV) status:

```typescript
<TimeValueBadge 
  timeValue={1.50}  // Displays as safe (green)
  size="small"      // Badge size
/>
```

Status levels:
- **Safe** (green): TV > $1.00
- **Risk** (yellow): TV $0.10 - $1.00
- **Critical** (red): TV ≤ $0.10

### Enhanced Pages

All pages now use the V2 versions with live data:

- `DashboardPageV2`: Real-time metrics and overview
- `FollowersPageV2`: Complete follower management
- `LogsPageV2`: Live log streaming with filters

## WebSocket Integration

Real-time updates via WebSocket connection:

```typescript
const { isConnected, lastMessage, sendMessage } = useWebSocket();
```

Supported real-time events:
- Log entries
- Follower status updates
- P&L changes
- System alerts

## Error Handling

All API calls include comprehensive error handling:

1. **Network Errors**: Display user-friendly messages
2. **Validation Errors**: Log Zod validation issues
3. **Auth Errors**: Auto-redirect to login
4. **API Errors**: Show specific error messages

## Performance Optimizations

1. **Parallel API Calls**: Use Promise.all for multiple requests
2. **Auto-refresh**: Configurable intervals for data updates
3. **Debounced Search**: Prevent excessive API calls
4. **Memoized Calculations**: Cache computed values

## Testing API Integration

1. Start backend services:
   ```bash
   docker-compose up admin-api
   ```

2. Set environment variables:
   ```bash
   VITE_API_BASE_URL=http://localhost:8083/api/v1
   VITE_WS_URL=ws://localhost:8084/ws
   ```

3. Run frontend:
   ```bash
   npm run dev
   ```

4. Test features:
   - Login with valid JWT
   - View real-time dashboard
   - Manage followers
   - Stream logs
   - Close positions with PIN