# SpreadPilot Frontend

React + TypeScript frontend application for the SpreadPilot copy-trading platform.

## Overview

This is the web-based admin dashboard for SpreadPilot, providing real-time monitoring and management of trading followers, positions, and system health.

## Features

- **Dashboard**: Real-time overview of P&L, active followers, positions, and alerts
- **Followers Management**: Enable/disable followers, view P&L, close positions
- **Log Console**: Live streaming logs with filtering and search capabilities
- **Trading Activity**: Monitor trades and positions across all followers
- **Manual Commands**: Execute manual operations with PIN authentication
- **Service Health Monitoring**: RED/YELLOW/GREEN status indicators with system metrics
- **Service Management**: Restart unhealthy services directly from dashboard

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Material-UI (MUI)** for component library
- **Axios** for API communication
- **Zod** for runtime type validation
- **React Router** for navigation
- **WebSocket** for real-time updates

## Environment Setup

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Configure the following variables:
- `VITE_API_BASE_URL` or `VITE_API_BASE`: Backend API URL (default: http://localhost:8002/api/v1)
- `VITE_WS_URL`: WebSocket URL for real-time updates (default: ws://localhost:8002/ws)

## Development

Install dependencies:
```bash
npm install
```

Start development server:
```bash
npm run dev
```

The app will be available at http://localhost:5173

## API Integration

The frontend integrates with the admin-api backend service:

### Services
- `api.ts`: Central Axios configuration with JWT interceptor
- `followerService.ts`: Follower CRUD operations
- `pnlService.ts`: P&L data fetching (supports PostgreSQL format)
- `logService.ts`: Log retrieval and streaming
- `authService.ts`: Authentication management
- `healthService.ts`: Health monitoring and service restart functionality

### Hooks
- `useFollowers`: Manages follower data with auto-refresh
- `useLogs`: Handles log streaming and filtering
- `useDashboard`: Aggregates dashboard metrics
- `useAuth`: Authentication state management
- `useServiceHealth`: Polls health endpoint every 15 seconds

### Schema Validation
All API responses are validated using Zod schemas to ensure type safety:
- `follower.schema.ts`: Follower data structures
- `pnl.schema.ts`: P&L response schemas
- `log.schema.ts`: Log entry validation

## Key Components

### Pages
- `DashboardPageV2`: Main overview with metrics and charts
- `FollowersPageV3`: Enhanced follower management with real-time data
- `LogsPageV2`: Real-time log viewer with filtering
- `LoginPage`: JWT authentication

### Common Components
- `TimeValueBadge`: Visual indicator for time value status
- `ActiveFollowersListV2`: Dashboard follower summary
- `RecentAlertsV2`: System alerts display
- `ServiceHealthWidget`: Comprehensive health monitoring with restart actions

## Authentication

The app uses JWT authentication:
1. Login with credentials at `/login`
2. Token stored in localStorage
3. Axios interceptor adds token to all requests
4. Auto-redirect to login on 401 errors

## WebSocket Integration

Real-time updates are handled via WebSocket:
- Connection managed by `WebSocketContext`
- Auto-reconnection on disconnect
- Live log streaming
- Real-time follower status updates

## Time Value Monitoring

The dashboard displays Time Value badges for each follower's positions:
- **SAFE** (Green): Time value > $1.00
- **RISK** (Yellow): Time value between $0.10 and $1.00
- **CRITICAL** (Red): Time value ≤ $0.10 (auto-liquidation may trigger)

## Service Health Monitoring

The UI polls the `/health` endpoint every 15 seconds and displays:
- Overall system health with color-coded dots (GREEN/YELLOW/RED)
- Individual service status
- Service restart capability directly from the UI

## Testing

Run Cypress E2E tests:
```bash
npm run cypress:open  # Interactive mode
npm run cypress:run   # Headless mode
```

The tests cover:
- Real data fetching from all API endpoints
- Time-value badge color verification
- Service health polling
- Service restart functionality
- Follower actions including position closing with PIN

## Build & Deploy

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

Lint code:
```bash
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   ├── contexts/        # React contexts (Auth, WebSocket)
│   ├── hooks/           # Custom React hooks
│   ├── pages/           # Page components
│   ├── schemas/         # Zod validation schemas
│   ├── services/        # API service functions
│   ├── theme/           # MUI theme configuration
│   └── types/           # TypeScript type definitions
├── public/              # Static assets
└── .env.example         # Environment template
```

## Recent Updates

- Replaced mock data with live API integration
- Added Axios with JWT interceptor for authenticated requests
- Implemented Zod validation for all API responses
- Created enhanced V3 pages with real-time data
- Added visual TV (Time Value) badge indicators with SAFE/RISK/CRITICAL status
- Implemented service health polling every 15 seconds
- Added service restart functionality from the UI
- Integrated with PostgreSQL-based P&L endpoints
- Implemented comprehensive error handling and loading states
- Added Cypress E2E tests for real data integration

## Troubleshooting

### API Connection Issues
- Verify `VITE_API_BASE_URL` or `VITE_API_BASE` in `.env`
- Check if admin-api is running on port 8002
- Ensure JWT token is valid

### WebSocket Connection
- Verify `VITE_WS_URL` in `.env`
- Check WebSocket service is running
- Look for connection errors in browser console

### Build Errors
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check for TypeScript errors: `npm run lint`
- Verify all environment variables are set