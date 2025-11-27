# Current Implementation Gaps Report

**Analysis Date**: 2025-10-25
**Scope**: Full Codebase Audit
**Focus**: Implementation Completeness, Mock Data Usage, Technical Debt

## Executive Summary

The SpreadPilot codebase is in a polished state regarding backend services (Trading Bot, Admin API, Alert Router), with robust error handling and no critical "TODO" gaps. However, the **Frontend Dashboard** contains significant implementation gaps, relying heavily on hardcoded "mock" data. Crucially, **several backend endpoints required to support the frontend are missing** from the `admin-api`.

### 🔴 Critical Gaps (Frontend & Backend)

The following features require both backend API development and frontend integration:

1.  **Trading Activity - Positions & History**
    *   **Frontend**: `TradingActivityPage.tsx` uses `mockPositions` and `mockTradeHistory`.
    *   **Backend**: `admin-api` is **missing** endpoints to fetch positions and trades (`GET /positions`, `GET /trades`).
    *   **Required Work**:
        *   Implement `admin-api` endpoints to read from MongoDB `positions` and `trades` collections.
        *   Update frontend to fetch this data.

2.  **Trading Signals**
    *   **Frontend**: `TradingActivityPage.tsx` uses `mockTradingSignals`.
    *   **Backend**: `admin-api` is **missing** endpoint to fetch signals (`GET /signals`).
    *   **Required Work**:
        *   Implement `admin-api` endpoint to read from MongoDB `signals` collection.
        *   Update frontend to fetch this data.

3.  **System Alerts**
    *   **Frontend**: `RecentAlerts.tsx` uses `mockAlerts`.
    *   **Backend**: `admin-api` is **missing** endpoint to fetch structured alerts (`GET /alerts`). (Note: `GET /logs` exists but is generic).
    *   **Required Work**:
        *   Implement `admin-api` endpoint to read from MongoDB `alerts` collection (populated by `trading-bot`).
        *   Update frontend to fetch this data.

### 🟡 Integration Gaps (Frontend Only)

The following features have backend support but lack frontend integration:

1.  **Active Followers List** (`frontend/src/components/dashboard/ActiveFollowersList.tsx`)
    *   **Status**: ❌ Static Data
    *   **Backend**: ✅ Supported. `GET /api/v1/followers` and `/api/v1/followers/summary` exist.
    *   **Required Work**: Update component to use `useFollowers` hook.

### 🟡 Minor Gaps & Technical Debt

1.  **Intraday P&L Charting** (`frontend/src/services/pnlService.ts`)
    *   **Status**: ⚠️ Simulated
    *   **Details**: The `getPnLHistory` function mocks '1D' (hourly) data because the API purportedly does not provide hourly granularity.
    *   **Impact**: The "1 Day" view on P&L charts is a smooth interpolation, not real data.

2.  **Frontend TODOs** (`frontend/src/pages/LogsPage.tsx`)
    *   "Implement more specific logic based on message content"
    *   "Add WebSocket connection status indicator"

## Implementation Plan

1.  **Backend Phase**:
    *   Create `PositionsService`, `TradesService`, `AlertsService` in `admin-api`.
    *   Expose endpoints in `admin-api/app/api/v1/endpoints/`.
    *   Ensure proper response schemas.

2.  **Frontend Phase**:
    *   Create `usePositions`, `useTrades`, `useAlerts` hooks in frontend.
    *   Refactor `TradingActivityPage` and `RecentAlerts` to use these hooks.
    *   Refactor `ActiveFollowersList` to use existing `useFollowers` hook.
