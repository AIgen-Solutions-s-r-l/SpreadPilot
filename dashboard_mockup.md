# SpreadPilot Dashboard Overview Mockup

## Description

The Dashboard Overview page serves as the central hub for administrators to monitor the SpreadPilot system at a glance. It provides key metrics, system status, and recent activity in a visually appealing and informative layout.

## Layout Structure

```
+-----------------------------------------------------------------------+
|                           HEADER                                       |
+---------------+-------------------------------------------------------+
|               |                                                       |
|               |  SYSTEM STATUS BANNER                                 |
|               |                                                       |
|               +-------------------------------------------------------+
|               |                                                       |
|               |  +-------------+  +-------------+  +-------------+    |
|    SIDEBAR    |  | METRIC CARD |  | METRIC CARD |  | METRIC CARD |    |
|    NAVIGATION |  +-------------+  +-------------+  +-------------+    |
|               |                                                       |
|               |  +-------------+  +-------------+  +-------------+    |
|               |  | METRIC CARD |  | METRIC CARD |  | METRIC CARD |    |
|               |  +-------------+  +-------------+  +-------------+    |
|               |                                                       |
|               +-------------------------------------------------------+
|               |                                                       |
|               |  +----------------------------+  +------------------+ |
|               |  |                            |  |                  | |
|               |  |                            |  |                  | |
|               |  |      PERFORMANCE CHART     |  |  ACTIVE         | |
|               |  |                            |  |  FOLLOWERS      | |
|               |  |                            |  |  LIST           | |
|               |  |                            |  |                  | |
|               |  +----------------------------+  +------------------+ |
|               |                                                       |
|               +-------------------------------------------------------+
|               |                                                       |
|               |  +----------------------------+  +------------------+ |
|               |  |                            |  |                  | |
|               |  |      TRADING ACTIVITY      |  |  RECENT         | |
|               |  |      TIMELINE              |  |  ALERTS         | |
|               |  |                            |  |                  | |
|               |  |                            |  |                  | |
|               |  +----------------------------+  +------------------+ |
|               |                                                       |
+---------------+-------------------------------------------------------+
```

## Component Details

### 1. System Status Banner

A prominent banner at the top of the dashboard showing the overall system health:

```
+-----------------------------------------------------------------------+
| SYSTEM STATUS: OPERATIONAL                                             |
| Trading Bot: Online | IB Gateway: Connected | Followers: 12/15 Active  |
+-----------------------------------------------------------------------+
```

