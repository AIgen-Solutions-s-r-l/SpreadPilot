# SpreadPilot Folder Structure Consolidation Guide

This guide provides step-by-step instructions for consolidating the duplicated folder structure in the SpreadPilot project.

## Background

The SpreadPilot project currently has duplicated folder structures:
- Hyphenated versions (`trading-bot`, `admin-api`, etc.) used for deployment
- Underscore versions (`trading_bot`, `admin_api`, etc.) used for testing

This duplication creates maintenance challenges as code changes need to be synchronized between both versions.

## Implementation Steps

### 1. Review the Decision Document

Before proceeding, review the decision document that outlines the rationale and approach:
```
project_journal/decisions/20250418-folder-structure-consolidation.md
```

### 2. Make a Backup

Create a backup of the project before making any changes:
```bash
cp -r /home/alessio/Projects/SpreadPilot /home/alessio/Projects/SpreadPilot_backup
```

### 3. Run the Consolidation Script

The `consolidate_folders.sh` script automates most of the consolidation process:

```bash
# Make the script executable
chmod +x consolidate_folders.sh

# Run the script
./consolidate_folders.sh
```

The script will:
- Create `__init__.py` files in the hyphenated directories
- Update import statements in test files and service files

### 4. Run Tests to Verify Changes

Run the integration tests to verify that the updated imports work correctly:

```bash
# Run tests
pytest tests/integration/
```

If you encounter any issues:
1. Check for import errors in the test output
2. Manually update any imports that were missed by the script
3. Run the tests again until they pass

### 5. Remove Underscore Directories

Once the tests pass, you can safely remove the underscore directories:

```bash
rm -rf trading_bot/ admin_api/ alert_router/ report_worker/ watchdog/
```

### 6. Update Documentation

Update any project documentation that references the underscore directories:

1. Check the README.md file
2. Review any developer guides
3. Update any CI/CD configuration if needed

### 7. Commit Changes

Commit the changes to version control:

```bash
git add .
git commit -m "Consolidate folder structure by keeping hyphenated versions and updating imports"
```

## Potential Issues and Solutions

### Python Import Errors

If you encounter import errors with hyphens in package names:

1. Ensure all directories have `__init__.py` files
2. Consider using importlib for dynamic imports if needed:
   ```python
   import importlib
   trading_bot = importlib.import_module('trading-bot.app')
   ```

### IDE Configuration

Some IDEs may have issues with hyphenated package names:

1. Update IDE configurations to recognize the hyphenated directories as Python packages
2. Restart the IDE after making changes

### Build and Deployment

The build and deployment process should continue to work as before since it already uses the hyphenated versions.

## Benefits of Consolidation

- Eliminates code duplication
- Simplifies maintenance as changes only need to be made in one place
- Provides a cleaner, more consistent project structure
- Reduces confusion for new developers