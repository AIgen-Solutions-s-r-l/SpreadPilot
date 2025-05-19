# SpreadPilot Trading Activity Mockup

## Description

The Trading Activity page provides a comprehensive view of all trading operations across the platform. This new page allows administrators to monitor real-time positions, track trade history, and analyze performance metrics for all followers in one centralized interface.

## Layout Structure

```
+-----------------------------------------------------------------------+
|                           HEADER                                       |
+---------------+-------------------------------------------------------+
|               |                                                       |
|               |  TRADING ACTIVITY                       [REFRESH] [⚙️] |
|               |                                                       |
|               +-------------------------------------------------------+
|               |                                                       |
|    SIDEBAR    |  [POSITIONS] [HISTORY] [PERFORMANCE] [SIGNALS]        |
|    NAVIGATION |                                                       |
|               +-------------------------------------------------------+
|               |                                                       |
|               |  ACTIVE POSITIONS SUMMARY                             |
|               |  Total: 24 positions | Value: $245,678.90 | P&L: +$12,345.67 |
|               |                                                       |
|               +-------------------------------------------------------+
|               |                                                       |
|               |  POSITIONS TABLE                                      |
|               |  +---------------------------------------------------+|
|               |  | FOLLOWER | SYMBOL | QTY | ENTRY | CURRENT | P&L | ACTIONS ||
|               |  |---------+--------+-----+-------+---------+-----+--------|
|               |  | ........ | ..... | ... | ..... | ....... | ... | ...... ||
|               |  | ........ | ..... | ... | ..... | ....... | ... | ...... ||
|               |  | ........ | ..... | ... | ..... | ....... | ... | ...... ||
|               |  | ........ | ..... | ... | ..... | ....... | ... | ...... ||
|               |  | ........ | ..... | ... | ..... | ....... | ... | ...... ||
|               |  | ........ | ..... | ... | ..... | ....... | ... | ...... ||
|               |  | ........ | ..... | ... | ..... | ....... | ... | ...... ||
|               |  +---------------------------------------------------+|
|               |                                                       |
|               |  POSITION DISTRIBUTION                                |
|               |  [PIE CHART: Distribution by Symbol]                  |
|               |                                                       |
+---------------+-------------------------------------------------------+
```

## Component Details

### 1. Page Header

```
+-----------------------------------------------------------------------+
| TRADING ACTIVITY                                      [REFRESH] [⚙️]    |
+-----------------------------------------------------------------------+
```

**Features:**
- Clear page title with appropriate typography
- Refresh button to manually update data
- Settings gear icon for configuring view preferences

### 2. Tab Navigation

```
+-----------------------------------------------------------------------+
| [POSITIONS] [HISTORY] [PERFORMANCE] [SIGNALS]                         |
+-----------------------------------------------------------------------+
```

**Features:**
- Tab-based navigation for different trading views
- Active tab highlighted with accent color and underline
- Each tab shows different content in the main area

### 3. Active Positions Summary

```
+-----------------------------------------------------------------------+
| ACTIVE POSITIONS SUMMARY                                              |
| Total: 24 positions | Value: $245,678.90 | P&L: +$12,345.67 (+5.3%)   |
+-----------------------------------------------------------------------+
```

**Features:**
- Quick overview of all active positions across the platform
- Total count of open positions
- Total market value of all positions
- Aggregate P&L with percentage gain/loss
- Values color-coded (green for positive, red for negative)

### 4. Positions Table (Positions Tab)

```
+-----------------------------------------------------------------------+
| FOLLOWER    | SYMBOL | QTY  | ENTRY    | CURRENT  | P&L       | ACTIONS |
+----------------------------------------------------------------------------+
| Follower_001| SOXL   | 100  | $45.67   | $47.89   | +$222.00  | [···]   |
| Follower_001| QQQ    | 25   | $410.25  | $415.75  | +$137.50  | [···]   |
| Follower_002| SOXL   | 75   | $46.12   | $47.89   | +$132.75  | [···]   |
| Follower_003| SOXS   | 50   | $32.10   | $31.45   | -$32.50   | [···]   |
| Follower_005| SOXL   | 120  | $44.98   | $47.89   | +$349.20  | [···]   |
| Follower_005| SOXS   | 60   | $31.75   | $31.45   | -$18.00   | [···]   |
| Follower_005| QQQ    | 30   | $412.50  | $415.75  | +$97.50   | [···]   |
| Follower_006| SOXL   | 90   | $45.25   | $47.89   | +$237.60  | [···]   |
+-----------------------------------------------------------------------+
```

