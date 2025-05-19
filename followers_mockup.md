# SpreadPilot Followers Management Mockup

## Description

The Followers Management page provides administrators with a comprehensive interface to monitor, manage, and control all follower accounts in the SpreadPilot system. This enhanced design improves upon the existing implementation with better visual indicators, more detailed information, and improved user interactions.

## Layout Structure

```
+-----------------------------------------------------------------------+
|                           HEADER                                       |
+---------------+-------------------------------------------------------+
|               |                                                       |
|               |  FOLLOWERS MANAGEMENT                      [+ ADD NEW]|
|               |                                                       |
|               +-------------------------------------------------------+
|               |                                                       |
|               |  [SEARCH] [FILTER ▼] [STATUS ▼] [SORT BY ▼] [EXPORT ▼]|
|               |                                                       |
|    SIDEBAR    +-------------------------------------------------------+
|    NAVIGATION |                                                       |
|               |  FOLLOWERS TABLE                                      |
|               |  +---------------------------------------------------+|
|               |  | ID | STATUS | BOT | IBGW | POSITIONS | P&L | ACTIONS ||
|               |  |----+--------+-----+------+-----------+-----+--------|
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  | .. | ...... | ... | .... | ......... | ... | ...... ||
|               |  +---------------------------------------------------+|
|               |                                                       |
|               |  [< PREV] Page 1 of 3 [NEXT >]                        |
|               |                                                       |
+---------------+-------------------------------------------------------+
```

## Component Details

### 1. Page Header

```
+-----------------------------------------------------------------------+
| FOLLOWERS MANAGEMENT                                       [+ ADD NEW] |
+-----------------------------------------------------------------------+
```

**Features:**
- Clear page title with appropriate typography
- Prominent "Add New Follower" button with + icon
- Subtle divider separating the header from content

### 2. Search and Filter Bar

```
+-----------------------------------------------------------------------+
| 🔍 Search...  | Status: All ▼ | Bot Status: All ▼ | Sort: ID ▼ | ⬇️ Export |
+-----------------------------------------------------------------------+
```

**Features:**
- Search input with placeholder and search icon
- Status filter dropdown (All, Active, Inactive)
- Bot Status filter dropdown (All, Online, Offline, Error)
- Sort dropdown (ID, Status, P&L, etc.)
- Export button with options (CSV, Excel, PDF)

### 3. Followers Table

```
+-----------------------------------------------------------------------+
| ID          | STATUS  | BOT    | IBGW   | POSITIONS | P&L TODAY | ACTIONS |
+---------------------------------------------------------------------------+
| Follower_001| ● ACTIVE| ● ONLINE| ● CONN | 3 ($12.5K)| +$1,245.67| [···] |
| Follower_002| ● ACTIVE| ● ONLINE| ● CONN | 2 ($8.2K) | +$867.45  | [···] |
| Follower_003| ● ACTIVE| ● ONLINE| ● CONN | 1 ($5.1K) | -$123.45  | [···] |
| Follower_004| ○ INACTV| ○ OFFLN| ○ DISC | 0 ($0)    | $0.00     | [···] |
| Follower_005| ● ACTIVE| ⚠️ WARN | ● CONN | 4 ($18.7K)| +$2,345.67| [···] |
| Follower_006| ● ACTIVE| ● ONLINE| ⚠️ WARN | 2 ($9.3K) | +$456.78  | [···] |
| Follower_007| ○ INACTV| ○ OFFLN| ○ DISC | 0 ($0)    | $0.00     | [···] |
| Follower_008| ● ACTIVE| ● ONLINE| ● CONN | 3 ($14.2K)| +$789.12  | [···] |
+-----------------------------------------------------------------------+
```

**Features:**
- Sortable column headers with subtle indicators
- Status indicators using colors and icons:
  - Green dot (●) for active/online/connected
  - Gray dot (○) for inactive/offline/disconnected
  - Yellow warning (⚠️) for warning states
  - Red alert (🔴) for error states
- Positions column showing count and total value
- P&L values color-coded (green for positive, red for negative)
- Actions menu (⋮) with dropdown options

### 4. Expanded Row Detail View

When a row is clicked, it expands to show more detailed information:

```
+-----------------------------------------------------------------------+
| Follower_001 | ● ACTIVE | ● ONLINE | ● CONN | 3 ($12.5K) | +$1,245.67 | [···] |
+-----------------------------------------------------------------------+
|                                                                       |
| DETAILS                                                               |
| Account ID: IB12345678 | Created: 2025-01-15 | Last Active: 2 min ago |
|                                                                       |
| PERFORMANCE                                                           |
| P&L Today: +$1,245.67 | P&L MTD: +$5,678.90 | P&L YTD: +$12,345.67   |
|                                                                       |
| POSITIONS                                                             |
| SOXL: 100 shares @ $45.67 | SOXS: 50 shares @ $32.10 | QQQ: 25 @ $410.25 |
|                                                                       |
| ACTIONS                                                               |
| [EDIT] [DISABLE] [CLOSE POSITIONS] [VIEW TRADES] [VIEW LOGS]         |
|                                                                       |
+-----------------------------------------------------------------------+
```

