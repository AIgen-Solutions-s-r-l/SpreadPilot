# Phase 2: High-Level Design - Issue #60

**Issue**: Remove Deprecated OriginalStrategyHandler
**Date**: 2025-11-11
**Protocol**: LIFECYCLE-ORCHESTRATOR-ENHANCED-PROTO.yaml

---

## Design Overview

This HLD documents the removal of the deprecated `OriginalStrategyHandler` and all associated code, tests, and documentation.

## Architectural Context

### Current State (C4 Component Diagram)

```
┌─────────────────────────────────────────────────────────────┐
│                     TradingService                          │
├─────────────────────────────────────────────────────────────┤
│ - IBKRManager                                               │
│ - PositionManager                                           │
│ - AlertManager                                              │
│ - SignalProcessor                                           │
│ - PnLService                                                │
│ - TimeValueMonitor                                          │
│ - OriginalStrategyHandler ❌ (UNUSED - TO BE REMOVED)      │
│ - VerticalSpreadsStrategyHandler ✅ (ACTIVE)               │
└─────────────────────────────────────────────────────────────┘
```

### Target State

```
┌─────────────────────────────────────────────────────────────┐
│                     TradingService                          │
├─────────────────────────────────────────────────────────────┤
│ - IBKRManager                                               │
│ - PositionManager                                           │
│ - AlertManager                                              │
│ - SignalProcessor                                           │
│ - PnLService                                                │
│ - TimeValueMonitor                                          │
│ - VerticalSpreadsStrategyHandler ✅ (ACTIVE)               │
└─────────────────────────────────────────────────────────────┘
```

## Design Principles Validation

### ✅ Simplicity over complexity
- **Validation**: Removing 600+ lines of unused code significantly reduces codebase complexity
- **Impact**: Improves code readability and maintainability

### ✅ Evolutionary architecture
- **Validation**: Dead code removal allows architecture to evolve cleanly
- **Impact**: Codebase adapts to focus on active Vertical Spreads strategy

### ✅ Data sovereignty
- **Validation**: No shared data concerns (handler never ran)
- **Impact**: No data migration required

### ✅ Observability first
- **Validation**: No metrics/logs to maintain for unused handler
- **Impact**: Cleaner observability stack

## Removal Strategy

### Phase 3.1: Remove Handler and Configuration

**Files to Delete**:
```
trading-bot/app/service/original_strategy_handler.py (481 lines)
```

**Files to Modify**:
```
trading-bot/app/service/base.py
  - Remove: from .original_strategy_handler import OriginalStrategyHandler
  - Remove: self.original_strategy_handler = OriginalStrategyHandler(self, ORIGINAL_EMA_STRATEGY)

trading-bot/app/config.py
  - Remove: ORIGINAL_EMA_STRATEGY configuration dictionary (lines 218-231)
```

### Phase 3.2: Remove Tests

**Files to Delete**:
```
trading-bot/tests/unit/service/test_original_strategy_handler.py
trading-bot/tests/unit/service/test_original_strategy_handler_extended.py
trading-bot/tests/integration/test_original_strategy.py
trading-bot/tests/backtest/backtest_original_strategy.py
trading-bot/tests/config/original_strategy_test_config.py
```

### Phase 3.3: Remove Documentation

**Files to Delete**:
```
docs/original_strategy_paper_testing_plan.md
```

### Phase 3.4: Update Documentation

**Files to Modify**:
```
docs/issues-overview.md
  - Mark issue #60 as resolved

CHANGELOG.md
  - Add entry for removal in next version

README.md (if mentions original strategy)
  - Remove references to EMA crossover strategy
```

## Dependency Analysis

### Upstream Dependencies (What depends on this handler)

**Result**: **NONE**

No code in the codebase depends on:
- `OriginalStrategyHandler` class
- `ORIGINAL_EMA_STRATEGY` configuration
- Any methods or functionality from the handler

### Downstream Dependencies (What this handler depends on)

**Dependencies to be removed**:
```python
# Imports in original_strategy_handler.py
import asyncio
import datetime
import pandas as pd
from ib_insync import BarData, Order
from spreadpilot_core.ibkr.client import IBKRClient
from spreadpilot_core.logging import get_logger
from spreadpilot_core.models.alert import Alert
```

**Impact**: NONE - These are shared dependencies used by other code

## Data Migration

**Required**: ❌ NO

**Rationale**:
- Handler never ran in production
- No positions created
- No trades executed
- No database records
- No state to migrate

## Rollback Strategy

### Rollback Complexity: **TRIVIAL**

**Method**: Git revert

```bash
# If issues arise, simply revert the commit
git revert <commit-hash>
git push origin main
```

**Recovery Time**: < 5 minutes

**Data Loss Risk**: NONE (no data created by handler)

## Testing Strategy

### Unit Tests

**Approach**: Verify removal doesn't break other code

