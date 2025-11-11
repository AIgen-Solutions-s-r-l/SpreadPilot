# Manual Testing Checklist: Frontend Authentication (Issue #59)

**Feature:** Frontend Authentication Implementation
**Date:** 2025-11-11
**Tester:** [To be completed during testing]
**Environment:** Development (local)

## Prerequisites

- [ ] Admin API is running on port 8083
- [ ] Environment variables configured:
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD_HASH`
  - `JWT_SECRET`
- [ ] Frontend build successful (`npm run build`)
- [ ] Frontend dev server running (`npm run dev`)

## Test Scenarios

### 1. Fresh Login (No Stored Token)

**Steps:**
1. Clear browser localStorage (DevTools > Application > Local Storage > Clear All)
2. Navigate to `http://localhost:5173` (or configured port)
3. Verify redirect to `/login` page
4. Enter valid credentials:
   - Username: [from ADMIN_USERNAME env var]
   - Password: [from admin account]
5. Click "Login" button

**Expected Results:**
- [ ] Loading state shows ("Logging in...")
- [ ] No console errors
- [ ] Redirect to dashboard (`/`)
- [ ] Token stored in localStorage (key: `authToken`)
- [ ] User information displayed in header/navbar
- [ ] Backend logs show successful login

**Actual Results:**
```
[To be filled during testing]
```

---

### 2. Invalid Credentials

**Steps:**
1. Clear localStorage
2. Navigate to `/login`
3. Enter invalid credentials:
   - Username: `wronguser`
   - Password: `wrongpass`
4. Click "Login" button

**Expected Results:**
- [ ] Loading state shows briefly
- [ ] Error message displays: "Login failed. Please check your credentials."
- [ ] User remains on login page
- [ ] No token stored in localStorage
- [ ] Backend logs show failed login attempt with username

**Actual Results:**
```
[To be filled during testing]
```

---

### 3. Empty Form Validation

**Steps:**
1. Navigate to `/login`
2. Leave username field empty
3. Enter password
4. Click "Login" button

**Expected Results:**
- [ ] Error message: "Please enter both username and password."
- [ ] No API call made (check Network tab)
- [ ] User remains on login page

**Actual Results:**
```
[To be filled during testing]
```

**Steps (2):**
1. Enter username
2. Leave password field empty
3. Click "Login" button

**Expected Results:**
- [ ] Same validation error appears

**Actual Results:**
```
[To be filled during testing]
```

---

### 4. Token Persistence (Page Reload)

**Steps:**
1. Login with valid credentials
2. Verify dashboard loads
3. Refresh the page (F5 or Cmd+R)

**Expected Results:**
- [ ] User remains authenticated
- [ ] Dashboard loads without redirect to login
- [ ] User information still displayed
- [ ] Token still present in localStorage

**Actual Results:**
```
[To be filled during testing]
```

---

### 5. Logout Functionality

**Steps:**
1. Login with valid credentials
2. Navigate to dashboard
3. Click logout button/link

**Expected Results:**
- [ ] Token removed from localStorage
- [ ] User redirected to `/login`
- [ ] User information cleared from UI
- [ ] Accessing protected routes redirects to login

**Actual Results:**
```
[To be filled during testing]
```

---

### 6. Expired/Invalid Token Handling

**Steps:**
1. Login with valid credentials
2. Open DevTools > Application > Local Storage
3. Manually corrupt the token (change a few characters)
4. Refresh the page

**Expected Results:**
- [ ] Token validation fails
- [ ] Token removed from localStorage
- [ ] User redirected to `/login`
- [ ] No console errors (graceful handling)

**Actual Results:**
```
[To be filled during testing]
```

---

### 7. Protected Route Access (Unauthorized)

**Steps:**
1. Clear localStorage (logout)
2. Manually navigate to `http://localhost:5173/` (dashboard)

**Expected Results:**
- [ ] Automatic redirect to `/login`
- [ ] Login page displays

**Actual Results:**
```
[To be filled during testing]
```

---

### 8. API Request Authorization

**Steps:**
1. Login with valid credentials
2. Open DevTools > Network tab
3. Navigate to any page that makes API calls (e.g., Followers page)
4. Inspect API request headers

**Expected Results:**
- [ ] All API requests include `Authorization: Bearer <token>` header
- [ ] Token matches the one in localStorage
- [ ] API responses are successful (200/201)

**Actual Results:**
```
[To be filled during testing]
```

---

### 9. 401 Unauthorized Auto-Logout

**Steps:**
1. Login with valid credentials
2. Wait for token to expire (24 hours - can be tested by manually expiring on backend)
   - Alternative: Temporarily reduce JWT_EXPIRATION_MINUTES on backend to 1 minute
3. Make an API call (navigate to Followers page)

**Expected Results:**
- [ ] API returns 401 Unauthorized
- [ ] Axios interceptor catches error
- [ ] Token removed from localStorage
- [ ] User redirected to `/login`
- [ ] Error message displayed (optional)

**Actual Results:**
```
[To be filled during testing]
```

---

### 10. Network Error Handling

**Steps:**
1. Stop the Admin API backend
2. Attempt to login

**Expected Results:**
- [ ] Error message displays: "Login failed. Please check your credentials." (or network error)
- [ ] No console crashes
- [ ] User can retry after backend restarts

**Actual Results:**
```
[To be filled during testing]
```

---

## Browser Compatibility Testing

Test the above scenarios on:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

## Performance Checks

- [ ] Initial page load < 3 seconds
- [ ] Login response time < 1 second (with fast backend)
- [ ] No memory leaks (check DevTools > Memory)
- [ ] No excessive re-renders (React DevTools Profiler)

## Security Checks

- [ ] Password field type="password" (masked input)
- [ ] Token not logged to console in production build
- [ ] No sensitive data in URL parameters
- [ ] HTTPS enforced in production (environment check)

## Acceptance Criteria Validation

From Issue #59:

- [ ] ✅ Users can log in with username and password
- [ ] ✅ JWT token is stored securely (localStorage)
- [ ] ✅ Token is sent with all API requests
- [ ] ✅ Token is validated on app initialization
- [ ] ✅ Login errors are displayed to users
- [ ] ✅ Session persists across page reloads
- [ ] ✅ Logout clears session properly
- [ ] ⚠️ Integration tests added (Technical Debt - requires test infrastructure)

## Issues Found

| # | Severity | Description | Steps to Reproduce | Status |
|---|----------|-------------|-------------------|--------|
| 1 |          |             |                   |        |
| 2 |          |             |                   |        |

## Notes

```
[Additional observations, edge cases discovered, or recommendations]
```

## Sign-off

- [ ] All critical scenarios pass
- [ ] No blocking issues
- [ ] Known issues documented
- [ ] Ready for code review

**Tester Signature:** ___________________
**Date:** ___________________
