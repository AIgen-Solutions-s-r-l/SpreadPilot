# Phase 1: Discover & Frame - Issue #60

**Issue**: Review and Complete Original Strategy Handler
**Priority**: CRITICAL (if actively used)
**Date**: 2025-11-11
**Protocol**: LIFECYCLE-ORCHESTRATOR-ENHANCED-PROTO.yaml

---

## Problem Statement

The `OriginalStrategyHandler` contains 7 TODO comments indicating incomplete implementation:

1. **Line 57**: Fetch dedicated IBKR credentials using vault
2. **Line 169**: Implement trading hours check
3. **Line 172**: Implement bar timing logic (5-min bar close)
4. **Line 175**: Fetch latest bar data
5. **Line 183**: Implement EOD check
6. **Lines 303, 345**: Track stop orders (2 occurrences)

## Investigation Results

### Active Usage Analysis

**CRITICAL FINDING**: The handler is **NOT actively used in production**.

#### Evidence:

1. **Configuration Status**
   `trading-bot/app/config.py:220`
   ```python
   ORIGINAL_EMA_STRATEGY = {
       "enabled": False,  # Disabled in favor of Vertical Spreads Strategy
       # ... rest of config
   }
   ```

2. **Code Invocation**
   - Handler instantiated: `trading-bot/app/service/base.py:86`
   ```python
   self.original_strategy_handler = OriginalStrategyHandler(self, ORIGINAL_EMA_STRATEGY)
   ```
   - **Never initialized**: No calls to `.initialize()`
   - **Never executed**: No calls to `.run()`

3. **Active Strategy**
   Only the `VerticalSpreadsStrategyHandler` is invoked:
   ```python
   # Line 170-172 in base.py
   vertical_spreads_task = asyncio.create_task(
       self.vertical_spreads_strategy_handler.run(shutdown_event)
   )
   ```

### Impact Assessment

**Current Impact**: **NONE** - Handler is not used in production

**Risk of Keeping**:
- **Technical Debt**: 481 lines of incomplete code
- **Maintenance Burden**: Code must be maintained despite not being used
- **Confusion**: New developers may think this is active
- **Test Coverage**: Tests exist but test unused code
- **Documentation Overhead**: Must document unused functionality

**Risk of Removing**:
- **LOW**: No active usage, configuration disabled
- **Reversible**: Code is in git history if ever needed
- **Clear Intent**: "Disabled in favor of Vertical Spreads Strategy"

## Success Metrics

- ✅ **Determined Active Usage**: Confirmed NOT actively used
- ✅ **Configuration Analysis**: `enabled: False` in config
- ✅ **Code Flow Analysis**: Handler never invoked
- ✅ **Risk Assessment**: Low risk removal
- ✅ **Impact Analysis**: Zero impact on production

## Recommended Path

### **Option B: Remove Deprecated Handler**

**Rationale**:
1. Handler explicitly disabled in configuration
2. Never invoked in production code
3. Incomplete implementation (7 TODOs)
4. Active strategy (Vertical Spreads) is fully functional
5. Code preserved in git history if needed

**Benefits**:
- Reduces codebase complexity by ~600 lines (handler + tests + docs)
- Eliminates technical debt
- Improves code clarity
- Reduces maintenance burden
- Prevents confusion for new developers

**Effort**: 0.5 days (removal + testing + documentation)

## Technical Feasibility

### Removal Complexity: **LOW**

**Files to Remove**:
1. `trading-bot/app/service/original_strategy_handler.py` (481 lines)
2. `trading-bot/tests/unit/service/test_original_strategy_handler.py`
3. `trading-bot/tests/unit/service/test_original_strategy_handler_extended.py`
4. `trading-bot/tests/integration/test_original_strategy.py`
5. `trading-bot/tests/backtest/backtest_original_strategy.py`
6. `trading-bot/tests/config/original_strategy_test_config.py`
7. `docs/original_strategy_paper_testing_plan.md`

**Files to Modify**:
1. `trading-bot/app/service/base.py` (remove import and instantiation)
2. `trading-bot/app/config.py` (remove ORIGINAL_EMA_STRATEGY config)
3. `docs/issues-overview.md` (mark issue as resolved)
4. `CHANGELOG.md` (document removal)

**Dependencies**: NONE - No other code depends on this handler

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Code needed in future | LOW | LOW | Available in git history |
| Breaking other code | NONE | NONE | No dependencies found |
| Test failures | NONE | NONE | Only tests for removed code |
| Production impact | NONE | NONE | Handler not invoked |

## Architectural Constraints

**Design Principle Alignment**:
- ✅ **Simplicity over complexity**: Removing unused code reduces complexity
- ✅ **Evolutionary architecture**: Dead code removal is good hygiene
- ✅ **Maintainability**: Reduces maintenance burden

**No ADR Required**:
- This is a straightforward dead code removal
- No architectural decision being made
- No new patterns introduced
- Reverting to simpler state

## Quality Gates Status

- ✅ **Problem statement validated**: Clear scope, bounded removal
- ✅ **Technical feasibility confirmed**: No blockers, low risk
- ✅ **ADR not required**: Simple dead code removal

## Next Phase

**Recommendation**: Proceed to **Phase 2: Design the Solution**

**Scope for Phase 2**:
1. Document removal strategy (HLD)
2. List all affected files
3. Plan test strategy
4. Define rollback plan
5. Create migration notes

---

**Tech Lead Sign-off**: ✅ APPROVED
**Go/Hold Decision**: **GO** - Proceed to Phase 2

**Phase 1 Deliverables**:
- ✅ Problem statement validated
- ✅ Active usage determined (NOT USED)
- ✅ Technical feasibility confirmed (LOW RISK)
- ✅ Risk assessment complete
- ✅ Recommendation documented (REMOVE)

**Phase Completion**: 2025-11-11