**Features:**
- Sortable column headers with subtle indicators
- Follower IDs linked to follower detail pages
- Symbol names with optional tooltip showing full security name
- Entry and current prices with clear formatting
- P&L values color-coded (green for positive, red for negative)
- Actions menu (⋮) with options like "Close Position", "Set Alert", "View History"
- Filtering options for follower, symbol, and P&L range

### 5. Position Distribution Chart

```
+-----------------------------------------------------------------------+
| POSITION DISTRIBUTION                                    [BY SYMBOL ▼] |
|                                                                       |
|                      ┌─────────────────────────┐                      |
|                      │           ┌──┐           │                      |
|                      │      ┌────┘  └────┐      │                      |
|                      │   ┌──┘            └──┐   │                      |
|                      │ ┌─┘                  └─┐ │                      |
|                      │ │      SOXL (55%)      │ │                      |
|                      │ └─┐                  ┌─┘ │                      |
|                      │   └──┐            ┌──┘   │                      |
|                      │      └────┐  ┌────┘      │                      |
|                      │           └──┘           │                      |
|                      └─────────────────────────┘                      |
|                                                                       |
| SOXL: 55% ($135,000) | SOXS: 25% ($61,250) | QQQ: 20% ($49,428.90)   |
+-----------------------------------------------------------------------+
```

**Features:**
- Interactive pie chart showing distribution of positions
- Toggle between different distribution views (by symbol, by follower, by P&L)
- Hover tooltips with detailed values
- Legend with percentage and absolute value
- Color-coded segments for easy identification

### 6. Trade History Table (History Tab)

```
+-----------------------------------------------------------------------+
| TRADE HISTORY                                                         |
| [FILTER BY: All ▼] [DATE RANGE: Last 7 days ▼] [EXPORT]              |
+-----------------------------------------------------------------------+
| TIME        | FOLLOWER    | ACTION | SYMBOL | QTY  | PRICE  | P&L     |
+----------------------------------------------------------------------------+
| 12:34:56 PM | Follower_001| BUY    | SOXL   | 100  | $45.67 | -       |
| 12:15:32 PM | Follower_003| SELL   | SOXS   | 50   | $32.10 | +$42.50 |
| 11:45:21 AM | Follower_002| BUY    | SOXL   | 75   | $46.12 | -       |
| 11:30:45 AM | Follower_005| BUY    | SOXS   | 60   | $31.75 | -       |
| 10:15:33 AM | Follower_001| SELL   | QQQ    | 15   | $415.25| +$75.00 |
| 10:02:17 AM | Follower_006| BUY    | SOXL   | 90   | $45.25 | -       |
| 09:45:52 AM | Follower_005| BUY    | QQQ    | 30   | $412.50| -       |
| 09:30:15 AM | Follower_003| BUY    | SOXS   | 50   | $31.25 | -       |
+-----------------------------------------------------------------------+
```

**Features:**
- Chronological list of all trades across the platform
- Timestamp with date for older entries
- Action type (Buy/Sell) with color coding (Buy: Blue, Sell: Purple)
- P&L shown for closing transactions
- Advanced filtering options
- Date range selector
- Export functionality for reporting

### 7. Performance Dashboard (Performance Tab)

```
+-----------------------------------------------------------------------+
| PERFORMANCE METRICS                                  [TIME: 1M ▼]      |
+-----------------------------------------------------------------------+
|                                                                       |
| +----------------------------+  +----------------------------+        |
| | CUMULATIVE P&L             |  | WIN/LOSS RATIO            |        |
| | [Line chart showing P&L    |  | [Bar chart showing win vs |        |
| |  over selected time period]|  |  loss trades by follower] |        |
| +----------------------------+  +----------------------------+        |
|                                                                       |
| +----------------------------+  +----------------------------+        |
| | SYMBOL PERFORMANCE         |  | HOURLY PERFORMANCE        |        |
| | [Bar chart showing P&L     |  | [Line chart showing P&L   |        |
| |  by traded symbol]         |  |  by hour of day]          |        |
| +----------------------------+  +----------------------------+        |
|                                                                       |
| KEY STATISTICS                                                        |
| Total Trades: 156 | Win Rate: 68% | Avg Win: $245.67 | Avg Loss: $78.45 |
| Best Day: May 15 (+$4,567.89) | Worst Day: May 12 (-$1,234.56)       |
+-----------------------------------------------------------------------+
```

**Features:**
- Multiple charts showing different performance aspects
- Time period selector (1D, 1W, 1M, 3M, YTD, 1Y, All)
- Interactive charts with hover tooltips
- Key statistics summarizing overall performance
- Ability to filter by follower or symbol
- Export options for reports

### 8. Trading Signals (Signals Tab)

