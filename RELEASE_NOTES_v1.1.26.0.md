# SpreadPilot v1.1.26.0 Release Notes

## 🚀 Release Overview

This release focuses on improving the CI/CD pipeline performance and completing all integration tests by removing placeholders and xfail markers.

## ✨ Key Features

### CI/CD Pipeline Enhancements
- **Docker Layer Caching**: Implemented buildx caching for significantly faster Docker builds
- **Parallel Builds**: E2E test images now build in parallel for improved performance
- **Improved Reliability**: Added 15-minute timeout for E2E tests and automatic cleanup
- **Better Caching**: Added pip package caching to integration tests job

### Integration Testing Improvements
- **Position Update Testing**: New `test_position_update_existing()` function for testing updates to existing positions
- **Time Value Monitor Tests**: Comprehensive integration tests for TV monitor alert paths
  - Critical alert publishing when Time Value ≤ $0.10
  - Risk alert publishing when $0.10 < Time Value ≤ $1.00
  - Complete Redis stream integration
  - Error handling and alert publishing
- **Async Test Fixes**: Fixed async mocking in monthly P&L calculations
- **API Test Updates**: Updated dashboard API tests to match actual response structure

## 🐛 Bug Fixes

- Fixed import error in admin-api health endpoint (`get_database` → `get_db`)
- Removed `@pytest.mark.skip` decorator from monthly P&L test
- Replaced placeholder assertions with proper test implementations
- Fixed async cursor mocking for MongoDB aggregation tests

## 📋 Technical Details

### Files Changed
- `.github/workflows/ci.yml`: CI pipeline optimizations
- `.github/workflows/README.md`: New CI/CD documentation
- `tests/integration/test_assignment_flow.py`: Added position update test
- `tests/integration/test_reporting_flow.py`: Fixed async mocking
- `tests/integration/test_admin_api_dashboard.py`: Updated assertions
- `tests/integration/test_time_value_monitor_alerts.py`: New comprehensive TV monitor tests
- `admin-api/app/api/v1/endpoints/health.py`: Fixed import error

### Dependencies
No new dependencies added in this release.

## 🔄 Migration Notes

No breaking changes. This release is fully backward compatible.

## 📝 Commit History

- `09d7b98` chore(release): v1.1.26.0
- `2a13dea` fix: Correct import error in health endpoint
- `6dbbc2a` feat(TST-β7): Complete all xfail and placeholder tests
- `abc9086` feat(CI-β6): Enhance CI pipeline with optimizations

## 🏷️ Version

- Previous: v1.1.25.0
- Current: v1.1.26.0

---

*Released on: 2025-06-29*