#!/bin/bash
# Script to consolidate folder structure by keeping hyphenated versions and updating imports

set -e  # Exit on error

echo "Starting folder structure consolidation..."

# Step 1: Make hyphenated versions importable
echo "Creating __init__.py files in hyphenated directories..."
touch trading-bot/__init__.py
touch admin-api/__init__.py
touch alert-router/__init__.py
touch report-worker/__init__.py
touch watchdog/__init__.py

# Step 2: Update imports in test files
echo "Updating imports in test files..."

# Function to replace imports in a file
replace_imports() {
    local file=$1
    echo "  Processing $file"
    
    # Replace imports
    sed -i 's/from trading_bot\./from trading-bot./g' "$file"
    sed -i 's/from admin_api\./from admin-api./g' "$file"
    sed -i 's/from alert_router\./from alert-router./g' "$file"
    sed -i 's/from report_worker\./from report-worker./g' "$file"
    sed -i 's/from watchdog\./from watchdog./g' "$file"
    
    # Replace import statements with 'import' keyword
    sed -i 's/import trading_bot\./import trading-bot./g' "$file"
    sed -i 's/import admin_api\./import admin-api./g' "$file"
    sed -i 's/import alert_router\./import alert-router./g' "$file"
    sed -i 's/import report_worker\./import report-worker./g' "$file"
    sed -i 's/import watchdog\./import watchdog./g' "$file"
}

# Update imports in integration tests
for file in tests/integration/*.py; do
    replace_imports "$file"
done

# Update imports in conftest.py
replace_imports "tests/integration/conftest.py"

# Update imports in service files
for file in admin-api/app/main.py admin-api/app/services/follower_service.py admin-api/app/api/v1/api.py admin-api/app/api/v1/endpoints/dashboard.py admin-api/app/api/v1/endpoints/followers.py; do
    if [ -f "$file" ]; then
        replace_imports "$file"
    fi
done

echo "Import statements updated."
echo "Please run the tests to verify everything works correctly."
echo "If tests pass, you can remove the underscore directories with:"
echo "rm -rf trading_bot/ admin_api/ alert_router/ report_worker/ watchdog/"

echo "Folder structure consolidation completed!"