# Repository Cleanup Plan

## Analysis Summary
- **11,790** temporary/cache files found
- **1,269** `__pycache__` directories
- **50MB** in potentially duplicate `admin-dashboard` directory
- Multiple virtual environments (`venv` and `.venv`)
- Various cache and temporary directories

## Proposed Cleanup

### 1. Python Cache Files (High Priority)
- Remove all `__pycache__` directories (1,269 directories)
- Remove all `.pyc`, `.pyo` files
- **Space saved**: ~100MB+

### 2. Virtual Environments
- Remove old `venv/` directory (using `.venv/` now)
- **Space saved**: ~200MB+

### 3. Cache Directories
- `.pytest_cache/` - Pytest cache
- `.ruff_cache/` - Ruff linter cache
- **Space saved**: ~10MB

### 4. Potentially Obsolete Directories
- `admin-dashboard/` - Appears to be old version (we use `frontend/` now)
  - Contains node_modules (50MB)
  - Has its own package.json
- `src/` - Only contains a theme folder, might be obsolete
- **Space saved**: ~50MB

### 5. Project Management Directories (Low Priority)
- `.claude/` - Old Claude-related files
- `.decisions/` - Old decision logs
- `.planning/` - Old planning docs
- `.tasks/` - Old task files
- **Space saved**: ~100KB

### 6. Build Artifacts
- `frontend/dist/` - Build output (can be regenerated)
- **Space saved**: ~5MB

### 7. Documentation Cleanup
- Old release summaries (keep only latest)
- Duplicate or outdated docs
- **Space saved**: ~1MB

### 8. Empty Directories
- `trading-bot/app/services/`
- `admin-dashboard/src/assets/`
- Various empty test directories

## Files to Keep
- All source code
- Configuration files
- Current documentation
- `.git/` directory
- `credentials/` (contains important configs)
- Active virtual environment (`.venv/`)

## Estimated Total Space Savings
**~366MB+**

## Recommended .gitignore Updates
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
ENV/
env/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
coverage.xml
*.cover

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# Build artifacts
dist/
build/
*.log

# Project specific
.claude/
.decisions/
.planning/
.tasks/
admin-dashboard/
```

## Execution Commands
```bash
# 1. Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -o -name "*.pyo" -exec rm -f {} +

# 2. Remove old virtual environment
rm -rf venv/

# 3. Remove cache directories
rm -rf .pytest_cache/ .ruff_cache/

# 4. Remove obsolete directories (after confirmation)
rm -rf admin-dashboard/
rm -rf src/

# 5. Remove project management dirs
rm -rf .claude/ .decisions/ .planning/ .tasks/

# 6. Remove build artifacts
rm -rf frontend/dist/

# 7. Remove empty directories
find . -type d -empty -delete 2>/dev/null
```

## Safety Notes
- All proposed deletions are for generated/cached files
- Source code will not be affected
- Can regenerate build artifacts anytime
- Virtual environment can be recreated with pip install