- **Background Color**: Green (#10B981) for operational, Yellow (#F59E0B) for warnings, Red (#EF4444) for critical issues
- **Text**: White, clear status message
- **Icons**: Status indicators for each major component

### 2. Metric Cards

Six key metric cards arranged in a grid, each showing:

```
+----------------------------------+
| TOTAL P&L                        |
| $12,456.78                       |
| +2.4% ↑ from yesterday           |
+----------------------------------+
```

**Metrics to Display:**
- Total P&L (with day-over-day change)
- Today's P&L (with hour-over-hour change)
- Monthly P&L (with week-over-week change)
- Active Positions (with count and value)
- Follower Count (with active/inactive breakdown)
- Trade Count (with daily volume)

**Design Elements:**
- Card background: White
- Metric value: Large, bold font
- Trend indicator: Green for positive, Red for negative
- Subtle icon representing the metric type

### 3. Performance Chart

A large chart showing P&L performance over time:

```
+-----------------------------------------------------------------------+
| PERFORMANCE                                                   [FILTER] |
|                                                                        |
|    ^                                                                   |
|    |                                          ****                     |
|    |                                     *****    **                   |
|    |                                 ****           *                  |
|    |                            *****               **                 |
|    |                       *****                      *                |
|    |                  *****                            **              |
|    |             *****                                  **             |
|    |        *****                                        **            |
|    |   *****                                              ***          |
|    +-----------------------------------------------------------------> |
|      Jan    Feb    Mar    Apr    May    Jun    Jul    Aug    Sep      |
|                                                                        |
+-----------------------------------------------------------------------+
```

**Features:**
- Line chart showing cumulative P&L
- Time range selector (Day, Week, Month, Year, All)
- Comparison option (vs. previous period)
- Hover tooltips with detailed values
- Annotations for significant events

### 4. Active Followers List

A compact list showing the status of all followers:

```
+-----------------------------------------------------------------------+
| ACTIVE FOLLOWERS                                             [VIEW ALL]|
|                                                                        |
| ● Follower_001  | P&L: +$1,245.67 | Positions: 3 | Status: Active     |
| ● Follower_002  | P&L: +$867.45   | Positions: 2 | Status: Active     |
| ● Follower_003  | P&L: -$123.45   | Positions: 1 | Status: Active     |
| ○ Follower_004  | P&L: $0.00      | Positions: 0 | Status: Inactive   |
| ● Follower_005  | P&L: +$2,345.67 | Positions: 4 | Status: Active     |
|                                                                        |
+-----------------------------------------------------------------------+
```

**Features:**
- Status indicator dot (green for active, gray for inactive)
- Key metrics for each follower
- Click to view detailed follower page
- Sortable by different columns

### 5. Trading Activity Timeline

A chronological feed of recent trading activities:

```
+-----------------------------------------------------------------------+
| TRADING ACTIVITY                                           [VIEW ALL]  |
|                                                                        |
| 12:34 PM | Follower_001 | Opened position SOXL | 100 shares @ $45.67  |
| 12:15 PM | Follower_003 | Closed position SOXS | 50 shares @ $32.10   |
| 11:45 AM | Follower_002 | Adjusted stop loss   | SOXL @ $44.20        |
| 11:30 AM | Follower_005 | Opened position SOXS | 75 shares @ $31.45   |
| 10:15 AM | Follower_001 | Closed position SOXL | 50 shares @ $46.78   |
|                                                                        |
+-----------------------------------------------------------------------+
```

**Features:**
- Timestamp for each activity
- Color-coded by activity type (open, close, adjust)
- Filterable by follower, action type, and symbol
- Click to view detailed trade information

### 6. Recent Alerts

A list of recent system alerts and notifications:

```
+-----------------------------------------------------------------------+
| RECENT ALERTS                                              [VIEW ALL]  |
|                                                                        |
| ⚠️ 12:45 PM | Connection to IB Gateway temporarily lost for Follower_004 |
| ✅ 12:30 PM | System backup completed successfully                    |
| ℹ️ 11:50 AM | New trading signal detected from Google Sheets          |
| ⚠️ 10:20 AM | High volatility detected for SOXL                       |
| ✅ 09:30 AM | Trading day started - all systems operational           |
|                                                                        |
+-----------------------------------------------------------------------+
```

**Features:**
- Icon indicating alert type (info, warning, error, success)
- Timestamp for each alert
- Brief description of the alert
- Click to view detailed alert information
- Color-coded by severity

## Interactive Elements

1. **Refresh Button**: To manually update the dashboard data
2. **Time Range Selectors**: For charts and activity feeds
3. **Filter Dropdowns**: To focus on specific followers or symbols
4. **Export Options**: To download data or generate reports
5. **Quick Action Buttons**: For common tasks like enabling/disabling followers

## Responsive Behavior

- **Desktop**: Full layout as described above
- **Tablet**: Stacked layout with metrics in 2x3 grid, charts and lists full width
- **Mobile**: Single column layout with collapsible sections

## Animation and Transitions

- Subtle loading animations for data fetching
- Smooth transitions between time ranges on charts
- Gentle pulse animation for real-time updates
- Fade-in effects for new alerts and activities

## Color Usage

- **Charts**: Use the primary blue for main data series, with secondary colors for comparisons
- **Status Indicators**: Green for positive/active, red for negative/errors, yellow for warnings
- **Background**: Light gray for the page, white for cards and containers
- **Text**: Dark gray for primary text, medium gray for secondary text

This mockup provides a comprehensive view of the SpreadPilot system's performance and status, enabling administrators to quickly assess the health of the system and take appropriate actions when needed.