# Technical Debt: Frontend Test Infrastructure

**Created:** 2025-11-11
**Priority:** HIGH
**Category:** Quality / Testing
**Estimated Effort:** 1-2 days

## Problem Statement

The frontend application currently lacks a testing infrastructure (no test runner, no testing libraries). This prevents:
- Unit testing of services and utilities
- Integration testing of React components
- Regression testing for UI changes
- Automated quality gates in CI/CD

## Current Impact

- **Code Quality:** No automated validation of component logic
- **Regression Risk:** Changes may break existing functionality without detection
- **Development Speed:** Manual testing is time-consuming and error-prone
- **CI/CD Pipeline:** Cannot enforce quality gates (coverage thresholds)

## Proposed Solution

Set up comprehensive testing infrastructure for the React/TypeScript frontend:

### 1. Test Runner & Framework
- **Vitest**: Fast, Vite-native test runner (recommended for Vite projects)
- Alternative: Jest (more mature ecosystem)

### 2. Testing Libraries
- `@testing-library/react`: Component testing
- `@testing-library/user-event`: User interaction simulation
- `@testing-library/jest-dom`: Custom matchers
- `vitest-fetch-mock` or `msw`: API mocking

### 3. Coverage Requirements
Per TECH-LEAD-PROTO.yaml standards:
- Line coverage: >= 90%
- Branch coverage: >= 80%
- Automated gate: BLOCK merge if below threshold

### 4. Test Structure
```
frontend/
├── src/
│   ├── services/
│   │   ├── authService.ts
│   │   └── __tests__/
│   │       └── authService.test.ts
│   ├── contexts/
│   │   ├── AuthContext.tsx
│   │   └── __tests__/
│   │       └── AuthContext.test.tsx
│   └── pages/
│       ├── LoginPage.tsx
│       └── __tests__/
│           └── LoginPage.test.tsx
└── vitest.config.ts
```

### 5. Implementation Steps
1. Install dependencies: `npm install -D vitest @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom`
2. Create `vitest.config.ts` configuration
3. Add test scripts to `package.json`
4. Write tests for existing code (authService, AuthContext, LoginPage)
5. Set up coverage thresholds
6. Integrate with CI/CD pipeline

## Priority Tests Needed

Once infrastructure is in place, these tests should be created:

### authService.test.ts (CRITICAL)
- ✅ login() - successful authentication
- ✅ login() - invalid credentials (401)
- ✅ login() - network error
- ✅ getCurrentUser() - valid token
- ✅ getCurrentUser() - invalid token
- ✅ validateToken() - valid/invalid scenarios
- ✅ logout() - clears token
- ✅ Token storage in localStorage

### AuthContext.test.tsx (HIGH)
- ✅ Initialization with valid stored token
- ✅ Initialization with invalid stored token
- ✅ Initialization with no token
- ✅ Login flow updates state correctly
- ✅ Login failure handling
- ✅ Logout clears state

### LoginPage.test.tsx (MEDIUM)
- ✅ Form submission with valid credentials
- ✅ Form validation (empty fields)
- ✅ Error message display
- ✅ Loading state during login
- ✅ Navigation after successful login

## Related Issues

- Issue #59: Frontend authentication implementation (completed without tests)
- Future: E2E testing with Playwright/Cypress

## Acceptance Criteria

- [ ] Vitest configured and running
- [ ] All critical tests implemented
- [ ] Coverage >= 90% lines, >= 80% branches
- [ ] npm test command runs all tests
- [ ] npm run test:coverage generates report
- [ ] CI/CD pipeline fails on coverage violations
- [ ] Documentation updated in CLAUDE.md

## Effort Breakdown

- Setup Vitest: 2 hours
- Write authService tests: 2 hours
- Write AuthContext tests: 2 hours
- Write LoginPage tests: 1 hour
- Configure coverage + CI: 1 hour
- **Total: 8 hours (1 day)**

## Next Steps

1. Create GitHub issue for test infrastructure setup
2. Prioritize in next sprint planning
3. Allocate 20% of sprint capacity per TECH-LEAD-PROTO.yaml
4. Track debt ratio to ensure reduction trend

## References

- TECH-LEAD-PROTO.yaml: codeQuality.standards.metrics
- DEV-PROTO.yaml: TDD approach (RED-GREEN-REFACTOR)
- LIFECYCLE-ORCHESTRATOR-PROTO.yaml: Phase 3 quality gates