**Features:**
- Comprehensive account details
- Performance metrics across different time periods
- Current positions with details
- Quick action buttons for common tasks

### 5. Add/Edit Follower Modal

When "Add New" is clicked or "Edit" is selected from the actions menu:

```
+-----------------------------------------------------------------------+
|                                                                       |
|  ADD NEW FOLLOWER                                           [X CLOSE] |
|  -------------------------------------------------------------------- |
|                                                                       |
|  ACCOUNT INFORMATION                                                  |
|  Follower ID*: [____________] (e.g., Follower_009)                    |
|  IB Account ID*: [____________] (e.g., U1234567)                      |
|  Description: [____________] (Optional)                               |
|                                                                       |
|  TRADING CONFIGURATION                                                |
|  Status: [●] Active  [○] Inactive                                     |
|  Position Sizing: [____________] % of signals                         |
|  Max Positions: [____] (0 for unlimited)                              |
|  Max Allocation: $[____________] (0 for unlimited)                    |
|                                                                       |
|  NOTIFICATIONS                                                        |
|  Email: [____________] (for alerts and reports)                       |
|  Telegram ID: [____________] (for instant notifications)              |
|  Notification Level: [All Events ▼]                                   |
|                                                                       |
|  [CANCEL]                                         [SAVE FOLLOWER]     |
|                                                                       |
+-----------------------------------------------------------------------+
```

**Features:**
- Clean, organized form layout
- Required fields marked with asterisk (*)
- Input validation with helpful error messages
- Toggle switches for boolean options
- Dropdown selectors for enumerated options
- Clear action buttons

### 6. Confirmation Dialogs

For critical actions like closing positions:

```
+-----------------------------------------------------------------------+
|                                                                       |
|  ⚠️ CLOSE ALL POSITIONS                                    [X CLOSE]  |
|  -------------------------------------------------------------------- |
|                                                                       |
|  You are about to close ALL positions for Follower_001.               |
|  This action cannot be undone.                                        |
|                                                                       |
|  Current Positions:                                                   |
|  - SOXL: 100 shares @ $45.67                                          |
|  - SOXS: 50 shares @ $32.10                                           |
|  - QQQ: 25 shares @ $410.25                                           |
|                                                                       |
|  Please enter your PIN to confirm:                                    |
|  PIN: [____]                                                          |
|                                                                       |
|  [CANCEL]                                    [CONFIRM CLOSE POSITIONS]|
|                                                                       |
+-----------------------------------------------------------------------+
```

**Features:**
- Clear warning icon and title
- Detailed explanation of the action and consequences
- Summary of affected items
- Security confirmation (PIN entry)
- Prominent, differently colored action buttons

### 7. Pagination Controls

```
+-----------------------------------------------------------------------+
| [< PREV]    Showing 1-8 of 24 followers    [NEXT >]                   |
| [1] [2] [3]                                                           |
+-----------------------------------------------------------------------+
```

**Features:**
- Previous/Next buttons
- Page number indicators
- Clear indication of current position in results

## Interactive Elements

1. **Row Hover Effects**: Subtle background color change on hover
2. **Row Click**: Expands/collapses the detail view
3. **Status Filters**: Quick-filter buttons for common status combinations
4. **Refresh Button**: To manually update the follower data
5. **Bulk Action Dropdown**: For performing actions on multiple selected followers
6. **Search Autocomplete**: Suggestions as you type in the search box

## Responsive Behavior

- **Desktop**: Full table layout as described
- **Tablet**: Simplified table with fewer columns, expandable for details
- **Mobile**: Card-based layout instead of table, one follower per card

## Animation and Transitions

- Smooth expand/collapse for detail views
- Fade-in effects for modals and dialogs
- Subtle loading indicators during data fetching
- Gentle pulse animation for status changes

## Color Usage

- **Status Indicators**:
  - Active/Online/Connected: Green (#10B981)
  - Inactive/Offline/Disconnected: Gray (#6B7280)
  - Warning: Amber (#F59E0B)
  - Error: Red (#EF4444)
- **P&L Values**:
  - Positive: Green (#10B981)
  - Negative: Red (#EF4444)
  - Zero/Neutral: Gray (#6B7280)
- **Action Buttons**:
  - Primary Actions: Blue (#3B82F6)
  - Destructive Actions: Red (#EF4444)
  - Neutral Actions: Gray (#6B7280)

This enhanced Followers Management interface provides administrators with a powerful yet intuitive way to monitor and control all follower accounts in the SpreadPilot system, with clear visual indicators and streamlined workflows for common tasks.