```
+-----------------------------------------------------------------------+
| TRADING SIGNALS                                                       |
| [SOURCE: Google Sheets ▼] [STATUS: All ▼] [REFRESH]                   |
+-----------------------------------------------------------------------+
| TIME        | SYMBOL | SIGNAL | DETAILS           | STATUS    | ACTIONS |
+----------------------------------------------------------------------------+
| 12:30:00 PM | SOXL   | BUY    | 100 shares @ MKT  | ✅ EXECUTED | [VIEW]  |
| 12:15:00 PM | SOXS   | SELL   | 50 shares @ MKT   | ✅ EXECUTED | [VIEW]  |
| 11:45:00 AM | SOXL   | BUY    | 75 shares @ MKT   | ✅ EXECUTED | [VIEW]  |
| 11:30:00 AM | SOXS   | BUY    | 60 shares @ MKT   | ✅ EXECUTED | [VIEW]  |
| 10:15:00 AM | QQQ    | SELL   | 15 shares @ MKT   | ✅ EXECUTED | [VIEW]  |
| 10:00:00 AM | SOXL   | BUY    | 90 shares @ MKT   | ✅ EXECUTED | [VIEW]  |
| 09:45:00 AM | QQQ    | BUY    | 30 shares @ MKT   | ✅ EXECUTED | [VIEW]  |
| 09:30:00 AM | SOXS   | BUY    | 50 shares @ MKT   | ✅ EXECUTED | [VIEW]  |
+-----------------------------------------------------------------------+
```

**Features:**
- List of trading signals from Google Sheets
- Signal status indicators (Pending, Executed, Failed, Ignored)
- Time of signal detection
- Signal details with action and parameters
- View button to see detailed execution across followers
- Filter by source, status, symbol, and time range

### 9. Position Detail Modal

When clicking on a position row, a detailed modal appears:

```
+-----------------------------------------------------------------------+
|                                                                       |
| POSITION DETAILS: SOXL - Follower_001                      [X CLOSE]  |
| -------------------------------------------------------------------- |
|                                                                       |
| GENERAL INFORMATION                                                   |
| Symbol: SOXL | Quantity: 100 | Entry: $45.67 | Current: $47.89       |
| Entry Date: May 18, 2025 12:34:56 PM | Days Held: 1                  |
| P&L: +$222.00 (+4.86%) | Unrealized                                  |
|                                                                       |
| PRICE CHART                                                          |
| [Line chart showing price movement since entry with entry point marked] |
|                                                                       |
| POSITION HISTORY                                                      |
| May 18, 12:34:56 PM | BUY | 100 shares @ $45.67 | Signal: GS-123     |
|                                                                       |
| RISK MANAGEMENT                                                       |
| Stop Loss: None | Take Profit: None                                   |
|                                                                       |
| ACTIONS                                                               |
| [CLOSE POSITION] [SET STOP LOSS] [SET TAKE PROFIT] [VIEW SIGNAL]     |
|                                                                       |
+-----------------------------------------------------------------------+
```

**Features:**
- Comprehensive position details
- Price chart showing movement since entry
- Position history for partial fills or adjustments
- Risk management settings and status
- Quick action buttons for common tasks

## Interactive Elements

1. **Tab Navigation**: Switch between different trading views
2. **Filters and Dropdowns**: Refine the data shown in tables and charts
3. **Sortable Columns**: Click column headers to sort data
4. **Interactive Charts**: Hover for details, zoom, pan, etc.
5. **Action Menus**: Quick access to common actions
6. **Refresh Button**: Manually update data
7. **Export Options**: Download data in various formats

## Responsive Behavior

- **Desktop**: Full layout as described
- **Tablet**: Tabs stack vertically, charts resize to fit width
- **Mobile**: Single column layout with collapsible sections

## Animation and Transitions

- Smooth tab transitions
- Subtle loading animations during data fetching
- Chart animations when data changes
- Highlight effect for new trades or signals

## Color Usage

- **Action Types**:
  - Buy: Blue (#3B82F6)
  - Sell: Purple (#8B5CF6)
- **P&L Values**:
  - Positive: Green (#10B981)
  - Negative: Red (#EF4444)
- **Status Indicators**:
  - Executed: Green (#10B981)
  - Pending: Amber (#F59E0B)
  - Failed: Red (#EF4444)
- **Charts**:
  - Primary data series: Blue (#3B82F6)
  - Secondary data series: Purple (#8B5CF6)
  - Tertiary data series: Teal (#14B8A6)

This Trading Activity interface provides administrators with a powerful tool to monitor and manage all trading operations across the SpreadPilot platform, with real-time data, historical analysis, and performance metrics in one centralized location.