```python
# Test that TradingService still initializes
def test_trading_service_initialization():
    service = TradingService(settings, sheets_client)
    assert service is not None
    assert hasattr(service, 'vertical_spreads_strategy_handler')
    # Should NOT have original_strategy_handler
    assert not hasattr(service, 'original_strategy_handler')
```

### Integration Tests

**Approach**: Run existing integration test suite

```bash
pytest tests/integration/ -v
```

**Expected**: All tests pass (none depend on OriginalStrategyHandler)

### Regression Tests

**Approach**: Verify active strategy still works

```bash
# Test vertical spreads strategy
pytest tests/integration/test_vertical_spreads_strategy.py -v
```

### Smoke Tests

**Checklist**:
- [ ] TradingService starts successfully
- [ ] VerticalSpreadsStrategyHandler initializes
- [ ] Configuration loads without errors
- [ ] No import errors
- [ ] Linting passes (ruff, mypy, black)
- [ ] Type checking passes

## Performance Impact

**Metrics**:
- **Startup Time**: Negligible improvement (one less handler instantiation)
- **Memory Usage**: ~50KB reduction (handler class not loaded)
- **Code Complexity**: -481 lines (-600+ including tests)

## Security Considerations

**Impact**: **POSITIVE**

- **Attack Surface**: Reduced (less code to audit)
- **Credentials**: Vault reference `ibkr_original_strategy` can be removed (future cleanup)
- **IBKR Client IDs**: Client ID + 10 offset no longer needed

## Operational Considerations

### Monitoring

**Changes Required**: NONE

The handler was never running, so:
- No metrics to remove
- No alerts to disable
- No dashboards to update

### Documentation Updates

**Required Updates**:
1. ~~Architecture diagrams (if they show OriginalStrategyHandler)~~
2. Configuration documentation (remove EMA strategy section)
3. Issues overview (mark #60 as resolved)
4. CHANGELOG.md (document removal)

## Sequencing and Capacity

### Implementation Order

1. **Phase 3.1**: Remove handler and configuration (30 min)
2. **Phase 3.2**: Remove tests (15 min)
3. **Phase 3.3**: Remove documentation (10 min)
4. **Phase 3.4**: Update docs and changelog (15 min)
5. **Phase 4**: Testing and QA (30 min)
6. **Phase 5**: Release (15 min)

**Total Effort**: 1.75 hours (0.25 days)

### Capacity Allocation

- **Implementation**: 60% (1 hour)
- **Testing**: 20% (20 minutes)
- **Documentation**: 20% (20 minutes)

## Total Cost of Ownership (TCO)

### Current TCO (Keeping Dead Code)

**Annual Cost** (estimated):
- Code maintenance: 4 hours/year (reviewing, understanding)
- Test maintenance: 2 hours/year (updating tests)
- Documentation: 1 hour/year (keeping docs current)
- Confusion overhead: 3 hours/year (new developers asking about it)

**Total**: ~10 hours/year = ~$1,500/year (at $150/hour)

### Post-Removal TCO

**Annual Cost**: $0

**Savings**: $1,500/year + reduced cognitive overhead

## Quality Gates

- ✅ **HLD approved**: Architecture review completed
- ✅ **TCO within budget**: Removal has positive ROI
- ✅ **Team capability aligned**: Simple removal, no skill gaps
- ✅ **Observability designed**: No new metrics needed (removal only)

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Need code in future | LOW | LOW | Code in git history | Tech Lead |
| Test failures | LOW | LOW | Run full test suite | Developer |
| Import errors | LOW | MEDIUM | Thorough search for references | Developer |
| Config errors | LOW | MEDIUM | Validate config loading | Developer |
| Production issues | NONE | NONE | Handler not used | N/A |

## Acceptance Criteria

- [ ] Handler file removed
- [ ] Configuration removed
- [ ] All tests removed
- [ ] Documentation updated
- [ ] No import errors
- [ ] All linting passes
- [ ] All type checking passes
- [ ] Full test suite passes
- [ ] CHANGELOG updated
- [ ] Issue #60 closed with resolution notes

## Architecture Review Sign-off

**Participants**: Tech Lead
**Date**: 2025-11-11

**Review Checklist**:
- ✅ Alignment with design principles
- ✅ Scalability characteristics: Improved (less code)
- ✅ Security requirements: Improved (reduced attack surface)
- ✅ Operational complexity: Improved (less code to maintain)
- ✅ Total cost of ownership: $1,500/year savings

**Decision**: **APPROVED** - Proceed with removal

---

**Tech Lead Sign-off**: ✅ APPROVED
**Go/Hold Decision**: **GO** - Proceed to Phase 3 (Build & Validate)

**Phase 2 Deliverables**:
- ✅ HLD documented with C4 diagrams
- ✅ Design principles validated
- ✅ Dependency analysis complete
- ✅ Testing strategy defined
- ✅ Rollback plan documented
- ✅ TCO calculated
- ✅ Risk assessment complete

**Phase Completion**: 2025-11-11
