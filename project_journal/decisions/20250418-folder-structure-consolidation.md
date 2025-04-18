# Folder Structure Consolidation

**Date:** 2025-04-18
**Author:** Roo Commander
**Status:** Approved

## Context

The SpreadPilot project currently has duplicated folder structures:

1. Hyphenated versions (`trading-bot`, `admin-api`, etc.) used for deployment
2. Underscore versions (`trading_bot`, `admin_api`, etc.) used for testing

This duplication creates maintenance challenges as code changes need to be synchronized between both versions.

## Decision

We will consolidate the folder structure by:

1. Keeping only the hyphenated versions
2. Making the hyphenated versions importable as Python packages
3. Updating the integration tests to import from the hyphenated versions
4. Removing the underscore versions

This approach was chosen because:
- The hyphenated versions are already the "official" service directories used in deployment
- It's easier to update a few test imports than to change all deployment configurations
- It results in a cleaner, more maintainable structure

## Implementation Plan

### Step 1: Make hyphenated versions importable

Add `__init__.py` files to make the hyphenated directories importable as Python packages:

```bash
# Create __init__.py files in hyphenated directories
touch trading-bot/__init__.py
touch admin-api/__init__.py
touch alert-router/__init__.py
touch report-worker/__init__.py
touch watchdog/__init__.py
```

### Step 2: Update integration tests

Update imports in integration tests to use the hyphenated versions:

1. In `tests/integration/conftest.py`:
   - Change `from trading_bot.app.service.signals import SignalProcessor` to `from trading-bot.app.service.signals import SignalProcessor`
   - Change `from trading_bot.app.sheets import GoogleSheetsClient` to `from trading-bot.app.sheets import GoogleSheetsClient`
   - Change `from alert_router.app.service.router import route_alert` to `from alert-router.app.service.router import route_alert`
   - Change `from report_worker.app.service.pnl import calculate_monthly_pnl` to `from report-worker.app.service.pnl import calculate_monthly_pnl`
   - Change `from admin_api.app.main import app as admin_app` to `from admin-api.app.main import app as admin_app`

2. Update similar imports in other test files:
   - `tests/integration/test_trading_flow.py`
   - `tests/integration/test_admin_api.py`
   - `tests/integration/test_assignment_flow.py`
   - `tests/integration/test_reporting_flow.py`

3. Update imports in service files that reference underscore versions:
   - `admin-api/app/main.py`
   - `admin-api/app/services/follower_service.py`
   - `admin-api/app/api/v1/api.py`
   - `admin-api/app/api/v1/endpoints/dashboard.py`
   - `admin-api/app/api/v1/endpoints/followers.py`

### Step 3: Remove underscore versions

Once all imports are updated and tests are passing, remove the underscore versions:

```bash
# Remove underscore directories
rm -rf trading_bot/
rm -rf admin_api/
rm -rf alert_router/
rm -rf report_worker/
rm -rf watchdog/
```

## Consequences

### Positive

- Eliminates code duplication
- Simplifies maintenance as changes only need to be made in one place
- Provides a cleaner, more consistent project structure
- Reduces confusion for new developers

### Negative

- Requires updates to import statements in tests and some service files
- May require adjustments to IDE configurations and tooling
- Hyphenated package names are less conventional in Python (though still valid with proper `__init__.py` files)

### Neutral

- No changes to deployment process or Docker configurations are needed
- The core functionality of the services remains unchanged